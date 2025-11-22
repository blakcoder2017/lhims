"""
Procedure Schemas

Pydantic schemas for procedure data validation and serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.procedure_models import ProcedureType, ProcedureStatus


class ProcedureBase(BaseModel):
    """Base schema for procedure data"""
    procedure_name: str = Field(..., max_length=200)
    procedure_code: Optional[str] = Field(None, max_length=50)
    procedure_type: ProcedureType
    description: Optional[str] = None
    indication: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    anesthesia_type: Optional[str] = Field(None, max_length=100)
    anesthesia_provider: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None


class ProcedureCreate(ProcedureBase):
    """Schema for creating a new procedure"""
    patient_id: int
    encounter_id: Optional[int] = None
    procedure_catalog_id: Optional[int] = None  # Link to procedure catalog
    ordered_by_id: int
    performed_by_id: Optional[int] = None
    status: ProcedureStatus = Field(default=ProcedureStatus.SCHEDULED)
    is_walk_in: bool = False


class ProcedureUpdate(BaseModel):
    """Schema for updating a procedure"""
    procedure_name: Optional[str] = Field(None, max_length=200)
    procedure_code: Optional[str] = Field(None, max_length=50)
    procedure_catalog_id: Optional[int] = None  # Link to procedure catalog
    procedure_type: Optional[ProcedureType] = None
    description: Optional[str] = None
    indication: Optional[str] = None
    status: Optional[ProcedureStatus] = None
    scheduled_date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    performed_by_id: Optional[int] = None
    findings: Optional[str] = None
    complications: Optional[str] = None
    outcome: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    anesthesia_type: Optional[str] = Field(None, max_length=100)
    anesthesia_provider: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None


class Procedure(ProcedureBase):
    """Schema for reading procedure data"""
    id: int
    procedure_number: str
    patient_id: int
    encounter_id: Optional[int] = None
    procedure_catalog_id: Optional[int] = None  # Link to procedure catalog
    ordered_by_id: int
    performed_by_id: Optional[int] = None
    is_walk_in: bool = False
    checked_in_at: Optional[datetime] = None
    checked_in_by_id: Optional[int] = None
    status: ProcedureStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    findings: Optional[str] = None
    complications: Optional[str] = None
    outcome: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

