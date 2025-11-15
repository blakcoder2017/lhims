from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ServicePricingBase(BaseModel):
    service_name: str = Field(..., max_length=200)
    service_code: Optional[str] = Field(None, max_length=50)
    charge_type: str = Field(..., max_length=50)  # consultation, lab_test, radiology, pharmacy, procedure, admission, other
    category: Optional[str] = Field(None, max_length=100)
    unit_price: Decimal = Field(..., ge=0)
    currency: str = Field(default="GHS", max_length=10)
    description: Optional[str] = None
    is_active: bool = Field(default=True)


class ServicePricingCreate(ServicePricingBase):
    pass


class ServicePricingUpdate(BaseModel):
    service_name: Optional[str] = Field(None, max_length=200)
    service_code: Optional[str] = Field(None, max_length=50)
    charge_type: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ServicePricing(ServicePricingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    created_by_id: Optional[int]
    updated_by_id: Optional[int]

    class Config:
        from_attributes = True

