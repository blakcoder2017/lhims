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
    PAEDIATRIC = "paediatric"
    NEONATAL = "neonatal"
    EMERGENCY = "emergency"
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
    appointment_id = Column(Integer, ForeignKey("scheduled_appointments.id"), nullable=True)  # Optional link to appointment
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)  # Link to OPD visit (for OPD billing)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Link to IPD admission (for IPD billing)
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
    refunds_credit = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Total refunds/credits applied
    balance = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Remaining balance (total - paid - refunds_credit)
    
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
    appointment = relationship("ScheduledAppointment")
    opd_visit = relationship("OPDVisit", back_populates="invoices")
    admission = relationship("Admission", foreign_keys=[admission_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    charges = relationship("Charge", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    pharmacy_dispenses = relationship("PharmacyDispense", back_populates="invoice")
    refunds = relationship("Refund", back_populates="invoice", cascade="all, delete-orphan")
    consolidated_receipt_invoices = relationship("ConsolidatedReceiptInvoice", back_populates="invoice", cascade="all, delete-orphan")
    
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
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)  # Link to OPD visit (denormalized for reporting)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Link to IPD admission (denormalized for reporting)
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=True)  # Optional link to lab order
    radiology_order_id = Column(Integer, ForeignKey("radiology_orders.id"), nullable=True)  # Optional link to radiology order
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)  # Optional link to prescription
    procedure_catalog_id = Column(Integer, ForeignKey("procedure_catalog.id"), nullable=True)  # Link to procedure catalog for procedure charges
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # Department this charge belongs to
    
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
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="charges")
    encounter = relationship("Encounter")
    lab_order = relationship("LabOrder")
    radiology_order = relationship("RadiologyOrder")
    prescription = relationship("Prescription", back_populates="charges")
    procedure_catalog = relationship("ProcedureCatalog")
    department = relationship("Department")
    charge_payments = relationship("ChargePayment", back_populates="charge")
    
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
    charge_payments = relationship("ChargePayment", back_populates="payment")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, payment_number='{self.payment_number}', amount={self.amount}, status={self.status.value})>"


class Receipt(Base):
    """
    SQLAlchemy Model for payment receipts.
    Tracks receipt generation and provides audit trail for payments.
    """
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who generated the receipt
    
    # Receipt Details
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique receipt number
    amount = Column(Numeric(10, 2), nullable=False)  # Payment amount
    payment_method = Column(String(50), nullable=False)  # Payment method used
    currency = Column(String(10), nullable=False, default="GHS")  # Currency code
    
    # Timestamps
    generated_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    payment = relationship("Payment")
    patient = relationship("Patient")
    invoice = relationship("Invoice")
    generated_by = relationship("User", foreign_keys=[generated_by_id])
    
    def __repr__(self):
        return f"<Receipt(id={self.id}, receipt_number='{self.receipt_number}', amount={self.amount})>"


class RefundStatus(str, enum.Enum):
    """Refund status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"
    CANCELLED = "cancelled"


class RefundPolicy(Base):
    """
    SQLAlchemy Model for refund policy configuration.
    Stores hospital-wide refund policy settings.
    """
    __tablename__ = "refund_policies"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Policy Settings
    name = Column(String(100), nullable=False)  # Policy name
    description = Column(Text, nullable=True)  # Policy description
    is_active = Column(Boolean, default=True)  # Whether this policy is active
    
    # Refund Rules
    max_refund_amount = Column(Numeric(10, 2), nullable=True)  # Maximum refund amount allowed (null = unlimited)
    refund_window_days = Column(Integer, nullable=True)  # Days after payment within which refund can be requested
    auto_approve_threshold = Column(Numeric(10, 2), nullable=True)  # Amount below which refund auto-approves
    
    # Approval Requirements
    requires_approval = Column(Boolean, default=True)  # Whether refunds require approval
    approval_level = Column(Integer, default=1)  # 1 = single approval, 2 = dual approval
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<RefundPolicy(id={self.id}, name='{self.name}', is_active={self.is_active})>"


class Refund(Base):
    """
    SQLAlchemy Model for refund requests.
    Tracks all refund requests and their processing status.
    """
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)  # Original payment being refunded
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who requested the refund
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who approved the refund
    processed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who processed the refund
    policy_id = Column(Integer, ForeignKey("refund_policies.id"), nullable=True)  # Applied policy
    
    # Refund Details
    refund_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique refund number
    amount = Column(Numeric(10, 2), nullable=False)  # Refund amount
    reason = Column(Text, nullable=False)  # Reason for refund
    status = Column(postgresql.ENUM(RefundStatus, values_callable=lambda x: [e.value for e in x], name='refundstatus', create_type=False), nullable=False, default=RefundStatus.PENDING)
    
    # Refund Processing
    refund_method = Column(postgresql.ENUM(PaymentMethod, values_callable=lambda x: [e.value for e in x], name='paymentmethod', create_type=False), nullable=True)  # How refund will be issued
    transaction_reference = Column(String(100), nullable=True)  # External refund transaction reference
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    
    # Notes
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Dates
    request_date = Column(DateTime, nullable=False, server_default=func.now())
    approval_date = Column(DateTime, nullable=True)
    processed_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="refunds")
    payment = relationship("Payment", back_populates="refunds")
    patient = relationship("Patient")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    processed_by = relationship("User", foreign_keys=[processed_by_id])
    policy = relationship("RefundPolicy")
    
    def __repr__(self):
        return f"<Refund(id={self.id}, refund_number='{self.refund_number}', amount={self.amount}, status={self.status.value})>"


class ChargePayment(Base):
    """
    SQLAlchemy Model for tracking payment allocations to individual charges.
    Allows partial payments per charge within an invoice.
    """
    __tablename__ = "charge_payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=False)
    
    # Payment Allocation
    amount = Column(Numeric(10, 2), nullable=False)  # Amount allocated to this charge
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    payment = relationship("Payment", back_populates="charge_payments")
    charge = relationship("Charge", back_populates="charge_payments")
    
    def __repr__(self):
        return f"<ChargePayment(id={self.id}, payment_id={self.payment_id}, charge_id={self.charge_id}, amount={self.amount})>"


class DiscountType(str, enum.Enum):
    """Discount type enumeration"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class DiscountRule(Base):
    """
    SQLAlchemy Model for discount rules.
    Allows structured discount management with configurable rules.
    """
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Rule Details
    name = Column(String(100), nullable=False)  # Rule name
    description = Column(Text, nullable=True)  # Rule description
    is_active = Column(Boolean, default=True)  # Whether this rule is active
    
    # Discount Type and Value
    discount_type = Column(postgresql.ENUM(DiscountType, values_callable=lambda x: [e.value for e in x], name='discounttype', create_type=False), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)  # Percentage or fixed amount
    
    # Service Applicability (JSON - list of charge types this applies to)
    applicable_services = Column(postgresql.JSON, nullable=True)  # e.g., ["consultation", "lab_test"]
    
    # Patient Category Applicability (JSON - list of patient categories)
    # Categories: elderly, children, pregnant, nhis, staff, etc.
    patient_categories = Column(postgresql.JSON, nullable=True)
    
    # Minimum and Maximum Amount
    min_invoice_amount = Column(Numeric(10, 2), nullable=True)  # Minimum invoice amount to qualify
    max_discount_amount = Column(Numeric(10, 2), nullable=True)  # Maximum discount amount allowed
    
    # Validity Period
    valid_from = Column(DateTime, nullable=True)  # Start date
    valid_to = Column(DateTime, nullable=True)  # End date
    
    # Priority (higher priority rules applied first)
    priority = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<DiscountRule(id={self.id}, name='{self.name}', discount_type={self.discount_type.value}, discount_value={self.discount_value})>"


class ConsolidatedReceiptStatus(str, enum.Enum):
    """Status for consolidated receipt"""
    DRAFT = "draft"
    PRINTED = "printed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConsolidatedReceiptPrintAction(str, enum.Enum):
    """Print action types for audit log"""
    PRINT = "print"
    REPRINT = "reprint"
    CANCEL = "cancel"
    VIEW = "view"


class ConsolidatedReceipt(Base):
    """
    SQLAlchemy Model for consolidated receipts.
    Links multiple invoices/payments into a single receipt.
    """
    __tablename__ = "consolidated_receipts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    generated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Receipt Details
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default=ConsolidatedReceiptStatus.DRAFT.value)
    
    # Financial Summary
    total_invoices = Column(Integer, nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_paid = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_discount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_balance = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    
    # Primary Payment Method (for display)
    primary_payment_method = Column(String(50), nullable=False)
    
    # Timestamps
    generated_at = Column(DateTime, nullable=False, server_default=func.now())
    printed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient")
    generated_by = relationship("User", foreign_keys=[generated_by_id])
    invoices = relationship("ConsolidatedReceiptInvoice", back_populates="receipt", cascade="all, delete-orphan")
    payments = relationship("ConsolidatedReceiptPayment", back_populates="receipt", cascade="all, delete-orphan")
    print_logs = relationship("ConsolidatedReceiptPrintLog", back_populates="receipt", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConsolidatedReceipt(id={self.id}, receipt_number='{self.receipt_number}', total={self.total_amount})>"


class ConsolidatedReceiptInvoice(Base):
    """
    Links invoices to a consolidated receipt.
    """
    __tablename__ = "consolidated_receipt_invoices"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    receipt_id = Column(Integer, ForeignKey("consolidated_receipts.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # Invoice Details at Time of Receipt
    invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_amount = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False)
    charge_type = Column(String(20), nullable=True)  # Primary charge type
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    receipt = relationship("ConsolidatedReceipt", back_populates="invoices")
    invoice = relationship("Invoice", back_populates="consolidated_receipt_invoices")
    charges = relationship("ConsolidatedReceiptCharge", back_populates="receipt_invoice", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ConsolidatedReceiptInvoice(id={self.id}, invoice_number='{self.invoice_number}')>"


class ConsolidatedReceiptCharge(Base):
    """
    Stores individual charges from invoices for the receipt.
    Provides itemized breakdown.
    """
    __tablename__ = "consolidated_receipt_charges"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    receipt_invoice_id = Column(Integer, ForeignKey("consolidated_receipt_invoices.id"), nullable=False)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=True)  # Optional link to original charge
    
    # Charge Details
    description = Column(String(500), nullable=False)
    charge_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    receipt_invoice = relationship("ConsolidatedReceiptInvoice", back_populates="charges")
    
    def __repr__(self):
        return f"<ConsolidatedReceiptCharge(id={self.id}, description='{self.description}')>"


class ConsolidatedReceiptPayment(Base):
    """
    Links payments to a consolidated receipt.
    Supports multiple payment methods in single transaction.
    """
    __tablename__ = "consolidated_receipt_payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    receipt_id = Column(Integer, ForeignKey("consolidated_receipts.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    
    # Payment Details
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    transaction_reference = Column(String(100), nullable=True)
    payment_number = Column(String(50), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    receipt = relationship("ConsolidatedReceipt", back_populates="payments")
    payment = relationship("Payment")
    
    def __repr__(self):
        return f"<ConsolidatedReceiptPayment(id={self.id}, amount={self.amount}, method={self.payment_method})>"


class ConsolidatedReceiptPrintLog(Base):
    """
    Audit log for all print actions on consolidated receipts.
    """
    __tablename__ = "consolidated_receipt_print_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    receipt_id = Column(Integer, ForeignKey("consolidated_receipts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Print Details
    action = Column(String(20), nullable=False)  # PRINT, REPRINT, CANCEL, VIEW
    status = Column(String(20), nullable=False)  # SUCCESS, FAILED
    printer_name = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Authorization for reprints
    authorized_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)
    
    # Request Details
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    receipt = relationship("ConsolidatedReceipt", back_populates="print_logs")
    user = relationship("User", foreign_keys=[user_id])
    authorized_by = relationship("User", foreign_keys=[authorized_by_id])
    
    def __repr__(self):
        return f"<ConsolidatedReceiptPrintLog(id={self.id}, action={self.action}, status={self.status})>"

