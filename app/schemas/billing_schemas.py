from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.billing_models import InvoiceStatus, PaymentMethod, PaymentStatus, ChargeType, RefundStatus, DiscountType


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
    procedure_catalog_id: Optional[int] = None  # Link to procedure catalog for procedure charges


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
    opd_visit_id: Optional[int] = None  # Link to OPD visit (for OPD billing)
    admission_id: Optional[int] = None  # Link to IPD admission (for IPD billing)
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


# Refund Policy Schemas
class RefundPolicyBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    max_refund_amount: Optional[Decimal] = Field(None, ge=0)
    refund_window_days: Optional[int] = Field(None, ge=0)
    auto_approve_threshold: Optional[Decimal] = Field(None, ge=0)
    requires_approval: bool = True
    approval_level: int = Field(default=1, ge=1, le=2)


class RefundPolicyCreate(RefundPolicyBase):
    pass


class RefundPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_refund_amount: Optional[Decimal] = Field(None, ge=0)
    refund_window_days: Optional[int] = Field(None, ge=0)
    auto_approve_threshold: Optional[Decimal] = Field(None, ge=0)
    requires_approval: Optional[bool] = None
    approval_level: Optional[int] = Field(None, ge=1, le=2)


class RefundPolicyRead(RefundPolicyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Refund Schemas
class RefundBase(BaseModel):
    invoice_id: int
    payment_id: int
    amount: Decimal = Field(..., gt=0)
    reason: str
    notes: Optional[str] = None


class RefundCreate(RefundBase):
    pass


class RefundUpdate(BaseModel):
    reason: Optional[str] = None
    notes: Optional[str] = None


class RefundApprove(BaseModel):
    notes: Optional[str] = None


class RefundReject(BaseModel):
    rejection_reason: str
    notes: Optional[str] = None


class RefundProcess(BaseModel):
    refund_method: PaymentMethod
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None


class RefundRead(RefundBase):
    id: int
    refund_number: str
    status: RefundStatus
    refund_method: Optional[PaymentMethod] = None
    transaction_reference: Optional[str] = None
    rejection_reason: Optional[str] = None
    request_date: datetime
    approval_date: Optional[datetime] = None
    processed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    patient_id: int
    requested_by_id: int
    approved_by_id: Optional[int] = None
    processed_by_id: Optional[int] = None
    policy_id: Optional[int] = None

    class Config:
        from_attributes = True


# Refund with relationships
class RefundReadWithDetails(RefundRead):
    invoice: Optional[InvoiceRead] = None
    payment: Optional[PaymentRead] = None
    requested_by: Optional['UserRead'] = None
    approved_by: Optional['UserRead'] = None
    processed_by: Optional['UserRead'] = None
    policy: Optional[RefundPolicyRead] = None

    class Config:
        from_attributes = True


# User schema for forward reference
class UserRead(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


# Update forward references
RefundReadWithDetails.model_rebuild()


# Discount Rule Schemas
class DiscountRuleBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    applicable_services: Optional[List[str]] = None
    patient_categories: Optional[List[str]] = None
    min_invoice_amount: Optional[Decimal] = Field(None, ge=0)
    max_discount_amount: Optional[Decimal] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    priority: int = Field(default=0, ge=0)
    is_active: bool = True


class DiscountRuleCreate(DiscountRuleBase):
    pass


class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[Decimal] = Field(None, gt=0)
    applicable_services: Optional[List[str]] = None
    patient_categories: Optional[List[str]] = None
    min_invoice_amount: Optional[Decimal] = Field(None, ge=0)
    max_discount_amount: Optional[Decimal] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    priority: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class DiscountRuleRead(DiscountRuleBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Discount Calculation Schemas
class DiscountCalculationInput(BaseModel):
    invoice_id: int
    charge_type: Optional[str] = None  # If applying to specific charge type


class DiscountCalculationResult(BaseModel):
    discount_amount: Decimal
    applicable_rules: List[str]
    final_amount: Decimal

