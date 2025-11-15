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
from app.models.patient_models import Patient
from app.models.encounter_models import Encounter
from app.models.appointment_models import Appointment
from app.models.triage_models import TriageVitals
from app.crud import patient_crud

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
    
    # Get all vitals records
    vitals_records = db.query(TriageVitals).filter(
        TriageVitals.patient_id == patient_id
    ).order_by(TriageVitals.recorded_at.desc()).limit(50).all()
    
    # Get all admissions for this patient
    admissions = ipd_crud.get_admissions_by_patient(db, patient_id)
    
    # Get current admission if any
    current_admission = ipd_crud.get_current_admission(db, patient_id)
    
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
    
    # Sort timeline by date (most recent first)
    timeline.sort(key=lambda x: x["date"], reverse=True)
    
    # Prepare blood pressure data for chart (systolic and diastolic over time)
    bp_chart_data = {
        "dates": [],
        "systolic": [],
        "diastolic": []
    }
    # Get vitals with BP data, sorted by date (oldest first for chart)
    vitals_with_bp = [v for v in vitals_records if v.systolic_bp and v.diastolic_bp]
    vitals_with_bp.sort(key=lambda x: x.recorded_at)
    
    for vital in vitals_with_bp:
        bp_chart_data["dates"].append(vital.recorded_at.strftime('%Y-%m-%d %H:%M'))
        bp_chart_data["systolic"].append(vital.systolic_bp)
        bp_chart_data["diastolic"].append(vital.diastolic_bp)
    
    # Calculate statistics
    appointment_count = len(appointments)
    vitals_count = len(vitals_records)
    admissions_count = len(admissions)
    
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
        "admissions": admissions,
        "current_admission": current_admission,
        "invoices": invoices,
        "invoice_summary": invoice_summary,
        "timeline": timeline,
        "bp_chart_data": bp_chart_data,
        "appointment_count": appointment_count,
        "vitals_count": vitals_count,
        "admissions_count": admissions_count
    }
    
    return templates.TemplateResponse("clinical/patient_records.html", context)


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
