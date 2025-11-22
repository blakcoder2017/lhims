from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.opd_models import OPDVisitStatus


# OPD Visit Schemas
class OPDVisitBase(BaseModel):
    """Base schema for OPD visit data"""
    appointment_id: Optional[int] = None
    visit_date: Optional[datetime] = None
    visit_type: Optional[str] = Field(None, max_length=50)  # "routine", "emergency", "follow_up", "walk_in"
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None


class OPDVisitCreate(OPDVisitBase):
    """Schema for creating a new OPD visit"""
    status: Optional[OPDVisitStatus] = OPDVisitStatus.ACTIVE
    payment_status: Optional[str] = "pending"  # "pending", "paid", "waived", "emergency"


class OPDVisitUpdate(BaseModel):
    """Schema for updating an OPD visit"""
    appointment_id: Optional[int] = None
    visit_date: Optional[datetime] = None
    status: Optional[OPDVisitStatus] = None
    payment_status: Optional[str] = None
    visit_type: Optional[str] = Field(None, max_length=50)
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None
    consultation_charge_created: Optional[bool] = None
    total_charges: Optional[Decimal] = None


class OPDVisit(OPDVisitBase):
    """Schema for reading OPD visit data"""
    id: int
    opd_number: str
    patient_id: int
    status: OPDVisitStatus
    payment_status: str
    consultation_charge_created: bool
    total_charges: Decimal
    created_at: datetime
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class OPDVisitWithPatient(OPDVisit):
    """Schema for OPD visit with patient information"""
    patient: Optional[dict] = None  # Will be populated with patient data

    class Config:
        from_attributes = True

