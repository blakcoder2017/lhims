from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from decimal import Decimal


class InvoiceStatus(str, enum.Enum):
    """Invoice status enumeration"""
    DRAFT = "draft"
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration"""
    CASH = "cash"
    MOBILE_MONEY = "mobile_money"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    NHIS = "nhis"
    PRIVATE_INSURANCE = "private_insurance"


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class ChargeType(str, enum.Enum):
    """Charge type enumeration"""
    CONSULTATION = "consultation"
    LAB_TEST = "lab_test"
    RADIOLOGY = "radiology"
    PHARMACY = "pharmacy"
    PROCEDURE = "procedure"
    ADMISSION = "admission"
    ANTENATAL = "antenatal"
    OTHER = "other"


class Invoice(Base):
    """
    SQLAlchemy Model for patient invoices.
    Tracks all charges and payments for a patient encounter or visit.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)  # Optional link to encounter
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)  # Optional link to appointment
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who created the invoice
    
    # Invoice Details
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique invoice number
    status = Column(postgresql.ENUM(InvoiceStatus, values_callable=lambda x: [e.value for e in x], name='invoicestatus', create_type=False), nullable=False, default=InvoiceStatus.DRAFT)
    
    # Financial Details
    subtotal = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Subtotal before discounts
    discount_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Discount amount
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Tax amount
    total_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Total amount due
    paid_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Amount paid so far
    balance = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Remaining balance
    
    # Payment Mechanism
    payment_mechanism = Column(postgresql.ENUM(PaymentMethod, values_callable=lambda x: [e.value for e in x], name='paymentmethod', create_type=False), nullable=True)
    
    # NHIS/Insurance Details
    nhis_number = Column(String(50), nullable=True)  # NHIS card number if applicable
    insurance_provider = Column(String(100), nullable=True)  # Private insurance provider if applicable
    insurance_policy_number = Column(String(100), nullable=True)  # Insurance policy number
    
    # Dates
    invoice_date = Column(DateTime, nullable=False, server_default=func.now())
    due_date = Column(DateTime, nullable=True)  # Payment due date
    paid_date = Column(DateTime, nullable=True)  # Date when fully paid
    
    # Notes
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="invoices")
    encounter = relationship("Encounter")
    appointment = relationship("Appointment")
    created_by = relationship("User", foreign_keys=[created_by_id])
    charges = relationship("Charge", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, invoice_number='{self.invoice_number}', total={self.total_amount}, balance={self.balance})>"


class Charge(Base):
    """
    SQLAlchemy Model for individual charges on an invoice.
    Each charge represents a service or item billed to the patient.
    """
    __tablename__ = "charges"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)  # Optional link to encounter
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=True)  # Optional link to lab order
    radiology_order_id = Column(Integer, ForeignKey("radiology_orders.id"), nullable=True)  # Optional link to radiology order
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)  # Optional link to prescription
    
    # Charge Details
    charge_type = Column(postgresql.ENUM(ChargeType, values_callable=lambda x: [e.value for e in x], name='chargetype', create_type=False), nullable=False)
    description = Column(String(500), nullable=False)  # Description of the charge
    quantity = Column(Integer, nullable=False, default=1)  # Quantity
    unit_price = Column(Numeric(10, 2), nullable=False)  # Unit price
    discount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Discount for this charge
    tax_rate = Column(Numeric(5, 2), nullable=False, default=Decimal('0.00'))  # Tax rate percentage
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Tax amount
    total_amount = Column(Numeric(10, 2), nullable=False)  # Total amount for this charge
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    invoice = relationship("Invoice", back_populates="charges")
    encounter = relationship("Encounter")
    lab_order = relationship("LabOrder")
    radiology_order = relationship("RadiologyOrder")
    prescription = relationship("Prescription")
    
    def __repr__(self):
        return f"<Charge(id={self.id}, type={self.charge_type.value}, amount={self.total_amount})>"


class Payment(Base):
    """
    SQLAlchemy Model for payments made against invoices.
    Tracks individual payment transactions.
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who received the payment
    
    # Payment Details
    payment_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique payment number
    amount = Column(Numeric(10, 2), nullable=False)  # Payment amount
    payment_method = Column(postgresql.ENUM(PaymentMethod, values_callable=lambda x: [e.value for e in x], name='paymentmethod', create_type=False), nullable=False)
    status = Column(postgresql.ENUM(PaymentStatus, values_callable=lambda x: [e.value for e in x], name='paymentstatus', create_type=False), nullable=False, default=PaymentStatus.PENDING)
    
    # Transaction Details
    transaction_reference = Column(String(100), nullable=True)  # External transaction reference (e.g., mobile money reference)
    receipt_number = Column(String(50), nullable=True)  # Receipt number
    
    # Notes
    notes = Column(Text, nullable=True)  # Payment notes
    
    # Dates
    payment_date = Column(DateTime, nullable=False, server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    patient = relationship("Patient")
    received_by = relationship("User", foreign_keys=[received_by_id])
    
    def __repr__(self):
        return f"<Payment(id={self.id}, payment_number='{self.payment_number}', amount={self.amount}, status={self.status.value})>"

