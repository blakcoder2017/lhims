# 
from fastapi import APIRouter, Request, Depends, status, Query
from typing import Optional
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.deps import get_current_user, role_required
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.crud import patient_crud 
from app.schemas.patient_schemas import Patient 
from app.models.user_models import User
from app.services import create_charge_for_consultation

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

@router.get("/", name="dashboard")
# Protected by get_current_user, which raises 401 if unauthenticated.
async def dashboard(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Renders the main dashboard page with real-time metrics and statistics.
    If unauthenticated, a 401 is raised, and main.py redirects to /login.
    """
    from sqlalchemy import func, and_, extract
    from datetime import datetime, timedelta
    from decimal import Decimal
    from app.models.patient_models import Patient
    from app.models.appointment_models import Appointment, AppointmentStatus
    from app.models.encounter_models import Encounter, EncounterStatus, LabOrder, RadiologyOrder, Prescription, OrderStatus
    from app.models.billing_models import Invoice, Payment, InvoiceStatus, PaymentStatus
    from app.models.inventory_models import StockItem, StockStatus
    from app.models.lab_models import LabSample, SampleStatus
    
    # Date ranges
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    this_month_start = datetime.now().replace(day=1).date()
    
    # Patient Statistics
    total_patients = db.query(func.count(Patient.id)).filter(Patient.is_active == True).scalar() or 0
    new_patients_today = db.query(func.count(Patient.id)).filter(
        func.date(Patient.created_at) == today,
        Patient.is_active == True
    ).scalar() or 0
    new_patients_month = db.query(func.count(Patient.id)).filter(
        Patient.created_at >= this_month_start,
        Patient.is_active == True
    ).scalar() or 0
    
    # Appointment Statistics
    total_appointments_today = db.query(func.count(Appointment.id)).filter(
        Appointment.scheduled_date == today,
        Appointment.is_active == True
    ).scalar() or 0
    pending_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.status == AppointmentStatus.SCHEDULED.value,
        Appointment.is_active == True
    ).scalar() or 0
    
    # Encounter Statistics
    total_encounters_today = db.query(func.count(Encounter.id)).filter(
        func.date(Encounter.encounter_date) == today,
        Encounter.is_active == True
    ).scalar() or 0
    pending_encounters = db.query(func.count(Encounter.id)).filter(
        Encounter.status == EncounterStatus.IN_PROGRESS.value,
        Encounter.is_active == True
    ).scalar() or 0
    
    # Order Statistics
    pending_lab_orders = db.query(func.count(LabOrder.id)).filter(
        LabOrder.status == OrderStatus.PENDING.value
    ).scalar() or 0
    pending_radiology_orders = db.query(func.count(RadiologyOrder.id)).filter(
        RadiologyOrder.status == OrderStatus.PENDING.value
    ).scalar() or 0
    pending_prescriptions = db.query(func.count(Prescription.id)).filter(
        Prescription.status == OrderStatus.PENDING.value
    ).scalar() or 0
    
    # Financial Statistics
    revenue_today = db.query(func.sum(Payment.amount)).filter(
        func.date(Payment.payment_date) == today,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).scalar() or Decimal('0.00')
    
    revenue_month = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_date >= this_month_start,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).scalar() or Decimal('0.00')
    
    outstanding_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.balance > 0,
        Invoice.is_active == True
    ).scalar() or 0
    
    total_outstanding = db.query(func.sum(Invoice.balance)).filter(
        Invoice.balance > 0,
        Invoice.is_active == True
    ).scalar() or Decimal('0.00')
    
    # Inventory Statistics
    low_stock_items = db.query(func.count(StockItem.id)).filter(
        StockItem.status == StockStatus.LOW_STOCK.value,
        StockItem.is_active == True
    ).scalar() or 0
    
    out_of_stock_items = db.query(func.count(StockItem.id)).filter(
        StockItem.status == StockStatus.OUT_OF_STOCK.value,
        StockItem.is_active == True
    ).scalar() or 0
    
    expired_items = db.query(func.count(StockItem.id)).filter(
        StockItem.status == StockStatus.EXPIRED.value,
        StockItem.is_active == True
    ).scalar() or 0
    
    # Lab Sample Statistics - Only count COLLECTED samples as pending (not RECEIVED)
    pending_samples = db.query(func.count(LabSample.id)).filter(
        LabSample.status == SampleStatus.COLLECTED.value,
        LabSample.is_active == True
    ).scalar() or 0
    
    # IPD Statistics
    from app.models.ipd_models import Ward, Bed, Admission, WardStatus, BedStatus, AdmissionStatus
    
    # Total beds and occupancy
    # Count only active beds (exclude maintenance beds from total)
    total_beds = db.query(func.count(Bed.id)).filter(
        Bed.is_active == True,
        Bed.status != BedStatus.MAINTENANCE.value
    ).scalar() or 0
    occupied_beds = db.query(func.count(Bed.id)).filter(
        Bed.status == BedStatus.OCCUPIED.value,
        Bed.is_active == True
    ).scalar() or 0
    # Available beds = beds with status AVAILABLE (not occupied, reserved, or maintenance)
    available_beds = db.query(func.count(Bed.id)).filter(
        Bed.status == BedStatus.AVAILABLE.value,
        Bed.is_active == True
    ).scalar() or 0
    reserved_beds = db.query(func.count(Bed.id)).filter(
        Bed.status == BedStatus.RESERVED.value,
        Bed.is_active == True
    ).scalar() or 0
    bed_occupancy_percentage = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    
    # Ward statistics
    total_wards = db.query(func.count(Ward.id)).filter(Ward.is_active == True).scalar() or 0
    active_wards = db.query(func.count(Ward.id)).filter(
        Ward.status == WardStatus.ACTIVE.value,
        Ward.is_active == True
    ).scalar() or 0
    
    # Admission statistics
    current_admissions = db.query(func.count(Admission.id)).filter(
        Admission.status == AdmissionStatus.ADMITTED.value,
        Admission.is_active == True
    ).scalar() or 0
    admissions_today = db.query(func.count(Admission.id)).filter(
        func.date(Admission.admission_date) == today,
        Admission.is_active == True
    ).scalar() or 0
    discharges_today = db.query(func.count(Admission.id)).filter(
        func.date(Admission.discharge_date) == today,
        Admission.status == AdmissionStatus.DISCHARGED.value,
        Admission.is_active == True
    ).scalar() or 0
    
    context = {
        "request": request,
        "title": "Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name,
        # Patient stats
        "total_patients": total_patients,
        "new_patients_today": new_patients_today,
        "new_patients_month": new_patients_month,
        # Appointment stats
        "total_appointments_today": total_appointments_today,
        "pending_appointments": pending_appointments,
        # Encounter stats
        "total_encounters_today": total_encounters_today,
        "pending_encounters": pending_encounters,
        # Order stats
        "pending_lab_orders": pending_lab_orders,
        "pending_radiology_orders": pending_radiology_orders,
        "pending_prescriptions": pending_prescriptions,
        # Financial stats
        "revenue_today": float(revenue_today),
        "revenue_month": float(revenue_month),
        "outstanding_invoices": outstanding_invoices,
        "total_outstanding": float(total_outstanding),
        # Inventory stats
        "low_stock_items": low_stock_items,
        "out_of_stock_items": out_of_stock_items,
        "expired_items": expired_items,
        # Lab stats
        "pending_samples": pending_samples,
        # IPD stats
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "available_beds": available_beds,
        "reserved_beds": reserved_beds,
        "bed_occupancy_percentage": round(bed_occupancy_percentage, 1),
        "total_wards": total_wards,
        "active_wards": active_wards,
        "current_admissions": current_admissions,
        "admissions_today": admissions_today,
        "discharges_today": discharges_today
    }
    return templates.TemplateResponse("index.html", context)

@router.get("/patients/register", name="register_patient")
def get_patient_registration_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required("Front Office")) 
):
    """Patient registration page with insurance providers dropdown"""
    from app.crud import insurance_provider_crud
    
    # Get active insurance providers for dropdown
    insurance_providers = insurance_provider_crud.get_insurance_providers(db, active_only=True)
    
    context = {
        "request": request,
        "title": "Patient Registration",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "insurance_providers": insurance_providers
    }
    return templates.TemplateResponse("front_office/register_patient.html", context)

# NEW: Triage Page Route
@router.get("/patients/{patient_id}/triage", name="patient_triage")
def get_patient_triage_page(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    # FIX: Dependency syntax is now simplified
    current_user = Depends(role_required(["Front Office", "Nurse", "Doctor", "Clinician", "Admin"])) 
):
    """
    Renders the Patient Triage page.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    # Fetch Patient Details
    patient_data = patient_crud.get_patient(db, patient_id=patient_id)
    if not patient_data:
        # Redirect to dashboard if patient not found
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Check payment requirement for cash patients
    # Consultation fee now covers both vitals and encounter
    payment_required = False
    payment_paid = True
    charge = None
    invoice = None
    
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.CONSULTATION  # Consultation fee covers vitals + encounter
        )
        if payment_required and not charge:
            try:
                charge = create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None)
                payment_paid = False
            except Exception as billing_error:
                print(f"Warning: Unable to seed consultation charge for patient {patient_id}: {billing_error}")
        
    # Get doctors on duty for appointment assignment
    from app.crud import ipd_crud
    doctors_on_duty = ipd_crud.get_doctors_on_duty(db)
    
    # Get all clinicians for manual assignment
    from app.models.user_models import User
    from sqlalchemy.orm import joinedload
    try:
        from app.models.role_models import Role
        clinicians = db.query(User).options(joinedload(User.role)).join(Role).filter(Role.name.in_(["Clinician", "Admin"])).all()
    except Exception as e:
        # Fallback: get all users and filter by role name in Python
        all_users = db.query(User).options(joinedload(User.role)).all()
        clinicians = [u for u in all_users if u.role and u.role.name in ["Clinician", "Admin"]]
    
    # Check if patient has recent vitals (within last hour) to show check-in button
    from app.models.triage_models import TriageVitals
    from datetime import timedelta
    recent_vitals = db.query(TriageVitals).filter(
        TriageVitals.patient_id == patient_id
    ).order_by(TriageVitals.recorded_at.desc()).first()
    
    has_recent_vitals = False
    if recent_vitals:
        time_diff = datetime.now() - recent_vitals.recorded_at
        has_recent_vitals = time_diff < timedelta(hours=1)
    
    # Check if patient is already checked in (has appointment with checked_in status)
    from app.models.appointment_models import Appointment, AppointmentStatus
    checked_in_appointment = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.status == AppointmentStatus.CHECKED_IN,
        Appointment.is_active == True,
        func.date(Appointment.scheduled_date) == datetime.now().date()
    ).first()
    
    context = {
        "request": request,
        "title": f"Triage - {patient_data.first_name} {patient_data.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient_data,
        "doctors_on_duty": doctors_on_duty,
        "clinicians": clinicians,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "charge": charge,
        "invoice": invoice,
        "has_recent_vitals": has_recent_vitals,
        "recent_vitals": recent_vitals,
        "checked_in_appointment": checked_in_appointment
    }
    return templates.TemplateResponse("front_office/triage_page.html", context)


# Clinical Encounter Routes
@router.get("/patients/{patient_id}/encounters/new", name="new_encounter")
def get_new_encounter_page(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """
    Renders the page for creating a new clinical encounter.
    Only doctors/clinicians (and admins) can create encounters. Front desk and nurses should check in patients to the doctor's queue instead.
    """
    from app.crud import patient_crud, appointment_crud, disease_crud
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    
    # Fetch Patient Details
    patient_data = patient_crud.get_patient(db, patient_id=patient_id)
    if not patient_data:
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Fetch appointment if provided in query params
    appointment_data = None
    appointment_id = request.query_params.get("appointment_id")
    if appointment_id:
        try:
            appointment_data = appointment_crud.get_appointment(db, int(appointment_id))
        except (ValueError, TypeError):
            pass
    
    # Check payment requirement for cash patients (consultation fee)
    payment_required = False
    payment_paid = True
    charge = None
    invoice = None
    
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.CONSULTATION
        )
        if payment_required and not charge:
            try:
                charge = create_charge_for_consultation(db, patient_id, current_user.id, encounter_id=None)
                payment_paid = False
            except Exception as billing_error:
                print(f"Warning: Unable to seed consultation charge for patient {patient_id}: {billing_error}")

    # Load diseases for dropdowns
    diseases = disease_crud.get_diseases(db, skip=0, limit=1000)

    context = {
        "request": request,
        "title": f"New Encounter - {patient_data.first_name} {patient_data.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient_data,
        "appointment": appointment_data,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "charge": charge,
        "invoice": invoice,
        "diseases": diseases
    }
    return templates.TemplateResponse("clinical/new_encounter.html", context)


@router.get("/encounters/today", name="pending_encounters")
def get_pending_encounters_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
    search: Optional[str] = Query(None)
):
    """
    Renders a page showing pending (in-progress) encounters for today with search functionality.
    """
    from app.crud import encounter_crud
    from app.models.encounter_models import Encounter, EncounterStatus
    from app.models.patient_models import Patient
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_, func, String
    from datetime import datetime, date
    
    # Get today's date
    today = date.today()
    
    # Base query for in-progress encounters from today with eager loading
    query = db.query(Encounter).options(
        joinedload(Encounter.patient),
        joinedload(Encounter.clinician),
        joinedload(Encounter.appointment)
    ).filter(
        Encounter.status == EncounterStatus.IN_PROGRESS.value,
        Encounter.is_active == True,
        Encounter.encounter_date >= datetime.combine(today, datetime.min.time()),
        Encounter.encounter_date < datetime.combine(today, datetime.max.time())
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        # Join with Patient table for search
        query = query.join(Patient, Encounter.patient_id == Patient.id).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.national_id.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                func.cast(Patient.id, String).ilike(search_term),
                func.cast(Encounter.id, String).ilike(search_term),  # Search by encounter ID
                Encounter.chief_complaint.ilike(search_term)
            )
        )
    
    encounters = query.order_by(Encounter.encounter_date.desc()).all()
    
    context = {
        "request": request,
        "title": "Pending Encounters - Today",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounters": encounters,
        "today": today,
        "search_query": search or ""
    }
    return templates.TemplateResponse("clinical/pending_encounters.html", context)


@router.get("/encounters/{encounter_id}", name="view_encounter")
def get_encounter_page(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Renders the page for viewing/editing a clinical encounter.
    """
    from app.crud import encounter_crud
    from app.utils.patient_utils import calculate_age
    
    # Fetch Encounter with orders
    encounter_data = encounter_crud.get_encounter_with_orders(db, encounter_id)
    if not encounter_data:
        return RedirectResponse(url=request.url_for("dashboard"), status_code=status.HTTP_302_FOUND)
    
    # Calculate patient age
    patient_age = calculate_age(encounter_data.patient.date_of_birth)
    
    # Check for pending orders
    from app.models.encounter_models import LabOrder, RadiologyOrder, OrderStatus
    pending_lab_orders = [order for order in (encounter_data.lab_orders or []) 
                         if order.status in [OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS]]
    pending_radiology_orders = [order for order in (encounter_data.radiology_orders or []) 
                               if order.status in [OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS]]
    
    # Get service pricing dropdowns
    from app.crud import service_pricing_crud
    procedure_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "procedure")
    procedure_names = [p.service_name for p in procedure_pricing if p.is_active]
    lab_service_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "lab_test")
    radiology_service_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "radiology")
    antenatal_service_pricing = service_pricing_crud.get_service_pricing_by_charge_type(db, "antenatal")
    
    # Get existing procedures for this encounter
    from app.crud import procedure_crud
    procedures, _ = procedure_crud.get_procedures(db, encounter_id=encounter_id, limit=100)
    
    # Check if patient is currently admitted
    from app.crud import ipd_crud
    from app.models.ipd_models import AdmissionStatus
    current_admission = ipd_crud.get_current_admission(db, encounter_data.patient_id)
    is_admitted = current_admission is not None and current_admission.status == AdmissionStatus.ADMITTED
    
    # List antenatal charges already applied to this encounter
    from app.models.billing_models import Charge, ChargeType
    antenatal_charges = db.query(Charge).filter(
        Charge.encounter_id == encounter_id,
        Charge.charge_type == ChargeType.ANTENATAL
    ).order_by(Charge.created_at.desc()).all()

    # Parse secondary diagnosis codes from JSON
    import json
    secondary_diagnoses = []
    if encounter_data.secondary_diagnosis_codes:
        try:
            secondary_diagnoses = json.loads(encounter_data.secondary_diagnosis_codes)
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, treat as plain text
            secondary_diagnoses = [{"description": encounter_data.secondary_diagnosis_codes}]
    
    context = {
        "request": request,
        "title": f"Encounter #{encounter_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounter": encounter_data,
        "patient": encounter_data.patient,
        "patient_age": patient_age,
        "pending_lab_orders": pending_lab_orders,
        "pending_radiology_orders": pending_radiology_orders,
        "has_pending_orders": len(pending_lab_orders) > 0 or len(pending_radiology_orders) > 0,
        "procedure_names": procedure_names,
        "procedures": procedures,
        "lab_services": lab_service_pricing,
        "radiology_services": radiology_service_pricing,
        "antenatal_services": antenatal_service_pricing,
        "antenatal_charges": antenatal_charges,
        "is_admitted": is_admitted,
        "current_admission": current_admission,
        "secondary_diagnoses": secondary_diagnoses
    }
    return templates.TemplateResponse("clinical/view_encounter.html", context)