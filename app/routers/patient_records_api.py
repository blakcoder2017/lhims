"""
Patient Records API Routes

Routes for viewing patient medical records and searching patients.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from collections import OrderedDict

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import Encounter
from app.models.appointment_models import Appointment
from app.models.triage_models import TriageVitals
from app.crud import patient_crud, opd_crud
from app.schemas.opd_schemas import OPDVisitCreate
from app.schemas.patient_schemas import PatientUpdate
from app.models.opd_models import OPDVisitStatus
from fastapi import Form

router = APIRouter(
    prefix="",
    tags=["Patient Records"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/patients/search", name="search_patients")
def search_patients_page(
    request: Request,
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    gender: Optional[str] = Query(None),
    payment_mechanism: Optional[str] = Query(None),
    sort_by: str = Query("id", regex="^(id|name|patient_number|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Patient search page with pagination, filtering, and search functionality.
    Searches by patient_number, name, phone_number, national_id, or patient ID.
    Accessible by: All clinical staff (Admin, Clinician, Front Office, Nurses, Lab Staff, Pharmacy Staff)
    """
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Search patients with pagination
    patients, total_count = patient_crud.search_patients(
        db,
        query=query,
        skip=skip,
        limit=per_page,
        gender=gender,
        payment_mechanism=payment_mechanism,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    context = {
        "request": request,
        "title": "Search Patients",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patients": patients,
        "search_query": query or "",
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "gender_filter": gender,
        "payment_mechanism_filter": payment_mechanism,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "genders": ["Male", "Female", "Other"],
        "payment_mechanisms": ["cash", "nhis", "private_insurance", "self_pay"]
    }
    
    return templates.TemplateResponse("clinical/patient_search.html", context)


@router.get("/patients/list", name="patients_list")
def patients_list_page(
    request: Request,
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    gender: Optional[str] = Query(None),
    payment_mechanism: Optional[str] = Query(None),
    sort_by: str = Query("id", regex="^(id|name|patient_number|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Comprehensive patient list page with pagination, filtering, search, and print functionality.
    """
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Get patients with pagination
    patients, total_count = patient_crud.search_patients(
        db,
        query=query,
        skip=skip,
        limit=per_page,
        gender=gender,
        payment_mechanism=payment_mechanism,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    context = {
        "request": request,
        "title": "Patients List",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patients": patients,
        "search_query": query or "",
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "gender_filter": gender,
        "payment_mechanism_filter": payment_mechanism,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "genders": ["Male", "Female", "Other"],
        "payment_mechanisms": ["cash", "nhis", "private_insurance", "self_pay"]
    }
    
    return templates.TemplateResponse("clinical/patients_list.html", context)


@router.get("/patients/{patient_id}/records", name="view_patient_records")
def view_patient_records(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    View comprehensive patient medical records including:
    - Demographics
    - Vitals history
    - Appointments
    - Encounters
    - Admissions
    - Invoices
    - Lab orders
    - Radiology orders
    - Prescriptions
    """
    from app.crud import appointment_crud, triage_crud, ipd_crud
    from app.models.encounter_models import EncounterStatus
    from app.models.appointment_models import AppointmentStatus
    from app.models.ipd_models import AdmissionStatus
    from app.utils.patient_utils import calculate_age
    
    # Get patient
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Calculate patient age
    patient_age = calculate_age(patient.date_of_birth)
    
    # Get all appointments
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.is_active == True
    ).order_by(Appointment.scheduled_date.desc()).limit(50).all()
    
    # Get all encounters
    encounters = db.query(Encounter).filter(
        Encounter.patient_id == patient_id,
        Encounter.is_active == True
    ).order_by(Encounter.encounter_date.desc()).limit(50).all()
    
    # Get all vitals records with eager loading of relationships
    from sqlalchemy.orm import joinedload
    vitals_records = db.query(TriageVitals).options(
        joinedload(TriageVitals.recorded_by),
        joinedload(TriageVitals.triage_assigned_by)
    ).filter(
        TriageVitals.patient_id == patient_id
    ).order_by(TriageVitals.recorded_at.desc()).limit(100).all()
    
    # Get all admissions for this patient
    admissions = ipd_crud.get_admissions_by_patient(db, patient_id)
    
    # Get current admission if any
    current_admission = ipd_crud.get_current_admission(db, patient_id)
    
    # Get all OPD visits for this patient
    opd_visits = opd_crud.get_opd_visits_by_patient(db, patient_id, skip=0, limit=50)
    
    # Get active OPD visit if any
    active_opd_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    
    # Sync payment status for active OPD visit (fixes cases where payment was made before auto-update was added)
    if active_opd_visit:
        opd_crud.sync_opd_visit_payment_status(db, active_opd_visit.id)
        # Refresh the visit to get updated status
        db.refresh(active_opd_visit)
    
    # Get invoices
    from app.models.billing_models import Invoice
    invoices = db.query(Invoice).filter(
        Invoice.patient_id == patient_id,
        Invoice.is_active == True
    ).order_by(Invoice.invoice_date.desc()).limit(50).all()
    
    # Build billing summary grouped by payment mechanism
    payment_label_map = OrderedDict([
        ("cash", "Cash / Self-Pay"),
        ("self_pay", "Self-Pay"),
        ("nhis", "NHIS"),
        ("private_insurance", "Private Insurance"),
        ("company", "Company / Corporate"),
        ("other", "Other"),
        ("unspecified", "Unspecified"),
    ])
    
    summary_by_mechanism: OrderedDict[str, dict] = OrderedDict()
    overall_summary = {
        "label": "All Payment Mechanisms",
        "invoice_count": 0,
        "open_invoices": 0,
        "total_billed": Decimal("0.00"),
        "total_paid": Decimal("0.00"),
        "total_balance": Decimal("0.00"),
    }
    
    for invoice in invoices:
        mechanism_value = None
        if invoice.payment_mechanism:
            mechanism_value = getattr(invoice.payment_mechanism, "value", invoice.payment_mechanism)
        elif patient.payment_mechanism:
            mechanism_value = getattr(patient.payment_mechanism, "value", patient.payment_mechanism)
        mechanism_key = (mechanism_value or "unspecified").lower()
        
        label = payment_label_map.get(
            mechanism_key,
            (mechanism_value or "Unspecified").replace("_", " ").title()
        )
        
        if mechanism_key not in summary_by_mechanism:
            summary_by_mechanism[mechanism_key] = {
                "label": label,
                "invoice_count": 0,
                "open_invoices": 0,
                "total_billed": Decimal("0.00"),
                "total_paid": Decimal("0.00"),
                "total_balance": Decimal("0.00"),
            }
        
        entry = summary_by_mechanism[mechanism_key]
        billed = invoice.total_amount or Decimal("0.00")
        paid = invoice.paid_amount or Decimal("0.00")
        balance = invoice.balance if invoice.balance is not None else (billed - paid)
        
        entry["invoice_count"] += 1
        entry["total_billed"] += billed
        entry["total_paid"] += paid
        entry["total_balance"] += balance
        if balance > 0:
            entry["open_invoices"] += 1
        
        overall_summary["invoice_count"] += 1
        overall_summary["total_billed"] += billed
        overall_summary["total_paid"] += paid
        overall_summary["total_balance"] += balance
        if balance > 0:
            overall_summary["open_invoices"] += 1
    
    invoice_summary = {
        "by_mechanism": list(summary_by_mechanism.values()),
        "overall": overall_summary
    }
    
    # Create timeline of medical events
    timeline = []
    
    # Add appointments to timeline
    for appointment in appointments:
        timeline.append({
            "date": appointment.scheduled_date,
            "type": "appointment",
            "title": f"Appointment: {appointment.department}",
            "description": f"Type: {appointment.appointment_type.value}, Status: {appointment.status.value}",
            "details": appointment,
        })
    
    # Add encounters to timeline
    for encounter in encounters:
        timeline.append({
            "date": encounter.encounter_date,
            "type": "encounter",
            "title": f"Encounter: {encounter.chief_complaint or 'No chief complaint'}",
            "description": f"Status: {encounter.status.value}, Clinician: {encounter.clinician.full_name if encounter.clinician else 'N/A'}",
            "details": encounter,
        })
    
    # Add vitals to timeline
    for vitals in vitals_records:
        # Build description with available vitals
        desc_parts = []
        if vitals.systolic_bp and vitals.diastolic_bp:
            desc_parts.append(f"BP: {vitals.systolic_bp}/{vitals.diastolic_bp}")
        desc_parts.append(f"Temp: {vitals.temperature}°C")
        if vitals.pulse_rate:
            desc_parts.append(f"Pulse: {vitals.pulse_rate} bpm")
        
        timeline.append({
            "date": vitals.recorded_at,
            "type": "vitals",
            "title": f"Vitals Recorded",
            "description": ", ".join(desc_parts),
            "details": vitals,
        })
    
    # Add admissions to timeline
    for admission in admissions:
        timeline.append({
            "date": admission.admission_date,
            "type": "admission",
            "title": f"Admission: {admission.admission_number}",
            "description": f"Ward: {admission.ward.name}, Bed: {admission.bed.bed_number} - Status: {admission.status.value.title()}",
            "details": admission,
        })
    
    # Add OPD visits to timeline
    for opd_visit in opd_visits:
        timeline.append({
            "date": opd_visit.visit_date,
            "type": "opd_visit",
            "title": f"OPD Visit: {opd_visit.opd_number}",
            "description": f"Status: {opd_visit.status.value.title()}, Payment: {opd_visit.payment_status.title()}",
            "details": opd_visit,
        })
    
    # Sort timeline by date (most recent first)
    timeline.sort(key=lambda x: x["date"], reverse=True)
    
    # Prepare comprehensive vital signs data for charts (all important vitals over time)
    vitals_chart_data = {
        "dates": [],
        "systolic": [],
        "diastolic": [],
        "temperature": [],
        "pulse_rate": [],
        "respiratory_rate": [],
        "oxygen_saturation": [],
        "pain_scale": []
    }
    # Get all vitals records, sorted by date (oldest first for chart)
    vitals_sorted = sorted(vitals_records, key=lambda x: x.recorded_at)
    
    for vital in vitals_sorted:
        vitals_chart_data["dates"].append(vital.recorded_at.strftime('%Y-%m-%d %H:%M'))
        vitals_chart_data["systolic"].append(vital.systolic_bp if vital.systolic_bp else None)
        vitals_chart_data["diastolic"].append(vital.diastolic_bp if vital.diastolic_bp else None)
        vitals_chart_data["temperature"].append(float(vital.temperature) if vital.temperature else None)
        vitals_chart_data["pulse_rate"].append(vital.pulse_rate if vital.pulse_rate else None)
        vitals_chart_data["respiratory_rate"].append(vital.respiratory_rate if vital.respiratory_rate else None)
        vitals_chart_data["oxygen_saturation"].append(vital.oxygen_saturation if vital.oxygen_saturation else None)
        vitals_chart_data["pain_scale"].append(vital.pain_scale if vital.pain_scale is not None else None)
    
    # Also prepare BP chart data for backward compatibility
    bp_chart_data = {
        "dates": vitals_chart_data["dates"],
        "systolic": vitals_chart_data["systolic"],
        "diastolic": vitals_chart_data["diastolic"]
    }
    
    # Calculate statistics
    appointment_count = len(appointments)
    vitals_count = len(vitals_records)
    admissions_count = len(admissions)
    opd_visits_count = len(opd_visits)
    
    # Check workflow completion status for encounter creation
    from app.utils.payment_verification import verify_encounter_workflow
    workflow_complete, missing_step, vitals_record, appointment_record, payment_info = verify_encounter_workflow(
        db, patient_id, check_vitals=True, check_checkin=True, check_payment=True
    )
    has_checked_in_appointment = appointment_record is not None
    
    context = {
        "request": request,
        "title": f"Patient Records: {patient.first_name} {patient.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "patient_age": patient_age,
        "appointments": appointments,
        "encounters": encounters,
        "vitals_records": vitals_records,
        "vitals_history": vitals_records,  # Alias for template compatibility
        "admissions": admissions,
        "current_admission": current_admission,
        "opd_visits": opd_visits,
        "active_opd_visit": active_opd_visit,
        "opd_visits_count": opd_visits_count,
        "invoices": invoices,
        "invoice_summary": invoice_summary,
        "timeline": timeline,
        "bp_chart_data": bp_chart_data,
        "vitals_chart_data": vitals_chart_data,
        "appointment_count": appointment_count,
        "vitals_count": vitals_count,
        "admissions_count": admissions_count,
        "workflow_complete": workflow_complete,
        "missing_step": missing_step,
        "has_checked_in_appointment": has_checked_in_appointment
    }
    
    return templates.TemplateResponse("clinical/patient_records.html", context)


@router.post("/patients/{patient_id}/opd-visits/{opd_visit_id}/complete", name="complete_opd_visit")
def complete_opd_visit(
    request: Request,
    patient_id: int,
    opd_visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Nurse", "Doctor", "Clinician"]))
):
    """
    Complete an OPD visit.
    Marks the visit as completed and redirects back to patient records.
    """
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify OPD visit exists and belongs to patient
    opd_visit = opd_crud.get_opd_visit(db, opd_visit_id)
    if not opd_visit or opd_visit.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="OPD visit not found")
    
    # Complete the visit
    try:
        completed_visit = opd_crud.complete_opd_visit(db, opd_visit_id)
        if not completed_visit:
            raise HTTPException(status_code=404, detail="Failed to complete OPD visit")
        
        # Redirect back to patient records with success message
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?status=opd_visit_completed",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        # Redirect back with error
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/patients/{patient_id}/start-new-visit", name="start_new_opd_visit")
def start_new_opd_visit(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Nurse"]))
):
    """
    Start a new OPD visit for a patient.
    Creates an OPD visit record and redirects to triage page.
    """
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if there's an active OPD visit
    active_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    if active_visit:
        # If active visit exists, redirect to triage with existing visit
        return RedirectResponse(
            url=str(request.url_for("patient_triage", patient_id=patient_id)) + f"?opd_visit_id={active_visit.id}",
            status_code=status.HTTP_302_FOUND
        )
    
    # Determine visit type based on payment mechanism
    visit_type = "walk_in"
    payment_status = "pending"
    
    if patient.payment_mechanism:
        if patient.payment_mechanism.value == "cash":
            payment_status = "pending"
        elif patient.payment_mechanism.value in ["nhis", "private_insurance"]:
            payment_status = "paid"  # Insurance patients don't need upfront payment
    
    # Create OPD visit
    try:
        opd_visit_data = OPDVisitCreate(
            visit_type=visit_type,
            payment_status=payment_status
        )
        
        opd_visit = opd_crud.create_opd_visit(db, opd_visit_data, patient_id)
        
        # For cash patients, create consultation charge
        if patient.payment_mechanism and patient.payment_mechanism.value == "cash":
            from app.services.charge_automation import create_charge_for_consultation
            try:
                create_charge_for_consultation(
                    db, 
                    patient_id, 
                    current_user.id,
                    encounter_id=None,
                    opd_visit_id=opd_visit.id
                )
                opd_crud.mark_consultation_charge_created(db, opd_visit.id)
            except Exception as e:
                # Log error but don't fail the visit creation
                print(f"Error creating consultation charge: {e}")
        
        # Redirect to triage with OPD visit ID
        return RedirectResponse(
            url=str(request.url_for("patient_triage", patient_id=patient_id)) + f"?opd_visit_id={opd_visit.id}&new_visit=true",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        # Redirect back to patient records with error
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/patients/{patient_id}/edit", name="edit_patient_form")
def edit_patient_form(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office"]))
):
    """
    Show form to edit patient biodata and payment mechanism.
    Accessible by: Admin, Front Office
    """
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    context = {
        "request": request,
        "title": f"Edit Patient: {patient.first_name} {patient.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "payment_mechanisms": [pm.value for pm in PaymentMechanism],
        "genders": ["Male", "Female", "Other"]
    }
    return templates.TemplateResponse("clinical/edit_patient.html", context)


@router.post("/patients/{patient_id}/edit", name="update_patient")
def update_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office"])),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    national_id: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    payment_mechanism: Optional[str] = Form(None),
    nhis_number: Optional[str] = Form(None),
    insurance_provider: Optional[str] = Form(None),
    insurance_provider_manual: Optional[str] = Form(None),
    insurance_policy_number: Optional[str] = Form(None),
    languages_spoken: Optional[str] = Form(None),
):
    """
    Update patient biodata and payment mechanism.
    Accessible by: Admin, Front Office
    """
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    try:
        # Parse date_of_birth if provided
        date_of_birth_obj = None
        if date_of_birth and date_of_birth.strip():
            try:
                date_of_birth_obj = datetime.strptime(date_of_birth.strip(), "%Y-%m-%d").date()
            except ValueError:
                return RedirectResponse(
                    url=str(request.url_for("edit_patient_form", patient_id=patient_id)) + "?error=Invalid date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_302_FOUND
                )
        
        # Handle payment mechanism enum
        payment_mechanism_enum = None
        if payment_mechanism and payment_mechanism.strip():
            try:
                payment_mechanism_enum = PaymentMechanism(payment_mechanism.strip())
            except ValueError:
                return RedirectResponse(
                    url=str(request.url_for("edit_patient_form", patient_id=patient_id)) + "?error=Invalid payment mechanism",
                    status_code=status.HTTP_302_FOUND
                )
        
        # Handle insurance provider (use manual entry if provided, otherwise use dropdown)
        # Only update insurance_provider if payment_mechanism is private_insurance
        final_insurance_provider = None
        if payment_mechanism_enum == PaymentMechanism.PRIVATE_INSURANCE:
            if insurance_provider_manual is not None:
                # Manual entry takes precedence
                final_insurance_provider = insurance_provider_manual.strip() if insurance_provider_manual.strip() else None
            elif insurance_provider is not None:
                # Use dropdown value
                final_insurance_provider = insurance_provider.strip() if insurance_provider.strip() else None
        
        # Build update data - only include fields that are provided
        update_data = {}
        if first_name and first_name.strip():
            update_data["first_name"] = first_name.strip()
        if last_name and last_name.strip():
            update_data["last_name"] = last_name.strip()
        if date_of_birth_obj:
            update_data["date_of_birth"] = date_of_birth_obj
        if gender and gender.strip():
            update_data["gender"] = gender.strip()
        # For optional fields, allow clearing by submitting empty string
        if national_id is not None:
            update_data["national_id"] = national_id.strip() if national_id.strip() else None
        if phone_number is not None:
            update_data["phone_number"] = phone_number.strip() if phone_number.strip() else None
        if address is not None:
            update_data["address"] = address.strip() if address.strip() else None
        if payment_mechanism_enum:
            update_data["payment_mechanism"] = payment_mechanism_enum
        if nhis_number is not None:
            update_data["nhis_number"] = nhis_number.strip() if nhis_number.strip() else None
        # Only update insurance_provider if payment mechanism is private_insurance
        if payment_mechanism_enum == PaymentMechanism.PRIVATE_INSURANCE and final_insurance_provider is not None:
            update_data["insurance_provider"] = final_insurance_provider
        elif payment_mechanism_enum == PaymentMechanism.PRIVATE_INSURANCE and insurance_provider_manual is not None:
            # Allow clearing insurance provider by submitting empty manual field
            update_data["insurance_provider"] = None
        if insurance_policy_number is not None:
            update_data["insurance_policy_number"] = insurance_policy_number.strip() if insurance_policy_number.strip() else None
        if languages_spoken is not None:
            update_data["languages_spoken"] = languages_spoken.strip() if languages_spoken.strip() else None
        
        # Create PatientUpdate schema
        patient_update = PatientUpdate(**update_data)
        
        # Update patient
        updated_patient = patient_crud.update_patient(db, patient_id, patient_update)
        if not updated_patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?status=patient_updated",
            status_code=status.HTTP_302_FOUND
        )
    except ValueError as e:
        # Handle duplicate national_id or other validation errors
        return RedirectResponse(
            url=str(request.url_for("edit_patient_form", patient_id=patient_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("edit_patient_form", patient_id=patient_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/patients/{patient_id}", name="patient_detail_redirect")
def patient_detail_redirect(
    request: Request,
    patient_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Redirect bare /patients/{id} URLs to the full patient records page.
    Positioned after explicit /patients routes so it doesn't intercept /patients/list.
    """
    return RedirectResponse(
        url=request.url_for("view_patient_records", patient_id=patient_id),
        status_code=status.HTTP_302_FOUND
    )
