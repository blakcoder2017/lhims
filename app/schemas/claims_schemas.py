"""
Pydantic schemas for NHIS Claims.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.models.claims_models import ClaimStatus


class NHISClaimBase(BaseModel):
    """Base schema for NHIS claim"""
    nhis_number: str
    facility_code: Optional[str] = None
    notes: Optional[str] = None


class NHISClaimCreate(NHISClaimBase):
    """Schema for creating an NHIS claim"""
    encounter_id: int
    invoice_id: Optional[int] = None


class NHISClaimUpdate(BaseModel):
    """Schema for updating an NHIS claim"""
    status: Optional[ClaimStatus] = None
    submission_reference: Optional[str] = None
    response_data: Optional[str] = None
    approved_amount: Optional[Decimal] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


class NHISClaim(NHISClaimBase):
    """Schema for reading NHIS claim data"""
    id: int
    claim_number: str
    encounter_id: int
    patient_id: int
    invoice_id: Optional[int] = None
    status: ClaimStatus
    total_amount: Decimal
    nhis_amount: Decimal
    co_pay_amount: Decimal
    claim_date: datetime
    submitted_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    approved_amount: Optional[Decimal] = None
    
    class Config:
        from_attributes = True

