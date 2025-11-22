"""
Procedure Catalog CRUD Operations

Database operations for procedure catalog management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List, Tuple
from decimal import Decimal

from app.models.procedure_catalog_models import ProcedureCatalog
from app.schemas.procedure_catalog_schemas import ProcedureCatalogCreate, ProcedureCatalogUpdate


def create_procedure_catalog(
    db: Session, 
    procedure_catalog: ProcedureCatalogCreate,
    created_by_id: Optional[int] = None
) -> ProcedureCatalog:
    """Create a new procedure catalog entry."""
    db_procedure = ProcedureCatalog(
        procedure_name=procedure_catalog.procedure_name,
        procedure_code=procedure_catalog.procedure_code,
        procedure_category=procedure_catalog.procedure_category,
        procedure_type=procedure_catalog.procedure_type,
        description=procedure_catalog.description,
        indication=procedure_catalog.indication,
        preparation_instructions=procedure_catalog.preparation_instructions,
        post_procedure_care=procedure_catalog.post_procedure_care,
        estimated_duration_minutes=procedure_catalog.estimated_duration_minutes,
        typical_duration_minutes=procedure_catalog.typical_duration_minutes,
        cash_price=procedure_catalog.cash_price,
        cash_currency=procedure_catalog.cash_currency or "GHS",
        nhis_covered=procedure_catalog.nhis_covered,
        nhis_code=procedure_catalog.nhis_code,
        nhis_price=procedure_catalog.nhis_price,
        private_insurance_covered=procedure_catalog.private_insurance_covered,
        private_insurance_price=procedure_catalog.private_insurance_price,
        requires_anesthesia=procedure_catalog.requires_anesthesia,
        typical_anesthesia_type=procedure_catalog.typical_anesthesia_type,
        requires_operating_room=procedure_catalog.requires_operating_room,
        typical_location=procedure_catalog.typical_location,
        is_specialized=procedure_catalog.is_specialized,
        requires_consultation=procedure_catalog.requires_consultation,
        is_active=True,
        created_by_id=created_by_id
    )
    
    db.add(db_procedure)
    db.commit()
    db.refresh(db_procedure)
    return db_procedure


def get_procedure_catalog(db: Session, catalog_id: int) -> Optional[ProcedureCatalog]:
    """Get a procedure catalog entry by ID."""
    return db.query(ProcedureCatalog).filter(
        ProcedureCatalog.id == catalog_id
    ).first()


def get_procedure_catalog_by_code(db: Session, procedure_code: str) -> Optional[ProcedureCatalog]:
    """Get a procedure catalog entry by code."""
    return db.query(ProcedureCatalog).filter(
        ProcedureCatalog.procedure_code == procedure_code,
        ProcedureCatalog.is_active == True
    ).first()


def get_procedure_catalog_by_name(db: Session, procedure_name: str) -> Optional[ProcedureCatalog]:
    """Get a procedure catalog entry by name."""
    return db.query(ProcedureCatalog).filter(
        ProcedureCatalog.procedure_name == procedure_name,
        ProcedureCatalog.is_active == True
    ).first()


def search_procedure_catalog(
    db: Session,
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    procedure_category: Optional[str] = None,
    procedure_type: Optional[str] = None,
    active_only: bool = True
) -> Tuple[List[ProcedureCatalog], int]:
    """
    Search procedure catalog with pagination and filtering.
    Returns tuple of (procedures list, total count)
    """
    base_query = db.query(ProcedureCatalog)
    
    if active_only:
        base_query = base_query.filter(ProcedureCatalog.is_active == True)
    
    # Apply search query
    if query:
        search_term = f"%{query.strip()}%"
        base_query = base_query.filter(
            or_(
                ProcedureCatalog.procedure_name.ilike(search_term),
                ProcedureCatalog.procedure_code.ilike(search_term),
                ProcedureCatalog.description.ilike(search_term),
                ProcedureCatalog.procedure_category.ilike(search_term)
            )
        )
    
    # Apply filters
    if procedure_category:
        base_query = base_query.filter(ProcedureCatalog.procedure_category == procedure_category)
    
    if procedure_type:
        base_query = base_query.filter(ProcedureCatalog.procedure_type == procedure_type)
    
    # Get total count before pagination
    total_count = base_query.count()
    
    # Apply pagination and ordering
    procedures = base_query.order_by(ProcedureCatalog.procedure_name.asc()).offset(skip).limit(limit).all()
    
    return procedures, total_count


def get_all_procedure_catalog(
    db: Session,
    active_only: bool = True
) -> List[ProcedureCatalog]:
    """Get all procedure catalog entries."""
    query = db.query(ProcedureCatalog)
    
    if active_only:
        query = query.filter(ProcedureCatalog.is_active == True)
    
    return query.order_by(ProcedureCatalog.procedure_name.asc()).all()


def update_procedure_catalog(
    db: Session,
    catalog_id: int,
    procedure_catalog_update: ProcedureCatalogUpdate,
    updated_by_id: Optional[int] = None
) -> Optional[ProcedureCatalog]:
    """Update a procedure catalog entry."""
    db_procedure = get_procedure_catalog(db, catalog_id)
    if not db_procedure:
        return None
    
    update_data = procedure_catalog_update.model_dump(exclude_unset=True)
    
    # Update fields
    for field, value in update_data.items():
        if value is not None:
            setattr(db_procedure, field, value)
    
    if updated_by_id:
        db_procedure.updated_by_id = updated_by_id
    
    db.commit()
    db.refresh(db_procedure)
    return db_procedure


def delete_procedure_catalog(db: Session, catalog_id: int) -> bool:
    """Soft delete a procedure catalog entry."""
    db_procedure = get_procedure_catalog(db, catalog_id)
    if not db_procedure:
        return False
    
    db_procedure.is_active = False
    db.commit()
    return True


def get_procedure_price(
    db: Session,
    procedure_catalog_id: Optional[int] = None,
    procedure_name: Optional[str] = None,
    procedure_code: Optional[str] = None,
    payment_mechanism: Optional[str] = None
) -> Optional[Decimal]:
    """
    Get procedure price based on payment mechanism.
    Returns cash price, NHIS price, or private insurance price.
    """
    procedure = None
    
    if procedure_catalog_id:
        procedure = get_procedure_catalog(db, procedure_catalog_id)
    elif procedure_code:
        procedure = get_procedure_catalog_by_code(db, procedure_code)
    elif procedure_name:
        procedure = get_procedure_catalog_by_name(db, procedure_name)
    
    if not procedure:
        return None
    
    # Return price based on payment mechanism
    if payment_mechanism == "nhis" and procedure.nhis_covered:
        return procedure.nhis_price or procedure.cash_price
    elif payment_mechanism == "private_insurance" and procedure.private_insurance_covered:
        return procedure.private_insurance_price or procedure.cash_price
    else:
        # Cash or default
        return procedure.cash_price

