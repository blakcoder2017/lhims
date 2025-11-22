from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.opd_models import OPDVisitStatus
from app.crud import opd_crud, patient_crud
from app.schemas.opd_schemas import (
    OPDVisitCreate, OPDVisitUpdate, OPDVisit
)

router = APIRouter(tags=["OPD"])


@router.post("/api/v1/opd-visits", response_model=OPDVisit, status_code=status.HTTP_201_CREATED)
def create_opd_visit_endpoint(
    opd_visit: OPDVisitCreate,
    patient_id: int = Query(..., description="Patient ID for the OPD visit"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new OPD visit.
    Automatically generates OPD number (format: OPD-YYYY-NNNN).
    """
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Create OPD visit
    db_opd_visit = opd_crud.create_opd_visit(
        db, 
        opd_visit=opd_visit, 
        patient_id=patient_id
    )
    
    return db_opd_visit


@router.get("/api/v1/opd-visits", response_model=List[OPDVisit])
def get_opd_visits_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[OPDVisitStatus] = Query(None),
    payment_status: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all OPD visits with optional filters."""
    return opd_crud.get_opd_visits(
        db, 
        skip=skip, 
        limit=limit, 
        status=status,
        payment_status=payment_status,
        patient_id=patient_id
    )


@router.get("/api/v1/opd-visits/{opd_visit_id}", response_model=OPDVisit)
def get_opd_visit_endpoint(
    opd_visit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get an OPD visit by ID."""
    opd_visit = opd_crud.get_opd_visit(db, opd_visit_id)
    if not opd_visit:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return opd_visit


@router.get("/api/v1/opd-visits/number/{opd_number}", response_model=OPDVisit)
def get_opd_visit_by_number_endpoint(
    opd_number: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get an OPD visit by OPD number."""
    opd_visit = opd_crud.get_opd_visit_by_number(db, opd_number)
    if not opd_visit:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return opd_visit


@router.get("/api/v1/patients/{patient_id}/opd-visits", response_model=List[OPDVisit])
def get_patient_opd_visits_endpoint(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[OPDVisitStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all OPD visits for a specific patient."""
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return opd_crud.get_opd_visits_by_patient(
        db, 
        patient_id=patient_id, 
        skip=skip, 
        limit=limit,
        status=status
    )


@router.get("/api/v1/patients/{patient_id}/opd-visits/active", response_model=Optional[OPDVisit])
def get_active_opd_visit_endpoint(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the active OPD visit for a patient (if any)."""
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return opd_crud.get_active_opd_visit_by_patient(db, patient_id)


@router.put("/api/v1/opd-visits/{opd_visit_id}", response_model=OPDVisit)
def update_opd_visit_endpoint(
    opd_visit_id: int,
    opd_visit_update: OPDVisitUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update an OPD visit."""
    opd_visit = opd_crud.update_opd_visit(db, opd_visit_id, opd_visit_update)
    if not opd_visit:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return opd_visit


@router.post("/api/v1/opd-visits/{opd_visit_id}/complete", response_model=OPDVisit)
def complete_opd_visit_endpoint(
    opd_visit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark an OPD visit as completed."""
    opd_visit = opd_crud.complete_opd_visit(db, opd_visit_id)
    if not opd_visit:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return opd_visit


@router.post("/api/v1/opd-visits/{opd_visit_id}/cancel", response_model=OPDVisit)
def cancel_opd_visit_endpoint(
    opd_visit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cancel an OPD visit."""
    opd_visit = opd_crud.cancel_opd_visit(db, opd_visit_id)
    if not opd_visit:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return opd_visit


@router.put("/api/v1/opd-visits/{opd_visit_id}/payment-status", response_model=OPDVisit)
def update_payment_status_endpoint(
    opd_visit_id: int,
    payment_status: str = Query(..., description="Payment status: pending, paid, waived, emergency"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update payment status of an OPD visit."""
    valid_statuses = ["pending", "paid", "waived", "emergency"]
    if payment_status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid payment status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    opd_visit = opd_crud.update_opd_visit_payment_status(db, opd_visit_id, payment_status)
    if not opd_visit:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return opd_visit


@router.delete("/api/v1/opd-visits/{opd_visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opd_visit_endpoint(
    opd_visit_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Soft delete an OPD visit (Admin only)."""
    success = opd_crud.delete_opd_visit(db, opd_visit_id)
    if not success:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    return None

