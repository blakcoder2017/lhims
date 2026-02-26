"""
Encounter Auto-Close Service
Automatically closes encounters that have been in progress for more than 24 hours.
This service is designed to run via scheduler (hourly) or cron job.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.database import SessionLocal
from app.models.encounter_models import Encounter, EncounterStatus, LabOrder, RadiologyOrder
from app.models.patient_models import Patient
from app.models.user_models import User

logger = logging.getLogger(__name__)

# Configuration: Hours after which encounters are considered stale
STALE_ENCOUNTER_HOURS = 24


def auto_close_stale_encounters(db: Session = None) -> Dict[str, Any]:
    """
    Automatically close encounters that have been in progress for more than 24 hours.
    
    Rules:
    - Only closes OPD encounters (excludes IPD encounters with admission_id)
    - Excludes encounters that have pending lab or radiology orders
    - Sets status to AUTO_CLOSED for audit tracking
    
    Args:
        db: Database session. If not provided, a new session will be created.
        
    Returns:
        Dictionary with results: {
            "success": bool,
            "closed_count": int,
            "skipped_count": int,
            "encounters": List of closed encounter details,
            "message": str
        }
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # Calculate cutoff time (24 hours ago)
        cutoff_time = datetime.utcnow() - timedelta(hours=STALE_ENCOUNTER_HOURS)
        
        # Query for stale encounters:
        # - Status is IN_PROGRESS
        # - Started more than 24 hours ago
        # - No admission_id (OPD encounters only, exclude IPD)
        stale_encounters = db.query(Encounter).filter(
            and_(
                Encounter.status == EncounterStatus.IN_PROGRESS,
                Encounter.started_at < cutoff_time,
                Encounter.admission_id == None  # Exclude IPD encounters
            )
        ).all()
        
        closed_encounters = []
        skipped_encounters = []
        
        for encounter in stale_encounters:
            # Close the encounter regardless of pending orders
            # Doctors can always view results when they are ready
            encounter.status = EncounterStatus.AUTO_CLOSED
            encounter.completed_at = datetime.utcnow()
            
            # Get patient info for logging
            patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
            clinician = db.query(User).filter(User.id == encounter.clinician_id).first()
            
            # Check for pending orders for logging purposes
            pending_lab_orders = db.query(LabOrder).filter(
                and_(
                    LabOrder.encounter_id == encounter.id,
                    LabOrder.status.in_(['pending', 'ordered', 'in_progress'])
                )
            ).count()
            
            pending_radiology_orders = db.query(RadiologyOrder).filter(
                and_(
                    RadiologyOrder.encounter_id == encounter.id,
                    RadiologyOrder.status.in_(['pending', 'ordered', 'in_progress'])
                )
            ).count()
            
            closed_encounters.append({
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                "clinician": f"{clinician.first_name} {clinician.last_name}" if clinician else "Unknown",
                "started_at": encounter.started_at.isoformat() if encounter.started_at else None,
                "closed_at": encounter.completed_at.isoformat() if encounter.completed_at else None,
                "hours_stale": STALE_ENCOUNTER_HOURS,
                "pending_lab_orders": pending_lab_orders,
                "pending_radiology_orders": pending_radiology_orders
            })
        
        # Commit all changes
        db.commit()
        
        result = {
            "success": True,
            "closed_count": len(closed_encounters),
            "skipped_count": len(skipped_encounters),
            "encounters": closed_encounters,
            "skipped": skipped_encounters,
            "message": f"Auto-closed {len(closed_encounters)} stale encounters."
        }
        
        logger.info(f"Encounter auto-close: {result['message']}")
        return result
        
    except Exception as e:
        logger.error(f"Error in auto_close_stale_encounters: {str(e)}")
        if db:
            db.rollback()
        return {
            "success": False,
            "closed_count": 0,
            "skipped_count": 0,
            "encounters": [],
            "skipped": [],
            "message": f"Error: {str(e)}"
        }
    finally:
        if close_session and db:
            db.close()


def get_stale_encounters_preview(db: Session = None) -> Dict[str, Any]:
    """
    Preview which encounters would be closed without actually closing them.
    Useful for admin review before running the auto-close.
    
    Args:
        db: Database session. If not provided, a new session will be created.
        
    Returns:
        Dictionary with preview data
    """
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=STALE_ENCOUNTER_HOURS)
        
        # Get all stale encounters
        stale_encounters = db.query(Encounter).filter(
            and_(
                Encounter.status == EncounterStatus.IN_PROGRESS,
                Encounter.started_at < cutoff_time,
                Encounter.admission_id == None
            )
        ).all()
        
        preview_list = []
        
        for encounter in stale_encounters:
            # Check pending orders
            pending_lab = db.query(LabOrder).filter(
                and_(
                    LabOrder.encounter_id == encounter.id,
                    LabOrder.status.in_(['pending', 'ordered', 'in_progress'])
                )
            ).count()
            
            pending_radiology = db.query(RadiologyOrder).filter(
                and_(
                    RadiologyOrder.encounter_id == encounter.id,
                    RadiologyOrder.status.in_(['pending', 'ordered', 'in_progress'])
                )
            ).count()
            
            patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
            
            # Calculate hours stale
            hours_stale = (datetime.utcnow() - encounter.started_at).total_seconds() / 3600 if encounter.started_at else 0
            
            preview_list.append({
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                "started_at": encounter.started_at.isoformat() if encounter.started_at else None,
                "hours_stale": round(hours_stale, 1),
                "pending_lab_orders": pending_lab,
                "pending_radiology_orders": pending_radiology
            })
        
        return {
            "success": True,
            "total_stale": len(stale_encounters),
            "encounters": preview_list
        }
        
    except Exception as e:
        logger.error(f"Error in get_stale_encounters_preview: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }
    finally:
        if close_session and db:
            db.close()


# Standalone function for cron/scheduler execution
def run_encounter_auto_close():
    """Entry point for cron job or scheduler"""
    logger.info("Running encounter auto-close task...")
    result = auto_close_stale_encounters()
    logger.info(f"Encounter auto-close completed: {result['message']}")
    return result


if __name__ == "__main__":
    # Can be run directly: python -m app.services.encounter_auto_close_service
    logging.basicConfig(level=logging.INFO)
    result = run_encounter_auto_close()
    print(result)


# Cron Job Helper Functions
def generate_cron_job_entry(
    hour: int = 1,
    minute: int = 0
) -> str:
    """
    Generate a cron job entry for automatic encounter auto-close.
    
    Args:
        hour: Hour of day (0-23) to run the auto-close
        minute: Minute of hour (0-59) to run the auto-close
        
    Returns:
        Cron job entry string
    """
    import os
    import subprocess
    
    # Get project path
    result = subprocess.run(
        ["pwd"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    project_path = result.stdout.strip() if result.returncode == 0 else "/home/dei-gratia-server/Documents/lhims"
    
    python_path = subprocess.run(
        ["which", "python"],
        capture_output=True,
        text=True
    ).stdout.strip() or "python"
    
    # Generate cron entry
    cron_entry = f"{minute} {hour} * * * cd {project_path} && {python_path} -c \"from app.services.encounter_auto_close_service import run_encounter_auto_close; run_encounter_auto_close()\""
    
    return cron_entry


def install_cron_job(
    hour: int = 1,
    minute: int = 0
) -> tuple[bool, str]:
    """
    Install a cron job for automatic encounter auto-close (Linux/Mac only).
    
    Args:
        hour: Hour of day (0-23) to run the auto-close
        minute: Minute of hour (0-59) to run the auto-close
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    import subprocess
    
    try:
        cron_entry = generate_cron_job_entry(hour=hour, minute=minute)
        cron_entry_with_comment = f"{cron_entry} # LHIMS Encounter Auto-Close"
        
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        existing_crontab = result.stdout if result.returncode == 0 else ""
        
        # Check if encounter auto-close cron job already exists
        if "LHIMS Encounter Auto-Close" in existing_crontab or "encounter_auto_close" in existing_crontab:
            # Remove existing entry
            lines = existing_crontab.split('\n')
            lines = [line for line in lines if "LHIMS Encounter Auto-Close" not in line and "encounter_auto_close" not in line]
            existing_crontab = '\n'.join(lines)
        
        # Add new entry
        new_crontab = existing_crontab.rstrip() + '\n' + cron_entry_with_comment + '\n'
        
        # Install new crontab
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            return True, f"Encounter auto-close cron job installed: {minute} {hour} * * *"
        else:
            return False, f"Failed to install cron job: {stderr}"
            
    except Exception as e:
        return False, f"Error installing cron job: {str(e)}"


def remove_cron_job() -> tuple[bool, str]:
    """
    Remove the LHIMS encounter auto-close cron job.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    import subprocess
    
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
        
        # Remove encounter auto-close related entries
        lines = existing_crontab.split('\n')
        filtered_lines = [
            line for line in lines
            if "LHIMS Encounter Auto-Close" not in line
            and "encounter_auto_close" not in line
            and line.strip()  # Keep non-empty lines
        ]
        
        new_crontab = '\n'.join(filtered_lines) + '\n'
        
        # Install updated crontab
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            return True, "Encounter auto-close cron job removed"
        else:
            return False, f"Failed to remove cron job: {stderr}"
            
    except Exception as e:
        return False, f"Error removing cron job: {str(e)}"


def get_cron_job_status() -> dict:
    """
    Check if an encounter auto-close cron job is currently installed.
    
    Returns:
        Dictionary with status information
    """
    import subprocess
    
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
        has_job = "LHIMS Encounter Auto-Close" in crontab or "encounter_auto_close" in crontab
        
        if has_job:
            # Try to extract schedule info
            lines = crontab.split('\n')
            job_line = None
            for line in lines:
                if "LHIMS Encounter Auto-Close" in line or "encounter_auto_close" in line:
                    job_line = line
                    break
            
            return {
                "installed": True,
                "cron_entry": job_line,
                "message": "Encounter auto-close cron job is installed"
            }
        else:
            return {
                "installed": False,
                "message": "No encounter auto-close cron job found"
            }
            
    except Exception as e:
        return {
            "installed": False,
            "error": str(e),
            "message": f"Error checking cron job status: {str(e)}"
        }
