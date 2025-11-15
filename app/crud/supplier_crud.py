from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models.supplier_models import Supplier
from app.schemas.supplier_schemas import SupplierCreate, SupplierUpdate


def create_supplier(db: Session, supplier: SupplierCreate) -> Supplier:
    """Create a new supplier"""
    db_supplier = Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


def get_supplier(db: Session, supplier_id: int) -> Optional[Supplier]:
    """Get a supplier by ID"""
    return db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.is_active == True
    ).first()


def get_supplier_by_code(db: Session, code: str) -> Optional[Supplier]:
    """Get a supplier by code"""
    return db.query(Supplier).filter(
        Supplier.code == code,
        Supplier.is_active == True
    ).first()


def get_suppliers(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[Supplier]:
    """Get all suppliers with optional search"""
    query = db.query(Supplier).filter(Supplier.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                Supplier.name.ilike(f"%{search}%"),
                Supplier.code.ilike(f"%{search}%"),
                Supplier.contact_person.ilike(f"%{search}%")
            )
        )
    
    return query.order_by(Supplier.name).offset(skip).limit(limit).all()


def update_supplier(db: Session, supplier_id: int, supplier_update: SupplierUpdate) -> Optional[Supplier]:
    """Update a supplier"""
    db_supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not db_supplier:
        return None
    
    update_data = supplier_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_supplier, field, value)
    
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


def delete_supplier(db: Session, supplier_id: int) -> bool:
    """Soft delete a supplier"""
    db_supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not db_supplier:
        return False
    
    db_supplier.is_active = False
    db.commit()
    return True

