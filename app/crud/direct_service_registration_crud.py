"""
Direct Service Registration CRUD Operations

CRUD operations for direct service registration.
Supports: Antenatal, Lab, Pharmacy, Radiology, Procedures
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_
from typing import List, Optional, Tuple
from datetime import datetime, date

from app.models.direct_service_registration_models import DirectServiceRegistration
from app.schemas.direct_service_registration_schemas import DirectServiceRegistrationCreate, DirectServiceRegistrationUpdate


def create_direct_service_registration(
    db: Session,
    registration: DirectServiceRegistrationCreate,
    registered_by_id: int
) -> DirectServiceRegistration:
    """
    Create a new direct service registration record.
    """
    db_registration = DirectServiceRegistration(
        patient_id=registration.patient_id,
        service_type=registration.service_type,
        service_type_label=registration.service_type_label or get_service_type_label(registration.service_type),
        gestational_weeks=registration.gestational_weeks,
        lmp=registration.lmp,
        edd=registration.edd,
        registration_notes=registration.registration_notes,
        registered_by_id=registered_by_id,
        status="pending"
    )
    db.add(db_registration)
    db.commit()
    db.refresh(db_registration)
    return db_registration


def get_direct_service_registration(db: Session, registration_id: int) -> Optional[DirectServiceRegistration]:
    """Get direct service registration by ID"""
    return db.query(DirectServiceRegistration).options(
        joinedload(DirectServiceRegistration.patient),
        joinedload(DirectServiceRegistration.registered_by)
    ).filter(
        DirectServiceRegistration.id == registration_id
    ).first()


def get_direct_service_registrations(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    service_type: Optional[str] = None,
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Tuple[List[DirectServiceRegistration], int]:
    """
    Get direct service registrations with optional filters.
    """
    query = db.query(DirectServiceRegistration).options(
        joinedload(DirectServiceRegistration.patient),
        joinedload(DirectServiceRegistration.registered_by)
    )
    
    # Apply filters
    if service_type:
        query = query.filter(DirectServiceRegistration.service_type == service_type)
    
    if patient_id:
        query = query.filter(DirectServiceRegistration.patient_id == patient_id)
    
    if status:
        query = query.filter(DirectServiceRegistration.status == status)
    
    if from_date:
        query = query.filter(DirectServiceRegistration.created_at >= from_date)
    
    if to_date:
        query = query.filter(DirectServiceRegistration.created_at <= to_date)
    
    # Get total count
    total_count = query.count()
    
    # Apply sorting and pagination
    registrations = query.order_by(desc(DirectServiceRegistration.created_at)).offset(skip).limit(limit).all()
    
    return registrations, total_count


def update_direct_service_registration(
    db: Session,
    registration_id: int,
    update_data: DirectServiceRegistrationUpdate
) -> Optional[DirectServiceRegistration]:
    """
    Update a direct service registration.
    """
    db_registration = get_direct_service_registration(db, registration_id)
    if not db_registration:
        return None
    
    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(db_registration, field, value)
    
    # Update timestamp
    db_registration.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_registration)
    return db_registration


def complete_direct_service_registration(
    db: Session,
    registration_id: int,
    order_id: int,
    order_type: str
) -> Optional[DirectServiceRegistration]:
    """
    Mark a direct service registration as completed with the order details.
    """
    db_registration = get_direct_service_registration(db, registration_id)
    if not db_registration:
        return None
    
    db_registration.status = "completed"
    db_registration.order_id = order_id
    db_registration.order_type = order_type
    db_registration.completed_at = datetime.now()
    db_registration.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_registration)
    return db_registration


def cancel_direct_service_registration(
    db: Session,
    registration_id: int
) -> Optional[DirectServiceRegistration]:
    """
    Cancel a direct service registration.
    """
    db_registration = get_direct_service_registration(db, registration_id)
    if not db_registration:
        return None
    
    db_registration.status = "cancelled"
    db_registration.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_registration)
    return db_registration


def get_direct_service_registrations_by_patient(
    db: Session,
    patient_id: int,
    limit: int = 50
) -> List[DirectServiceRegistration]:
    """
    Get all direct service registrations for a patient.
    """
    return db.query(DirectServiceRegistration).options(
        joinedload(DirectServiceRegistration.registered_by)
    ).filter(
        DirectServiceRegistration.patient_id == patient_id
    ).order_by(desc(DirectServiceRegistration.created_at)).limit(limit).all()


def get_today_direct_service_registrations(
    db: Session,
    service_type: Optional[str] = None
) -> List[DirectServiceRegistration]:
    """
    Get today's direct service registrations.
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(DirectServiceRegistration).options(
        joinedload(DirectServiceRegistration.patient),
        joinedload(DirectServiceRegistration.registered_by)
    ).filter(
        DirectServiceRegistration.created_at >= today_start
    )
    
    if service_type:
        query = query.filter(DirectServiceRegistration.service_type == service_type)
    
    return query.order_by(desc(DirectServiceRegistration.created_at)).all()


def get_direct_service_statistics(
    db: Session,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> dict:
    """
    Get statistics for direct service registrations.
    """
    # Base query
    query = db.query(DirectServiceRegistration)
    
    if from_date:
        query = query.filter(DirectServiceRegistration.created_at >= from_date)
    
    if to_date:
        query = query.filter(DirectServiceRegistration.created_at <= to_date)
    
    total = query.count()
    
    # Count by service type
    by_service_type = {}
    for st in ["antenatal", "lab", "pharmacy", "radiology", "procedure"]:
        count = query.filter(DirectServiceRegistration.service_type == st).count()
        by_service_type[st] = count
    
    # Count by status
    by_status = {}
    for status in ["pending", "in_progress", "completed", "cancelled"]:
        count = query.filter(DirectServiceRegistration.status == status).count()
        by_status[status] = count
    
    return {
        "total": total,
        "by_service_type": by_service_type,
        "by_status": by_status
    }


def get_service_type_label(service_type: str) -> str:
    """Get human-readable label for service type"""
    labels = {
        "antenatal": "Antenatal Care",
        "lab": "Laboratory",
        "pharmacy": "Pharmacy",
        "radiology": "Radiology",
        "procedure": "Procedure"
    }
    return labels.get(service_type, service_type.title())
