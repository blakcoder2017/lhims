from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.encounter_models import EncounterStatus, OrderStatus


# Encounter Schemas
class EncounterBase(BaseModel):
    """Base schema for encounter data"""
    patient_id: int
    appointment_id: Optional[int] = None
    opd_visit_id: Optional[int] = None  # Link to OPD visit (for OPD encounters)
    admission_id: Optional[int] = None  # Link to IPD admission (for IPD encounters)
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    past_medical_history: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[str] = None
    physical_examination: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    primary_diagnosis_code: Optional[str] = Field(None, max_length=20)
    primary_diagnosis_description: Optional[str] = Field(None, max_length=500)
    secondary_diagnosis_codes: Optional[str] = None  # JSON string of secondary diagnoses
    differential_diagnosis_data: Optional[str] = None  # JSON blob string


class EncounterCreate(EncounterBase):
    """Schema for creating a new encounter"""
    clinician_id: int
    status: EncounterStatus = EncounterStatus.IN_PROGRESS


class EncounterUpdate(BaseModel):
    """Schema for updating an encounter"""
    status: Optional[EncounterStatus] = None
    chief_complaint: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    past_medical_history: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[str] = None
    physical_examination: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    primary_diagnosis_code: Optional[str] = None
    primary_diagnosis_description: Optional[str] = None
    secondary_diagnosis_codes: Optional[str] = None
    differential_diagnosis_data: Optional[str] = None
    completed_at: Optional[datetime] = None


class Encounter(EncounterBase):
    """Schema for reading encounter data"""
    id: int
    clinician_id: int
    status: EncounterStatus
    encounter_date: datetime
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    differential_diagnosis_data: Optional[str] = None

    class Config:
        from_attributes = True


# Lab Order Schemas
class LabOrderBase(BaseModel):
    """Base schema for lab order data"""
    test_name: str = Field(..., max_length=200)
    test_code: Optional[str] = Field(None, max_length=50)
    instructions: Optional[str] = None
    priority: str = "routine"


class LabOrderCreate(LabOrderBase):
    """Schema for creating a new lab order"""
    encounter_id: Optional[int] = None  # Optional for walk-in orders
    patient_id: Optional[int] = None  # Required for walk-in orders
    ordered_by_id: int
    is_walk_in: bool = False


class LabOrderUpdate(BaseModel):
    """Schema for updating a lab order"""
    status: Optional[OrderStatus] = None
    result: Optional[str] = None
    result_entered_by_id: Optional[int] = None
    result_entered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LabOrder(LabOrderBase):
    """Schema for reading lab order data"""
    id: int
    encounter_id: Optional[int] = None
    patient_id: Optional[int] = None
    ordered_by_id: int
    is_walk_in: bool = False
    checked_in_at: Optional[datetime] = None
    checked_in_by_id: Optional[int] = None
    status: OrderStatus
    ordered_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    result_entered_by_id: Optional[int] = None
    result_entered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Radiology Order Schemas
class RadiologyOrderBase(BaseModel):
    """Base schema for radiology order data"""
    study_type: str = Field(..., max_length=200)
    study_code: Optional[str] = Field(None, max_length=50)
    body_part: Optional[str] = Field(None, max_length=100)
    clinical_indication: Optional[str] = None
    instructions: Optional[str] = None
    priority: str = "routine"


class RadiologyOrderCreate(RadiologyOrderBase):
    """Schema for creating a new radiology order"""
    encounter_id: Optional[int] = None  # Optional for walk-in orders
    patient_id: Optional[int] = None  # Required for walk-in orders
    ordered_by_id: int
    is_walk_in: bool = False


class RadiologyOrderUpdate(BaseModel):
    """Schema for updating a radiology order"""
    status: Optional[OrderStatus] = None
    report: Optional[str] = None
    report_entered_by_id: Optional[int] = None
    report_entered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RadiologyOrder(RadiologyOrderBase):
    """Schema for reading radiology order data"""
    id: int
    encounter_id: Optional[int] = None
    patient_id: Optional[int] = None
    ordered_by_id: int
    is_walk_in: bool = False
    checked_in_at: Optional[datetime] = None
    checked_in_by_id: Optional[int] = None
    status: OrderStatus
    ordered_at: datetime
    completed_at: Optional[datetime] = None
    report: Optional[str] = None
    report_entered_by_id: Optional[int] = None
    report_entered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Prescription Schemas
class PrescriptionBase(BaseModel):
    """Base schema for prescription data"""
    medication_id: Optional[int] = None  # Link to inventory medication (optional)
    medication_name: str = Field(..., max_length=200)
    medication_code: Optional[str] = Field(None, max_length=50)
    dosage: str = Field(..., max_length=100)
    frequency: str = Field(..., max_length=100)
    duration: str = Field(..., max_length=100)
    quantity: Optional[int] = None
    instructions: Optional[str] = None


class PrescriptionCreate(PrescriptionBase):
    """Schema for creating a new prescription"""
    encounter_id: int
    prescribed_by_id: int
    is_walk_in: bool = False


class PrescriptionUpdate(BaseModel):
    """Schema for updating a prescription"""
    status: Optional[OrderStatus] = None
    dispensed_at: Optional[datetime] = None
    dispensed_by_id: Optional[int] = None
    checked_in_at: Optional[datetime] = None
    checked_in_by_id: Optional[int] = None


class Prescription(PrescriptionBase):
    """Schema for reading prescription data"""
    id: int
    encounter_id: int
    prescribed_by_id: int
    is_walk_in: bool = False
    checked_in_at: Optional[datetime] = None
    checked_in_by_id: Optional[int] = None
    status: OrderStatus
    prescribed_at: datetime
    dispensed_at: Optional[datetime] = None
    dispensed_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Combined schemas for encounter with orders
class EncounterWithOrders(Encounter):
    """Schema for encounter with all related orders"""
    lab_orders: List[LabOrder] = []
    radiology_orders: List[RadiologyOrder] = []
    prescriptions: List[Prescription] = []

    class Config:
        from_attributes = True


# Differential diagnosis helper schemas
class DifferentialInput(BaseModel):
    clinical_summary: str
    age: Optional[int] = None
    sex: Optional[str] = Field(None, max_length=20)
    key_vitals: Optional[str] = Field(None, max_length=500)
    key_labs: Optional[str] = Field(None, max_length=500)


class DifferentialSuggestion(BaseModel):
    diagnosis: str
    body_system: Optional[str] = None
    stg_reference: Optional[str] = None
    stg_summary: Optional[str] = None
    relevance_score: float = 0.0
    flags: List[str] = []
    status: str = Field("suggested", pattern="^(suggested|working|ruled_out)$")


class DifferentialResponse(BaseModel):
    clinical_summary: str
    generated_at: datetime
    suggestions: List[DifferentialSuggestion]
    notes: Optional[str] = None


class DifferentialSaveRequest(BaseModel):
    clinical_summary: str
    suggestions: List[DifferentialSuggestion]
    notes: Optional[str] = None

