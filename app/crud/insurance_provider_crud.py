"""
CRUD operations for Insurance Providers.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.insurance_provider_models import InsuranceProvider
from app.schemas.insurance_provider_schemas import InsuranceProviderCreate, InsuranceProviderUpdate


def create_insurance_provider(db: Session, insurance_provider: InsuranceProviderCreate) -> InsuranceProvider:
    """Create a new insurance provider"""
    db_insurance_provider = InsuranceProvider(**insurance_provider.model_dump())
    db.add(db_insurance_provider)
    db.commit()
    db.refresh(db_insurance_provider)
    return db_insurance_provider


def get_insurance_provider(db: Session, insurance_provider_id: int) -> Optional[InsuranceProvider]:
    """Get an insurance provider by ID"""
    return db.query(InsuranceProvider).filter(
        InsuranceProvider.id == insurance_provider_id,
        InsuranceProvider.is_active == True
    ).first()


def get_insurance_provider_by_code(db: Session, code: str) -> Optional[InsuranceProvider]:
    """Get an insurance provider by code"""
    return db.query(InsuranceProvider).filter(
        InsuranceProvider.code == code,
        InsuranceProvider.is_active == True
    ).first()


def get_insurance_provider_by_name(db: Session, name: str) -> Optional[InsuranceProvider]:
    """Get an insurance provider by name"""
    return db.query(InsuranceProvider).filter(
        InsuranceProvider.name == name,
        InsuranceProvider.is_active == True
    ).first()


def get_insurance_providers(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[InsuranceProvider]:
    """Get all insurance providers"""
    query = db.query(InsuranceProvider)
    if active_only:
        query = query.filter(InsuranceProvider.is_active == True)
    return query.offset(skip).limit(limit).all()


def update_insurance_provider(
    db: Session, 
    insurance_provider_id: int, 
    insurance_provider_update: InsuranceProviderUpdate
) -> Optional[InsuranceProvider]:
    """Update an insurance provider"""
    db_insurance_provider = get_insurance_provider(db, insurance_provider_id)
    if not db_insurance_provider:
        return None
    
    update_data = insurance_provider_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_insurance_provider, field, value)
    
    db.commit()
    db.refresh(db_insurance_provider)
    return db_insurance_provider


def delete_insurance_provider(db: Session, insurance_provider_id: int) -> bool:
    """Soft delete an insurance provider"""
    db_insurance_provider = get_insurance_provider(db, insurance_provider_id)
    if not db_insurance_provider:
        return False
    
    db_insurance_provider.is_active = False
    db.commit()
    return True

