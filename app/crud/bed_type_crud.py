from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.bed_type_models import BedType
from app.schemas.bed_type_schemas import BedTypeCreate, BedTypeUpdate


def create_bed_type(db: Session, bed_type: BedTypeCreate) -> BedType:
    """Create a new bed type"""
    db_bed_type = BedType(**bed_type.model_dump())
    db.add(db_bed_type)
    db.commit()
    db.refresh(db_bed_type)
    return db_bed_type


def get_bed_type(db: Session, bed_type_id: int) -> Optional[BedType]:
    """Get a bed type by ID"""
    return db.query(BedType).filter(BedType.id == bed_type_id).first()


def get_bed_types(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False
) -> tuple[List[BedType], int]:
    """Get all bed types with optional filtering"""
    query = db.query(BedType)
    
    if active_only:
        query = query.filter(BedType.is_active == True)
    
    total = query.count()
    bed_types = query.offset(skip).limit(limit).all()
    
    return bed_types, total


def get_bed_type_by_name(db: Session, name: str) -> Optional[BedType]:
    """Get a bed type by name"""
    return db.query(BedType).filter(BedType.name == name).first()


def get_bed_type_by_code(db: Session, code: str) -> Optional[BedType]:
    """Get a bed type by code"""
    return db.query(BedType).filter(BedType.code == code).first()


def update_bed_type(
    db: Session, 
    bed_type_id: int, 
    bed_type: BedTypeUpdate
) -> Optional[BedType]:
    """Update a bed type"""
    db_bed_type = get_bed_type(db, bed_type_id)
    if not db_bed_type:
        return None
    
    update_data = bed_type.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_bed_type, field, value)
    
    db.commit()
    db.refresh(db_bed_type)
    return db_bed_type


def delete_bed_type(db: Session, bed_type_id: int) -> bool:
    """Soft delete a bed type"""
    db_bed_type = get_bed_type(db, bed_type_id)
    if not db_bed_type:
        return False
    
    db_bed_type.is_active = False
    db.commit()
    return True

