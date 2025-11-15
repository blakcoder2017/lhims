from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.permission_models import Permission
from app.models.user_models import Role


def get_permission(db: Session, permission_id: int) -> Optional[Permission]:
    """Get a permission by ID"""
    return db.query(Permission).filter(Permission.id == permission_id).first()


def get_permission_by_name(db: Session, name: str) -> Optional[Permission]:
    """Get a permission by name"""
    return db.query(Permission).filter(Permission.name == name).first()


def get_all_permissions(db: Session, module: Optional[str] = None, include_inactive: bool = False) -> List[Permission]:
    """Get all permissions, optionally filtered by module"""
    query = db.query(Permission)
    if module:
        query = query.filter(Permission.module == module)
    if not include_inactive:
        query = query.filter(Permission.is_active == True)
    return query.order_by(Permission.module, Permission.name).all()


def get_permissions_by_role(db: Session, role_id: int) -> List[Permission]:
    """Get all permissions for a specific role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return []
    return list(role.permissions)


def assign_permission_to_role(db: Session, role_id: int, permission_id: int) -> bool:
    """Assign a permission to a role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    
    if not role or not permission:
        return False
    
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()
    return True


def remove_permission_from_role(db: Session, role_id: int, permission_id: int) -> bool:
    """Remove a permission from a role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    
    if not role or not permission:
        return False
    
    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()
    return True


def create_permission(db: Session, name: str, description: Optional[str] = None, module: Optional[str] = None) -> Permission:
    """Create a new permission"""
    permission = Permission(
        name=name,
        description=description,
        module=module,
        is_active=True
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission

