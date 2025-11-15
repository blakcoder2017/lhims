"""
Ward Type UI Routes

UI routes for managing ward types.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.schemas.ward_type_schemas import WardTypeCreate, WardTypeUpdate
from app.crud import ward_type_crud

router = APIRouter(
    prefix="",
    tags=["Ward Types UI"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/ward-types", name="ward_types_list")
def list_ward_types(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    active_only: bool = Query(True)
):
    """List all ward types"""
    ward_types, total_count = ward_type_crud.get_ward_types(db, active_only=active_only)
    
    context = {
        "request": request,
        "title": "Ward Types",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "ward_types": ward_types,
        "active_only": active_only,
        "total_count": total_count
    }
    return templates.TemplateResponse("admin/ward_types_list.html", context)


@router.get("/admin/ward-types/create", name="ward_type_create_form")
def ward_type_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create ward type form"""
    context = {
        "request": request,
        "title": "Create Ward Type",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("admin/ward_type_form.html", context)


@router.post("/admin/ward-types/create", name="ward_type_create", status_code=status.HTTP_302_FOUND)
def create_ward_type_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """Handle create ward type form submission"""
    try:
        # Check if ward type with same name or code already exists
        if code:
            existing = ward_type_crud.get_ward_type_by_code(db, code)
            if existing:
                return RedirectResponse(
                    url=str(request.url_for("ward_type_create_form")) + "?error=code_exists",
                    status_code=status.HTTP_302_FOUND
                )
        
        existing_name = ward_type_crud.get_ward_type_by_name(db, name)
        if existing_name:
            return RedirectResponse(
                url=str(request.url_for("ward_type_create_form")) + "?error=name_exists",
                status_code=status.HTTP_302_FOUND
            )
        
        ward_type_data = WardTypeCreate(
            name=name,
            code=code if code else None,
            description=description if description else None
        )
        
        ward_type_crud.create_ward_type(db, ward_type_data)
        
        return RedirectResponse(
            url=str(request.url_for("ward_types_list")) + "?status=created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ward_type_create_form")) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/admin/ward-types/{ward_type_id}", name="ward_type_detail")
def ward_type_detail(
    request: Request,
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show ward type detail (admins can view inactive ward types)"""
    # Allow admins to view inactive ward types
    ward_type = ward_type_crud.get_ward_type(db, ward_type_id, include_inactive=True)
    if not ward_type:
        raise HTTPException(status_code=404, detail="Ward type not found")
    
    context = {
        "request": request,
        "title": f"Ward Type: {ward_type.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "ward_type": ward_type
    }
    return templates.TemplateResponse("admin/ward_type_detail.html", context)


@router.get("/admin/ward-types/{ward_type_id}/edit", name="ward_type_edit_form")
def ward_type_edit_form(
    request: Request,
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show edit ward type form (admins can edit inactive ward types)"""
    # Allow admins to edit inactive ward types (e.g., reactivate them)
    ward_type = ward_type_crud.get_ward_type(db, ward_type_id, include_inactive=True)
    if not ward_type:
        raise HTTPException(status_code=404, detail="Ward type not found")
    
    context = {
        "request": request,
        "title": f"Edit Ward Type: {ward_type.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "ward_type": ward_type
    }
    return templates.TemplateResponse("admin/ward_type_form.html", context)


@router.post("/admin/ward-types/{ward_type_id}/edit", name="ward_type_update", status_code=status.HTTP_302_FOUND)
def update_ward_type_form(
    request: Request,
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None)
):
    """Handle update ward type form submission"""
    try:
        # Convert checkbox to boolean (HTML checkbox sends "on" when checked, nothing when unchecked)
        is_active_bool = True if is_active else False
        
        ward_type_update = WardTypeUpdate(
            name=name,
            code=code if code else None,
            description=description if description else None,
            is_active=is_active_bool
        )
        
        ward_type = ward_type_crud.update_ward_type(
            db, ward_type_id, ward_type_update
        )
        if not ward_type:
            raise HTTPException(status_code=404, detail="Ward type not found")
        
        return RedirectResponse(
            url=str(request.url_for("ward_type_detail", ward_type_id=ward_type_id)) + "?status=updated",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ward_type_edit_form", ward_type_id=ward_type_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/admin/ward-types/{ward_type_id}/delete", name="ward_type_delete", status_code=status.HTTP_302_FOUND)
def delete_ward_type_form(
    request: Request,
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Handle delete ward type form submission"""
    success = ward_type_crud.delete_ward_type(db, ward_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ward type not found")
    
    return RedirectResponse(
        url=str(request.url_for("ward_types_list")) + "?status=deleted",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/admin/ward-types/{ward_type_id}/toggle-status", name="ward_type_toggle_status", status_code=status.HTTP_302_FOUND)
def toggle_ward_type_status(
    request: Request,
    ward_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    return_to: Optional[str] = Query("list")
):
    """Toggle ward type active status (activate/deactivate)"""
    ward_type = ward_type_crud.get_ward_type(db, ward_type_id, include_inactive=True)
    if not ward_type:
        raise HTTPException(status_code=404, detail="Ward type not found")
    
    # Toggle status
    ward_type.is_active = not ward_type.is_active
    db.commit()
    db.refresh(ward_type)
    
    status_message = "activated" if ward_type.is_active else "deactivated"
    
    # Redirect based on return_to parameter
    if return_to == "detail":
        return RedirectResponse(
            url=str(request.url_for("ward_type_detail", ward_type_id=ward_type_id)) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(
            url=str(request.url_for("ward_types_list")) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )

