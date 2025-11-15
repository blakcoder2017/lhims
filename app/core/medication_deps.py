"""
Dependencies for Medication Administration Routes

Reusable dependencies for validating admission and prescription access.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import ipd_crud
from app.models.ipd_models import Admission, AdmissionStatus
from app.models.encounter_models import Prescription, OrderStatus
from typing import Optional


def get_active_admission(
    admission_id: int,
    db: Session = Depends(get_db)
) -> Admission:
    """
    Dependency to get and validate an active admission.
    Raises HTTPException if admission not found or not active.
    """
    admission = ipd_crud.get_admission(db, admission_id)
    
    if not admission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admission with ID {admission_id} not found"
        )
    
    if admission.status != AdmissionStatus.ADMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only record medications for active admissions. Current status: {admission.status.value}"
        )
    
    return admission


def get_valid_prescription(
    prescription_id: int,
    admission: Admission = Depends(get_active_admission),
    db: Session = Depends(get_db)
) -> Prescription:
    """
    Dependency to get and validate a prescription for medication administration.
    Raises HTTPException if prescription is invalid.
    """
    from app.models.encounter_models import Encounter
    
    if not prescription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prescription is required for medication administration"
        )
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {prescription_id} not found"
        )
    
    # Allow completed (dispensed) or cancelled (not in stock) prescriptions
    if prescription.status not in [OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prescription must be dispensed (completed) or cancelled (not in stock) before administration. Current status: {prescription.status.value}"
        )
    
    # Verify prescription belongs to this patient
    encounter = db.query(Encounter).filter(Encounter.id == prescription.encounter_id).first()
    
    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter not found for prescription {prescription_id}"
        )
    
    if encounter.patient_id != admission.patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prescription does not belong to this patient"
        )
    
    if encounter.encounter_date.date() < admission.admission_date.date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prescription must be from an encounter during the admission period"
        )
    
    return prescription

