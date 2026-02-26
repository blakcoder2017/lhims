from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from sqlalchemy.exc import IntegrityError

from app.models.billing_models import Invoice, Charge, Payment, ChargePayment, InvoiceStatus, PaymentStatus, PaymentMethod, ChargeType, Refund, RefundPolicy, RefundStatus
from app.models.user_models import User
from app.schemas.billing_schemas import (
    InvoiceCreate, InvoiceUpdate, InvoiceRead,
    ChargeCreate, ChargeUpdate,
    PaymentCreate, PaymentUpdate,
    RefundCreate, RefundUpdate, RefundPolicyCreate, RefundPolicyUpdate
)


def generate_invoice_number(db: Session) -> str:
    """Generate a unique invoice number with retry logic for race conditions"""
    prefix = "INV"
    date_str = datetime.now().strftime("%Y%m%d")
    max_retries = 5
    
    for attempt in range(max_retries):
        # Get the last invoice number for today
        last_invoice = db.query(Invoice).filter(
            Invoice.invoice_number.like(f"{prefix}-{date_str}-%")
        ).order_by(Invoice.id.desc()).first()
        
        if last_invoice:
            # Extract sequence number and increment
            try:
                sequence = int(last_invoice.invoice_number.split('-')[-1])
                sequence += 1
            except (ValueError, IndexError):
                sequence = 1
        else:
            sequence = 1
        
        invoice_number = f"{prefix}-{date_str}-{sequence:04d}"
        
        # Check if this invoice number already exists
        existing = db.query(Invoice).filter(
            Invoice.invoice_number == invoice_number
        ).first()
        
        if not existing:
            return invoice_number
        
        # If exists, retry with incremented sequence
        if attempt < max_retries - 1:
            db.rollback()  # Clear any pending transaction
            continue
    
    # Fallback: use UUID if all retries fail
    return f"{prefix}-{date_str}-{uuid.uuid4().hex[:8].upper()}"


def generate_payment_number(db: Session) -> str:
    """Generate a unique payment number with retry logic for race conditions"""
    prefix = "PAY"
    date_str = datetime.now().strftime("%Y%m%d")
    max_retries = 5
    
    for attempt in range(max_retries):
        # Get the last payment number for today
        last_payment = db.query(Payment).filter(
            Payment.payment_number.like(f"{prefix}-{date_str}-%")
        ).order_by(Payment.id.desc()).first()
        
        if last_payment:
            try:
                sequence = int(last_payment.payment_number.split('-')[-1])
                sequence += 1
            except (ValueError, IndexError):
                sequence = 1
        else:
            sequence = 1
        
        payment_number = f"{prefix}-{date_str}-{sequence:04d}"
        
        # Check if this payment number already exists
        existing = db.query(Payment).filter(
            Payment.payment_number == payment_number
        ).first()
        
        if not existing:
            return payment_number
        
        # If exists, retry with incremented sequence
        if attempt < max_retries - 1:
            db.rollback()
            continue
    
    # Fallback: use UUID if all retries fail
    return f"{prefix}-{date_str}-{uuid.uuid4().hex[:8].upper()}"


def generate_receipt_number(db: Session) -> str:
    """Generate a unique receipt number with retry logic for race conditions"""
    prefix = "RCP"
    date_str = datetime.now().strftime("%Y%m%d")
    max_retries = 5
    
    for attempt in range(max_retries):
        # Get the last receipt number for today
        last_payment = db.query(Payment).filter(
            Payment.receipt_number.isnot(None),
            Payment.receipt_number.like(f"{prefix}-{date_str}-%")
        ).order_by(Payment.id.desc()).first()
        
        if last_payment and last_payment.receipt_number:
            try:
                sequence = int(last_payment.receipt_number.split('-')[-1])
                sequence += 1
            except (ValueError, IndexError):
                sequence = 1
        else:
            sequence = 1
        
        receipt_number = f"{prefix}-{date_str}-{sequence:04d}"
        
        # Check if this receipt number already exists
        existing = db.query(Payment).filter(
            Payment.receipt_number == receipt_number
        ).first()
        
        if not existing:
            return receipt_number
        
        # If exists, retry with incremented sequence
        if attempt < max_retries - 1:
            db.rollback()
            continue
    
    # Fallback: use UUID if all retries fail
    return f"{prefix}-{date_str}-{uuid.uuid4().hex[:8].upper()}"


def calculate_charge_total(charge: ChargeCreate) -> tuple[Decimal, Decimal]:
    """Calculate tax amount and total amount for a charge"""
    subtotal = charge.unit_price * charge.quantity - charge.discount
    tax_amount = subtotal * (charge.tax_rate / Decimal('100'))
    total = subtotal + tax_amount
    return tax_amount, total


def create_invoice(db: Session, invoice: InvoiceCreate, created_by_id: int) -> Invoice:
    """Create a new invoice with charges"""
    # Generate invoice number
    invoice_number = generate_invoice_number(db)
    
    # Calculate totals
    subtotal = Decimal('0.00')
    total_tax = Decimal('0.00')
    
    # Create invoice
    db_invoice = Invoice(
        invoice_number=invoice_number,
        patient_id=invoice.patient_id,
        encounter_id=invoice.encounter_id,
        appointment_id=invoice.appointment_id,
        opd_visit_id=invoice.opd_visit_id,  # Link to OPD visit
        admission_id=invoice.admission_id,  # Link to IPD admission
        created_by_id=created_by_id,
        payment_mechanism=invoice.payment_mechanism,
        nhis_number=invoice.nhis_number,
        insurance_provider=invoice.insurance_provider,
        insurance_policy_number=invoice.insurance_policy_number,
        due_date=invoice.due_date,
        notes=invoice.notes,
        status=InvoiceStatus.DRAFT,
        subtotal=subtotal,
        discount_amount=Decimal('0.00'),
        tax_amount=total_tax,
        total_amount=Decimal('0.00'),
        paid_amount=Decimal('0.00'),
        balance=Decimal('0.00')
    )
    db.add(db_invoice)
    db.flush()  # Get the invoice ID
    
    # Create charges
    for charge_data in invoice.charges or []:
        tax_amount, total_amount = calculate_charge_total(charge_data)
        
        db_charge = Charge(
            invoice_id=db_invoice.id,
            charge_type=charge_data.charge_type,
            description=charge_data.description,
            quantity=charge_data.quantity,
            unit_price=charge_data.unit_price,
            discount=charge_data.discount,
            tax_rate=charge_data.tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            encounter_id=charge_data.encounter_id,
            lab_order_id=charge_data.lab_order_id,
            radiology_order_id=charge_data.radiology_order_id,
            prescription_id=charge_data.prescription_id
        )
        db.add(db_charge)
        
        subtotal += charge_data.unit_price * charge_data.quantity - charge_data.discount
        total_tax += tax_amount
    
    # Update invoice totals
    db_invoice.subtotal = subtotal
    db_invoice.tax_amount = total_tax
    db_invoice.total_amount = subtotal + total_tax
    db_invoice.balance = db_invoice.total_amount - db_invoice.paid_amount
    
    # Set status to PENDING if there are charges
    if invoice.charges:
        db_invoice.status = InvoiceStatus.PENDING
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


def get_invoice(db: Session, invoice_id: int) -> Optional[Invoice]:
    """Get an invoice by ID"""
    return db.query(Invoice).options(
        joinedload(Invoice.patient),
        joinedload(Invoice.charges),
        joinedload(Invoice.payments).joinedload(Payment.received_by),
        joinedload(Invoice.created_by)
    ).filter(Invoice.id == invoice_id, Invoice.is_active == True).first()


def get_invoice_by_number(db: Session, invoice_number: str) -> Optional[Invoice]:
    """Get an invoice by invoice number"""
    return db.query(Invoice).options(
        joinedload(Invoice.patient),
        joinedload(Invoice.charges),
        joinedload(Invoice.payments).joinedload(Payment.received_by),
        joinedload(Invoice.created_by)
    ).filter(Invoice.invoice_number == invoice_number, Invoice.is_active == True).first()


def get_invoices_by_patient(db: Session, patient_id: int, skip: int = 0, limit: int = 100) -> List[Invoice]:
    """Get all invoices for a patient"""
    return db.query(Invoice).options(
        joinedload(Invoice.charges),
        joinedload(Invoice.payments)
    ).filter(
        Invoice.patient_id == patient_id,
        Invoice.is_active == True
    ).order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit).all()


def get_invoices_by_encounter(db: Session, encounter_id: int) -> List[Invoice]:
    """Get all invoices for an encounter"""
    return db.query(Invoice).options(
        joinedload(Invoice.charges),
        joinedload(Invoice.payments)
    ).filter(
        Invoice.encounter_id == encounter_id,
        Invoice.is_active == True
    ).all()


def update_invoice(db: Session, invoice_id: int, invoice_update: InvoiceUpdate) -> Optional[Invoice]:
    """Update an invoice"""
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        return None
    
    update_data = invoice_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_invoice, field, value)
    
    # Recalculate balance if totals changed
    if 'discount_amount' in update_data or 'tax_amount' in update_data:
        db_invoice.total_amount = db_invoice.subtotal - db_invoice.discount_amount + db_invoice.tax_amount
        db_invoice.balance = db_invoice.total_amount - db_invoice.paid_amount
    
    # Update status based on balance
    if db_invoice.balance <= 0 and db_invoice.paid_amount > 0:
        db_invoice.status = InvoiceStatus.PAID
        db_invoice.paid_date = datetime.now()
    elif db_invoice.paid_amount > 0 and db_invoice.balance > 0:
        db_invoice.status = InvoiceStatus.PARTIALLY_PAID
    elif db_invoice.status == InvoiceStatus.DRAFT and db_invoice.total_amount > 0:
        db_invoice.status = InvoiceStatus.PENDING
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice


def delete_invoice(db: Session, invoice_id: int) -> bool:
    """Soft delete an invoice"""
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        return False
    
    db_invoice.is_active = False
    db.commit()
    return True


# Charge CRUD
def add_charge_to_invoice(db: Session, invoice_id: int, charge: ChargeCreate) -> Charge:
    """Add a charge to an existing invoice"""
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise ValueError("Invoice not found")
    
    tax_amount, total_amount = calculate_charge_total(charge)
    
    db_charge = Charge(
        invoice_id=invoice_id,
        charge_type=charge.charge_type,
        description=charge.description,
        quantity=charge.quantity,
        unit_price=charge.unit_price,
        discount=charge.discount,
        tax_rate=charge.tax_rate,
        tax_amount=tax_amount,
        total_amount=total_amount,
        encounter_id=charge.encounter_id,
        opd_visit_id=db_invoice.opd_visit_id,  # Link to OPD visit from invoice
        admission_id=db_invoice.admission_id,  # Link to IPD admission from invoice
        lab_order_id=charge.lab_order_id,
        radiology_order_id=charge.radiology_order_id,
        prescription_id=charge.prescription_id,
        procedure_catalog_id=charge.procedure_catalog_id  # Link to procedure catalog
    )
    db.add(db_charge)
    
    # Update invoice totals
    db_invoice.subtotal += charge.unit_price * charge.quantity - charge.discount
    db_invoice.tax_amount += tax_amount
    db_invoice.total_amount = db_invoice.subtotal - db_invoice.discount_amount + db_invoice.tax_amount
    db_invoice.balance = db_invoice.total_amount - db_invoice.paid_amount
    
    if db_invoice.status == InvoiceStatus.DRAFT:
        db_invoice.status = InvoiceStatus.PENDING
    
    db.commit()
    db.refresh(db_charge)
    return db_charge


def update_charge(db: Session, charge_id: int, charge_update: ChargeUpdate) -> Optional[Charge]:
    """Update a charge"""
    db_charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not db_charge:
        return None
    
    # Store old values for recalculation
    old_subtotal = db_charge.unit_price * db_charge.quantity - db_charge.discount
    old_tax = db_charge.tax_amount
    
    update_data = charge_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_charge, field, value)
    
    # Recalculate charge totals
    new_subtotal = db_charge.unit_price * db_charge.quantity - db_charge.discount
    new_tax = new_subtotal * (db_charge.tax_rate / Decimal('100'))
    db_charge.tax_amount = new_tax
    db_charge.total_amount = new_subtotal + new_tax
    
    # Update invoice totals
    db_invoice = db.query(Invoice).filter(Invoice.id == db_charge.invoice_id).first()
    db_invoice.subtotal = db_invoice.subtotal - old_subtotal + new_subtotal
    db_invoice.tax_amount = db_invoice.tax_amount - old_tax + new_tax
    db_invoice.total_amount = db_invoice.subtotal - db_invoice.discount_amount + db_invoice.tax_amount
    
    # Calculate potential new balance
    potential_balance = db_invoice.total_amount - db_invoice.paid_amount
    
    # If reducing the charge would cause negative balance (e.g., revisit discount applied after payment),
    # also reduce the paid_amount to prevent negative balance. This handles cases where a patient
    # paid full price but later a discount (revisit) is applied.
    if potential_balance < Decimal('0.00') and db_invoice.paid_amount > Decimal('0.00'):
        # Adjust paid_amount to match the new total, keeping balance at 0
        db_invoice.paid_amount = db_invoice.total_amount
        potential_balance = Decimal('0.00')
    
    db_invoice.balance = potential_balance
    
    # Update invoice status based on final balance
    if db_invoice.balance <= Decimal('0.00') and db_invoice.paid_amount > Decimal('0.00'):
        db_invoice.status = InvoiceStatus.PAID
        if not db_invoice.paid_date:
            db_invoice.paid_date = datetime.now()
    elif db_invoice.paid_amount > Decimal('0.00') and db_invoice.balance > Decimal('0.00'):
        db_invoice.status = InvoiceStatus.PARTIALLY_PAID
    
    db.commit()
    db.refresh(db_charge)
    return db_charge


def delete_charge(db: Session, charge_id: int) -> bool:
    """Delete a charge and update invoice totals"""
    db_charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not db_charge:
        return False
    
    # Update invoice totals
    db_invoice = db.query(Invoice).filter(Invoice.id == db_charge.invoice_id).first()
    charge_subtotal = db_charge.unit_price * db_charge.quantity - db_charge.discount
    
    db_invoice.subtotal -= charge_subtotal
    db_invoice.tax_amount -= db_charge.tax_amount
    db_invoice.total_amount = db_invoice.subtotal - db_invoice.discount_amount + db_invoice.tax_amount
    db_invoice.balance = db_invoice.total_amount - db_invoice.paid_amount
    
    db.delete(db_charge)
    db.commit()
    return True


# Payment CRUD
def create_payment(db: Session, payment: PaymentCreate, received_by_id: int) -> Payment:
    """Create a payment and update invoice"""
    # Generate payment number
    payment_number = generate_payment_number(db)
    
    # Generate receipt number if not provided
    receipt_number = payment.receipt_number
    if not receipt_number:
        receipt_number = generate_receipt_number(db)
    
    # Get invoice
    db_invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    if not db_invoice:
        raise ValueError("Invoice not found")
    
    # Create payment
    db_payment = Payment(
        payment_number=payment_number,
        invoice_id=payment.invoice_id,
        patient_id=db_invoice.patient_id,
        received_by_id=received_by_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        transaction_reference=payment.transaction_reference,
        receipt_number=receipt_number,
        notes=payment.notes,
        status=PaymentStatus.COMPLETED
    )
    db.add(db_payment)
    
    # Update invoice - ensure we're working with Decimal types
    from decimal import Decimal
    payment_amount = Decimal(str(payment.amount))
    
    # Get current values as Decimal
    current_paid = Decimal(str(db_invoice.paid_amount or 0))
    total_amount = Decimal(str(db_invoice.total_amount or 0))
    
    # Update paid amount
    new_paid_amount = current_paid + payment_amount
    db_invoice.paid_amount = new_paid_amount
    
    # Recalculate balance
    new_balance = total_amount - new_paid_amount
    db_invoice.balance = new_balance
    
    # Update invoice status
    if new_balance <= Decimal('0.00') and payment_amount > Decimal('0.00'):
        db_invoice.status = InvoiceStatus.PAID
        db_invoice.paid_date = datetime.now()
    elif new_paid_amount > Decimal('0.00'):
        db_invoice.status = InvoiceStatus.PARTIALLY_PAID
    
    db.commit()
    db.refresh(db_invoice)
    db.refresh(db_payment)
    
    # Update OPD visit payment status if invoice is linked to an OPD visit
    if db_invoice.opd_visit_id:
        from app.crud import opd_crud
        # Sync payment status (this will check if invoice is fully paid)
        opd_crud.sync_opd_visit_payment_status(db, db_invoice.opd_visit_id)
    
    return db_payment


def allocate_payment_to_charge(db: Session, payment_id: int, charge_id: int, amount: Decimal) -> Optional[ChargePayment]:
    """Allocate a payment to a charge (ChargePayment) so it appears in paid bills and charge-level tracking."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not payment or not charge or amount <= 0:
        return None
    if charge.invoice_id != payment.invoice_id:
        return None
    cp = ChargePayment(payment_id=payment_id, charge_id=charge_id, amount=amount)
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return cp


def create_receipt(db: Session, payment_id: int, generated_by_id: int) -> "Receipt":
    """
    Create a receipt for a payment.
    Returns the created receipt.
    """
    from app.models.billing_models import Receipt, Payment
    
    # Get payment
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise ValueError("Payment not found")
    
    # Check if receipt already exists
    existing_receipt = db.query(Receipt).filter(
        Receipt.payment_id == payment_id,
        Receipt.is_active == True
    ).first()
    
    if existing_receipt:
        return existing_receipt
    
    # Create receipt
    receipt = Receipt(
        payment_id=payment.id,
        patient_id=payment.patient_id,
        invoice_id=payment.invoice_id,
        generated_by_id=generated_by_id,
        receipt_number=payment.receipt_number or generate_receipt_number(db),
        amount=payment.amount,
        payment_method=payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method),
        currency="GHS"
    )
    
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    
    return receipt


def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    """Get a payment by ID"""
    from app.models.billing_models import Invoice
    return db.query(Payment).options(
        joinedload(Payment.invoice).joinedload(Invoice.patient),
        joinedload(Payment.patient),
        joinedload(Payment.received_by)
    ).filter(Payment.id == payment_id, Payment.is_active == True).first()


def get_payments_by_invoice(db: Session, invoice_id: int) -> List[Payment]:
    """Get all payments for an invoice"""
    return db.query(Payment).options(
        joinedload(Payment.received_by)
    ).filter(
        Payment.invoice_id == invoice_id,
        Payment.is_active == True
    ).order_by(Payment.payment_date.desc()).all()


def get_payments_by_patient(db: Session, patient_id: int, skip: int = 0, limit: int = 100) -> List[Payment]:
    """Get all payments for a patient"""
    return db.query(Payment).options(
        joinedload(Payment.invoice)
    ).filter(
        Payment.patient_id == patient_id,
        Payment.is_active == True
    ).order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()


def update_payment(db: Session, payment_id: int, payment_update: PaymentUpdate) -> Optional[Payment]:
    """Update a payment"""
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        return None
    
    update_data = payment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_payment, field, value)
    
    db.commit()
    db.refresh(db_payment)
    return db_payment


def delete_payment(db: Session, payment_id: int) -> bool:
    """Soft delete a payment and update invoice"""
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        return False
    
    # Update invoice
    db_invoice = db.query(Invoice).filter(Invoice.id == db_payment.invoice_id).first()
    db_invoice.paid_amount -= db_payment.amount
    db_invoice.balance = db_invoice.total_amount - db_invoice.paid_amount
    
    # Update invoice status
    if db_invoice.balance == db_invoice.total_amount:
        db_invoice.status = InvoiceStatus.PENDING
        db_invoice.paid_date = None
    elif db_invoice.paid_amount > 0:
        db_invoice.status = InvoiceStatus.PARTIALLY_PAID
    
    db_payment.is_active = False
    db.commit()
    return True


# ==================== Refund Policy CRUD ====================

def generate_refund_number(db: Session) -> str:
    """Generate a unique refund number"""
    prefix = "RFN"
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Get the last refund number for today
    last_refund = db.query(Refund).filter(
        Refund.refund_number.like(f"{prefix}-{date_str}-%")
    ).order_by(Refund.id.desc()).first()
    
    if last_refund:
        try:
            sequence = int(last_refund.refund_number.split('-')[-1])
            sequence += 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1
    
    return f"{prefix}-{date_str}-{sequence:04d}"


def create_refund_policy(db: Session, policy_data: RefundPolicyCreate, user_id: int) -> RefundPolicy:
    """Create a new refund policy"""
    db_policy = RefundPolicy(
        name=policy_data.name,
        description=policy_data.description,
        is_active=policy_data.is_active,
        max_refund_amount=policy_data.max_refund_amount,
        refund_window_days=policy_data.refund_window_days,
        auto_approve_threshold=policy_data.auto_approve_threshold,
        requires_approval=policy_data.requires_approval,
        approval_level=policy_data.approval_level,
        created_by_id=user_id
    )
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


def get_refund_policies(db: Session, skip: int = 0, limit: int = 100) -> List[RefundPolicy]:
    """Get all refund policies"""
    return db.query(RefundPolicy).offset(skip).limit(limit).all()


def get_refund_policy(db: Session, policy_id: int) -> Optional[RefundPolicy]:
    """Get a refund policy by ID"""
    return db.query(RefundPolicy).filter(RefundPolicy.id == policy_id).first()


def get_active_refund_policy(db: Session) -> Optional[RefundPolicy]:
    """Get the active refund policy"""
    return db.query(RefundPolicy).filter(RefundPolicy.is_active == True).first()


def update_refund_policy(db: Session, policy_id: int, policy_data: RefundPolicyUpdate) -> Optional[RefundPolicy]:
    """Update a refund policy"""
    db_policy = db.query(RefundPolicy).filter(RefundPolicy.id == policy_id).first()
    if not db_policy:
        return None
    
    update_data = policy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_policy, field, value)
    
    db.commit()
    db.refresh(db_policy)
    return db_policy


def delete_refund_policy(db: Session, policy_id: int) -> bool:
    """Soft delete a refund policy"""
    db_policy = db.query(RefundPolicy).filter(RefundPolicy.id == policy_id).first()
    if not db_policy:
        return False
    
    db_policy.is_active = False
    db.commit()
    return True


# ==================== Refund CRUD ====================

def create_refund(db: Session, refund_data: RefundCreate, user_id: int) -> Optional[Refund]:
    """Create a new refund request"""
    
    # Verify the payment exists and is valid
    payment = db.query(Payment).filter(Payment.id == refund_data.payment_id).first()
    if not payment:
        return None
    
    # Verify the invoice matches
    invoice = db.query(Invoice).filter(Invoice.id == refund_data.invoice_id).first()
    if not invoice:
        return None
    
    # Verify the patient matches
    if payment.patient_id != invoice.patient_id:
        return None
    
    # Check refund policy rules
    policy = get_active_refund_policy(db)
    error_message = validate_refund_request(db, payment, invoice, refund_data.amount, policy)
    if error_message:
        raise ValueError(error_message)
    
    # Generate refund number
    refund_number = generate_refund_number(db)
    
    # Check if auto-approve
    auto_approve = False
    if policy and policy.auto_approve_threshold and refund_data.amount <= policy.auto_approve_threshold:
        auto_approve = True
    
    db_refund = Refund(
        invoice_id=refund_data.invoice_id,
        payment_id=refund_data.payment_id,
        patient_id=payment.patient_id,
        requested_by_id=user_id,
        refund_number=refund_number,
        amount=refund_data.amount,
        reason=refund_data.reason,
        notes=refund_data.notes,
        status=RefundStatus.APPROVED if auto_approve else RefundStatus.PENDING,
        policy_id=policy.id if policy else None
    )
    
    db.add(db_refund)
    db.commit()
    db.refresh(db_refund)
    return db_refund


def validate_refund_request(db: Session, payment: Payment, invoice: Invoice, amount: Decimal, policy: Optional[RefundPolicy]) -> Optional[str]:
    """Validate a refund request against policy rules"""
    
    # Check if payment is completed
    if payment.status != PaymentStatus.COMPLETED:
        return "Can only refund completed payments"
    
    # Check if payment was already refunded
    existing_refund = db.query(Refund).filter(
        Refund.payment_id == payment.id,
        Refund.status == RefundStatus.PROCESSED
    ).first()
    if existing_refund:
        return "Payment has already been refunded"
    
    # Check amount doesn't exceed payment amount
    if amount > payment.amount:
        return "Refund amount cannot exceed payment amount"
    
    # Check policy rules
    if policy:
        # Check refund window
        if policy.refund_window_days:
            days_since_payment = (datetime.now() - payment.payment_date).days
            if days_since_payment > policy.refund_window_days:
                return f"Refund window of {policy.refund_window_days} days has expired"
        
        # Check max refund amount
        if policy.max_refund_amount and amount > policy.max_refund_amount:
            return f"Refund amount exceeds maximum allowed of {policy.max_refund_amount}"
    
    return None


def get_refunds(db: Session, skip: int = 0, limit: int = 100, status: Optional[RefundStatus] = None) -> List[Refund]:
    """Get all refunds with optional status filter"""
    query = db.query(Refund)
    if status:
        query = query.filter(Refund.status == status)
    return query.order_by(Refund.created_at.desc()).offset(skip).limit(limit).all()


def get_refund(db: Session, refund_id: int) -> Optional[Refund]:
    """Get a refund by ID"""
    return db.query(Refund).filter(Refund.id == refund_id).first()


def get_refund_by_number(db: Session, refund_number: str) -> Optional[Refund]:
    """Get a refund by refund number"""
    return db.query(Refund).filter(Refund.refund_number == refund_number).first()


def get_patient_refunds(db: Session, patient_id: int, skip: int = 0, limit: int = 100) -> List[Refund]:
    """Get all refunds for a patient"""
    return db.query(Refund).filter(
        Refund.patient_id == patient_id
    ).order_by(Refund.created_at.desc()).offset(skip).limit(limit).all()


def get_invoice_refunds(db: Session, invoice_id: int) -> List[Refund]:
    """Get all refunds for an invoice"""
    return db.query(Refund).filter(Refund.invoice_id == invoice_id).all()


def approve_refund(db: Session, refund_id: int, user_id: int, notes: Optional[str] = None) -> Optional[Refund]:
    """Approve a refund request"""
    db_refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not db_refund:
        return None
    
    if db_refund.status != RefundStatus.PENDING:
        raise ValueError("Only pending refunds can be approved")
    
    db_refund.status = RefundStatus.APPROVED
    db_refund.approved_by_id = user_id
    db_refund.approval_date = datetime.now()
    if notes:
        db_refund.notes = (db_refund.notes or "") + f"\nApproval: {notes}"
    
    db.commit()
    db.refresh(db_refund)
    return db_refund


def reject_refund(db: Session, refund_id: int, user_id: int, rejection_reason: str, notes: Optional[str] = None) -> Optional[Refund]:
    """Reject a refund request"""
    db_refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not db_refund:
        return None
    
    if db_refund.status != RefundStatus.PENDING:
        raise ValueError("Only pending refunds can be rejected")
    
    db_refund.status = RefundStatus.REJECTED
    db_refund.approved_by_id = user_id
    db_refund.approval_date = datetime.now()
    db_refund.rejection_reason = rejection_reason
    if notes:
        db_refund.notes = (db_refund.notes or "") + f"\nRejection: {notes}"
    
    db.commit()
    db.refresh(db_refund)
    return db_refund


def process_refund(db: Session, refund_id: int, user_id: int, refund_method: PaymentMethod, transaction_reference: Optional[str] = None, notes: Optional[str] = None) -> Optional[Refund]:
    """Process a refund - update payment and invoice status"""
    db_refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not db_refund:
        return None
    
    if db_refund.status != RefundStatus.APPROVED:
        raise ValueError("Only approved refunds can be processed")
    
    # Get the payment
    payment = db.query(Payment).filter(Payment.id == db_refund.payment_id).first()
    invoice = db.query(Invoice).filter(Invoice.id == db_refund.invoice_id).first()
    
    # Update payment status
    payment.status = PaymentStatus.REFUNDED
    
    # Update invoice - reduce paid amount and update balance
    invoice.paid_amount -= db_refund.amount
    invoice.balance = invoice.total_amount - invoice.paid_amount
    
    # Update invoice status based on new balance
    if invoice.balance == invoice.total_amount:
        invoice.status = InvoiceStatus.PENDING
        invoice.paid_date = None
    elif invoice.balance > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    
    # Update refund
    db_refund.status = RefundStatus.PROCESSED
    db_refund.processed_by_id = user_id
    db_refund.processed_date = datetime.now()
    db_refund.refund_method = refund_method
    db_refund.transaction_reference = transaction_reference
    if notes:
        db_refund.notes = (db_refund.notes or "") + f"\nProcessed: {notes}"
    
    db.commit()
    db.refresh(db_refund)
    return db_refund


def cancel_refund(db: Session, refund_id: int) -> Optional[Refund]:
    """Cancel a pending refund request"""
    db_refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not db_refund:
        return None
    
    if db_refund.status not in [RefundStatus.PENDING, RefundStatus.APPROVED]:
        raise ValueError("Only pending or approved refunds can be cancelled")
    
    db_refund.is_active = False
    db.commit()
    db.refresh(db_refund)
    return db_refund

