"""
CRUD operations for Ward Types.
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from app.models.ward_type_models import WardType
from app.schemas.ward_type_schemas import WardTypeCreate, WardTypeUpdate


def create_ward_type(db: Session, ward_type: WardTypeCreate) -> WardType:
    """Create a new ward type"""
    db_ward_type = WardType(**ward_type.model_dump())
    db.add(db_ward_type)
    db.commit()
    db.refresh(db_ward_type)
    return db_ward_type


def get_ward_type(db: Session, ward_type_id: int, include_inactive: bool = False) -> Optional[WardType]:
    """Get a ward type by ID
    
    Args:
        db: Database session
        ward_type_id: ID of the ward type
        include_inactive: If True, include inactive ward types (for admin viewing)
    """
    query = db.query(WardType).filter(WardType.id == ward_type_id)
    if not include_inactive:
        query = query.filter(WardType.is_active == True)
    return query.first()


def get_ward_type_by_name(db: Session, name: str) -> Optional[WardType]:
    """Get a ward type by name"""
    return db.query(WardType).filter(
        WardType.name == name,
        WardType.is_active == True
    ).first()


def get_ward_type_by_code(db: Session, code: str) -> Optional[WardType]:
    """Get a ward type by code"""
    return db.query(WardType).filter(
        WardType.code == code,
        WardType.is_active == True
    ).first()


def get_ward_types(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True
) -> Tuple[List[WardType], int]:
    """
    Get all ward types with pagination.
    Returns tuple of (ward_types list, total count)
    """
    query = db.query(WardType)
    if active_only:
        query = query.filter(WardType.is_active == True)
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination and ordering
    ward_types = query.order_by(WardType.name.asc()).offset(skip).limit(limit).all()
    
    return ward_types, total_count


def update_ward_type(
    db: Session,
    ward_type_id: int,
    ward_type_update: WardTypeUpdate
) -> Optional[WardType]:
    """Update a ward type (allows updating inactive ward types, e.g., reactivating them)"""
    # Allow updating inactive ward types (e.g., reactivating them)
    db_ward_type = get_ward_type(db, ward_type_id, include_inactive=True)
    if not db_ward_type:
        return None
    
    update_data = ward_type_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_ward_type, field, value)
    
    db.commit()
    db.refresh(db_ward_type)
    return db_ward_type


def delete_ward_type(db: Session, ward_type_id: int) -> bool:
    """Soft delete a ward type (allows deleting already inactive ward types)"""
    # Allow deleting inactive ward types (though they're already inactive)
    db_ward_type = get_ward_type(db, ward_type_id, include_inactive=True)
    if not db_ward_type:
        return False
    
    db_ward_type.is_active = False
    db.commit()
    return True

