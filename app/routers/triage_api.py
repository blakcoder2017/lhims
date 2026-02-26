# In lhims/app/routers/triage_api.py

from fastapi import APIRouter, Depends, status, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.core.templates import templates
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import triage_crud, service_pricing_crud
from app.schemas.triage_schemas import TriageVitalsCreate 
from app.utils.payment_verification import (
    requires_payment_before_service,
    has_paid_for_service,
    get_or_create_service_charge,
    check_payment_required_and_paid
)
from app.models.billing_models import ChargeType
from app.models.triage_models import TriageVitals
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.services import create_charge_for_consultation


router = APIRouter(
    prefix="/api/v1/triage",
    tags=["Triage"]
)

@router.post("/{patient_id}/vitals", status_code=status.HTTP_302_FOUND, name="record_vitals")
def record_vitals_form(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    # Allow Front Office and Nurses to record vitals
    current_user = Depends(role_required(["Front Office", "Nurse", "Doctor", "Clinician", "Admin"])),
    create_encounter: Optional[str] = Form(None),  # If "yes", create encounter after vitals
    from_admission: Optional[str] = Form(None),  # If set, redirect back to IPD admission page after recording
    queue_entry_id: Optional[str] = Form(None),  # OPDQueue id when from triage queue - used for auto check-in
    department: Optional[str] = Form("General Medicine"),  # For auto check-in when creating new queue
    chief_complaint: Optional[str] = Form(None),  # For auto check-in
    
    # Vital signs (temperature optional)
    temperature: Optional[str] = Form(None),
    
    # Blood pressure - can use separate fields or legacy string
    systolic_bp: Optional[str] = Form(None),
    diastolic_bp: Optional[str] = Form(None),
    blood_pressure: Optional[str] = Form(None),  # Legacy field
    
    # Optional vital signs
    pulse_rate: Optional[str] = Form(None),
    respiratory_rate: Optional[str] = Form(None),
    oxygen_saturation: Optional[str] = Form(None),
    weight: Optional[str] = Form(None),
    height: Optional[str] = Form(None),
    pain_scale: Optional[str] = Form(None),
    
    # Triage Level Assignment
    triage_level: Optional[str] = Form(None),  # P1, P2, P3 or Red, Yellow, Green
    triage_category: Optional[str] = Form(None),  # Critical, Urgent, Routine
    auto_calculate_triage: Optional[str] = Form(None),  # "yes" to auto-calculate from vitals
    
    # Nurse Notes
    notes: Optional[str] = Form(None),  # Nurse observations
):
    """
    Handles HTML form submission for recording comprehensive patient vital signs (Triage) and saves to DB.
    Supports all vital signs: temperature, BP, pulse, respiratory rate, SpO2, weight, height, BMI (auto-calculated), pain scale.
    
    For cash patients: Checks if payment has been made before allowing vitals recording.
    For emergency patients: Payment is bypassed (stabilize first, payment after).
    """
    from app.models.patient_models import Patient
    
    # Check if this is an emergency case
    is_emergency = request.query_params.get('emergency') == 'true' or request.query_params.get('emergency') == '1'
    
    # Check payment requirement for cash patients
    # Consultation fee now covers both vitals and encounter, so check for CONSULTATION fee
    # For returning patients (new_visit), check for the MOST RECENT charge for THIS visit
    # Emergency patients bypass payment requirement
    
    payment_required = requires_payment_before_service(db, patient_id, ChargeType.CONSULTATION, is_emergency=is_emergency)
    
    # Check if this is a new visit
    new_visit_param = request.query_params.get('new_visit')
    is_new_visit = new_visit_param and new_visit_param.lower() == 'true'
    
    if payment_required:
        # Improved payment check: look for recent consultation charges
        from datetime import timedelta
        from app.models.billing_models import Charge, Invoice, Payment, PaymentStatus, InvoiceStatus
        
        # For new visits, only check the MOST RECENT charge (the one created for this visit)
        # For regular visits, check charges from last 24 hours
        if is_new_visit:
            # Get the most recent consultation charge (should be the one created for this visit)
            recent_charges = db.query(Charge).join(Invoice).filter(
                Invoice.patient_id == patient_id,
                Charge.charge_type == ChargeType.CONSULTATION,
                Charge.encounter_id.is_(None),
                Invoice.is_active == True
            ).order_by(Charge.created_at.desc()).limit(1).all()
        else:
            yesterday = datetime.now() - timedelta(hours=24)
            # Look for any consultation charges created in the last 24 hours
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
        
        # For new visits, if no paid charge found, we should have already created one in the triage page
        # For regular visits, fallback to standard check
        if not has_paid and not is_new_visit:
            has_paid, charge, invoice = has_paid_for_service(
                db, patient_id, ChargeType.CONSULTATION,
                encounter_id=None,
                check_today_only=True
            )
            if charge:
                recent_paid_charge = charge
        
        payment_paid = has_paid
        
        # IPD admission vitals recording: bypass consultation payment (monitoring only)
        if not payment_paid and from_admission and from_admission.strip():
            payment_paid = True
        
        if not payment_paid:
            # For new visits, charge should already exist (created in triage page)
            # For regular visits, create one if it doesn't exist
            if not recent_paid_charge and not is_new_visit:
                try:
                    create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None)
                except Exception as billing_error:
                    print(f"Warning: Unable to seed consultation charge for patient {patient_id}: {billing_error}")
            
            # Redirect to consultation fee payment page, preserving new_visit parameter
            new_visit_url_param = ""
            if is_new_visit and new_visit_param:
                new_visit_url_param = f"&new_visit={new_visit_param}"
            return RedirectResponse(
                url=f"/patients/{patient_id}/pay/consultation?return_to=triage{new_visit_url_param}",
                status_code=status.HTTP_302_FOUND
            )
    else:
        payment_paid = True
    
    # Helper function to convert string to int, handling empty strings
    def str_to_int(value: Optional[str]) -> Optional[int]:
        if value and value.strip():
            try:
                return int(value.strip())
            except ValueError:
                return None
        return None
    
    # Helper function to convert string to float, handling empty strings
    def str_to_float(value: Optional[str]) -> Optional[float]:
        if value and value.strip():
            try:
                return float(value.strip())
            except ValueError:
                return None
        return None
    
    # Convert all optional numeric fields from strings to appropriate types
    systolic_bp_int = str_to_int(systolic_bp)
    diastolic_bp_int = str_to_int(diastolic_bp)
    pulse_rate_int = str_to_int(pulse_rate)
    respiratory_rate_int = str_to_int(respiratory_rate)
    oxygen_saturation_int = str_to_int(oxygen_saturation)
    pain_scale_int = str_to_int(pain_scale)
    
    # Convert weight and height to Decimal if provided
    weight_float = str_to_float(weight)
    height_float = str_to_float(height)
    weight_decimal = Decimal(str(weight_float)) if weight_float is not None else None
    height_decimal = Decimal(str(height_float)) if height_float is not None else None
    
    # Parse temperature (optional)
    temperature_float = str_to_float(temperature) if isinstance(temperature, str) else temperature
    
    # Determine triage level
    final_triage_level = triage_level
    final_triage_category = triage_category
    
    # Auto-calculate triage level from vitals if requested
    if auto_calculate_triage and auto_calculate_triage.lower() == "yes":
        from app.services.triage_level_calculator import calculate_triage_level_from_vitals
        # Create temporary vitals object for calculation
        temp_vitals = TriageVitals(
            temperature=temperature_float,
            systolic_bp=systolic_bp_int,
            diastolic_bp=diastolic_bp_int,
            pulse_rate=pulse_rate_int,
            respiratory_rate=respiratory_rate_int,
            oxygen_saturation=oxygen_saturation_int,
            pain_scale=pain_scale_int
        )
        calculated_level, calculated_category = calculate_triage_level_from_vitals(temp_vitals)
        final_triage_level = calculated_level
        final_triage_category = calculated_category
    
    # 1. Create a data transfer object (DTO)
    vitals_data = TriageVitalsCreate(
        patient_id=patient_id,
        recorded_by_id=current_user.id, 
        temperature=temperature_float,
        systolic_bp=systolic_bp_int,
        diastolic_bp=diastolic_bp_int,
        blood_pressure=blood_pressure,
        pulse_rate=pulse_rate_int,
        respiratory_rate=respiratory_rate_int,
        oxygen_saturation=oxygen_saturation_int,
        weight=weight_decimal,
        height=height_decimal,
        pain_scale=pain_scale_int,
        triage_level=final_triage_level,
        triage_category=final_triage_category,
        notes=notes,
    )
    
    # 2. Save to database (BMI will be calculated automatically in CRUD)
    db_vitals = triage_crud.create_vitals(db, vitals=vitals_data)
    
    # 3. If triage level was assigned, update the triage_assigned_by and triage_assigned_at fields
    if final_triage_level:
        db_vitals.triage_assigned_by_id = current_user.id
        db_vitals.triage_assigned_at = datetime.now()
        db.commit()
        db.refresh(db_vitals)
    
    # AJAX request (e.g. from admission page modal): return JSON so page can reload instead of redirect
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if is_ajax:
        return JSONResponse(
            content={"success": True, "message": "Vitals recorded successfully."},
            status_code=status.HTTP_200_OK
        )
    
    # Redirect back to IPD admission page if user came from there (constant monitoring)
    if from_admission and from_admission.strip():
        try:
            admission_id = int(from_admission.strip())
            return RedirectResponse(
                url=f"/ipd/admissions/{admission_id}?status=vitals_recorded",
                status_code=status.HTTP_302_FOUND
            )
        except ValueError:
            pass
    
    # 3. Only doctors/admins can jump straight to encounter creation. Front desk & nurses should check-in only.
    if create_encounter and create_encounter.lower() == "yes" and current_user.role.name in ["Doctor", "Admin"]:
        return RedirectResponse(
            url=f"/patients/{patient_id}/encounters/new?from_triage=true&status=vitals_saved",
            status_code=status.HTTP_302_FOUND
        )
    
    # 4. For NEW triage: add patient to doctor's queue. For UPDATE: only vitals were saved, no queue change.
    from app.models.appointment_models import OPDQueue, QueueStatus, VisitType
    from app.schemas.appointment_schemas import QueueCreate
    from app.crud import appointment_crud
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check if patient is already in doctor's queue (has OPDQueue with checked_in_at today)
    already_in_doctor_queue = db.query(OPDQueue).filter(
        OPDQueue.patient_id == patient_id,
        OPDQueue.is_active == True,
        OPDQueue.created_at >= today_start,
        OPDQueue.checked_in_at.isnot(None),
        OPDQueue.status.in_([QueueStatus.WAITING.value, QueueStatus.IN_PROGRESS.value])
    ).first()
    
    if not already_in_doctor_queue:
        # New triage: add to doctor's queue after saving vitals
        queue_entry = None
        if queue_entry_id and queue_entry_id.strip():
            try:
                qid = int(queue_entry_id.strip())
                queue_entry = appointment_crud.get_queue_entry(db, qid)
                if queue_entry and queue_entry.patient_id != patient_id:
                    queue_entry = None
            except (ValueError, TypeError):
                pass
        
        # If no queue_entry_id provided, try to find existing OPDQueue for patient today (from triage queue)
        if not queue_entry:
            queue_entry = db.query(OPDQueue).filter(
                OPDQueue.patient_id == patient_id,
                OPDQueue.is_active == True,
                OPDQueue.created_at >= today_start,
                OPDQueue.checked_in_at.is_(None),
                OPDQueue.status.in_([QueueStatus.WAITING.value, QueueStatus.IN_PROGRESS.value])
            ).order_by(OPDQueue.created_at.desc()).first()
        
        if queue_entry:
            # Update existing OPDQueue: set checked_in_at so patient appears in doctor queue
            queue_entry.checked_in_at = datetime.now()
            queue_entry.notes = (queue_entry.notes or "") + " [Checked in after vitals]"
            db.commit()
        else:
            # No queue entry: create new one (patient came from somewhere without queue)
            dept = (department or "General Medicine").strip()
            queue_data = QueueCreate(
                patient_id=patient_id,
                department=dept,
                department_type="opd",
                visit_type=VisitType.WALK_IN,
                priority=5,
                chief_complaint=chief_complaint,
                notes="Check-in after vitals",
                assigned_clinician_id=None,
                created_by_id=current_user.id
            )
            new_entry = appointment_crud.create_queue_entry(db, queue_data)
            new_entry.checked_in_at = datetime.now()
            db.commit()
    
    # Redirect to triage queue so nurse can continue with next patient
    return RedirectResponse(
        url="/nurse/triage-queue?status=vitals_saved",
        status_code=status.HTTP_302_FOUND
    )