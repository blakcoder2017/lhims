from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BedTypeBase(BaseModel):
    """Base schema for bed type data"""
    name: str = Field(..., max_length=50, description="Bed type name")
    code: Optional[str] = Field(None, max_length=20, description="Bed type code")
    description: Optional[str] = Field(None, description="Bed type description")
    default_charge_per_day: Optional[str] = Field(None, max_length=20, description="Default charge per day")
    is_active: bool = Field(True, description="Whether the bed type is active")


class BedTypeCreate(BedTypeBase):
    """Schema for creating a new bed type"""
    pass


class BedTypeUpdate(BaseModel):
    """Schema for updating a bed type"""
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    default_charge_per_day: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class BedType(BedTypeBase):
    """Schema for bed type response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

