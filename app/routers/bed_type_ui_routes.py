"""
Bed Type UI Routes

UI routes for managing bed types.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.schemas.bed_type_schemas import BedTypeCreate, BedTypeUpdate
from app.crud import bed_type_crud

router = APIRouter(
    prefix="",
    tags=["Bed Types UI"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/bed-types", name="bed_types_list")
def list_bed_types(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    active_only: bool = Query(False)
):
    """List all bed types"""
    bed_types, total_count = bed_type_crud.get_bed_types(db, active_only=active_only)
    
    context = {
        "request": request,
        "title": "Bed Types",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "bed_types": bed_types,
        "active_only": active_only,
        "total_count": total_count
    }
    return templates.TemplateResponse("admin/bed_types_list.html", context)


@router.get("/admin/bed-types/create", name="bed_type_create_form")
def bed_type_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create bed type form"""
    context = {
        "request": request,
        "title": "Create Bed Type",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("admin/bed_type_form.html", context)


@router.post("/admin/bed-types/create", name="bed_type_create", status_code=status.HTTP_302_FOUND)
def create_bed_type_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    default_charge_per_day: Optional[str] = Form(None)
):
    """Handle create bed type form submission"""
    try:
        # Check if bed type with same name or code already exists
        if code:
            existing = bed_type_crud.get_bed_type_by_code(db, code)
            if existing:
                return RedirectResponse(
                    url=str(request.url_for("bed_type_create_form")) + "?error=code_exists",
                    status_code=status.HTTP_302_FOUND
                )
        
        existing_name = bed_type_crud.get_bed_type_by_name(db, name)
        if existing_name:
            return RedirectResponse(
                url=str(request.url_for("bed_type_create_form")) + "?error=name_exists",
                status_code=status.HTTP_302_FOUND
            )
        
        bed_type_data = BedTypeCreate(
            name=name,
            code=code if code else None,
            description=description if description else None,
            default_charge_per_day=default_charge_per_day if default_charge_per_day else None
        )
        
        bed_type_crud.create_bed_type(db, bed_type_data)
        
        return RedirectResponse(
            url=str(request.url_for("bed_types_list")) + "?status=created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("bed_type_create_form")) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/admin/bed-types/{bed_type_id}", name="bed_type_detail")
def bed_type_detail(
    request: Request,
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """View bed type details"""
    bed_type = bed_type_crud.get_bed_type(db, bed_type_id)
    if not bed_type:
        raise HTTPException(status_code=404, detail="Bed type not found")
    
    context = {
        "request": request,
        "title": f"Bed Type: {bed_type.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "bed_type": bed_type
    }
    return templates.TemplateResponse("admin/bed_type_detail.html", context)


@router.get("/admin/bed-types/{bed_type_id}/edit", name="bed_type_edit_form")
def bed_type_edit_form(
    request: Request,
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show edit bed type form"""
    bed_type = bed_type_crud.get_bed_type(db, bed_type_id)
    if not bed_type:
        raise HTTPException(status_code=404, detail="Bed type not found")
    
    context = {
        "request": request,
        "title": f"Edit Bed Type: {bed_type.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "bed_type": bed_type
    }
    return templates.TemplateResponse("admin/bed_type_form.html", context)


@router.post("/admin/bed-types/{bed_type_id}/edit", name="bed_type_update", status_code=status.HTTP_302_FOUND)
def update_bed_type_form(
    request: Request,
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    default_charge_per_day: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None)
):
    """Handle update bed type form submission"""
    try:
        # Convert checkbox to boolean (HTML checkbox sends "on" when checked, nothing when unchecked)
        is_active_bool = True if is_active else False
        
        bed_type_update = BedTypeUpdate(
            name=name,
            code=code if code else None,
            description=description if description else None,
            default_charge_per_day=default_charge_per_day if default_charge_per_day else None,
            is_active=is_active_bool
        )
        
        bed_type = bed_type_crud.update_bed_type(
            db, bed_type_id, bed_type_update
        )
        if not bed_type:
            raise HTTPException(status_code=404, detail="Bed type not found")
        
        return RedirectResponse(
            url=str(request.url_for("bed_types_list")) + "?status=updated",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("bed_type_edit_form", bed_type_id=bed_type_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/admin/bed-types/{bed_type_id}/delete", name="bed_type_delete", status_code=status.HTTP_302_FOUND)
def delete_bed_type_form(
    request: Request,
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Handle delete bed type (soft delete)"""
    bed_type = bed_type_crud.get_bed_type(db, bed_type_id)
    if not bed_type:
        raise HTTPException(status_code=404, detail="Bed type not found")
    
    bed_type_crud.delete_bed_type(db, bed_type_id)
    
    return RedirectResponse(
        url=str(request.url_for("bed_types_list")) + "?status=deleted",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/admin/bed-types/{bed_type_id}/toggle-status", name="bed_type_toggle_status", status_code=status.HTTP_302_FOUND)
def toggle_bed_type_status(
    request: Request,
    bed_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    return_to: Optional[str] = Query("list")
):
    """Toggle bed type active status (activate/deactivate)"""
    bed_type = bed_type_crud.get_bed_type(db, bed_type_id)
    if not bed_type:
        raise HTTPException(status_code=404, detail="Bed type not found")
    
    # Toggle status
    bed_type.is_active = not bed_type.is_active
    db.commit()
    db.refresh(bed_type)
    
    status_message = "activated" if bed_type.is_active else "deactivated"
    
    # Redirect based on return_to parameter
    if return_to == "detail":
        return RedirectResponse(
            url=str(request.url_for("bed_type_detail", bed_type_id=bed_type_id)) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(
            url=str(request.url_for("bed_types_list")) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )
