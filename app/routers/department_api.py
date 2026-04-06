"""
API routes for Department management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, Request
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.crud import department_crud
from app.schemas.department_schemas import DepartmentCreate, DepartmentUpdate

router = APIRouter(tags=["Departments"])


@router.get("/admin/departments", name="departments_list")
def departments_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Management"])),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False)
):
    """List all departments"""
    departments, total = department_crud.get_departments(db, skip=skip, limit=limit, active_only=active_only)
    
    context = {
        "request": request,
        "title": "Departments",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "departments": departments,
        "total": total,
        "skip": skip,
        "limit": limit,
        "active_only": active_only
    }
    return templates.TemplateResponse("admin/departments_list.html", context)


@router.get("/admin/departments/create", name="department_create_form")
def department_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create department form"""
    context = {
        "request": request,
        "title": "Create Department",
        "current_user": current_user,
        "user_role": current_user.role.name
    }
    return templates.TemplateResponse("admin/department_form.html", context)


@router.post("/admin/departments/create", name="department_create")
def department_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    consultation_price: Optional[float] = Form(None),
    is_active: bool = Form(True)
):
    """Create a new department"""
    try:
        from decimal import Decimal
        department_data = DepartmentCreate(
            name=name,
            code=code if code and code.strip() else None,
            description=description if description and description.strip() else None,
            consultation_price=Decimal(str(consultation_price)) if consultation_price is not None else None,
            is_active=is_active
        )
        department = department_crud.create_department(db, department_data)
        return RedirectResponse(
            url=f"/admin/departments?status=created&department_id={department.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/departments/create?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/admin/departments/{department_id}", name="department_detail")
def department_detail(
    request: Request,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """View department details"""
    department = department_crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    context = {
        "request": request,
        "title": f"Department: {department.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "department": department
    }
    return templates.TemplateResponse("admin/department_detail.html", context)


@router.get("/admin/departments/{department_id}/edit", name="department_edit_form")
def department_edit_form(
    request: Request,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show edit department form"""
    department = department_crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    context = {
        "request": request,
        "title": f"Edit Department: {department.name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "department": department
    }
    return templates.TemplateResponse("admin/department_form.html", context)


@router.post("/admin/departments/{department_id}/edit", name="department_update")
def department_update(
    request: Request,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    consultation_price: Optional[float] = Form(None),
    is_active: Optional[str] = Form(None)
):
    """Update a department"""
    try:
        from decimal import Decimal
        # Convert checkbox to boolean (HTML checkbox sends "on" when checked, nothing when unchecked)
        is_active_bool = True if is_active else False
        
        update_data = DepartmentUpdate(
            name=name if name and name.strip() else None,
            code=code if code and code.strip() else None,
            description=description if description and description.strip() else None,
            consultation_price=Decimal(str(consultation_price)) if consultation_price is not None else None,
            is_active=is_active_bool
        )
        department = department_crud.update_department(db, department_id, update_data)
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")
        
        return RedirectResponse(
            url=f"/admin/departments?status=updated&department_id={department.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/admin/departments/{department_id}/edit?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/admin/departments/{department_id}/toggle-status", name="department_toggle_status", status_code=status.HTTP_302_FOUND)
def toggle_department_status(
    request: Request,
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    return_to: Optional[str] = Query("list")
):
    """Toggle department active status (activate/deactivate)"""
    department = department_crud.get_department(db, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Toggle status
    department.is_active = not department.is_active
    db.commit()
    db.refresh(department)
    
    status_message = "activated" if department.is_active else "deactivated"
    
    # Redirect based on return_to parameter
    if return_to == "detail":
        return RedirectResponse(
            url=str(request.url_for("department_detail", department_id=department_id)) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(
            url=str(request.url_for("departments_list")) + f"?status={status_message}",
            status_code=status.HTTP_302_FOUND
        )

