"""
Procedure Catalog Schemas

Pydantic schemas for procedure catalog data validation and serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.schemas.department_schemas import Department


class ProcedureCatalogBase(BaseModel):
    """Base schema for procedure catalog data"""
    procedure_name: str = Field(..., max_length=255)
    procedure_code: Optional[str] = Field(None, max_length=50)
    procedure_category: Optional[str] = Field(None, max_length=100)
    procedure_type: Optional[str] = Field(None, max_length=100)
    charge_type: str = Field(..., max_length=50)  # Charge type for billing (required)
    department_id: Optional[int] = Field(None)  # Department (kept for reference)
    description: Optional[str] = None
    indication: Optional[str] = None
    preparation_instructions: Optional[str] = None
    post_procedure_care: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=0)
    typical_duration_minutes: Optional[int] = Field(None, ge=0)
    
    # Pricing - Cash
    cash_price: Optional[Decimal] = Field(None, ge=0)
    cash_currency: Optional[str] = Field(None, max_length=10)
    
    # Pricing - Insurance
    nhis_covered: bool = False
    nhis_code: Optional[str] = Field(None, max_length=50)
    nhis_price: Optional[Decimal] = Field(None, ge=0)
    private_insurance_covered: bool = False
    private_insurance_price: Optional[Decimal] = Field(None, ge=0)
    
    # Anesthesia
    requires_anesthesia: bool = False
    typical_anesthesia_type: Optional[str] = Field(None, max_length=100)
    
    # Location
    requires_operating_room: bool = False
    typical_location: Optional[str] = Field(None, max_length=200)
    
    # Restrictions
    is_specialized: bool = False
    requires_consultation: bool = False


class ProcedureCatalogCreate(ProcedureCatalogBase):
    """Schema for creating a new procedure catalog entry"""
    pass


class ProcedureCatalogUpdate(BaseModel):
    """Schema for updating a procedure catalog entry"""
    procedure_name: Optional[str] = Field(None, max_length=255)
    procedure_code: Optional[str] = Field(None, max_length=50)
    procedure_category: Optional[str] = Field(None, max_length=100)
    procedure_type: Optional[str] = Field(None, max_length=100)
    charge_type: str = Field(..., max_length=50)  # Charge type for billing (required)
    department_id: Optional[int] = Field(None)  # Department (kept for reference)
    description: Optional[str] = None
    indication: Optional[str] = None
    preparation_instructions: Optional[str] = None
    post_procedure_care: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=0)
    typical_duration_minutes: Optional[int] = Field(None, ge=0)
    
    # Pricing - Cash
    cash_price: Optional[Decimal] = Field(None, ge=0)
    cash_currency: Optional[str] = Field(None, max_length=10)
    
    # Pricing - Insurance
    nhis_covered: Optional[bool] = None
    nhis_code: Optional[str] = Field(None, max_length=50)
    nhis_price: Optional[Decimal] = Field(None, ge=0)
    private_insurance_covered: Optional[bool] = None
    private_insurance_price: Optional[Decimal] = Field(None, ge=0)
    
    # Anesthesia
    requires_anesthesia: Optional[bool] = None
    typical_anesthesia_type: Optional[str] = Field(None, max_length=100)
    
    # Location
    requires_operating_room: Optional[bool] = None
    typical_location: Optional[str] = Field(None, max_length=200)
    
    # Restrictions
    is_specialized: Optional[bool] = None
    requires_consultation: Optional[bool] = None
    is_active: Optional[bool] = None


class ProcedureCatalogRead(ProcedureCatalogBase):
    """Schema for reading procedure catalog data"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    updated_by_id: Optional[int] = None
    department: Optional[Department] = None  # Nested department information

    class Config:
        from_attributes = True

