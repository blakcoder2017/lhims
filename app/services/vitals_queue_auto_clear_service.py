"""
Vitals Queue Auto-Clear Service
Automatically clears patients from vitals queue who have not had vitals recorded 
after 48 hours.
This service is designed to run via scheduler (hourly) or cron job.
"""
import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

from sqlalchemy.orm import Session, joinedload

from app.db.database import SessionLocal
from app.models.appointment_models import OPDQueue, QueueStatus
from app.models.triage_models import TriageVitals
from app.models.patient_models import Patient

logger = logging.getLogger(__name__)

# Configuration: Hours after which queue entries are considered stale
STALE_QUEUE_HOURS = 48


def auto_clear_stale_vitals_queue(db: Session = None, hours_threshold: int = None) -> Dict[str, Any]:
    """
    Automatically clear patients from vitals queue who have not had vitals recorded 
    after the specified threshold (default 48 hours).
    
    Rules:
    - Only clears queue entries with status WAITING or IN_PROGRESS
    - Only clears entries where no vitals were recorded after the queue entry was created
    - Sets status to NO_SHOW for audit tracking
    
    Args:
        db: Database session. If not provided, a new session will be created.
        hours_threshold: Hours after which to clear stale entries (default: STALE_QUEUE_HOURS)
        
    Returns:
        Dictionary with results: {
            "success": bool,
            "cleared_count": int,
            "entries": List of cleared entry details,
            "message": str
        }
    """
    if hours_threshold is None:
        hours_threshold = STALE_QUEUE_HOURS
    
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Calculate the threshold time
        threshold_time = datetime.now() - timedelta(hours=hours_threshold)
        
        # Find all active queue entries that are WAITING or IN_PROGRESS
        # and were created before the threshold
        stale_queue_entries = db.query(OPDQueue).options(
            joinedload(OPDQueue.patient)
        ).filter(
            OPDQueue.created_at < threshold_time,
            OPDQueue.status.in_([
                QueueStatus.WAITING.value,
                QueueStatus.IN_PROGRESS.value
            ]),
            OPDQueue.is_active == True
        ).all()
        
        cleared_entries = []
        
        for queue_entry in stale_queue_entries:
            # Check if any vitals were recorded for this patient after the queue entry was created
            vitals_recorded = db.query(TriageVitals).filter(
                TriageVitals.patient_id == queue_entry.patient_id,
                TriageVitals.recorded_at > queue_entry.created_at
            ).first()
            
            # If no vitals recorded after queue entry was created, mark as NO_SHOW
            if not vitals_recorded:
                patient = queue_entry.patient
                
                # Mark as NO_SHOW
                queue_entry.status = QueueStatus.NO_SHOW
                queue_entry.notes = (queue_entry.notes or "") + f" [Auto-cleared: No vitals recorded after {hours_threshold} hours]"
                
                cleared_entries.append({
                    "queue_id": queue_entry.id,
                    "patient_id": queue_entry.patient_id,
                    "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                    "patient_number": patient.patient_number if patient else "Unknown",
                    "created_at": queue_entry.created_at.isoformat() if queue_entry.created_at else None,
                    "status": queue_entry.status.value,
                    "department": queue_entry.department
                })
        
        # Commit all changes
        db.commit()
        
        return {
            "success": True,
            "cleared_count": len(cleared_entries),
            "entries": cleared_entries,
            "message": f"Cleared {len(cleared_entries)} stale vitals queue entries"
        }
        
    except Exception as e:
        logger.error(f"Error in auto_clear_stale_vitals_queue: {str(e)}")
        if db:
            db.rollback()
        return {
            "success": False,
            "cleared_count": 0,
            "entries": [],
            "message": f"Error: {str(e)}"
        }
    finally:
        if close_session and db:
            db.close()


# Standalone function for cron/scheduler execution
def run_vitals_queue_auto_clear():
    """Entry point for cron job or scheduler"""
    logger.info("Running vitals queue auto-clear task...")
    result = auto_clear_stale_vitals_queue()
    logger.info(f"Vitals queue auto-clear result: {result['message']}")
    return result


# Cron Job Helper Functions
def generate_cron_job_entry(
    hour: int = 1,
    minute: int = 30
) -> str:
    """
    Generate a cron job entry for automatic vitals queue auto-clear.
    
    Args:
        hour: Hour of day (0-23) to run the task
        minute: Minute of hour (0-59) to run the task
    
    Returns:
        Cron job entry string
    """
    # Get project path
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Go up to the parent directory (lhims)
    project_path = os.path.dirname(project_path)
    
    # Generate cron entry
    cron_entry = f"{minute} {hour} * * * cd {project_path} && python3 -c \"from app.services.vitals_queue_auto_clear_service import run_vitals_queue_auto_clear; run_vitals_queue_auto_clear()\""
    
    return cron_entry


def install_cron_job(
    hour: int = 1,
    minute: int = 30
) -> Tuple[bool, str]:
    """
    Install a cron job for automatic vitals queue auto-clear (Linux/Mac only).
    
    Args:
        hour: Hour of day (0-23) to run the task
        minute: Minute of hour (0-59) to run the task
    
    Returns:
        Tuple of (success, message)
    """
    try:
        cron_entry = generate_cron_job_entry(hour=hour, minute=minute)
        cron_entry_with_comment = f"{cron_entry} # LHIMS Vitals Queue Auto-Clear"
        
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        existing_crontab = result.stdout if result.returncode == 0 else ""
        
        # Check if vitals queue auto-clear cron job already exists
        if "LHIMS Vitals Queue Auto-Clear" in existing_crontab or "vitals_queue_auto_clear" in existing_crontab:
            # Remove existing entry
            lines = existing_crontab.split('\n')
            lines = [
                line for line in lines 
                if "LHIMS Vitals Queue Auto-Clear" not in line 
                and "vitals_queue_auto_clear" not in line
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
            return True, f"Vitals queue auto-clear cron job installed: {minute} {hour} * * *"
        else:
            return False, f"Failed to install cron job: {stderr.decode('utf-8')}"
        
    except Exception as e:
        return False, f"Error installing cron job: {str(e)}"


def remove_cron_job() -> Tuple[bool, str]:
    """
    Remove the LHIMS vitals queue auto-clear cron job.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            return False, "No crontab found or error reading crontab"
        
        existing_crontab = result.stdout
        
        # Remove vitals queue auto-clear related entries
        lines = existing_crontab.split('\n')
        filtered_lines = [
            line for line in lines
            if "LHIMS Vitals Queue Auto-Clear" not in line
            and "vitals_queue_auto_clear" not in line
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
            return True, "Vitals queue auto-clear cron job removed"
        else:
            return False, f"Failed to remove cron job: {stderr.decode('utf-8')}"
        
    except Exception as e:
        return False, f"Error removing cron job: {str(e)}"


def get_cron_job_status() -> Dict[str, Any]:
    """
    Check if a vitals queue auto-clear cron job is currently installed.
    
    Returns:
        Dictionary with cron job status
    """
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "installed": False,
                "message": "No crontab found"
            }
        
        crontab = result.stdout
        has_job = "LHIMS Vitals Queue Auto-Clear" in crontab or "vitals_queue_auto_clear" in crontab
        
        if has_job:
            # Try to extract schedule info
            lines = crontab.split('\n')
            job_line = None
            for line in lines:
                if "LHIMS Vitals Queue Auto-Clear" in line or "vitals_queue_auto_clear" in line:
                    job_line = line
                    break
            
            return {
                "installed": True,
                "cron_entry": job_line,
                "message": "Vitals queue auto-clear cron job is installed"
            }
        else:
            return {
                "installed": False,
                "message": "No vitals queue auto-clear cron job found"
            }
            
    except Exception as e:
        return {
            "installed": False,
            "error": str(e),
            "message": f"Error checking cron job status: {str(e)}"
        }
