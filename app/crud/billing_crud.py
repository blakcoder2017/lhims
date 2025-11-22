from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.billing_models import Invoice, Charge, Payment, InvoiceStatus, PaymentStatus, PaymentMethod
from app.models.user_models import User
from app.schemas.billing_schemas import (
    InvoiceCreate, InvoiceUpdate, InvoiceRead,
    ChargeCreate, ChargeUpdate,
    PaymentCreate, PaymentUpdate
)


def generate_invoice_number(db: Session) -> str:
    """Generate a unique invoice number"""
    prefix = "INV"
    date_str = datetime.now().strftime("%Y%m%d")
    
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
    
    return f"{prefix}-{date_str}-{sequence:04d}"


def generate_payment_number(db: Session) -> str:
    """Generate a unique payment number"""
    prefix = "PAY"
    date_str = datetime.now().strftime("%Y%m%d")
    
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
    
    return f"{prefix}-{date_str}-{sequence:04d}"


def generate_receipt_number(db: Session) -> str:
    """Generate a unique receipt number"""
    prefix = "RCP"
    date_str = datetime.now().strftime("%Y%m%d")
    
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
    
    return f"{prefix}-{date_str}-{sequence:04d}"


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
        prescription_id=charge.prescription_id
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
    db_invoice.balance = db_invoice.total_amount - db_invoice.paid_amount
    
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
    if new_balance <= Decimal('0.00'):
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

