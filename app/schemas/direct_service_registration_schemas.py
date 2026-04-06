"""
Direct Service Registration Schemas

Pydantic schemas for direct service registration API.
Supports: Antenatal, Lab, Pharmacy, Radiology, Procedures
"""
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional, Any, Dict, Union
from app.models.patient_models import PaymentMechanism


# Service type enum
class DirectServiceType(str):
    ANTENATAL = "antenatal"
    LAB = "lab"
    PHARMACY = "pharmacy"
    RADIOLOGY = "radiology"
    PROCEDURE = "procedure"


# Base schema for direct service registration
class DirectServiceRegistrationBase(BaseModel):
    """Base schema for direct service registration attributes"""
    service_type: str = Field(..., description="Service type: antenatal, lab, pharmacy, radiology, procedure")
    service_type_label: Optional[str] = Field(None, description="Human-readable service name")
    
    # Antenatal specific
    gestational_weeks: Optional[float] = Field(None, description="Gestational weeks for antenatal")
    lmp: Optional[date] = Field(None, description="Last menstrual period")
    edd: Optional[date] = Field(None, description="Expected delivery date")
    
    # Registration notes
    registration_notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('lmp', 'edd', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class DirectServiceRegistrationCreate(DirectServiceRegistrationBase):
    """Schema for creating a direct service registration"""
    # Patient identification - either search query or patient_id
    search_query: Optional[str] = Field(None, description="Search for existing patient by name/phone/national_id")
    patient_id: Optional[int] = Field(None, description="If existing patient, provide patient ID")
    
    # New patient details (if not existing patient)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=10)
    national_id: Optional[str] = Field(None, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    
    # Payment mechanism
    payment_mechanism: Optional[PaymentMechanism] = Field(None, description="Payment mechanism: cash, nhis, private_insurance")
    nhis_number: Optional[str] = Field(None, max_length=50)
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_policy_number: Optional[str] = Field(None, max_length=50)
    
    # Service-specific details (JSON for flexibility)
    service_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional service-specific details")
    
    @field_validator('date_of_birth', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class DirectServiceRegistrationUpdate(BaseModel):
    """Schema for updating direct service registration"""
    status: Optional[str] = None
    order_id: Optional[int] = None
    order_type: Optional[str] = None
    registration_notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class DirectServiceRegistration(DirectServiceRegistrationBase):
    """Schema for reading direct service registration"""
    id: int
    patient_id: int
    status: str
    order_id: Optional[int] = None
    order_type: Optional[str] = None
    registered_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Response schemas
class PatientSearchResult(BaseModel):
    """Schema for patient search results"""
    id: int
    patient_number: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone_number: Optional[str] = None
    payment_mechanism: Optional[str] = None
    
    class Config:
        from_attributes = True


class DirectServiceRegistrationResponse(BaseModel):
    """Response schema for direct service registration"""
    success: bool
    message: str
    patient_id: Optional[int] = None
    patient_number: Optional[str] = None
    registration_id: Optional[int] = None
    order_id: Optional[int] = None
    order_type: Optional[str] = None
    service_type: Optional[str] = None
    redirect_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class ServicePricingInfo(BaseModel):
    """Schema for service pricing information"""
    service_name: str
    service_code: Optional[str] = None
    unit_price: float
    currency: str = "GHS"
    charge_type: str
    
    class Config:
        from_attributes = True
