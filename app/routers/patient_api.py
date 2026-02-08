import logging
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date 
from app.db.database import get_db

logger = logging.getLogger(__name__)

from app.schemas.patient_schemas import PatientCreate, Patient
from app.crud import patient_crud
from app.core.deps import role_required, get_current_user

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["Patients"]
)

@router.post("/register") 
def register_patient_form(
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Admin"])), 
    
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: date = Form(..., description="Must be in YYYY-MM-DD format"),
    gender: str = Form(...),
    national_id: str = Form(None),  # Optional - not compulsory 
    phone_number: str = Form(""), 
    address: str = Form(""),
    # Financial Screening Fields (Workflow Step 3)
    payment_mechanism: str = Form(""),
    nhis_number: str = Form(""),
    insurance_provider: str = Form(""),
    insurance_provider_manual: str = Form(""),
    insurance_policy_number: str = Form(""),
    # Languages spoken
    languages_spoken: Optional[str] = Form(None),
    # Emergency case flag
    is_emergency: Optional[str] = Form(None),
):
    """
    Handles HTML form submission for patient registration with financial screening.
    Workflow Steps 1 & 3: Registration & Financial Screening
    Saves to DB and redirects to the patient's Triage page.
    """
    from app.models.patient_models import PaymentMechanism
    
    # 1. Pydantic Validation & Data Preparation
    try:
        # Parse payment mechanism
        payment_mech = None
        if payment_mechanism:
            try:
                payment_mech = PaymentMechanism(payment_mechanism)
            except ValueError:
                payment_mech = None
        
        # Handle optional national_id
        national_id_clean = national_id.strip() if national_id and national_id.strip() else None
        
        # Handle insurance provider - use manual entry if provided, otherwise use dropdown selection
        insurance_provider_final = None
        insurance_policy_final = None
        if payment_mechanism == "private_insurance":
            # Use manual entry if provided, otherwise use dropdown selection
            if insurance_provider_manual and insurance_provider_manual.strip():
                insurance_provider_final = insurance_provider_manual.strip()
            elif insurance_provider and insurance_provider.strip():
                insurance_provider_final = insurance_provider.strip()
            # Policy number is optional but recommended
            insurance_policy_final = insurance_policy_number if insurance_policy_number and insurance_policy_number.strip() else None
        
        patient_in = PatientCreate(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            gender=gender,
            national_id=national_id_clean,
            phone_number=phone_number if phone_number else None,
            address=address if address else None,
            payment_mechanism=payment_mech,
            nhis_number=nhis_number if nhis_number else None,
            insurance_provider=insurance_provider_final,
            insurance_policy_number=insurance_policy_final,
            languages_spoken=languages_spoken.strip() if languages_spoken and languages_spoken.strip() else None,
        )
    except Exception as e:
        # Redirect back to the form with a generic validation error
        return RedirectResponse(url="/patients/register?error=1", status_code=status.HTTP_302_FOUND)


    # 2. Check for duplicate ID only if national_id is provided
    if patient_in.national_id:
        db_patient = patient_crud.get_patient_by_national_id(db, national_id=patient_in.national_id)
        if db_patient:
            # Redirect on logic error (duplicate ID)
            return RedirectResponse(
                url="/patients/register?error=duplicate_id", 
                status_code=status.HTTP_302_FOUND
            )
        
    # 3. Save to database, capture the created patient object
    new_patient = patient_crud.create_patient(db=db, patient=patient_in)
    
    # 3b. OPD registration SMS (only if valid phone) – log/print outcome for debugging
    try:
        from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
        phone_raw = (new_patient.phone_number or "").strip()
        has_phone = bool(phone_raw)
        valid_phone = is_valid_phone(phone_raw) if has_phone else False
        # Always print so outcome is visible in terminal (uvicorn) regardless of log level
        print(
            f"[OPD Registration SMS] patient_id={new_patient.id} name={new_patient.first_name} {new_patient.last_name} "
            f"phone_raw={repr(phone_raw or '(empty)')} has_phone={has_phone} is_valid_phone={valid_phone}"
        )
        logger.info(
            "OPD registration SMS check: patient_id=%s, name=%s %s, phone_raw=%r, has_phone=%s, is_valid_phone=%s",
            new_patient.id, new_patient.first_name, new_patient.last_name,
            phone_raw or "(empty)", has_phone, valid_phone,
        )
        if has_phone and valid_phone:
            msg = "Hello {$name}. You have been registered at Dei Gratia. Your patient number is {$number}. Please proceed to triage. Thank you!"
            destinations = [{
                "number": new_patient.phone_number,
                "values": [f"{new_patient.first_name} {new_patient.last_name}", new_patient.patient_number or "N/A"]
            }]
            sent = send_personalized_sms_notification(msg, destinations)
            print(f"[OPD Registration SMS] patient_id={new_patient.id} phone={repr(phone_raw)} sent={sent}")
            logger.info("OPD registration SMS send: patient_id=%s, phone=%r, sent=%s", new_patient.id, phone_raw, sent)
        else:
            print(f"[OPD Registration SMS] patient_id={new_patient.id} SKIPPED (no valid phone)")
            logger.info("OPD registration SMS skipped: patient_id=%s (no valid phone)", new_patient.id)
    except Exception as e:
        print(f"[OPD Registration SMS] patient_id={new_patient.id} FAILED: {e}")
        logger.warning(
            "OPD registration SMS failed: patient_id=%s, phone_raw=%r, error=%s",
            new_patient.id, getattr(new_patient, "phone_number", ""), e,
            exc_info=True,
        )
    
    # 4. Handle emergency cases - create appointment with high priority and fast-track
    is_emergency_case = is_emergency and is_emergency.lower() == "yes"
    
    # 5. Cash and insurance: go to triage first. Cash pays after doctor + labs (see CASH_PAYMENT_FLOW_PLAN).
    from app.utils.payment_verification import is_cash_patient
    
    if is_cash_patient(db, new_patient.id):
        # Cash patient: go to triage (payment is after doctor orders labs, not before)
        if is_emergency_case:
            # For emergency cases, create appointment immediately with highest priority
            from app.crud import appointment_crud
            from app.schemas.appointment_schemas import AppointmentCreate, AppointmentUpdate
            from app.models.scheduled_appointment_models import AppointmentType, AppointmentStatus
            from datetime import datetime
            
            emergency_appointment = AppointmentCreate(
                patient_id=new_patient.id,
                department="Emergency",
                department_type="opd",
                appointment_type=AppointmentType.EMERGENCY,
                scheduled_date=datetime.now(),
                chief_complaint="Emergency case - immediate attention required",
                notes="Emergency case - fast-tracked from registration",
                priority=1,  # Highest priority
                assigned_clinician_id=None,
                created_by_id=current_user.id
            )
            
            new_appointment = appointment_crud.create_appointment(db, emergency_appointment)
            # Auto check-in emergency patients
            appointment_crud.update_appointment(
                db,
                new_appointment.id,
                AppointmentUpdate(status=AppointmentStatus.CHECKED_IN, checked_in_at=datetime.now())
            )
            
            redirect_url = f"/patients/{new_patient.id}/triage?status=registered&emergency=true&appointment_id={new_appointment.id}&from_registration=true"
        else:
            # Normal cash: triage first, pay after doctor + labs
            redirect_url = f"/patients/{new_patient.id}/triage?status=registered&from_registration=true"
    else:
        # Insurance patient: go directly to triage
        redirect_url = f"/patients/{new_patient.id}/triage?status=registered"
        
        if is_emergency_case:
            # For emergency cases, create appointment immediately with highest priority
            from app.crud import appointment_crud
            from app.schemas.appointment_schemas import AppointmentCreate, AppointmentUpdate
            from app.models.scheduled_appointment_models import AppointmentType, AppointmentStatus
            from datetime import datetime
            
            emergency_appointment = AppointmentCreate(
                patient_id=new_patient.id,
                department="Emergency",
                department_type="opd",
                appointment_type=AppointmentType.EMERGENCY,
                scheduled_date=datetime.now(),
                chief_complaint="Emergency case - immediate attention required",
                notes="Emergency case - fast-tracked from registration",
                priority=1,  # Highest priority
                assigned_clinician_id=None,
                created_by_id=current_user.id
            )
            
            new_appointment = appointment_crud.create_appointment(db, emergency_appointment)
            # Auto check-in emergency patients
            appointment_crud.update_appointment(
                db,
                new_appointment.id,
                AppointmentUpdate(status=AppointmentStatus.CHECKED_IN, checked_in_at=datetime.now())
            )
            
            redirect_url = f"/patients/{new_patient.id}/triage?status=registered&emergency=true&appointment_id={new_appointment.id}"
    
    # FINAL REDIRECT
    return RedirectResponse(
        url=redirect_url, 
        status_code=status.HTTP_302_FOUND
    )


@router.get("/search", response_model=List[Patient])
def search_patients_api(
    query: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    JSON API endpoint for searching patients.
    Returns a list of patients matching the search query.
    Used by frontend components like patient selectors.
    """
    if not query or len(query.strip()) < 2:
        return []
    
    # Search patients (limit to 10 for dropdown/autocomplete)
    patients, total_count = patient_crud.search_patients(
        db,
        query=query,
        skip=0,
        limit=limit
    )
    
    return patients


@router.get("", response_model=List[Patient])
def get_patients_api(
    query: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    gender: Optional[str] = Query(None),
    payment_mechanism: Optional[str] = Query(None),
    sort_by: str = Query("id", regex="^(id|name|patient_number|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    JSON API endpoint for getting patients with pagination and filtering.
    """
    patients, total_count = patient_crud.search_patients(
        db,
        query=query,
        skip=skip,
        limit=limit,
        gender=gender,
        payment_mechanism=payment_mechanism,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return patients


@router.get("/{patient_id}", response_model=Patient)
def get_patient_api(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a patient by ID"""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

# Placeholder for JSON API endpoint
@router.post("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def register_patient_api_json():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="This endpoint is for external API use only.")
