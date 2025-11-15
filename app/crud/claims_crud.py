"""
CRUD operations for NHIS Claims.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import json

from app.models.claims_models import NHISClaim, ClaimStatus
from app.models.encounter_models import Encounter
from app.models.billing_models import Invoice
from app.schemas.claims_schemas import NHISClaimCreate, NHISClaimUpdate


def generate_claim_number(db: Session) -> str:
    """Generate a unique claim number"""
    prefix = "CLM"
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Get the last claim number for today
    last_claim = db.query(NHISClaim).filter(
        NHISClaim.claim_number.like(f"{prefix}-{date_str}-%")
    ).order_by(NHISClaim.id.desc()).first()
    
    if last_claim:
        try:
            sequence = int(last_claim.claim_number.split('-')[-1])
            sequence += 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1
    
    return f"{prefix}-{date_str}-{sequence:04d}"


def create_claim_from_encounter(
    db: Session,
    encounter_id: int,
    created_by_id: int
) -> NHISClaim:
    """
    Create an NHIS claim from an encounter.
    Automatically packages encounter data into claim format.
    """
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise ValueError("Encounter not found")
    
    patient = encounter.patient
    if not patient.nhis_number:
        raise ValueError("Patient does not have NHIS number")
    
    # Get invoice for this encounter if exists
    invoice = db.query(Invoice).filter(
        Invoice.encounter_id == encounter_id,
        Invoice.is_active == True
    ).first()
    
    # Collect diagnosis codes
    diagnosis_codes = []
    if encounter.primary_diagnosis_code:
        diagnosis_codes.append({
            "code": encounter.primary_diagnosis_code,
            "description": encounter.primary_diagnosis_description,
            "type": "primary"
        })
    
    # Collect service codes from charges
    service_codes = []
    total_amount = Decimal('0.00')
    if invoice:
        for charge in invoice.charges:
            service_codes.append({
                "type": charge.charge_type.value,
                "description": charge.description,
                "amount": str(charge.total_amount)
            })
            total_amount += charge.total_amount
    
    # Calculate NHIS amount and co-pay
    from app.services.co_pay_calculator import calculate_nhis_co_pay
    co_pay = calculate_nhis_co_pay(total_amount)
    nhis_amount = total_amount - co_pay
    
    # Create claim data structure
    claim_data = {
        "encounter_id": encounter.id,
        "encounter_date": encounter.encounter_date.isoformat() if encounter.encounter_date else None,
        "patient_id": patient.id,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "services": service_codes
    }
    
    # Create claim
    claim = NHISClaim(
        claim_number=generate_claim_number(db),
        encounter_id=encounter_id,
        patient_id=patient.id,
        invoice_id=invoice.id if invoice else None,
        created_by_id=created_by_id,
        nhis_number=patient.nhis_number,
        claim_date=encounter.started_at or datetime.now(),
        status=ClaimStatus.DRAFT,
        claim_data=json.dumps(claim_data),
        diagnosis_codes=json.dumps(diagnosis_codes),
        service_codes=json.dumps(service_codes),
        total_amount=total_amount,
        nhis_amount=nhis_amount,
        co_pay_amount=co_pay
    )
    
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def get_claim(db: Session, claim_id: int) -> Optional[NHISClaim]:
    """Get a claim by ID"""
    from sqlalchemy.orm import joinedload
    return db.query(NHISClaim).options(
        joinedload(NHISClaim.patient),
        joinedload(NHISClaim.encounter).joinedload(Encounter.clinician),
        joinedload(NHISClaim.invoice),
        joinedload(NHISClaim.created_by)
    ).filter(NHISClaim.id == claim_id, NHISClaim.is_active == True).first()


def get_claims_by_patient(db: Session, patient_id: int) -> List[NHISClaim]:
    """Get all claims for a patient"""
    return db.query(NHISClaim).filter(
        NHISClaim.patient_id == patient_id,
        NHISClaim.is_active == True
    ).order_by(NHISClaim.claim_date.desc()).all()


def get_claims_by_status(db: Session, status: ClaimStatus) -> List[NHISClaim]:
    """Get all claims by status"""
    return db.query(NHISClaim).filter(
        NHISClaim.status == status.value,
        NHISClaim.is_active == True
    ).order_by(NHISClaim.claim_date.desc()).all()


def update_claim_status(
    db: Session,
    claim_id: int,
    new_status: ClaimStatus,
    response_data: Optional[str] = None,
    approved_amount: Optional[Decimal] = None,
    rejection_reason: Optional[str] = None
) -> Optional[NHISClaim]:
    """Update claim status (e.g., after submission to NHIA)"""
    claim = db.query(NHISClaim).filter(NHISClaim.id == claim_id).first()
    if not claim:
        return None
    
    claim.status = new_status.value
    
    if new_status == ClaimStatus.SUBMITTED:
        claim.submitted_at = datetime.now()
    elif new_status == ClaimStatus.APPROVED:
        claim.processed_at = datetime.now()
        if approved_amount:
            claim.approved_amount = approved_amount
    elif new_status == ClaimStatus.REJECTED:
        claim.processed_at = datetime.now()
        if rejection_reason:
            claim.rejection_reason = rejection_reason
    
    if response_data:
        claim.response_data = response_data
    
    db.commit()
    db.refresh(claim)
    return claim

