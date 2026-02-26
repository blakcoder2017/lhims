from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.models.department_models import Department
from app.schemas.department_schemas import DepartmentCreate, DepartmentUpdate


def create_department(db: Session, department: DepartmentCreate) -> Department:
    """Create a new department"""
    db_department = Department(**department.model_dump())
    db.add(db_department)
    db.commit()
    db.refresh(db_department)
    return db_department


def get_department(db: Session, department_id: int) -> Optional[Department]:
    """Get a department by ID"""
    return db.query(Department).filter(Department.id == department_id).first()


def get_departments(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    active_only: bool = False
) -> tuple[List[Department], int]:
    """Get all departments with optional filtering"""
    query = db.query(Department)
    
    if active_only:
        query = query.filter(Department.is_active == True)
    
    total = query.count()
    departments = query.offset(skip).limit(limit).all()
    
    return departments, total


def get_department_by_name(db: Session, name: str) -> Optional[Department]:
    """Get a department by name (case-insensitive, strips whitespace)."""
    if not name or not str(name).strip():
        return None
    clean = str(name).strip()
    return db.query(Department).filter(func.lower(Department.name) == clean.lower()).first()


def update_department(
    db: Session, 
    department_id: int, 
    department: DepartmentUpdate
) -> Optional[Department]:
    """Update a department"""
    db_department = get_department(db, department_id)
    if not db_department:
        return None
    
    update_data = department.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_department, field, value)
    
    db.commit()
    db.refresh(db_department)
    return db_department


def delete_department(db: Session, department_id: int) -> bool:
    """Soft delete a department"""
    db_department = get_department(db, department_id)
    if not db_department:
        return False
    
    db_department.is_active = False
    db.commit()
    return True

