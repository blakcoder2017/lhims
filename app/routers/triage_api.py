# In lhims/app/routers/triage_api.py

from fastapi import APIRouter, Depends, status, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
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
from typing import Optional
from decimal import Decimal
from app.services import create_charge_for_consultation

templates = Jinja2Templates(directory="app/templates")

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
    current_user = Depends(role_required(["Front Office", "Nurse", "Admin"])),
    create_encounter: Optional[str] = Form(None),  # If "yes", create encounter after vitals 
    
    # Required fields
    temperature: float = Form(...),
    
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
):
    """
    Handles HTML form submission for recording comprehensive patient vital signs (Triage) and saves to DB.
    Supports all vital signs: temperature, BP, pulse, respiratory rate, SpO2, weight, height, BMI (auto-calculated), pain scale.
    
    For cash patients: Checks if payment has been made before allowing vitals recording.
    """
    from app.models.patient_models import Patient
    
    # Check payment requirement for cash patients
    # Consultation fee now covers both vitals and encounter, so check for CONSULTATION fee
    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
        db, patient_id, ChargeType.CONSULTATION  # Consultation fee covers vitals + encounter
    )
    
    if payment_required and not payment_paid:
        try:
            create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None)
        except Exception as billing_error:
            print(f"Warning: Unable to seed consultation charge for patient {patient_id}: {billing_error}")
        # Redirect to consultation fee payment page
        return RedirectResponse(
            url=f"/patients/{patient_id}/pay/consultation?return_to=triage",
            status_code=status.HTTP_302_FOUND
        )
    
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
    
    # 1. Create a data transfer object (DTO)
    vitals_data = TriageVitalsCreate(
        patient_id=patient_id,
        recorded_by_id=current_user.id, 
        temperature=temperature,
        systolic_bp=systolic_bp_int,
        diastolic_bp=diastolic_bp_int,
        blood_pressure=blood_pressure,
        pulse_rate=pulse_rate_int,
        respiratory_rate=respiratory_rate_int,
        oxygen_saturation=oxygen_saturation_int,
        weight=weight_decimal,
        height=height_decimal,
        pain_scale=pain_scale_int,
    )
    
    # 2. Save to database (BMI will be calculated automatically in CRUD)
    triage_crud.create_vitals(db, vitals=vitals_data)
    
    # 3. Only doctors/admins can jump straight to encounter creation. Front desk & nurses should check-in only.
    if create_encounter and create_encounter.lower() == "yes" and current_user.role.name in ["Doctor", "Admin"]:
        return RedirectResponse(
            url=f"/patients/{patient_id}/encounters/new?from_triage=true&status=vitals_saved",
            status_code=status.HTTP_302_FOUND
        )
    
    # Default redirect back to triage page to show check-in button
    return RedirectResponse(
        url=f"/patients/{patient_id}/triage?status=vitals_saved", 
        status_code=status.HTTP_302_FOUND
    )