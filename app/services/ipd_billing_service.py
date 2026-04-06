"""
IPD Billing Automation Service

This module handles automatic billing for IPD (Inpatient Department) services:
- Admission Fee (ward charges - daily charges for ward occupancy)
- Automatic charge creation when patient is admitted
- Automatic charge calculation on discharge

Note: Bed charges have been removed - patients should not be charged for bed charges.
"""
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta

from app.models.billing_models import Invoice, Charge, InvoiceStatus, ChargeType
from app.models.ipd_models import Admission, AdmissionStatus
from app.crud import billing_crud, ipd_crud
from app.crud import service_pricing_crud
from app.schemas.billing_schemas import ChargeCreate


def calculate_ward_bed_charges(
    db: Session,
    admission: Admission,
    created_by_id: int
) -> list[Charge]:
    """
    Calculate and create charges for ward and bed occupancy.
    This is called when a patient is discharged or when generating daily charges.
    
    Returns list of created charges.
    """
    charges = []
    
    # Determine charge end date (discharge date or current date)
    end_date = admission.discharge_date if admission.discharge_date else datetime.now()
    start_date = admission.admission_date
    
    # Calculate number of days (including admission day)
    days = (end_date.date() - start_date.date()).days + 1
    
    # Get or create invoice for the admission
    invoice = get_or_create_invoice_for_admission(db, admission, created_by_id)
    
    # Ensure ward and bed are loaded (they should already be loaded from ipd_crud.get_admission)
    # Access them directly - they should be available via relationships
    def upsert_duration_charge(description_prefix: str, unit_price: Decimal) -> Optional[Charge]:
        if unit_price <= 0:
            return None
        
        existing_charge = db.query(Charge).filter(
            Charge.invoice_id == invoice.id,
            Charge.description.like(f"{description_prefix}%")
        ).first()
        
        description = f"{description_prefix} ({days} days)"
        
        if existing_charge:
            if existing_charge.quantity < days:
                additional_days = days - existing_charge.quantity
                existing_charge.quantity = days
                existing_charge.description = description
                
                additional_amount = unit_price * additional_days
                existing_charge.total_amount = unit_price * existing_charge.quantity
                
                invoice.subtotal += additional_amount
                invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.tax_amount
                invoice.balance = invoice.total_amount - invoice.paid_amount
                
                db.commit()
                db.refresh(existing_charge)
                return existing_charge
            return None
        else:
            charge_data = ChargeCreate(
                charge_type=ChargeType.OTHER,
                description=description,
                quantity=days,
                unit_price=unit_price,
                discount=Decimal('0.00'),
                tax_rate=Decimal('0.00'),
                encounter_id=admission.encounter_id,
            )
            return billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    
    # Ward charges
    ward_charge_per_day = Decimal('0.00')
    if hasattr(admission, 'ward') and admission.ward and admission.ward.charge_per_day:
        ward_charge_per_day = Decimal(str(admission.ward.charge_per_day))
    
    ward_charge = upsert_duration_charge(f"Admission Fee : {admission.ward.name}", ward_charge_per_day)
    if ward_charge:
        charges.append(ward_charge)
    
    # Bed charges - COMMENTED OUT: Patients should not be charged for bed charges
    # bed_charge_per_day = Decimal('0.00')
    # if hasattr(admission, 'bed') and admission.bed and admission.bed.charge_per_day:
    #     bed_charge_per_day = Decimal(str(admission.bed.charge_per_day))
    
    # bed_charge = upsert_duration_charge(f"Bed Charges: {admission.bed.bed_number}", bed_charge_per_day)
    # if bed_charge:
    #     charges.append(bed_charge)
    
    return charges


def get_or_create_invoice_for_admission(
    db: Session,
    admission: Admission,
    created_by_id: int
) -> Invoice:
    """
    Get existing invoice for admission or create a new one.
    Returns the invoice (existing or newly created).
    """
    # Check if invoice already exists for this admission's encounter
    invoice = None
    status_filter = [InvoiceStatus.DRAFT.value, InvoiceStatus.PENDING.value, InvoiceStatus.PARTIALLY_PAID.value]
    
    if admission.invoice_id:
        invoice = db.query(Invoice).filter(
            Invoice.id == admission.invoice_id,
            Invoice.is_active == True
        ).first()
        if invoice:
            return invoice
    
    if admission.encounter_id:
        invoice = db.query(Invoice).filter(
            Invoice.encounter_id == admission.encounter_id,
            Invoice.is_active == True,
            Invoice.status.in_(status_filter)
        ).first()
    
    if invoice:
        if not admission.invoice_id:
            admission.invoice_id = invoice.id
            db.commit()
        return invoice
    
    # Create new invoice for the admission
    from app.schemas.billing_schemas import InvoiceCreate
    from app.models.billing_models import PaymentMethod
    from app.models.patient_models import Patient, PaymentMechanism
    
    patient = db.query(Patient).filter(Patient.id == admission.patient_id).first()
    if not patient:
        raise ValueError(f"Patient {admission.patient_id} not found")
    
    # Convert PaymentMechanism to PaymentMethod (handle enum mismatch)
    payment_method = None
    if patient.payment_mechanism:
        if patient.payment_mechanism == PaymentMechanism.CASH:
            payment_method = PaymentMethod.CASH
        elif patient.payment_mechanism == PaymentMechanism.NHIS:
            payment_method = PaymentMethod.NHIS
        elif patient.payment_mechanism == PaymentMechanism.PRIVATE_INSURANCE:
            payment_method = PaymentMethod.PRIVATE_INSURANCE
        elif patient.payment_mechanism == PaymentMechanism.SELF_PAY:
            payment_method = PaymentMethod.CASH  # Default to cash for self-pay
    
    invoice_data = InvoiceCreate(
        patient_id=admission.patient_id,
        encounter_id=admission.encounter_id,
        appointment_id=None,
        payment_mechanism=payment_method,
        charges=[]
    )
    
    invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    admission.invoice_id = invoice.id
    db.commit()
    return invoice


def create_daily_ward_bed_charges(
    db: Session,
    created_by_id: int,
    date: Optional[datetime] = None
) -> list[Charge]:
    """
    Create daily charges for all active admissions.
    This can be run as a scheduled job (e.g., daily at midnight).
    
    Args:
        date: Date for which to create charges (defaults to today)
    
    Returns:
        List of created charges
    """
    if date is None:
        date = datetime.now()
    
    # Get all active admissions
    from app.models.ipd_models import Admission
    active_admissions = db.query(Admission).filter(
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).all()
    
    all_charges = []
    
    for admission in active_admissions:
        # Calculate charges for this admission up to the specified date
        charges = calculate_ward_bed_charges(db, admission, created_by_id)
        all_charges.extend(charges)
    
    return all_charges


def process_discharge_billing(
    db: Session,
    admission_id: int,
    created_by_id: int
) -> Invoice:
    """
    Process billing when a patient is discharged.
    Creates final ward/bed charges and returns the invoice.
    
    This should be called when discharging a patient.
    """
    from app.models.billing_models import Charge
    
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise ValueError(f"Admission {admission_id} not found")
    
    # Calculate final ward/bed charges
    charges = calculate_ward_bed_charges(db, admission, created_by_id)
    
    # Get or create invoice
    invoice = get_or_create_invoice_for_admission(db, admission, created_by_id)
    
    # Recalculate invoice totals from all charges to ensure accuracy
    all_charges = db.query(Charge).filter(
        Charge.invoice_id == invoice.id
    ).all()
    
    # Recalculate totals from scratch
    subtotal = sum(charge.unit_price * charge.quantity - charge.discount for charge in all_charges)
    tax_amount = sum(charge.tax_amount for charge in all_charges)
    total_amount = subtotal - invoice.discount_amount + tax_amount
    balance = total_amount - invoice.paid_amount
    
    # Update invoice totals
    invoice.subtotal = subtotal
    invoice.tax_amount = tax_amount
    invoice.total_amount = total_amount
    invoice.balance = balance
    
    # Update status if needed
    if invoice.total_amount > 0 and invoice.status == InvoiceStatus.DRAFT:
        invoice.status = InvoiceStatus.PENDING
    
    db.commit()
    db.refresh(invoice)
    
    return invoice

