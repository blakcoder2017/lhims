"""
API routes for backup and recovery management.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional
import zipfile
import shutil
import platform

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.services.backup_service import create_full_backup, list_backups
from app.services.backup_scheduler import (
    install_cron_job,
    remove_cron_job,
    get_cron_job_status,
    generate_cron_job_entry
)

router = APIRouter(tags=["Backup"])
templates = Jinja2Templates(directory="app/templates")


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

