"""
API routes for Shift Type management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.crud import shift_type_crud
from app.schemas.shift_type_schemas import ShiftTypeCreate, ShiftTypeUpdate

router = APIRouter(tags=["Shift Types"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/shift-types", name="shift_types_list")
def shift_types_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False)
):
    """List all shift types"""
    shift_types, total = shift_type_crud.get_shift_types(db, skip=skip, limit=limit, active_only=active_only)
    
    context = {
        "request": request,
        "title": "Shift Types",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "shift_types": shift_types,
        "total": total,
        "skip": skip,
        "limit": limit,
        "active_only": active_only
    }
    return templates.TemplateResponse("admin/shift_types_list.html", context)


@router.get("/admin/shift-types/create", name="shift_type_create_form")
def shift_type_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create shift type form"""
    context = {
        "request": request,
        "title": "Create Shift Type",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("admin/shift_type_form.html", context)


@router.post("/admin/shift-types/create", name="shift_type_create")
def shift_type_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    default_start_hour: Optional[int] = Form(None),
    default_end_hour: Optional[int] = Form(None),
    is_active: bool = Form(True)
):
    """Create a new shift type"""
    try:
        shift_type_data = ShiftTypeCreate(
            name=name,
            code=code if code and code.strip() else None,
            description=description if description and description.strip() else None,
            default_start_hour=default_start_hour if default_start_hour is not None else None,
            default_end_hour=default_end_hour if default_end_hour is not None else None,
            is_active=is_active
        )
        shift_type = shift_type_crud.create_shift_type(db, shift_type_data)
        return RedirectResponse(
            url=f"/admin/shift-types?status=created&shift_type_id={shift_type.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/shift-types/create?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/admin/shift-types/{shift_type_id}", name="shift_type_detail")
def shift_type_detail(
    request: Request,
    shift_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """View shift type details"""
    shift_type = shift_type_crud.get_shift_type(db, shift_type_id)
    if not shift_type:
        raise HTTPException(status_code=404, detail="Shift type not found")
    
    context = {
        "request": request,
        "title": f"Shift Type: {shift_type.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "shift_type": shift_type
    }
    return templates.TemplateResponse("admin/shift_type_detail.html", context)


@router.get("/admin/shift-types/{shift_type_id}/edit", name="shift_type_edit_form")
def shift_type_edit_form(
    request: Request,
    shift_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show edit shift type form"""
    shift_type = shift_type_crud.get_shift_type(db, shift_type_id)
    if not shift_type:
        raise HTTPException(status_code=404, detail="Shift type not found")
    
    context = {
        "request": request,
        "title": f"Edit Shift Type: {shift_type.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "shift_type": shift_type
    }
    return templates.TemplateResponse("admin/shift_type_form.html", context)


@router.post("/admin/shift-types/{shift_type_id}/edit", name="shift_type_update")
def shift_type_update(
    request: Request,
    shift_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    default_start_hour: Optional[int] = Form(None),
    default_end_hour: Optional[int] = Form(None),
    is_active: Optional[str] = Form(None)
):
    """Update a shift type"""
    try:
        # Convert checkbox to boolean (HTML checkbox sends "on" when checked, nothing when unchecked)
        is_active_bool = True if is_active else False
        
        update_data = ShiftTypeUpdate(
            name=name if name and name.strip() else None,
            code=code if code and code.strip() else None,
            description=description if description and description.strip() else None,
            default_start_hour=default_start_hour if default_start_hour is not None else None,
            default_end_hour=default_end_hour if default_end_hour is not None else None,
            is_active=is_active_bool
        )
        shift_type = shift_type_crud.update_shift_type(db, shift_type_id, update_data)
        if not shift_type:
            raise HTTPException(status_code=404, detail="Shift type not found")
        
        return RedirectResponse(
            url=f"/admin/shift-types?status=updated&shift_type_id={shift_type.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/shift-types/{shift_type_id}/edit?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/admin/shift-types/{shift_type_id}/toggle-status", name="shift_type_toggle_status", status_code=status.HTTP_302_FOUND)
def toggle_shift_type_status(
    request: Request,
    shift_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    return_to: Optional[str] = Query("list")
):
    """Toggle shift type active status (activate/deactivate)"""
    shift_type = shift_type_crud.get_shift_type(db, shift_type_id)
    if not shift_type:
        raise HTTPException(status_code=404, detail="Shift type not found")
    
    # Toggle status
    shift_type.is_active = not shift_type.is_active
    db.commit()
    db.refresh(shift_type)
    
    status_message = "activated" if shift_type.is_active else "deactivated"
    
    # Redirect based on return_to parameter
    if return_to == "detail":
        return RedirectResponse(
            url=str(request.url_for("shift_type_detail", shift_type_id=shift_type_id)) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(
            url=str(request.url_for("shift_types_list")) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )

