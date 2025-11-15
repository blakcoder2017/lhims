"""
Ward Type Schemas

Pydantic schemas for ward type data validation and serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WardTypeBase(BaseModel):
    """Base schema for ward type data"""
    name: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_active: bool = True


class WardTypeCreate(WardTypeBase):
    """Schema for creating a new ward type"""
    pass


class WardTypeUpdate(BaseModel):
    """Schema for updating a ward type"""
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class WardType(WardTypeBase):
    """Schema for reading ward type data"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

