from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.models.service_pricing_models import ServicePricing
from app.schemas.service_pricing_schemas import ServicePricingCreate, ServicePricingUpdate


def create_service_pricing(db: Session, pricing: ServicePricingCreate, created_by_id: int) -> ServicePricing:
    """Create a new service pricing entry"""
    db_pricing = ServicePricing(**pricing.dict(), created_by_id=created_by_id)
    db.add(db_pricing)
    try:
        db.commit()
        db.refresh(db_pricing)
    except Exception as e:
        db.rollback()
        raise e
    return db_pricing


def get_service_pricing(db: Session, pricing_id: int) -> Optional[ServicePricing]:
    """Get a service pricing by ID"""
    return db.query(ServicePricing).filter(ServicePricing.id == pricing_id).first()


def get_service_pricing_by_name(db: Session, service_name: str) -> Optional[ServicePricing]:
    """Get service pricing by service name"""
    return db.query(ServicePricing).filter(
        ServicePricing.service_name == service_name,
        ServicePricing.is_active == True
    ).first()


def get_service_pricing_by_code(db: Session, service_code: str) -> Optional[ServicePricing]:
    """Get service pricing by service code"""
    return db.query(ServicePricing).filter(
        ServicePricing.service_code == service_code,
        ServicePricing.is_active == True
    ).first()


def get_service_pricing_by_charge_type(db: Session, charge_type: str) -> List[ServicePricing]:
    """Get all active service pricing for a specific charge type"""
    return db.query(ServicePricing).filter(
        ServicePricing.charge_type == charge_type,
        ServicePricing.is_active == True
    ).all()


def get_all_service_pricing(db: Session, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[ServicePricing]:
    """Get all service pricing entries"""
    query = db.query(ServicePricing)
    if not include_inactive:
        query = query.filter(ServicePricing.is_active == True)
    return query.order_by(ServicePricing.charge_type, ServicePricing.service_name).offset(skip).limit(limit).all()


def update_service_pricing(db: Session, pricing_id: int, pricing_update: ServicePricingUpdate, updated_by_id: int) -> Optional[ServicePricing]:
    """Update a service pricing entry"""
    db_pricing = db.query(ServicePricing).filter(ServicePricing.id == pricing_id).first()
    if not db_pricing:
        return None
    
    update_data = pricing_update.dict(exclude_unset=True)
    update_data['updated_by_id'] = updated_by_id
    
    for field, value in update_data.items():
        setattr(db_pricing, field, value)
    
    try:
        db.commit()
        db.refresh(db_pricing)
    except Exception as e:
        db.rollback()
        raise e
    return db_pricing


def delete_service_pricing(db: Session, pricing_id: int) -> bool:
    """Soft delete a service pricing entry"""
    db_pricing = db.query(ServicePricing).filter(ServicePricing.id == pricing_id).first()
    if not db_pricing:
        return False
    
    db_pricing.is_active = False
    db.commit()
    return True


def get_default_price_for_service(db: Session, service_name: str, charge_type: str) -> Optional[Decimal]:
    """Get default price for a service, useful for charge automation"""
    pricing = db.query(ServicePricing).filter(
        ServicePricing.service_name == service_name,
        ServicePricing.charge_type == charge_type,
        ServicePricing.is_active == True
    ).first()
    
    if pricing:
        return pricing.unit_price
    return None

