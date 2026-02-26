from fastapi import APIRouter, Depends, HTTPException, Request, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.deps import role_required
from app.models.user_models import Role
from app.models.permission_models import Permission
from app.crud import permission_crud

router = APIRouter(tags=["Role Permissions"])


@router.get("/admin/roles/permissions", name="role_permissions_management")
def role_permissions_management(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"])),
    role_id: Optional[int] = Query(None)
):
    """Role permissions management dashboard"""
    roles = db.query(Role).all()
    all_permissions = permission_crud.get_all_permissions(db)
    
    # Group permissions by module
    permissions_by_module = {}
    for perm in all_permissions:
        module = perm.module or "other"
        if module not in permissions_by_module:
            permissions_by_module[module] = []
        permissions_by_module[module].append(perm)
    
    selected_role = None
    role_permissions = []
    if role_id:
        selected_role = db.query(Role).filter(Role.id == role_id).first()
        if selected_role:
            role_permissions = permission_crud.get_permissions_by_role(db, role_id)
            role_permissions = [p.id for p in role_permissions]  # Convert to list of IDs for easier checking
    
    context = {
        "request": request,
        "title": "Role Permissions Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "roles": roles,
        "permissions_by_module": permissions_by_module,
        "selected_role": selected_role,
        "role_permissions": role_permissions
    }
    return templates.TemplateResponse("admin/role_permissions.html", context)


@router.post("/admin/roles/{role_id}/permissions", name="update_role_permissions", status_code=302)
async def update_role_permissions(
    request: Request,
    role_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Update permissions for a role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Get form data - permission_ids can be multiple values
    form_data = await request.form()
    permission_ids = form_data.getlist("permission_ids")
    
    # Convert to integers
    try:
        selected_permission_ids = {int(pid) for pid in permission_ids if pid}
    except (ValueError, TypeError):
        selected_permission_ids = set()
    
    # Get all permissions for this role
    current_permissions = permission_crud.get_permissions_by_role(db, role_id)
    current_permission_ids = {p.id for p in current_permissions}
    
    # Remove permissions that are not selected
    for perm in current_permissions:
        if perm.id not in selected_permission_ids:
            permission_crud.remove_permission_from_role(db, role_id, perm.id)
    
    # Add new permissions that are selected
    for perm_id in selected_permission_ids:
        if perm_id not in current_permission_ids:
            permission_crud.assign_permission_to_role(db, role_id, perm_id)
    
    return RedirectResponse(
        url=f"/admin/roles/permissions?role_id={role_id}&status=updated",
        status_code=302
    )

