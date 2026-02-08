from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Union
from app.models.appointment_models import QueueStatus, VisitType
from app.models.scheduled_appointment_models import AppointmentType, AppointmentStatus


class AppointmentBase(BaseModel):
    """Base schema for appointments"""
    patient_id: int
    department: str = Field(..., max_length=100)
    department_type: Optional[str] = Field("opd", max_length=20)
    appointment_type: Optional[AppointmentType] = Field(AppointmentType.CONSULTATION, description="Type of appointment")
    scheduled_date: Optional[datetime] = None
    chief_complaint: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    priority: int = Field(5, ge=1, le=10)
    assigned_clinician_id: Optional[int] = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment"""
    created_by_id: int


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment"""
    status: Optional[AppointmentStatus] = None
    assigned_clinician_id: Optional[int] = None
    department: Optional[str] = None
    department_type: Optional[str] = Field(None, max_length=20)
    priority: Optional[int] = Field(None, ge=1, le=10)
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Appointment(AppointmentBase):
    """Schema for reading appointment data"""
    id: int
    status: AppointmentStatus
    queue_number: Optional[int] = None
    created_by_id: int
    checked_in_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QueueBase(BaseModel):
    """Base schema for queue data"""
    patient_id: int
    department: str = Field(..., max_length=100)
    department_type: Optional[str] = Field("opd", max_length=20)  # "opd", "ipd", or "both" - for OPD/IPD distinction
    visit_type: VisitType
    chief_complaint: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=1000)
    priority: int = Field(5, ge=1, le=10)  # Priority scale 1-10
    assigned_clinician_id: Optional[int] = None


class QueueCreate(QueueBase):
    """Schema for creating a new queue entry"""
    created_by_id: int


class QueueUpdate(BaseModel):
    """Schema for updating a queue entry"""
    status: Optional[QueueStatus] = None
    assigned_clinician_id: Optional[int] = None
    department: Optional[str] = None
    department_type: Optional[str] = Field(None, max_length=20)
    priority: Optional[int] = Field(None, ge=1, le=10)
    chief_complaint: Optional[str] = None
    notes: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Queue(QueueBase):
    """Schema for reading queue data"""
    id: int
    status: QueueStatus
    queue_number: Optional[int] = None
    assigned_clinician_id: Optional[int] = None
    created_by_id: int
    department_type: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

