from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class DepartmentBase(BaseModel):
    """Base schema for department data"""
    name: str = Field(..., max_length=100, description="Department name")
    code: Optional[str] = Field(None, max_length=20, description="Department code")
    description: Optional[str] = Field(None, description="Department description")
    consultation_price: Optional[Decimal] = Field(None, ge=0, description="Consultation fee for this department")
    is_active: bool = Field(True, description="Whether the department is active")


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department"""
    pass


class DepartmentUpdate(BaseModel):
    """Schema for updating a department"""
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    consultation_price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class Department(DepartmentBase):
    """Schema for department response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

