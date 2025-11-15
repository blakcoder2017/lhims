from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.shift_type_models import ShiftType
from app.schemas.shift_type_schemas import ShiftTypeCreate, ShiftTypeUpdate


def create_shift_type(db: Session, shift_type: ShiftTypeCreate) -> ShiftType:
    """Create a new shift type"""
    db_shift_type = ShiftType(**shift_type.model_dump())
    db.add(db_shift_type)
    db.commit()
    db.refresh(db_shift_type)
    return db_shift_type


def get_shift_type(db: Session, shift_type_id: int) -> Optional[ShiftType]:
    """Get a shift type by ID"""
    return db.query(ShiftType).filter(ShiftType.id == shift_type_id).first()


def get_shift_types(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False
) -> tuple[List[ShiftType], int]:
    """Get all shift types with optional filtering"""
    query = db.query(ShiftType)
    
    if active_only:
        query = query.filter(ShiftType.is_active == True)
    
    total = query.count()
    shift_types = query.offset(skip).limit(limit).all()
    
    return shift_types, total


def get_shift_type_by_name(db: Session, name: str) -> Optional[ShiftType]:
    """Get a shift type by name"""
    return db.query(ShiftType).filter(ShiftType.name == name).first()


def update_shift_type(
    db: Session, 
    shift_type_id: int, 
    shift_type: ShiftTypeUpdate
) -> Optional[ShiftType]:
    """Update a shift type"""
    db_shift_type = get_shift_type(db, shift_type_id)
    if not db_shift_type:
        return None
    
    update_data = shift_type.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_shift_type, field, value)
    
    db.commit()
    db.refresh(db_shift_type)
    return db_shift_type


def delete_shift_type(db: Session, shift_type_id: int) -> bool:
    """Soft delete a shift type"""
    db_shift_type = get_shift_type(db, shift_type_id)
    if not db_shift_type:
        return False
    
    db_shift_type.is_active = False
    db.commit()
    return True

