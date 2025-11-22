"""
CRUD operations for Discharge Clearance.
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models.discharge_models import DischargeClearance


def get_discharge_clearance(db: Session, admission_id: int) -> Optional[DischargeClearance]:
    """Get discharge clearance for an admission"""
    return db.query(DischargeClearance).filter(
        DischargeClearance.admission_id == admission_id,
        DischargeClearance.is_active == True
    ).first()


def create_discharge_clearance(db: Session, admission_id: int, patient_id: int) -> DischargeClearance:
    """Create a discharge clearance record for an admission"""
    clearance = DischargeClearance(
        admission_id=admission_id,
        patient_id=patient_id,
        payment_cleared=False,
        nursing_cleared=False
    )
    db.add(clearance)
    db.commit()
    db.refresh(clearance)
    return clearance


def get_or_create_discharge_clearance(db: Session, admission_id: int, patient_id: int) -> DischargeClearance:
    """Get existing discharge clearance or create a new one"""
    clearance = get_discharge_clearance(db, admission_id)
    if clearance:
        return clearance
    return create_discharge_clearance(db, admission_id, patient_id)


def clear_payment(db: Session, admission_id: int, cleared_by_id: int, notes: Optional[str] = None) -> DischargeClearance:
    """Mark payment as cleared for discharge"""
    from app.models.ipd_models import Admission
    
    admission = db.query(Admission).filter(Admission.id == admission_id).first()
    if not admission:
        raise ValueError(f"Admission {admission_id} not found")
    
    clearance = get_or_create_discharge_clearance(db, admission_id, admission.patient_id)
    clearance.payment_cleared = True
    clearance.payment_cleared_at = datetime.now()
    clearance.payment_cleared_by_id = cleared_by_id
    if notes:
        clearance.payment_notes = notes
    
    db.commit()
    db.refresh(clearance)
    return clearance


def clear_nursing(db: Session, admission_id: int, cleared_by_id: int, notes: Optional[str] = None) -> DischargeClearance:
    """Mark nursing clearance as complete for discharge"""
    from app.models.ipd_models import Admission
    
    admission = db.query(Admission).filter(Admission.id == admission_id).first()
    if not admission:
        raise ValueError(f"Admission {admission_id} not found")
    
    clearance = get_or_create_discharge_clearance(db, admission_id, admission.patient_id)
    clearance.nursing_cleared = True
    clearance.nursing_cleared_at = datetime.now()
    clearance.nursing_cleared_by_id = cleared_by_id
    if notes:
        clearance.nursing_notes = notes
    
    db.commit()
    db.refresh(clearance)
    return clearance

