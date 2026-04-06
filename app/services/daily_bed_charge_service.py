"""
Daily Bed Charge Automation Service

This module handles automatic generation of daily bed and ward charges for IPD patients.
Can be run as a scheduled task (cron job) daily at midnight.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta

from app.models.billing_models import Invoice, Charge, ChargeType
from app.models.ipd_models import Admission, AdmissionStatus
from app.crud import billing_crud, ipd_crud
from app.schemas.billing_schemas import ChargeCreate


def generate_daily_bed_charges_for_admission(
    db: Session,
    admission: Admission,
    charge_date: date,
    created_by_id: int = 1  # System user ID
) -> List[Charge]:
    """
    Generate daily bed and ward charges for a specific admission on a specific date.
    
    Args:
        db: Database session
        admission: Admission record
        charge_date: Date for which to generate charges
        created_by_id: User ID who is creating the charges (default: 1 for system)
    
    Returns:
        List of created charges (ward charge and bed charge if applicable)
    """
    charges = []
    
    # Skip if admission is not active
    if admission.status != AdmissionStatus.ADMITTED:
        return charges
    
    # Skip if charge date is before admission date
    admission_date_only = admission.admission_date.date()
    if charge_date < admission_date_only:
        return charges
    
    # Skip if admission is discharged and charge date is after discharge date
    if admission.discharge_date:
        discharge_date_only = admission.discharge_date.date()
        if charge_date > discharge_date_only:
            return charges
    
    # Get or create invoice for the admission
    from app.services.ipd_billing_service import get_or_create_invoice_for_admission
    invoice = get_or_create_invoice_for_admission(db, admission, created_by_id)
    
    # Check if charge already exists for this date
    date_str = charge_date.strftime('%Y-%m-%d')
    
    # Ward charges
    ward_charge_per_day = Decimal('0.00')
    if admission.ward and admission.ward.charge_per_day:
        ward_charge_per_day = Decimal(str(admission.ward.charge_per_day))
    
    if ward_charge_per_day > 0:
        ward_description = f"Admission Fee : {admission.ward.name} ({date_str})"
        
        # Check if ward charge already exists for this date
        existing_ward_charge = db.query(Charge).filter(
            Charge.invoice_id == invoice.id,
            Charge.description == ward_description,
            Charge.charge_type == ChargeType.ADMISSION
        ).first()
        
        if not existing_ward_charge:
            ward_charge_data = ChargeCreate(
                charge_type=ChargeType.ADMISSION,
                description=ward_description,
                quantity=1,
                unit_price=ward_charge_per_day,
                discount=Decimal('0.00'),
                tax_rate=Decimal('0.00'),
                encounter_id=admission.encounter_id,
            )
            ward_charge = billing_crud.add_charge_to_invoice(db, invoice.id, ward_charge_data)
            charges.append(ward_charge)
    
    # Bed charges - COMMENTED OUT: Patients should not be charged for bed charges
    # bed_charge_per_day = Decimal('0.00')
    # if admission.bed and admission.bed.charge_per_day:
    #     bed_charge_per_day = Decimal(str(admission.bed.charge_per_day))
    
    # if bed_charge_per_day > 0:
    #     bed_description = f"Bed Charges: {admission.bed.bed_number} ({date_str})"
    #     
    #     # Check if bed charge already exists for this date
    #     existing_bed_charge = db.query(Charge).filter(
    #         Charge.invoice_id == invoice.id,
    #         Charge.description == bed_description,
    #         Charge.charge_type == ChargeType.ADMISSION
    #     ).first()
    #     
    #     if not existing_bed_charge:
    #         bed_charge_data = ChargeCreate(
    #             charge_type=ChargeType.ADMISSION,
    #             description=bed_description,
    #             quantity=1,
    #             unit_price=bed_charge_per_day,
    #             discount=Decimal('0.00'),
    #             tax_rate=Decimal('0.00'),
    #             encounter_id=admission.encounter_id,
    #         )
    #         bed_charge = billing_crud.add_charge_to_invoice(db, invoice.id, bed_charge_data)
    #         charges.append(bed_charge)
    
    return charges


def generate_daily_bed_charges_for_all_admissions(
    db: Session,
    charge_date: Optional[date] = None,
    created_by_id: int = 1
) -> List[Charge]:
    """
    Generate daily bed and ward charges for all active admissions on a specific date.
    
    This function should be called daily (e.g., via cron job) at midnight to generate
    charges for the previous day.
    
    Args:
        db: Database session
        charge_date: Date for which to generate charges (defaults to today)
        created_by_id: User ID who is creating the charges (default: 1 for system)
    
    Returns:
        List of all created charges
    """
    if charge_date is None:
        charge_date = date.today()
    
    # Get all active admissions
    active_admissions = db.query(Admission).options(
        # Eager load ward and bed relationships
    ).filter(
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).all()
    
    all_charges = []
    
    for admission in active_admissions:
        try:
            charges = generate_daily_bed_charges_for_admission(
                db, admission, charge_date, created_by_id
            )
            all_charges.extend(charges)
        except Exception as e:
            # Log error but continue with other admissions
            print(f"Error generating charges for admission {admission.id} on {charge_date}: {e}")
            continue
    
    return all_charges


def generate_charges_for_date_range(
    db: Session,
    start_date: date,
    end_date: date,
    created_by_id: int = 1
) -> List[Charge]:
    """
    Generate charges for a range of dates (useful for backfilling or catching up).
    
    Args:
        db: Database session
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        created_by_id: User ID who is creating the charges
    
    Returns:
        List of all created charges
    """
    all_charges = []
    current_date = start_date
    
    while current_date <= end_date:
        charges = generate_daily_bed_charges_for_all_admissions(
            db, current_date, created_by_id
        )
        all_charges.extend(charges)
        current_date += timedelta(days=1)
    
    return all_charges

