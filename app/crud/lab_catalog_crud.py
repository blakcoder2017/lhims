from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models.lab_catalog_models import LabTest
from app.models.lab_models import ReferenceRange
from app.schemas.lab_catalog_schemas import LabTestCreate, LabTestUpdate, ReferenceRangeCreate, ReferenceRangeUpdate


def create_lab_test(db: Session, test: LabTestCreate) -> LabTest:
    """Create a new lab test"""
    db_test = LabTest(**test.dict())
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test


def get_lab_test(db: Session, test_id: int) -> Optional[LabTest]:
    """Get a lab test by ID"""
    return db.query(LabTest).filter(
        LabTest.id == test_id,
        LabTest.is_active == True
    ).first()


def get_lab_test_by_code(db: Session, test_code: str) -> Optional[LabTest]:
    """Get a lab test by code"""
    return db.query(LabTest).filter(
        LabTest.test_code == test_code,
        LabTest.is_active == True
    ).first()


def get_lab_tests(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, category: Optional[str] = None) -> List[LabTest]:
    """Get all lab tests with optional search and category filter"""
    query = db.query(LabTest).filter(LabTest.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                LabTest.test_name.ilike(f"%{search}%"),
                LabTest.test_code.ilike(f"%{search}%"),
                LabTest.description.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(LabTest.test_category == category)
    
    return query.order_by(LabTest.test_name).offset(skip).limit(limit).all()


def update_lab_test(db: Session, test_id: int, test_update: LabTestUpdate) -> Optional[LabTest]:
    """Update a lab test"""
    db_test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not db_test:
        return None
    
    update_data = test_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_test, field, value)
    
    db.commit()
    db.refresh(db_test)
    return db_test


def delete_lab_test(db: Session, test_id: int) -> bool:
    """Soft delete a lab test"""
    db_test = db.query(LabTest).filter(LabTest.id == test_id).first()
    if not db_test:
        return False
    
    db_test.is_active = False
    db.commit()
    return True


def create_reference_range(db: Session, range_data: ReferenceRangeCreate) -> ReferenceRange:
    """Create a reference range"""
    db_range = ReferenceRange(**range_data.dict())
    db.add(db_range)
    db.commit()
    db.refresh(db_range)
    return db_range


def get_reference_ranges(db: Session, test_id: Optional[int] = None, test_name: Optional[str] = None) -> List[ReferenceRange]:
    """Get reference ranges"""
    query = db.query(ReferenceRange).filter(ReferenceRange.is_active == True)
    
    if test_id:
        query = query.filter(ReferenceRange.test_id == test_id)
    elif test_name:
        query = query.filter(ReferenceRange.test_name == test_name)
    
    return query.all()


def update_reference_range(db: Session, range_id: int, range_update: ReferenceRangeUpdate) -> Optional[ReferenceRange]:
    """Update a reference range"""
    db_range = db.query(ReferenceRange).filter(ReferenceRange.id == range_id).first()
    if not db_range:
        return None
    
    update_data = range_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_range, field, value)
    
    db.commit()
    db.refresh(db_range)
    return db_range

