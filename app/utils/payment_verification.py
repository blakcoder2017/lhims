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
from app.models.billing_models import Invoice, Charge, Payment, InvoiceStatus, PaymentStatus, ChargeType, ChargePayment
from app.models.encounter_models import Encounter
from app.models.triage_models import TriageVitals
from app.crud import ipd_crud, appointment_crud
from datetime import date, timedelta


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
    service_type: ChargeType,
    is_emergency: bool = False
) -> bool:
    """
    Determine if payment is required before a service can be performed.
    
    Rules:
    - Cash OPD patients: Pay-as-you-go (payment required for all services)
    - Cash IPD patients: 
      - Admission/bed fees: Paid at discharge ONLY
      - ALL other services: Pay-as-you-go (labs, imaging, procedures, drugs, consumables)
    - Insurance patients: No immediate payment required
    - Emergency patients: Payment after stabilization (bypass for consultation)
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return False
    
    # Emergency patients: Skip consultation fee payment (stabilize first)
    if is_emergency and service_type == ChargeType.CONSULTATION:
        return False
    
    # Only cash patients require payment
    if patient.payment_mechanism != PaymentMechanism.CASH:
        return False
    
    is_admitted = is_patient_admitted(db, patient_id)
    
    # For admitted patients (IPD cash patients):
    if is_admitted:
        # ONLY admission/bed charges are paid at discharge
        # ALL other services (labs, imaging, procedures, pharmacy, etc.) are pay-as-you-go
        if service_type == ChargeType.ADMISSION:
            return False  # Admission charges paid at discharge
        # Everything else requires immediate payment (pay-as-you-go)
        return True
    
    # For OPD cash patients: all services are pay-as-you-go
    return True


def has_paid_for_service(
    db: Session,
    patient_id: int,
    service_type: ChargeType,
    encounter_id: Optional[int] = None,
    lab_order_id: Optional[int] = None,
    radiology_order_id: Optional[int] = None,
    prescription_id: Optional[int] = None,
    procedure_id: Optional[int] = None,
    check_today_only: bool = False
) -> Tuple[bool, Optional[Charge], Optional[Invoice]]:
    """
    Check if patient has paid for a specific service.
    Now checks charge-level payments (ChargePayment) for accurate payment status.
    
    Args:
        check_today_only: If True, only check for charges created today (for new visits)
    
    Returns:
        Tuple of (has_paid, charge, invoice)
        - has_paid: True if payment is complete
        - charge: The charge object if found
        - invoice: The invoice object if found
    """
    from datetime import date
    
    # Build query to find charge
    charge_query = db.query(Charge).join(Invoice).filter(
        Invoice.patient_id == patient_id,
        Charge.charge_type == service_type,
        Invoice.is_active == True,
        Charge.invoice_id == Invoice.id
    )
    
    # For consultation charges without encounter_id (new visit), check for TODAY's charges only
    if check_today_only or (service_type == ChargeType.CONSULTATION and encounter_id is None):
        from sqlalchemy import func
        today = date.today()
        charge_query = charge_query.filter(
            func.date(Charge.created_at) == today
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
    if procedure_id:
        # Procedures are identified by description pattern "Procedure #{procedure_id}:"
        charge_query = charge_query.filter(Charge.description.like(f"Procedure #{procedure_id}%"))
    
    charge = charge_query.first()
    
    if not charge:
        return (False, None, None)
    
    invoice = charge.invoice
    
    # Method 1: Check charge-level payments (most accurate for individual charge payment)
    charge_payments = db.query(ChargePayment).join(Payment).filter(
        ChargePayment.charge_id == charge.id,
        ChargePayment.is_active == True,
        Payment.status == PaymentStatus.COMPLETED,
        Payment.is_active == True
    ).all()
    
    charge_paid_amount = sum(cp.amount for cp in charge_payments)
    
    # If charge is fully paid via charge-level payments, return True
    if charge_paid_amount >= charge.total_amount:
        return (True, charge, invoice)
    
    # Method 2: Check invoice balance directly (fallback for payments not allocated to charges)
    if invoice.balance <= Decimal('0'):
        return (True, charge, invoice)
    
    # Method 3: Check if invoice is fully paid (status)
    if invoice.status == InvoiceStatus.PAID:
        return (True, charge, invoice)
    
    # Method 4: Check if there are completed payments that cover the charge amount
    # (for backward compatibility with payments not yet allocated to charges)
    completed_payments = db.query(Payment).filter(
        Payment.invoice_id == invoice.id,
        Payment.status == PaymentStatus.COMPLETED,
        Payment.is_active == True
    ).all()
    
    total_paid = sum(payment.amount for payment in completed_payments)
    
    # If no charge-level payments exist, use invoice-level payment check
    if not charge_payments and total_paid >= charge.total_amount:
        return (True, charge, invoice)
    
    # Also check if invoice total is covered
    if total_paid >= invoice.total_amount:
        return (True, charge, invoice)
    
    return (False, charge, invoice)


def get_or_create_service_charge(
    db: Session,
    patient_id: int,
    service_type: ChargeType,
    description: str,
    amount: Decimal,
    encounter_id: Optional[int] = None,
    opd_visit_id: Optional[int] = None,
    admission_id: Optional[int] = None,
    lab_order_id: Optional[int] = None,
    radiology_order_id: Optional[int] = None,
    prescription_id: Optional[int] = None,
    created_by_id: int = 1
) -> Tuple[Charge, Invoice]:
    """
    Get or create a charge for a service.
    Creates invoice if needed.
    
    IMPORTANT: When opd_visit_id or admission_id is provided, this function will
    ALWAYS use an invoice linked to that visit/admission. It will never return
    an invoice without the proper link.
    
    Returns:
        Tuple of (charge, invoice)
    """
    from app.crud import billing_crud
    from app.schemas.billing_schemas import ChargeCreate, InvoiceCreate
    from app.models.billing_models import Invoice, Charge
    
    # Priority 1: If opd_visit_id is provided, ALWAYS use invoice with that opd_visit_id
    if opd_visit_id:
        # First, try to find existing invoice linked to this OPD visit
        invoice = db.query(Invoice).filter(
            Invoice.patient_id == patient_id,
            Invoice.opd_visit_id == opd_visit_id,
            Invoice.is_active == True
        ).first()
        
        if invoice:
            # Check if charge already exists for this service type on this invoice
            existing_charge = db.query(Charge).filter(
                Charge.invoice_id == invoice.id,
                Charge.charge_type == service_type
            )
            
            # Add service-specific filters
            if encounter_id:
                existing_charge = existing_charge.filter(Charge.encounter_id == encounter_id)
            if lab_order_id:
                existing_charge = existing_charge.filter(Charge.lab_order_id == lab_order_id)
            if radiology_order_id:
                existing_charge = existing_charge.filter(Charge.radiology_order_id == radiology_order_id)
            if prescription_id:
                existing_charge = existing_charge.filter(Charge.prescription_id == prescription_id)
            
            charge = existing_charge.first()
            if charge:
                return (charge, invoice)
        else:
            # No invoice exists for this OPD visit - create one
            invoice_data = InvoiceCreate(
                patient_id=patient_id,
                encounter_id=encounter_id,
                opd_visit_id=opd_visit_id,
                admission_id=None,  # Explicitly None for OPD
                payment_mechanism="cash"
            )
            invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    # Priority 2: If admission_id is provided, ALWAYS use invoice with that admission_id
    elif admission_id:
        # First, try to find existing invoice linked to this IPD admission
        invoice = db.query(Invoice).filter(
            Invoice.patient_id == patient_id,
            Invoice.admission_id == admission_id,
            Invoice.is_active == True
        ).first()
        
        if invoice:
            # Check if charge already exists
            existing_charge = db.query(Charge).filter(
                Charge.invoice_id == invoice.id,
                Charge.charge_type == service_type
            )
            
            if encounter_id:
                existing_charge = existing_charge.filter(Charge.encounter_id == encounter_id)
            if lab_order_id:
                existing_charge = existing_charge.filter(Charge.lab_order_id == lab_order_id)
            if radiology_order_id:
                existing_charge = existing_charge.filter(Charge.radiology_order_id == radiology_order_id)
            if prescription_id:
                existing_charge = existing_charge.filter(Charge.prescription_id == prescription_id)
            
            charge = existing_charge.first()
            if charge:
                return (charge, invoice)
        else:
            # No invoice exists for this admission - create one
            invoice_data = InvoiceCreate(
                patient_id=patient_id,
                encounter_id=encounter_id,
                opd_visit_id=None,  # Explicitly None for IPD
                admission_id=admission_id,
                payment_mechanism="cash"
            )
            invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    # Priority 3: If encounter_id is provided, use invoice for that encounter
    elif encounter_id:
        # Try to find existing invoice for this encounter
        invoice = db.query(Invoice).filter(
            Invoice.patient_id == patient_id,
            Invoice.encounter_id == encounter_id,
            Invoice.is_active == True
        ).first()
        
        if invoice:
            # Check if charge already exists
            existing_charge = db.query(Charge).filter(
                Charge.invoice_id == invoice.id,
                Charge.charge_type == service_type
            )
            
            if lab_order_id:
                existing_charge = existing_charge.filter(Charge.lab_order_id == lab_order_id)
            if radiology_order_id:
                existing_charge = existing_charge.filter(Charge.radiology_order_id == radiology_order_id)
            if prescription_id:
                existing_charge = existing_charge.filter(Charge.prescription_id == prescription_id)
            
            charge = existing_charge.first()
            if charge:
                return (charge, invoice)
        else:
            # No invoice exists for this encounter - create one
            invoice_data = InvoiceCreate(
                patient_id=patient_id,
                encounter_id=encounter_id,
                opd_visit_id=None,
                admission_id=None,
                payment_mechanism="cash"
            )
            invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    # Priority 4: No specific link provided - create standalone invoice
    else:
        # Check if charge already exists (without specific links)
        charge_query = db.query(Charge).join(Invoice).filter(
            Invoice.patient_id == patient_id,
            Charge.charge_type == service_type,
            Invoice.is_active == True,
            Invoice.opd_visit_id.is_(None),
            Invoice.admission_id.is_(None),
            Invoice.encounter_id.is_(None)
        )
        
        if lab_order_id:
            charge_query = charge_query.filter(Charge.lab_order_id == lab_order_id)
        if radiology_order_id:
            charge_query = charge_query.filter(Charge.radiology_order_id == radiology_order_id)
        if prescription_id:
            charge_query = charge_query.filter(Charge.prescription_id == prescription_id)
        
        existing_charge = charge_query.first()
        if existing_charge:
            return (existing_charge, existing_charge.invoice)
        
        # Create new standalone invoice
        invoice_data = InvoiceCreate(
            patient_id=patient_id,
            encounter_id=None,
            opd_visit_id=None,
            admission_id=None,
            payment_mechanism="cash"
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
    # Note: opd_visit_id and admission_id are set on the charge via add_charge_to_invoice
    # if they're linked through the invoice
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    
    return (charge, invoice)


def check_payment_required_and_paid(
    db: Session,
    patient_id: int,
    service_type: ChargeType,
    encounter_id: Optional[int] = None,
    lab_order_id: Optional[int] = None,
    radiology_order_id: Optional[int] = None,
    prescription_id: Optional[int] = None,
    procedure_id: Optional[int] = None
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
        prescription_id=prescription_id,
        procedure_id=procedure_id
    )
    
    return (payment_required, has_paid, charge, invoice)


def verify_encounter_workflow(
    db: Session,
    patient_id: int,
    check_vitals: bool = True,
    check_checkin: bool = True,
    check_payment: bool = True
) -> Tuple[bool, Optional[str], Optional[object], Optional[object], Optional[object]]:
    """
    Verify that a patient has completed the required workflow steps before creating an encounter.
    
    Workflow steps:
    1. Vitals must be recorded (today or recently)
    2. Patient must be checked in (appointment with CHECKED_IN or IN_PROGRESS status)
    3. Payment must be made (for cash patients only)
    
    Args:
        db: Database session
        patient_id: Patient ID to check
        check_vitals: Whether to check if vitals have been recorded
        check_checkin: Whether to check if patient has been checked in
        check_payment: Whether to check if payment has been made (for cash patients)
    
    Returns:
        Tuple of (workflow_complete, missing_step, vitals_record, appointment_record, payment_info)
        - workflow_complete: True if all required steps are complete
        - missing_step: Description of missing step if incomplete (e.g., "vitals", "checkin", "payment")
        - vitals_record: Latest vitals record if found, None otherwise
        - appointment_record: Checked-in appointment if found, None otherwise
        - payment_info: Tuple of (has_paid, charge, invoice) for payment check
    """
    from sqlalchemy import func
    
    vitals_record = None
    appointment_record = None
    payment_info = (True, None, None)  # Default: payment not required
    
    # Step 1: Check if vitals have been recorded (today or within last 24 hours)
    if check_vitals:
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        vitals_record = db.query(TriageVitals).filter(
            TriageVitals.patient_id == patient_id,
            func.date(TriageVitals.recorded_at) >= yesterday
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        if not vitals_record:
            return (False, "vitals", None, None, None)
    
    # Step 2: Check if patient has been checked in
    if check_checkin:
        appointment_record = appointment_crud.get_recent_checked_in_appointment(db, patient_id, within_hours=24)
        
        if not appointment_record:
            return (False, "checkin", vitals_record, None, None)
    
    # Step 3: Check payment (for cash patients only)
    if check_payment:
        if is_cash_patient(db, patient_id):
            payment_required = requires_payment_before_service(db, patient_id, ChargeType.CONSULTATION)
            
            if payment_required:
                # Look for consultation charges (created today or recently within last 24 hours)
                yesterday = datetime.now() - timedelta(hours=24)
                
                recent_charges = db.query(Charge).join(Invoice).filter(
                    Invoice.patient_id == patient_id,
                    Charge.charge_type == ChargeType.CONSULTATION,
                    Charge.encounter_id.is_(None),
                    Invoice.is_active == True,
                    Charge.created_at >= yesterday
                ).order_by(Charge.created_at.desc()).limit(10).all()
                
                recent_paid_charge = None
                has_paid = False
                
                for ch in recent_charges:
                    invoice = ch.invoice
                    
                    # Method 1: Check invoice balance directly (most reliable)
                    if invoice.balance <= Decimal('0'):
                        recent_paid_charge = ch
                        has_paid = True
                        break
                    
                    # Method 2: Check invoice status
                    if invoice.status == InvoiceStatus.PAID:
                        recent_paid_charge = ch
                        has_paid = True
                        break
                    
                    # Method 3: Check if payments cover the charge amount
                    all_payments = db.query(Payment).filter(
                        Payment.invoice_id == invoice.id,
                        Payment.status == PaymentStatus.COMPLETED,
                        Payment.is_active == True
                    ).all()
                    
                    if all_payments:
                        total_paid_all = sum(p.amount for p in all_payments)
                        
                        # Check if total paid covers the charge amount
                        if total_paid_all >= ch.total_amount:
                            recent_paid_charge = ch
                            has_paid = True
                            break
                        
                        # Also check if invoice balance is covered
                        if total_paid_all >= invoice.total_amount:
                            recent_paid_charge = ch
                            has_paid = True
                            break
                
                if not has_paid:
                    # Fallback: check for today's charges using the standard method
                    has_paid, charge, invoice = has_paid_for_service(
                        db, patient_id, ChargeType.CONSULTATION,
                        encounter_id=None,
                        check_today_only=True
                    )
                    payment_info = (has_paid, charge, invoice)
                else:
                    payment_info = (has_paid, recent_paid_charge, recent_paid_charge.invoice)
                
                if not payment_info[0]:  # has_paid is False
                    return (False, "payment", vitals_record, appointment_record, payment_info)
            else:
                payment_info = (True, None, None)
        else:
            # For insurance patients, payment is not required
            payment_info = (True, None, None)
    
    # All checks passed
    return (True, None, vitals_record, appointment_record, payment_info)

