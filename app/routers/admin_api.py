from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
import csv
import json
from io import StringIO

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User, Role
from app.models.audit_models import AuditLog, AuditAction
from app.crud import audit_crud
from app.crud import user_crud
from app.crud import hospital_settings_crud
from app.crud import service_pricing_crud
from app.crud import permission_crud
from app.schemas.audit_schemas import AuditLogCreate
from app.schemas.user_schemas import UserCreate
from app.schemas.hospital_settings_schemas import HospitalSettingsUpdate
from app.schemas.service_pricing_schemas import ServicePricingCreate, ServicePricingUpdate

router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/users", name="users_management")
def users_management(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    role_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None)
):
    """User management dashboard with pagination and filtering"""
    from app.crud import user_crud
    
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Get users with pagination
    users, total_count = user_crud.get_users(
        db,
        skip=skip,
        limit=per_page,
        search=search,
        role_id=role_id,
        is_active=is_active
    )
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    roles = db.query(Role).all()
    
    context = {
        "request": request,
        "title": "User Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "users": users,
        "roles": roles,
        "search": search,
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "role_id_filter": role_id,
        "is_active_filter": is_active
    }
    return templates.TemplateResponse("admin/users_management.html", context)


@router.get("/admin/users/create", name="create_user_page")
def create_user_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Create user page"""
    # Exclude "Clinician" role from selection (use Doctor or Nurse instead)
    roles = db.query(Role).filter(Role.name != "Clinician").all()
    
    context = {
        "request": request,
        "title": "Create New User",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "roles": roles
    }
    return templates.TemplateResponse("admin/create_user.html", context)


@router.post("/admin/users/create", name="create_user", status_code=302)
def create_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role_id: int = Form(...),
    is_active: bool = Form(True)
):
    """Create a new user"""
    errors = []
    
    # Validation
    if password != confirm_password:
        errors.append("Password and confirmation do not match")
    
    if len(password) < 6:
        errors.append("Password must be at least 6 characters long")
    
    if len(username) < 3:
        errors.append("Username must be at least 3 characters long")
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        errors.append(f"Username '{username}' already exists")
    
    # Check if email already exists (if provided)
    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            errors.append(f"Email '{email}' is already in use")
    
    # Verify role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        errors.append(f"Invalid role selected")
    
    if errors:
        # Exclude "Clinician" role from selection
        roles = db.query(Role).filter(Role.name != "Clinician").all()
        context = {
            "request": request,
            "title": "Create New User",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "roles": roles,
            "errors": errors,
            "username": username,
            "full_name": full_name,
            "email": email,
            "role_id": role_id
        }
        return templates.TemplateResponse("admin/create_user.html", context)
    
    # Create user
    try:
        user_data = UserCreate(
            username=username,
            password=password,
            full_name=full_name.strip() if full_name else None,
            email=email.strip() if email else None,
            role_id=role_id
        )
        
        new_user = user_crud.create_user(db, user_data)
        
        # Log audit
        try:
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                username=current_user.username,
                action=AuditAction.CREATE,
                resource_type="user",
                resource_id=new_user.id,
                description=f"Created user: {new_user.username}",
                request_path=request.url.path
            )
            audit_crud.create_audit_log(db, audit_data)
        except Exception as e:
            print(f"Error creating audit log: {e}")
        
        from urllib.parse import urlencode
        base_url = str(request.url_for("users_management"))
        query_params = urlencode({"status": "created", "user_id": new_user.id})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except ValueError as e:
        # Exclude "Clinician" role from selection
        roles = db.query(Role).filter(Role.name != "Clinician").all()
        context = {
            "request": request,
            "title": "Create New User",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "roles": roles,
            "errors": [str(e)],
            "username": username,
            "full_name": full_name,
            "email": email,
            "role_id": role_id
        }
        return templates.TemplateResponse("admin/create_user.html", context)
    except Exception as e:
        # Exclude "Clinician" role from selection
        roles = db.query(Role).filter(Role.name != "Clinician").all()
        context = {
            "request": request,
            "title": "Create New User",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "roles": roles,
            "errors": [f"An error occurred: {str(e)}"],
            "username": username,
            "full_name": full_name,
            "email": email,
            "role_id": role_id
        }
        return templates.TemplateResponse("admin/create_user.html", context)


@router.get("/admin/users/{user_id}/edit", name="edit")
def edit_user_page(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Edit user page"""
    from app.crud import user_crud
    from sqlalchemy.orm import joinedload
    
    # Get user with role relationship loaded
    user = db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Exclude "Clinician" role from selection (use Doctor or Nurse instead)
    roles = db.query(Role).filter(Role.name != "Clinician").all()
    
    context = {
        "request": request,
        "title": f"Edit User: {user.username}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "roles": roles,
        "user": user
    }
    return templates.TemplateResponse("admin/edit_user.html", context)


@router.post("/admin/users/{user_id}/edit", name="update_user", status_code=302)
def update_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    username: str = Form(...),
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role_id: int = Form(...),
    is_active: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None)
):
    """Update a user"""
    from app.crud import user_crud
    
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    errors = []
    
    # Validate password if provided
    if password:
        if password != confirm_password:
            errors.append("Password and confirmation do not match")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long")
    
    # Check if username already exists (if changed)
    if username != user.username:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            errors.append(f"Username '{username}' already exists")
    
    # Check if email already exists (if changed)
    if email and email != user.email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            errors.append(f"Email '{email}' is already in use")
    
    # Verify role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        errors.append(f"Invalid role selected")
    
    if errors:
        # Exclude "Clinician" role from selection
        roles = db.query(Role).filter(Role.name != "Clinician").all()
        context = {
            "request": request,
            "title": f"Edit User: {user.username}",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "roles": roles,
            "user": user,
            "errors": errors
        }
        return templates.TemplateResponse("admin/edit_user.html", context)
    
    # Update user
    try:
        update_data = {
            "username": username,
            "full_name": full_name.strip() if full_name else None,
            "email": email.strip() if email else None,
            "role_id": role_id,
            "is_active": True if is_active else False
        }
        
        if password:
            update_data["password"] = password
        
        updated_user = user_crud.update_user(db, user_id, update_data)
        
        # Log audit
        try:
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                username=current_user.username,
                action=AuditAction.UPDATE,
                resource_type="user",
                resource_id=updated_user.id,
                description=f"Updated user: {updated_user.username}",
                request_path=request.url.path
            )
            audit_crud.create_audit_log(db, audit_data)
        except Exception as e:
            print(f"Error creating audit log: {e}")
        
        from urllib.parse import urlencode
        base_url = str(request.url_for("users_management"))
        query_params = urlencode({"status": "updated", "user_id": updated_user.id})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except ValueError as e:
        # Exclude "Clinician" role from selection
        roles = db.query(Role).filter(Role.name != "Clinician").all()
        context = {
            "request": request,
            "title": f"Edit User: {user.username}",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "roles": roles,
            "user": user,
            "errors": [str(e)]
        }
        return templates.TemplateResponse("admin/edit_user.html", context)
    except Exception as e:
        # Exclude "Clinician" role from selection
        roles = db.query(Role).filter(Role.name != "Clinician").all()
        context = {
            "request": request,
            "title": f"Edit User: {user.username}",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "roles": roles,
            "user": user,
            "errors": [str(e)]
        }
        return templates.TemplateResponse("admin/edit_user.html", context)


@router.post("/admin/users/{user_id}/delete", name="delete_user", status_code=302)
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Delete a user (soft delete - sets is_active to False)"""
    from app.crud import user_crud
    
    user = user_crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        from urllib.parse import urlencode
        base_url = str(request.url_for("users_management"))
        query_params = urlencode({"error": "You cannot delete your own account"})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    try:
        user_crud.delete_user(db, user_id)
        
        # Log audit
        try:
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                username=current_user.username,
                action=AuditAction.DELETE,
                resource_type="user",
                resource_id=user_id,
                description=f"Deleted user: {user.username}",
                request_path=request.url.path
            )
            audit_crud.create_audit_log(db, audit_data)
        except Exception as e:
            print(f"Error creating audit log: {e}")
        
        from urllib.parse import urlencode
        base_url = str(request.url_for("users_management"))
        query_params = urlencode({"status": "deleted", "user_id": user_id})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        from urllib.parse import urlencode
        base_url = str(request.url_for("users_management"))
        query_params = urlencode({"error": str(e)})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/admin/audit-logs", name="audit_logs")
def audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Audit logs dashboard"""
    from datetime import datetime
    
    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
    
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            pass
    
    logs = audit_crud.get_audit_logs(
        db,
        user_id=user_id,
        action=action_enum,
        resource_type=resource_type,
        start_date=start_dt,
        end_date=end_dt,
        limit=200
    )
    
    context = {
        "request": request,
        "title": "Audit Logs",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "logs": logs,
        "filters": {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "start_date": start_date,
            "end_date": end_date
        }
    }
    return templates.TemplateResponse("admin/audit_logs.html", context)


@router.get("/admin/settings", name="system_settings")
def system_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """System settings page"""
    from app.services.backup_scheduler import get_cron_job_status
    import platform
    
    cron_status = get_cron_job_status()
    
    context = {
        "request": request,
        "title": "System Settings",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "cron_status": cron_status,
        "platform": platform.system()
    }
    return templates.TemplateResponse("admin/system_settings.html", context)


@router.get("/admin/export/{resource_type}", name="export_data")
def export_data(
    request: Request,
    resource_type: str,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    format: str = Query("csv", description="Export format: csv or json")
):
    """Export data functionality"""
    from app.models.patient_models import Patient
    from app.models.billing_models import Invoice, Payment
    from datetime import datetime
    
    # Log export action
    audit_data = AuditLogCreate(
        user_id=current_user.id,
        username=current_user.username,
        action=AuditAction.EXPORT,
        resource_type=resource_type,
        request_path=request.url.path,
        description=f"Exported {resource_type} data"
    )
    audit_crud.create_audit_log(db, audit_data)
    
    if resource_type == "patients":
        patients = db.query(Patient).filter(Patient.is_active == True).all()
        
        if format == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "First Name", "Last Name", "Date of Birth", "Gender", "Phone", "National ID"])
            for p in patients:
                writer.writerow([p.id, p.first_name, p.last_name, p.date_of_birth, p.gender, p.phone_number, p.national_id])
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=patients_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
        else:  # JSON
            data = [{
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "date_of_birth": str(p.date_of_birth),
                "gender": p.gender,
                "phone_number": p.phone_number,
                "national_id": p.national_id
            } for p in patients]
            
            return Response(
                content=json.dumps(data, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=patients_{datetime.now().strftime('%Y%m%d')}.json"}
            )
    
    elif resource_type == "invoices":
        invoices = db.query(Invoice).filter(Invoice.is_active == True).all()
        
        if format == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Invoice Number", "Patient ID", "Total Amount", "Paid Amount", "Balance", "Status", "Date"])
            for inv in invoices:
                writer.writerow([
                    inv.invoice_number, inv.patient_id, inv.total_amount,
                    inv.paid_amount, inv.balance, inv.status.value, inv.invoice_date
                ])
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=invoices_{datetime.now().strftime('%Y%m%d')}.csv"}
            )
    
    raise HTTPException(status_code=404, detail="Resource type not supported for export")


@router.get("/admin/hospital-settings", name="hospital_settings")
def hospital_settings_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Hospital settings page"""
    from app.crud.hospital_settings_crud import get_hospital_settings
    
    settings = get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": "Hospital Settings",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "settings": settings,
        "hospital_settings": settings  # Also pass as hospital_settings for template consistency
    }
    return templates.TemplateResponse("admin/hospital_settings.html", context)


@router.post("/admin/hospital-settings", name="update_hospital_settings", status_code=302)
def update_hospital_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    hospital_name: Optional[str] = Form(None),
    hospital_address: Optional[str] = Form(None),
    hospital_phone: Optional[str] = Form(None),
    hospital_email: Optional[str] = Form(None),
    hospital_website: Optional[str] = Form(None)
):
    """Update hospital settings"""
    from app.crud.hospital_settings_crud import update_hospital_settings
    
    try:
        settings = update_hospital_settings(
            db,
            hospital_name=hospital_name.strip() if hospital_name else None,
            hospital_address=hospital_address.strip() if hospital_address else None,
            hospital_phone=hospital_phone.strip() if hospital_phone else None,
            hospital_email=hospital_email.strip() if hospital_email else None,
            hospital_website=hospital_website.strip() if hospital_website else None
        )
        
        # Log audit
        try:
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                username=current_user.username,
                action=AuditAction.UPDATE,
                resource_type="hospital_settings",
                resource_id=settings.id,
                description="Updated hospital settings",
                request_path=request.url.path
            )
            audit_crud.create_audit_log(db, audit_data)
        except Exception as e:
            print(f"Error creating audit log: {e}")
        
        from urllib.parse import urlencode
        base_url = str(request.url_for("hospital_settings"))
        query_params = urlencode({"status": "updated"})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        from app.crud.hospital_settings_crud import get_hospital_settings
        settings = get_hospital_settings(db)
        context = {
            "request": request,
            "title": "Hospital Settings",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "settings": settings,
            "error": f"An error occurred: {str(e)}"
        }
        return templates.TemplateResponse("admin/hospital_settings.html", context)


@router.post("/admin/hospital-settings/upload-logo", name="upload_hospital_logo", status_code=302)
async def upload_hospital_logo(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    logo: UploadFile = File(None)
):
    """Upload hospital logo"""
    import os
    from pathlib import Path
    from app.crud.hospital_settings_crud import update_hospital_settings, get_hospital_settings
    
    if not logo or not logo.filename:
        from urllib.parse import urlencode
        base_url = str(request.url_for("hospital_settings"))
        query_params = urlencode({"error": "No logo file provided"})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    try:
        # Validate file type
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
        file_ext = os.path.splitext(logo.filename)[1].lower()
        if file_ext not in allowed_extensions:
            from urllib.parse import urlencode
            base_url = str(request.url_for("hospital_settings"))
            query_params = urlencode({"error": "Invalid file type. Please upload PNG, JPG, or GIF."})
            redirect_url = f"{base_url}?{query_params}"
            return RedirectResponse(url=redirect_url, status_code=302)
        
        # Create uploads directory if it doesn't exist
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        uploads_dir = os.path.join(BASE_DIR, "app", "static", "uploads", "logos")
        Path(uploads_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hospital_logo_{timestamp}{file_ext}"
        file_path = os.path.join(uploads_dir, filename)
        
        # Save file
        contents = await logo.read()
        if len(contents) > 2 * 1024 * 1024:  # 2MB limit
            from urllib.parse import urlencode
            base_url = str(request.url_for("hospital_settings"))
            query_params = urlencode({"error": "File too large. Maximum size is 2MB."})
            redirect_url = f"{base_url}?{query_params}"
            return RedirectResponse(url=redirect_url, status_code=302)
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Update settings
        logo_path = f"uploads/logos/{filename}"
        logo_url = f"/static/{logo_path}"
        
        update_hospital_settings(
            db,
            logo_path=logo_path,
            logo_url=logo_url
        )
        
        # Log audit
        try:
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                username=current_user.username,
                action=AuditAction.UPDATE,
                resource_type="hospital_settings",
                description="Uploaded hospital logo",
                request_path=request.url.path
            )
            audit_crud.create_audit_log(db, audit_data)
        except Exception as e:
            print(f"Error creating audit log: {e}")
        
        from urllib.parse import urlencode
        base_url = str(request.url_for("hospital_settings"))
        query_params = urlencode({"status": "logo_uploaded"})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(url=redirect_url, status_code=302)
    except Exception as e:
        settings = get_hospital_settings(db)
        context = {
            "request": request,
            "title": "Hospital Settings",
            "current_user": current_user,
            "user_role": current_user.role.name,
            "settings": settings,
            "error": f"Error uploading logo: {str(e)}"
        }
        return templates.TemplateResponse("admin/hospital_settings.html", context)

