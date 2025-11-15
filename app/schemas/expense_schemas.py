"""
Expense Schemas

Pydantic schemas for expense data validation and serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.expense_models import ExpenseCategory, ExpenseStatus


class ExpenseBase(BaseModel):
    """Base schema for expense data"""
    description: str = Field(..., max_length=1000)
    category: ExpenseCategory
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="GHS", max_length=10)
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_contact: Optional[str] = Field(None, max_length=100)
    invoice_number: Optional[str] = Field(None, max_length=100)
    status: ExpenseStatus = Field(default=ExpenseStatus.PENDING)
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_date: Optional[datetime] = None
    payment_reference: Optional[str] = Field(None, max_length=100)
    expense_date: datetime = Field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    receipt_path: Optional[str] = Field(None, max_length=500)
    department: Optional[str] = Field(None, max_length=100)


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense"""
    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense"""
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[ExpenseCategory] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    vendor_name: Optional[str] = Field(None, max_length=200)
    vendor_contact: Optional[str] = Field(None, max_length=100)
    invoice_number: Optional[str] = Field(None, max_length=100)
    status: Optional[ExpenseStatus] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_date: Optional[datetime] = None
    payment_reference: Optional[str] = Field(None, max_length=100)
    expense_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    receipt_path: Optional[str] = Field(None, max_length=500)
    department: Optional[str] = Field(None, max_length=100)


class Expense(ExpenseBase):
    """Schema for reading expense data"""
    id: int
    expense_number: str
    created_by_id: int
    approved_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True

