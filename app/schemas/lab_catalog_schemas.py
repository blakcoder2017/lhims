from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# Lab Test Schemas
class LabTestBase(BaseModel):
    test_name: str = Field(..., max_length=255)
    test_code: Optional[str] = Field(None, max_length=50)
    loinc_code: Optional[str] = Field(None, max_length=20, description="LOINC code for interoperability")
    test_category: Optional[str] = Field(None, max_length=100)
    test_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    specimen_type: Optional[str] = Field(None, max_length=100)
    specimen_volume: Optional[str] = Field(None, max_length=50)
    collection_method: Optional[str] = Field(None, max_length=200)
    storage_requirements: Optional[str] = Field(None, max_length=200)
    routine_tat: Optional[int] = Field(None, ge=0)
    urgent_tat: Optional[int] = Field(None, ge=0)
    stat_tat: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    nhis_covered: bool = False
    nhis_code: Optional[str] = Field(None, max_length=50)


class LabTestCreate(LabTestBase):
    pass


class LabTestUpdate(BaseModel):
    test_name: Optional[str] = Field(None, max_length=255)
    test_code: Optional[str] = Field(None, max_length=50)
    loinc_code: Optional[str] = Field(None, max_length=20)
    test_category: Optional[str] = Field(None, max_length=100)
    test_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    specimen_type: Optional[str] = Field(None, max_length=100)
    specimen_volume: Optional[str] = Field(None, max_length=50)
    collection_method: Optional[str] = Field(None, max_length=200)
    storage_requirements: Optional[str] = Field(None, max_length=200)
    routine_tat: Optional[int] = Field(None, ge=0)
    urgent_tat: Optional[int] = Field(None, ge=0)
    stat_tat: Optional[int] = Field(None, ge=0)
    cost: Optional[Decimal] = Field(None, ge=0)
    nhis_covered: Optional[bool] = None
    nhis_code: Optional[str] = Field(None, max_length=50)


class LabTestRead(LabTestBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Reference Range Schemas
class ReferenceRangeBase(BaseModel):
    test_id: Optional[int] = None
    test_name: str = Field(..., max_length=255)
    test_code: Optional[str] = Field(None, max_length=50)
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    gender: Optional[str] = Field(None, max_length=20)
    normal_min: Optional[Decimal] = None
    normal_max: Optional[Decimal] = None
    critical_low: Optional[Decimal] = None
    critical_high: Optional[Decimal] = None
    unit: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class ReferenceRangeCreate(ReferenceRangeBase):
    pass


class ReferenceRangeUpdate(BaseModel):
    test_id: Optional[int] = None
    test_name: Optional[str] = Field(None, max_length=255)
    test_code: Optional[str] = Field(None, max_length=50)
    age_min: Optional[int] = Field(None, ge=0)
    age_max: Optional[int] = Field(None, ge=0)
    gender: Optional[str] = Field(None, max_length=20)
    normal_min: Optional[Decimal] = None
    normal_max: Optional[Decimal] = None
    critical_low: Optional[Decimal] = None
    critical_high: Optional[Decimal] = None
    unit: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class ReferenceRangeRead(ReferenceRangeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Activation Status Schema
class LabTestActivate(BaseModel):
    """Schema for activating a lab test"""
    activate: bool = Field(..., description="Set to True to activate, False to deactivate")

    class Config:
        from_attributes = True

