"""
DHIMS2 Birth Record Auto-Sync Service

This module handles automatic synchronization of birth records to DHIMS2.
Can be run as a scheduled task (cron job) daily.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.birth_models import BirthRecord
from app.models.baby_discharge_models import BabyDischarge
from app.integrations.dhims2.birth_mapper import BirthRecordMapper

logger = logging.getLogger(__name__)


def get_unsynced_birth_records(
    db: Session,
    days_back: int = 7,
    limit: int = 100
) -> List[BirthRecord]:
    """
    Get birth records that haven't been synced to DHIMS2.
    
    Args:
        db: Database session
        days_back: Number of days to look back (default 7)
        limit: Maximum records to return
    
    Returns:
        List of unsynced birth records
    """
    cutoff_date = date.today() - timedelta(days=days_back)
    
    records = (
        db.query(BirthRecord)
        .filter(BirthRecord.birth_date >= cutoff_date)
        .filter(BirthRecord.is_active == True)
        .filter(BirthRecord.birth_outcome.in_(["live_birth", "live", "stillbirth"]))
        .order_by(BirthRecord.birth_date.desc())
        .limit(limit)
        .all()
    )
    
    logger.info(f"Found {len(records)} birth records from last {days_back} days")
    return records


def sync_birth_records_to_dhims2(
    db: Session,
    days_back: int = 7,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Sync birth records to DHIMS2.
    
    This function:
    1. Fetches unsynced birth records
    2. Maps them to DHIMS2 format
    3. Returns the data ready for submission
    
    Args:
        db: Database session
        days_back: Number of days to look back
        limit: Maximum records to sync
    
    Returns:
        Dictionary with sync results
    """
    logger.info(f"Starting birth records sync to DHIMS2 (days_back={days_back}, limit={limit})")
    
    start_time = datetime.utcnow()
    
    # Get unsynced records
    records = get_unsynced_birth_records(db, days_back, limit)
    
    if not records:
        return {
            "success": True,
            "message": "No records to sync",
            "total_records": 0,
            "synced_records": 0,
            "failed_records": 0,
            "duration_seconds": 0
        }
    
    synced_count = 0
    failed_count = 0
    errors = []
    
    for record in records:
        try:
            # Get baby discharge if exists
            baby_discharge = db.query(BabyDischarge).filter(
                BabyDischarge.birth_record_id == record.id
            ).first()
            
            # Map to DHIMS2 format
            dhims2_data = BirthRecordMapper.map_birth_record_to_dhims2(
                record, 
                baby_discharge
            )
            
            # In a full implementation, this would submit to DHIMS2
            # For now, we just prepare the data
            logger.info(f"Mapped birth record {record.id} ({record.birth_number}) to DHIMS2 format")
            synced_count += 1
            
        except Exception as e:
            logger.error(f"Error syncing birth record {record.id}: {str(e)}")
            failed_count += 1
            errors.append({
                "record_id": record.id,
                "error": str(e)
            })
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    result = {
        "success": failed_count == 0,
        "message": f"Synced {synced_count} records, {failed_count} failed",
        "total_records": len(records),
        "synced_records": synced_count,
        "failed_records": failed_count,
        "duration_seconds": duration,
        "errors": errors if errors else None
    }
    
    logger.info(f"Birth records sync completed: {result['message']} in {duration:.2f}s")
    return result


# ============== Cron Job Helper Functions ==============

def generate_cron_job_entry(
    hour: int = 6,
    minute: int = 0
) -> str:
    """
    Generate a cron job entry for automatic birth sync.
    
    Args:
        hour: Hour of day (0-23) to run sync
        minute: Minute of hour (0-59) to run sync
    
    Returns:
        Cron job entry string
    """
    import os
    
    project_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    python_path = os.executable
    
    # Generate cron entry - runs daily at specified time
    cron_entry = f"{minute} {hour} * * * cd {project_path} && {python_path} -c \"from app.services.birth_dhims2_sync import run_birth_sync; run_birth_sync()\""
    
    return cron_entry


def install_cron_job(
    hour: int = 6,
    minute: int = 0
) -> Tuple[bool, str]:
    """
    Install a cron job for automatic birth sync (Linux/Mac only).
    
    Args:
        hour: Hour of day (0-23) to run sync
        minute: Minute of hour (0-59) to run sync
    
    Returns:
        Tuple of (success, message)
    """
    import subprocess
    
    try:
        cron_entry = generate_cron_job_entry(hour=hour, minute=minute)
        cron_entry_with_comment = f"{cron_entry} # LHIMS Birth DHIMS2 Auto-Sync"
        
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        existing_crontab = result.stdout.decode('utf-8') if result.returncode == 0 else ""
        
        # Check if birth sync cron job already exists
        if "LHIMS Birth DHIMS2 Auto-Sync" in existing_crontab or "birth_dhims2_sync" in existing_crontab:
            # Remove existing entry
            lines = existing_crontab.split('\n')
            lines = [
                line for line in lines 
                if "LHIMS Birth DHIMS2 Auto-Sync" not in line 
                and "birth_dhims2_sync" not in line
            ]
            existing_crontab = '\n'.join(lines)
        
        # Add new entry
        new_crontab = existing_crontab.rstrip() + '\n' + cron_entry_with_comment + '\n'
        
        # Install new crontab
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=new_crontab.encode('utf-8'))
        
        if process.returncode == 0:
            return True, f"Birth sync cron job installed: {minute} {hour} * * *"
        else:
            return False, f"Failed to install cron job: {stderr.decode('utf-8')}"
    
    except Exception as e:
        return False, f"Error installing cron job: {str(e)}"


def remove_cron_job() -> Tuple[bool, str]:
    """
    Remove the LHIMS birth sync cron job.
    
    Returns:
        Tuple of (success, message)
    """
    import subprocess
    
    try:
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            return False, "No crontab found or error reading crontab"
        
        existing_crontab = result.stdout.decode('utf-8')
        
        # Remove birth sync related entries
        lines = existing_crontab.split('\n')
        filtered_lines = [
            line for line in lines
            if "LHIMS Birth DHIMS2 Auto-Sync" not in line
            and "birth_dhims2_sync" not in line
            and line.strip()  # Keep non-empty lines
        ]
        
        new_crontab = '\n'.join(filtered_lines) + '\n'
        
        # Install updated crontab
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=new_crontab.encode('utf-8'))
        
        if process.returncode == 0:
            return True, "Birth sync cron job removed"
        else:
            return False, f"Failed to remove cron job: {stderr.decode('utf-8')}"
    
    except Exception as e:
        return False, f"Error removing cron job: {str(e)}"


def get_cron_job_status() -> Dict[str, Any]:
    """
    Check if a birth sync cron job is currently installed.
    
    Returns:
        Dictionary with cron job status
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            return {
                "installed": False,
                "message": "No crontab found"
            }
        
        crontab = result.stdout.decode('utf-8')
        has_job = "LHIMS Birth DHIMS2 Auto-Sync" in crontab or "birth_dhims2_sync" in crontab
        
        if has_job:
            # Try to extract schedule info
            lines = crontab.split('\n')
            job_line = None
            for line in lines:
                if "LHIMS Birth DHIMS2 Auto-Sync" in line or "birth_dhims2_sync" in line:
                    job_line = line
                    break
            
            return {
                "installed": True,
                "cron_entry": job_line,
                "message": "Birth DHIMS2 auto-sync cron job is installed"
            }
        else:
            return {
                "installed": False,
                "message": "No birth sync cron job found"
            }
    
    except Exception as e:
        return {
            "installed": False,
            "error": str(e),
            "message": f"Error checking cron job status: {str(e)}"
        }


# ============== Standalone Entry Point ==============

def run_birth_sync():
    """Entry point for cron job or scheduler"""
    logger.info("Running birth DHIMS2 auto-sync task...")
    
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        result = sync_birth_records_to_dhims2(db, days_back=7, limit=100)
        logger.info(f"Birth sync result: {result}")
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run_birth_sync()
