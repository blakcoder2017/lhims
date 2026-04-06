"""
API routes for backup and recovery management.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query, Form, File, UploadFile
from app.core.templates import templates
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional
import zipfile
import shutil
import platform
import tempfile
import threading
import time
from datetime import datetime

# In-memory storage for background task status
# Format: {task_id: {"status": "running"|"completed"|"failed", "message": str, "result": str, "started_at": datetime}}
backup_tasks = {}
backup_task_lock = threading.Lock()

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.services.backup_service import (
    create_full_backup, 
    list_backups,
    create_complete_backup,
    restore_from_backup,
    get_database_info,
    list_complete_backups,
    BACKUP_DIR
)
from app.services.backup_scheduler import (
    install_cron_job,
    remove_cron_job,
    get_cron_job_status,
    generate_cron_job_entry
)

router = APIRouter(tags=["Backup"])


@router.get("/admin/backup", name="backup_dashboard")
def backup_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Backup management dashboard"""
    backups = list_backups()
    
    context = {
        "request": request,
        "title": "Backup & Recovery",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "backups": backups
    }
    return templates.TemplateResponse("admin/backup_dashboard.html", context)


@router.post("/admin/backup/create", name="create_backup", status_code=302)
def create_backup(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    return_to: Optional[str] = Query(None)
):
    """Create a new backup"""
    try:
        backup_path = create_full_backup(db, include_data=True)
        if backup_path:
            # If return_to is set to "settings", redirect to system settings
            if return_to == "settings":
                return RedirectResponse(
                    url=str(request.url_for("system_settings")) + "?backup_created=1",
                    status_code=302
                )
            return RedirectResponse(
                url=f"/admin/backup?status=created&path={backup_path}",
                status_code=302
            )
        else:
            if return_to == "settings":
                return RedirectResponse(
                    url=str(request.url_for("system_settings")) + "?error=backup_failed",
                    status_code=302
                )
            return RedirectResponse(
                url="/admin/backup?error=backup_failed",
                status_code=302
            )
    except Exception as e:
        if return_to == "settings":
            return RedirectResponse(
                url=str(request.url_for("system_settings")) + f"?error={str(e)}",
                status_code=302
            )
        return RedirectResponse(
            url=f"/admin/backup?error={str(e)}",
            status_code=302
        )


@router.get("/admin/backup/download/{backup_name}", name="download_backup")
def download_backup(
    request: Request,
    backup_name: str,
    current_user = Depends(role_required(["Admin"]))
):
    """Download a backup as ZIP file"""
    from app.services.backup_service import BACKUP_DIR
    
    backup_path = BACKUP_DIR / backup_name
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # Create ZIP file
    zip_path = backup_path.parent / f"{backup_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in backup_path.rglob('*'):
            if file_path.is_file():
                zipf.write(file_path, file_path.relative_to(backup_path))
    
    return FileResponse(
        path=zip_path,
        filename=f"{backup_name}.zip",
        media_type="application/zip"
    )


@router.get("/admin/backup/auto-config", name="backup_auto_config")
def backup_auto_config_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Show automatic backup configuration page"""
    cron_status = get_cron_job_status()
    
    context = {
        "request": request,
        "title": "Automatic Backup Configuration",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "cron_status": cron_status,
        "platform": platform.system()
    }
    return templates.TemplateResponse("admin/backup_auto_config.html", context)


@router.post("/admin/backup/auto-config/install", name="install_backup_cron", status_code=302)
def install_backup_cron(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    hour: int = Form(2),
    minute: int = Form(0),
    days_to_keep: int = Form(30)
):
    """Install automatic backup cron job"""
    try:
        success, message = install_cron_job(hour=hour, minute=minute)
        
        if success:
            return RedirectResponse(
                url=str(request.url_for("system_settings")) + f"?backup_cron_installed=1&message={message}",
                status_code=302
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("system_settings")) + f"?error={message}",
                status_code=302
            )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("system_settings")) + f"?error={str(e)}",
            status_code=302
        )


@router.post("/admin/backup/auto-config/remove", name="remove_backup_cron", status_code=302)
def remove_backup_cron(
    request: Request,
    current_user = Depends(role_required(["Admin"]))
):
    """Remove automatic backup cron job"""
    try:
        success, message = remove_cron_job()
        
        if success:
            return RedirectResponse(
                url=str(request.url_for("system_settings")) + f"?backup_cron_removed=1&message={message}",
                status_code=302
            )
        else:
            return RedirectResponse(
                url=str(request.url_for("system_settings")) + f"?error={message}",
                status_code=302
            )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("system_settings")) + f"?error={str(e)}",
            status_code=302
        )


@router.get("/admin/backup/auto-config/status", name="backup_cron_status")
def backup_cron_status(
    request: Request,
    current_user = Depends(role_required(["Admin"]))
):
    """Get automatic backup cron job status (JSON API)"""
    status = get_cron_job_status()
    return status


# ============================================
# Complete Database Backup/Restore Endpoints
# ============================================

@router.get("/admin/backup/complete", name="backup_complete_dashboard")
def backup_complete_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Complete database backup dashboard with full SQL dump and restore"""
    backups = list_complete_backups()
    db_info = get_database_info()
    cron_status = get_cron_job_status()
    
    context = {
        "request": request,
        "title": "Complete Database Backup & Restore",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "backups": backups,
        "db_info": db_info,
        "cron_status": cron_status
    }
    return templates.TemplateResponse("admin/backup_complete.html", context)


def _run_backup_in_background(task_id: str, include_data: bool, compress: bool):
    """Run backup in background thread"""
    try:
        with backup_task_lock:
            backup_tasks[task_id]["status"] = "running"
            backup_tasks[task_id]["message"] = "Backup in progress..."
        
        backup_path = create_complete_backup(include_data=include_data, compress=compress)
        
        if backup_path:
            with backup_task_lock:
                backup_tasks[task_id]["status"] = "completed"
                backup_tasks[task_id]["message"] = "Backup completed successfully"
                backup_tasks[task_id]["result"] = str(backup_path.name)
        else:
            with backup_task_lock:
                backup_tasks[task_id]["status"] = "failed"
                backup_tasks[task_id]["message"] = "Backup failed"
    except Exception as e:
        with backup_task_lock:
            backup_tasks[task_id]["status"] = "failed"
            backup_tasks[task_id]["message"] = f"Backup failed: {str(e)}"


@router.post("/admin/backup/complete/create", name="create_complete_backup", status_code=302)
def create_complete_backup_endpoint(
    request: Request,
    current_user = Depends(role_required(["Admin"])),
    include_data: bool = Form(True),
    compress: bool = Form(True)
):
    """Create a complete database backup using pg_dump (runs in background)"""
    try:
        # Generate unique task ID
        task_id = f"backup_{int(time.time())}"
        
        # Store task info
        with backup_task_lock:
            backup_tasks[task_id] = {
                "status": "starting",
                "message": "Starting backup...",
                "result": None,
                "started_at": datetime.now().isoformat()
            }
        
        # Start backup in background thread
        thread = threading.Thread(
            target=_run_backup_in_background,
            args=(task_id, include_data, compress)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediately with task ID
        return RedirectResponse(
            url=f"/admin/backup/complete?status=started&task_id={task_id}",
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/backup/complete?error={str(e)}",
            status_code=302
        )


@router.get("/admin/backup/complete/status/{task_id}")
def get_backup_status(
    task_id: str,
    current_user = Depends(role_required(["Admin"]))
):
    """Get status of background backup task"""
    with backup_task_lock:
        task = backup_tasks.get(task_id)
    
    if not task:
        return JSONResponse({
            "status": "not_found",
            "message": "Task not found"
        })
    
    return JSONResponse({
        "status": task["status"],
        "message": task["message"],
        "result": task.get("result"),
        "started_at": task.get("started_at")
    })


@router.get("/admin/backup/complete/download/{filename}", name="download_complete_backup")
def download_complete_backup(
    request: Request,
    filename: str,
    current_user = Depends(role_required(["Admin"]))
):
    """Download a complete SQL backup file"""
    backup_path = BACKUP_DIR / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    # Determine media type based on file extension
    if filename.endswith('.gz'):
        media_type = "application/gzip"
    else:
        media_type = "application/sql"
    
    return FileResponse(
        path=backup_path,
        filename=filename,
        media_type=media_type
    )


@router.post("/admin/backup/complete/restore", name="restore_complete_backup", status_code=302)
async def restore_complete_backup_endpoint(
    request: Request,
    current_user = Depends(role_required(["Admin"])),
    file: UploadFile = File(...),
    drop_existing: bool = Form(True)
):
    """Upload and restore a complete database backup"""
    try:
        # Validate file extension
        allowed_extensions = ['.sql', '.sql.gz', '.dump', '.gz']
        if not any(file.filename.endswith(ext) for ext in allowed_extensions):
            return RedirectResponse(
                url="/admin/backup/complete?error=invalid_file_type",
                status_code=302
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Perform restore
            success, message = restore_from_backup(tmp_path, drop_existing=drop_existing)
            
            if success:
                return RedirectResponse(
                    url="/admin/backup/complete?status=restored",
                    status_code=302
                )
            else:
                return RedirectResponse(
                    url=f"/admin/backup/complete?error={message}",
                    status_code=302
                )
        finally:
            # Clean up temp file
            if tmp_path.exists():
                tmp_path.unlink()
                
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/backup/complete?error={str(e)}",
            status_code=302
        )


@router.get("/admin/backup/complete/info", name="backup_db_info")
def backup_db_info(
    current_user = Depends(role_required(["Admin"]))
):
    """Get database information for backup display"""
    info = get_database_info()
    return info


@router.post("/admin/backup/complete/install-cron", name="install_backup_cron_complete", status_code=302)
def install_backup_cron_complete(
    request: Request,
    current_user = Depends(role_required(["Admin"])),
    hour: int = Form(2),
    minute: int = Form(0),
    days_to_keep: int = Form(30)
):
    """Install automatic complete backup cron job"""
    try:
        success, message = install_cron_job(hour=hour, minute=minute, backup_type="complete")
        
        if success:
            return RedirectResponse(
                url=f"/admin/backup/complete?status=cron_installed&message={message}",
                status_code=302
            )
        else:
            return RedirectResponse(
                url=f"/admin/backup/complete?error={message}",
                status_code=302
            )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/backup/complete?error={str(e)}",
            status_code=302
        )

