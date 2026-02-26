from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from app.models.ipd_models import WardStatus, BedStatus, AdmissionStatus, DischargeStatus


# Ward Schemas
class WardBase(BaseModel):
    """Base schema for ward data"""
    name: str = Field(..., max_length=100)
    ward_number: Optional[str] = Field(None, max_length=50)
    ward_type: Optional[str] = Field(None, max_length=50)
    capacity: int = Field(..., ge=0)
    floor: Optional[str] = Field(None, max_length=50)
    building: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    charge_per_day: Decimal = Field(..., ge=0)  # Required field, default to 0.00


class WardCreate(WardBase):
    """Schema for creating a new ward"""
    status: WardStatus = WardStatus.ACTIVE


class WardUpdate(BaseModel):
    """Schema for updating a ward"""
    name: Optional[str] = Field(None, max_length=100)
    ward_number: Optional[str] = Field(None, max_length=50)
    ward_type: Optional[str] = Field(None, max_length=50)
    capacity: Optional[int] = Field(None, ge=0)
    current_occupancy: Optional[int] = Field(None, ge=0)
    status: Optional[WardStatus] = None
    floor: Optional[str] = Field(None, max_length=50)
    building: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    charge_per_day: Optional[Decimal] = Field(None, ge=0)


class Ward(WardBase):
    """Schema for reading ward data"""
    id: int
    current_occupancy: int
    status: WardStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


# Bed Schemas
class BedBase(BaseModel):
    """Base schema for bed data"""
    ward_id: int
    bed_number: str = Field(..., max_length=50)
    bed_name: Optional[str] = Field(None, max_length=100)
    bed_type: Optional[str] = Field(None, max_length=50)
    charge_per_day: Decimal = Field(..., ge=0)  # Required field, default to 0.00
    notes: Optional[str] = None


class BedCreate(BedBase):
    """Schema for creating a new bed"""
    status: BedStatus = BedStatus.AVAILABLE


class BedUpdate(BaseModel):
    """Schema for updating a bed"""
    ward_id: Optional[int] = None
    bed_number: Optional[str] = Field(None, max_length=50)
    bed_name: Optional[str] = Field(None, max_length=100)
    status: Optional[BedStatus] = None
    bed_type: Optional[str] = Field(None, max_length=50)
    charge_per_day: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None


class Bed(BedBase):
    """Schema for reading bed data"""
    id: int
    status: BedStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


# Admission Schemas
class AdmissionBase(BaseModel):
    """Base schema for admission data"""
    patient_id: int
    encounter_id: Optional[int] = None
    ward_id: int
    bed_id: int
    admission_reason: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    expected_discharge_date: Optional[datetime] = None
    # Allergies - Critical for patient safety
    allergies: Optional[str] = None
    # Guardian/Attendant Information
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_relationship: Optional[str] = None
    guardian_address: Optional[str] = None


class AdmissionCreate(AdmissionBase):
    """Schema for creating a new admission"""
    admitted_by_id: int
    status: AdmissionStatus = AdmissionStatus.ADMITTED


class AdmissionUpdate(BaseModel):
    """Schema for updating an admission"""
    ward_id: Optional[int] = None
    bed_id: Optional[int] = None
    status: Optional[AdmissionStatus] = None
    discharge_date: Optional[datetime] = None
    expected_discharge_date: Optional[datetime] = None
    discharged_by_id: Optional[int] = None
    admission_reason: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    transfer_reason: Optional[str] = None
    transferred_from_ward_id: Optional[int] = None
    transferred_to_ward_id: Optional[int] = None
    # Discharge Information
    discharge_status: Optional[DischargeStatus] = None  # Discharge status: normal, death, referral
    discharge_diagnosis: Optional[str] = None  # Final diagnosis at discharge
    discharge_notes: Optional[str] = None  # Discharge notes and instructions


class Admission(AdmissionBase):
    """Schema for reading admission data"""
    id: int
    admission_number: str
    status: AdmissionStatus
    admitted_by_id: int
    discharged_by_id: Optional[int] = None
    admission_date: datetime
    discharge_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


# Doctor Duty Schemas
class DoctorDutyBase(BaseModel):
    """Base schema for doctor duty data"""
    doctor_id: int
    department: str = Field(..., max_length=100)
    duty_date: datetime
    shift_start: datetime
    shift_end: datetime
    shift_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class DoctorDutyCreate(DoctorDutyBase):
    """Schema for creating a new doctor duty"""
    is_on_duty: bool = True
    status: str = "scheduled"


class DoctorDutyUpdate(BaseModel):
    """Schema for updating a doctor duty"""
    doctor_id: Optional[int] = None
    department: Optional[str] = Field(None, max_length=100)
    duty_date: Optional[datetime] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    shift_type: Optional[str] = Field(None, max_length=50)
    is_on_duty: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class DoctorDuty(DoctorDutyBase):
    """Schema for reading doctor duty data"""
    id: int
    is_on_duty: bool
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

