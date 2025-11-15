from pydantic import BaseModel, Field
from datetime import date, datetime 
from typing import Optional
from app.models.patient_models import PaymentMechanism

# Base schema for shared attributes (remains the same)
class PatientBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: date 
    gender: str = Field(..., max_length=10)
    national_id: Optional[str] = Field(None, max_length=50)  # Optional - not compulsory 
    
    phone_number: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    
    # Financial Screening Fields (Workflow Step 3)
    payment_mechanism: Optional[PaymentMechanism] = None
    nhis_number: Optional[str] = Field(None, max_length=50)
    insurance_provider: Optional[str] = Field(None, max_length=100)
    insurance_policy_number: Optional[str] = Field(None, max_length=50)
    
    # Languages
    languages_spoken: Optional[str] = Field(None, max_length=200)  # Comma-separated list of languages

# Schema for creating a new patient (remains the same)
class PatientCreate(PatientBase):
    pass

# Schema for reading patient data from the API (FIXED)
class Patient(PatientBase):
    id: int
    patient_number: Optional[str] = None
    is_active: bool
    payment_mechanism: Optional[PaymentMechanism] = None
    nhis_number: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    created_at: datetime 
    updated_at: Optional[datetime] 

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2