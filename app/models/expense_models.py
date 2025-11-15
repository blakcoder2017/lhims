"""
Expense Models

SQLAlchemy models for tracking hospital expenses.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum
from decimal import Decimal


class ExpenseCategory(str, enum.Enum):
    """Expense category enumeration"""
    SUPPLIES = "supplies"
    EQUIPMENT = "equipment"
    MAINTENANCE = "maintenance"
    UTILITIES = "utilities"
    SALARIES = "salaries"
    MEDICATIONS = "medications"
    LAB_SUPPLIES = "lab_supplies"
    RADIOLOGY_SUPPLIES = "radiology_supplies"
    ADMINISTRATIVE = "administrative"
    MARKETING = "marketing"
    TRAINING = "training"
    OTHER = "other"


class ExpenseStatus(str, enum.Enum):
    """Expense status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Expense(Base):
    """
    SQLAlchemy Model for tracking hospital expenses.
    """
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    
    # Expense Details
    expense_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique expense number
    description = Column(Text, nullable=False)  # Description of the expense
    category = Column(Enum(ExpenseCategory), nullable=False)  # Expense category
    amount = Column(Numeric(10, 2), nullable=False)  # Expense amount
    currency = Column(String(10), nullable=False, default="GHS")  # Currency code
    
    # Vendor/Supplier Information
    vendor_name = Column(String(200), nullable=True)  # Vendor/supplier name
    vendor_contact = Column(String(100), nullable=True)  # Vendor contact information
    invoice_number = Column(String(100), nullable=True)  # Vendor invoice number
    
    # Status and Approval
    status = Column(Enum(ExpenseStatus), nullable=False, default=ExpenseStatus.PENDING)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who approved
    approved_at = Column(DateTime, nullable=True)  # Approval date
    
    # Payment Information
    payment_method = Column(String(50), nullable=True)  # Payment method used
    payment_date = Column(DateTime, nullable=True)  # Date payment was made
    payment_reference = Column(String(100), nullable=True)  # Payment reference number
    
    # Dates
    expense_date = Column(DateTime, nullable=False, server_default=func.now())  # Date expense was incurred
    due_date = Column(DateTime, nullable=True)  # Payment due date
    
    # Notes and Attachments
    notes = Column(Text, nullable=True)  # Additional notes
    receipt_path = Column(String(500), nullable=True)  # Path to receipt/document
    
    # Foreign Keys
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who created the expense
    department = Column(String(100), nullable=True)  # Department that incurred the expense
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True, server_default='true')
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    
    def __repr__(self):
        return f"<Expense(id={self.id}, expense_number='{self.expense_number}', amount={self.amount}, category={self.category.value})>"

