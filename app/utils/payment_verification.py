"""
Payment Verification Utilities

This module provides utilities to check if cash patients have paid for services
before they can proceed with pay-as-you-go services.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, Tuple
from decimal import Decimal
from datetime import datetime

from app.models.patient_models import Patient, PaymentMechanism
from app.models.billing_models import Invoice, Charge, Payment, InvoiceStatus, PaymentStatus, ChargeType
from app.models.encounter_models import Encounter
from app.crud import ipd_crud


def is_cash_patient(db: Session, patient_id: int) -> bool:
    """Check if patient is a cash-only patient."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return False
    return patient.payment_mechanism == PaymentMechanism.CASH


def is_patient_admitted(db: Session, patient_id: int) -> bool:
    """Check if patient is currently admitted (IPD)."""
    current_admission = ipd_crud.get_current_admission(db, patient_id)
    return current_admission is not None


def requires_payment_before_service(
    db: Session,
    patient_id: int,
    service_type: ChargeType
) -> bool:
    """
    Determine if payment is required before a service can be performed.
    
    Rules:
    - Cash OPD patients: Pay-as-you-go (payment required for all services)
    - Cash IPD patients: 
      - Admission/bed fees: Paid at discharge
      - Consumables (pharmacy): Pay-as-you-go
      - Other services: Can be deferred to discharge
    - Insurance patients: No immediate payment required
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return False
    
    # Only cash patients require payment
    if patient.payment_mechanism != PaymentMechanism.CASH:
        return False
    
    is_admitted = is_patient_admitted(db, patient_id)
    
    # For admitted patients:
    if is_admitted:
        # Admission and bed fees are paid at discharge
        if service_type in [ChargeType.ADMISSION, ChargeType.WARD_STAY, ChargeType.BED_STAY]:
            return False
        # Consumables and diagnostics are pay-as-you-go even for IPD cash patients
        if service_type in [ChargeType.PHARMACY, ChargeType.LAB_TEST, ChargeType.RADIOLOGY]:
            return True
        # Other services can be deferred to discharge for now
        return False
    
    # For OPD cash patients: all services are pay-as-you-go
    return True


def has_paid_for_service(
    db: Session,
    patient_id: int,
    service_type: ChargeType,
    encounter_id: Optional[int] = None,
    lab_order_id: Optional[int] = None,
    radiology_order_id: Optional[int] = None,
    prescription_id: Optional[int] = None
) -> Tuple[bool, Optional[Charge], Optional[Invoice]]:
    """
    Check if patient has paid for a specific service.
    
    Returns:
        Tuple of (has_paid, charge, invoice)
        - has_paid: True if payment is complete
        - charge: The charge object if found
        - invoice: The invoice object if found
    """
    # Build query to find charge
    charge_query = db.query(Charge).join(Invoice).filter(
        Invoice.patient_id == patient_id,
        Charge.charge_type == service_type,
        Invoice.is_active == True,
        Charge.invoice_id == Invoice.id
    )
    
    # Add specific filters based on service type
    if encounter_id:
        charge_query = charge_query.filter(Charge.encounter_id == encounter_id)
    if lab_order_id:
        charge_query = charge_query.filter(Charge.lab_order_id == lab_order_id)
    if radiology_order_id:
        charge_query = charge_query.filter(Charge.radiology_order_id == radiology_order_id)
    if prescription_id:
        charge_query = charge_query.filter(Charge.prescription_id == prescription_id)
    
    charge = charge_query.first()
    
    if not charge:
        return (False, None, None)
    
    invoice = charge.invoice
    
    # Check if invoice is fully paid
    if invoice.status == InvoiceStatus.PAID:
        return (True, charge, invoice)
    
    # Check if there are completed payments that cover the charge amount
    completed_payments = db.query(Payment).filter(
        Payment.invoice_id == invoice.id,
        Payment.status == PaymentStatus.COMPLETED,
        Payment.is_active == True
    ).all()
    
    total_paid = sum(payment.amount for payment in completed_payments)
    
    # Check if the specific charge is covered by payments
    # For simplicity, we check if invoice is at least partially paid
    # In a more complex system, we'd track which charges are paid
    if total_paid >= charge.total_amount:
        return (True, charge, invoice)
    
    return (False, charge, invoice)


def get_or_create_service_charge(
    db: Session,
    patient_id: int,
    service_type: ChargeType,
    description: str,
    amount: Decimal,
    encounter_id: Optional[int] = None,
    lab_order_id: Optional[int] = None,
    radiology_order_id: Optional[int] = None,
    prescription_id: Optional[int] = None,
    created_by_id: int = 1
) -> Tuple[Charge, Invoice]:
    """
    Get or create a charge for a service.
    Creates invoice if needed.
    
    Returns:
        Tuple of (charge, invoice)
    """
    from app.crud import billing_crud
    from app.schemas.billing_schemas import ChargeCreate, InvoiceCreate
    
    # Check if charge already exists
    charge_query = db.query(Charge).join(Invoice).filter(
        Invoice.patient_id == patient_id,
        Charge.charge_type == service_type,
        Invoice.is_active == True
    )
    
    if encounter_id:
        charge_query = charge_query.filter(Charge.encounter_id == encounter_id)
    if lab_order_id:
        charge_query = charge_query.filter(Charge.lab_order_id == lab_order_id)
    if radiology_order_id:
        charge_query = charge_query.filter(Charge.radiology_order_id == radiology_order_id)
    if prescription_id:
        charge_query = charge_query.filter(Charge.prescription_id == prescription_id)
    
    existing_charge = charge_query.first()
    
    if existing_charge:
        return (existing_charge, existing_charge.invoice)
    
    # Get or create invoice
    invoice = None
    if encounter_id:
        # Try to find existing invoice for this encounter
        invoice = db.query(Invoice).filter(
            Invoice.patient_id == patient_id,
            Invoice.encounter_id == encounter_id,
            Invoice.is_active == True
        ).first()
    
    if not invoice:
        # Create new invoice
        invoice_data = InvoiceCreate(
            patient_id=patient_id,
            encounter_id=encounter_id,
            payment_mechanism="cash"  # Will be set based on patient
        )
        invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    # Create charge
    charge_data = ChargeCreate(
        charge_type=service_type,
        description=description,
        quantity=1,
        unit_price=amount,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=encounter_id,
        lab_order_id=lab_order_id,
        radiology_order_id=radiology_order_id,
        prescription_id=prescription_id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    
    return (charge, invoice)


def check_payment_required_and_paid(
    db: Session,
    patient_id: int,
    service_type: ChargeType,
    encounter_id: Optional[int] = None,
    lab_order_id: Optional[int] = None,
    radiology_order_id: Optional[int] = None,
    prescription_id: Optional[int] = None
) -> Tuple[bool, bool, Optional[Charge], Optional[Invoice]]:
    """
    Check if payment is required and if it has been paid.
    
    Returns:
        Tuple of (payment_required, payment_paid, charge, invoice)
    """
    payment_required = requires_payment_before_service(db, patient_id, service_type)
    
    if not payment_required:
        return (False, True, None, None)  # No payment required, consider it "paid"
    
    has_paid, charge, invoice = has_paid_for_service(
        db, patient_id, service_type,
        encounter_id=encounter_id,
        lab_order_id=lab_order_id,
        radiology_order_id=radiology_order_id,
        prescription_id=prescription_id
    )
    
    return (payment_required, has_paid, charge, invoice)

