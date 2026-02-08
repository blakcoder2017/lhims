"""
Pydantic schemas for scheduled appointments
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date


class ScheduledAppointmentBase(BaseModel):
    """Base schema for scheduled appointments"""
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    assigned_doctor_id: int
    appointment_date: datetime
    duration_minutes: int = Field(default=30, ge=15, le=240)
    reason_complaint: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)

    @validator('patient_name')
    def validate_patient_info(cls, v, values):
        """Ensure either patient_id or patient_name is provided"""
        if not values.get('patient_id') and not v:
            raise ValueError('Either patient_id or patient_name must be provided')
        return v

    @validator('patient_phone')
    def validate_phone_for_non_system_patient(cls, v, values):
        """Require phone if patient is not in system"""
        if not values.get('patient_id') and not v:
            raise ValueError('Patient phone is required for patients not in the system')
        return v


class ScheduledAppointmentCreate(ScheduledAppointmentBase):
    """Schema for creating scheduled appointments"""
    pass


class ScheduledAppointmentUpdate(BaseModel):
    """Schema for updating scheduled appointments"""
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    assigned_doctor_id: Optional[int] = None
    appointment_date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=240)
    reason_complaint: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    status: Optional[str] = None


class ScheduledAppointmentResponse(BaseModel):
    """Schema for scheduled appointment responses"""
    id: int
    patient_id: Optional[int]
    patient_name: Optional[str]
    patient_phone: Optional[str]
    assigned_doctor_id: int
    appointment_date: datetime
    duration_minutes: int
    reason_complaint: Optional[str]
    notes: Optional[str]
    priority: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by_id: int
    cancelled_by_id: Optional[int]
    is_active: bool

    class Config:
        from_attributes = True


class ScheduledAppointmentList(BaseModel):
    """Schema for list of scheduled appointments"""
    appointments: List[ScheduledAppointmentResponse]
    total: int
    page: int
    per_page: int


class AppointmentStatistics(BaseModel):
    """Schema for appointment statistics"""
    total: int
    scheduled: int
    confirmed: int
    completed: int
    cancelled: int
    no_show: int
    completion_rate: float
    cancellation_rate: float


class DoctorAvailability(BaseModel):
    """Schema for doctor availability"""
    doctor_id: int
    doctor_name: str
    department: str
    available_slots: List[datetime]


class AppointmentSlot(BaseModel):
    """Schema for available appointment slots"""
    start_time: datetime
    end_time: datetime
    is_available: bool
    doctor_id: Optional[int] = None


class QuickAppointmentCreate(BaseModel):
    """Schema for quick appointment creation (minimal fields)"""
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    assigned_doctor_id: int
    appointment_date: datetime
    reason_complaint: Optional[str] = None

    @validator('patient_name')
    def validate_patient_info(cls, v, values):
        """Ensure either patient_id or patient_name is provided"""
        if not values.get('patient_id') and not v:
            raise ValueError('Either patient_id or patient_name must be provided')
        return v
