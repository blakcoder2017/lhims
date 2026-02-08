"""
Backup Scheduler Service

This module provides functionality to schedule and manage automatic backups.
It can generate cron job entries and execute scheduled backups.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import subprocess
import platform

# Add the project root to the path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db.database import SessionLocal
from app.services.backup_service import create_full_backup, list_backups, BACKUP_DIR
from app.crud.hospital_settings_crud import get_hospital_settings
from scripts.backup_to_drive import BackupToDrive


def run_scheduled_backup(days_to_keep: int = 30, include_drive_upload: bool = True):
    """
    Execute a scheduled backup.
    This function is designed to be called by cron jobs or scheduled tasks.
    
    Args:
        days_to_keep: Number of days of backups to retain (default: 30)
        include_drive_upload: Whether to upload to Google Drive (default: True)
    """
    db = SessionLocal()
    try:
        # Get hospital settings for backup naming
        settings = get_hospital_settings(db)
        prefix = settings.hospital_name.lower().replace(" ", "_")[:10] if settings else "lhims"
        
        # Create backup using enhanced backup system
        if include_drive_upload:
            # Use comprehensive backup system with Drive upload
            backup_system = BackupToDrive()
            success = backup_system.run_backup()
            
            if success:
                print(f"[{datetime.now()}] Comprehensive backup with Drive upload completed successfully")
            else:
                print(f"[{datetime.now()}] ERROR: Comprehensive backup failed")
                return False
        else:
            # Use original backup system
            backup_path = create_full_backup(db, include_data=True)
            
            if backup_path:
                print(f"[{datetime.now()}] Backup created successfully: {backup_path}")
                
                # Clean up old backups
                cleanup_old_backups(days_to_keep=days_to_keep)
                
                return True
            else:
                print(f"[{datetime.now()}] ERROR: Failed to create backup")
                return False
        
        return True
        
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {str(e)}")
        return False
    finally:
        db.close()


def cleanup_old_backups(days_to_keep: int = 30):
    """
    Remove backups older than the specified number of days.
    
    Args:
        days_to_keep: Number of days of backups to retain
    """
    try:
        if not BACKUP_DIR.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        backups = list_backups()
        
        for backup in backups:
            try:
                backup_date_str = backup.get("backup_date", "")
                if backup_date_str:
                    backup_date = datetime.fromisoformat(backup_date_str.replace('Z', '+00:00'))
                    if backup_date < cutoff_date:
                        backup_path = Path(backup.get("backup_path", ""))
                        if backup_path.exists():
                            import shutil
                            shutil.rmtree(backup_path)
                            print(f"[{datetime.now()}] Deleted old backup: {backup_path}")
            except Exception as e:
                print(f"[{datetime.now()}] Error cleaning up backup: {e}")
                continue
    except Exception as e:
        print(f"[{datetime.now()}] Error in cleanup_old_backups: {e}")


def generate_cron_job_entry(
    hour: int = 2,
    minute: int = 0,
    python_path: Optional[str] = None,
    project_path: Optional[str] = None
) -> str:
    """
    Generate a cron job entry for automatic backups.
    
    Args:
        hour: Hour of day (0-23) to run backup
        minute: Minute of hour (0-59) to run backup
        python_path: Path to Python executable (auto-detected if None)
        project_path: Path to project root (auto-detected if None)
    
    Returns:
        Cron job entry string
    """
    if python_path is None:
        python_path = sys.executable
    
    if project_path is None:
        project_path = str(BASE_DIR)
    
    # Get the script path
    script_path = Path(__file__).resolve()
    
    # Generate cron entry
    cron_entry = f"{minute} {hour} * * * cd {project_path} && {python_path} -c \"from app.services.backup_scheduler import run_scheduled_backup; run_scheduled_backup(include_drive_upload=True)\""
    
    return cron_entry


def install_cron_job(
    hour: int = 2,
    minute: int = 0,
    comment: str = "LHIMS Automatic Backup"
) -> tuple[bool, str]:
    """
    Install a cron job for automatic backups (Linux/Mac only).
    
    Args:
        hour: Hour of day (0-23) to run backup
        minute: Minute of hour (0-59) to run backup
        comment: Comment to identify the cron job
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if platform.system() not in ["Linux", "Darwin"]:
        return False, "Cron jobs are only supported on Linux and macOS. Use Task Scheduler on Windows."
    
    try:
        cron_entry = generate_cron_job_entry(hour=hour, minute=minute)
        cron_entry_with_comment = f"{cron_entry} # {comment}"
        
        # Get current crontab
        result = subprocess.run(
            ["crontab", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        existing_crontab = result.stdout if result.returncode == 0 else ""
        
        # Check if backup cron job already exists
        if "LHIMS Automatic Backup" in existing_crontab or "backup_scheduler" in existing_crontab:
            # Remove existing entry
            lines = existing_crontab.split('\n')
            lines = [line for line in lines if "LHIMS Automatic Backup" not in line and "backup_scheduler" not in line]
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
            return True, f"Cron job installed successfully. Backups will run daily at {hour:02d}:{minute:02d}"
        else:
            return False, f"Failed to install cron job: {stderr}"
    
    except Exception as e:
        return False, f"Error installing cron job: {str(e)}"


def remove_cron_job() -> tuple[bool, str]:
    """
    Remove the LHIMS backup cron job.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if platform.system() not in ["Linux", "Darwin"]:
        return False, "Cron jobs are only supported on Linux and macOS."
    
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
        
        # Remove backup-related entries
        lines = existing_crontab.split('\n')
        filtered_lines = [
            line for line in lines
            if "LHIMS Automatic Backup" not in line
            and "backup_scheduler" not in line
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
            return True, "Cron job removed successfully"
        else:
            return False, f"Failed to remove cron job: {stderr}"
    
    except Exception as e:
        return False, f"Error removing cron job: {str(e)}"


def get_cron_job_status() -> dict:
    """
    Check if a backup cron job is currently installed.
    
    Returns:
        Dictionary with status information
    """
    if platform.system() not in ["Linux", "Darwin"]:
        return {
            "installed": False,
            "platform": platform.system(),
            "message": "Cron jobs are only supported on Linux and macOS. Use Task Scheduler on Windows."
        }
    
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return {
                "installed": False,
                "message": "No crontab found"
            }
        
        crontab = result.stdout
        has_backup_job = "LHIMS Automatic Backup" in crontab or "backup_scheduler" in crontab
        
        if has_backup_job:
            # Try to extract schedule info
            lines = crontab.split('\n')
            backup_line = None
            for line in lines:
                if "LHIMS Automatic Backup" in line or "backup_scheduler" in line:
                    backup_line = line
                    break
            
            return {
                "installed": True,
                "cron_entry": backup_line,
                "message": "Backup cron job is installed"
            }
        else:
            return {
                "installed": False,
                "message": "No backup cron job found"
            }
    
    except Exception as e:
        return {
            "installed": False,
            "error": str(e),
            "message": f"Error checking cron job status: {str(e)}"
        }


if __name__ == "__main__":
    # When run directly, execute a backup
    print("Running scheduled backup...")
    success = run_scheduled_backup()
    sys.exit(0 if success else 1)

