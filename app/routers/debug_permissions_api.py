"""
Debug API to check user permissions
"""
from fastapi import APIRouter, Depends
from app.db.database import get_db
from app.core.deps import get_current_user, get_user_permissions

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/my-permissions")
def get_my_permissions(current_user = Depends(get_current_user)):
    """
    Get current user's permissions from the database.
    Permissions are assigned via the admin panel (/admin/roles/permissions)
    """
    # Get permissions from database
    permissions = get_user_permissions(current_user)
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name if current_user.role else None,
        "permissions_from_database": sorted(permissions),
        "total_permissions": len(permissions),
        "note": "Permissions are assigned via /admin/roles/permissions"
    }
