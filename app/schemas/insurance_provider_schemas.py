"""
Insurance Provider Schemas

Pydantic schemas for insurance provider data validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InsuranceProviderBase(BaseModel):
    """Base schema for insurance provider data"""
    name: str = Field(..., max_length=200, description="Insurance provider name")
    code: Optional[str] = Field(None, max_length=50, description="Provider code")
    contact_person: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    co_pay_rate: Optional[str] = Field(None, max_length=20, description="Co-pay rate (e.g., '10%', '20%')")
    billing_email: Optional[str] = Field(None, max_length=100)
    billing_address: Optional[str] = None


class InsuranceProviderCreate(InsuranceProviderBase):
    """Schema for creating a new insurance provider"""
    pass


class InsuranceProviderUpdate(BaseModel):
    """Schema for updating an insurance provider"""
    name: Optional[str] = Field(None, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    co_pay_rate: Optional[str] = Field(None, max_length=20)
    billing_email: Optional[str] = Field(None, max_length=100)
    billing_address: Optional[str] = None
    is_active: Optional[bool] = None


class InsuranceProvider(InsuranceProviderBase):
    """Schema for reading insurance provider data"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

