from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ShiftTypeBase(BaseModel):
    """Base schema for shift type data"""
    name: str = Field(..., max_length=50, description="Shift type name")
    code: Optional[str] = Field(None, max_length=20, description="Shift type code")
    description: Optional[str] = Field(None, description="Shift type description")
    default_start_hour: Optional[int] = Field(None, ge=0, le=23, description="Default start hour (0-23)")
    default_end_hour: Optional[int] = Field(None, ge=0, le=23, description="Default end hour (0-23)")
    is_active: bool = Field(True, description="Whether the shift type is active")


class ShiftTypeCreate(ShiftTypeBase):
    """Schema for creating a new shift type"""
    pass


class ShiftTypeUpdate(BaseModel):
    """Schema for updating a shift type"""
    name: Optional[str] = Field(None, max_length=50)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    default_start_hour: Optional[int] = Field(None, ge=0, le=23)
    default_end_hour: Optional[int] = Field(None, ge=0, le=23)
    is_active: Optional[bool] = None


class ShiftType(ShiftTypeBase):
    """Schema for shift type response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

