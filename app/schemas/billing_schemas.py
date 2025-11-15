from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.billing_models import InvoiceStatus, PaymentMethod, PaymentStatus, ChargeType


# Charge Schemas
class ChargeBase(BaseModel):
    charge_type: ChargeType
    description: str = Field(..., max_length=500)
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount: Decimal = Field(default=Decimal('0.00'), ge=0)
    tax_rate: Decimal = Field(default=Decimal('0.00'), ge=0, le=100)
    encounter_id: Optional[int] = None
    lab_order_id: Optional[int] = None
    radiology_order_id: Optional[int] = None
    prescription_id: Optional[int] = None


class ChargeCreate(ChargeBase):
    pass


class ChargeUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    quantity: Optional[int] = Field(None, ge=1)
    unit_price: Optional[Decimal] = Field(None, ge=0)
    discount: Optional[Decimal] = Field(None, ge=0)
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=100)


class ChargeRead(ChargeBase):
    id: int
    tax_amount: Decimal
    total_amount: Decimal
    invoice_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Invoice Schemas
class InvoiceBase(BaseModel):
    patient_id: int
    encounter_id: Optional[int] = None
    appointment_id: Optional[int] = None
    payment_mechanism: Optional[PaymentMethod] = None
    nhis_number: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    charges: Optional[List[ChargeCreate]] = []


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    discount_amount: Optional[Decimal] = Field(None, ge=0)
    tax_amount: Optional[Decimal] = Field(None, ge=0)
    payment_mechanism: Optional[PaymentMethod] = None
    nhis_number: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_policy_number: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class InvoiceRead(InvoiceBase):
    id: int
    invoice_number: str
    status: InvoiceStatus
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance: Decimal
    invoice_date: datetime
    paid_date: Optional[datetime] = None
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    charges: List[ChargeRead] = []
    payments: List['PaymentRead'] = []

    class Config:
        from_attributes = True


# Payment Schemas
class PaymentBase(BaseModel):
    invoice_id: int
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    transaction_reference: Optional[str] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    transaction_reference: Optional[str] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentRead(PaymentBase):
    id: int
    patient_id: int
    payment_number: str
    status: PaymentStatus
    payment_date: datetime
    received_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Update forward references
InvoiceRead.model_rebuild()

