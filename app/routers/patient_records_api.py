"""
Patient Records API Routes

Routes for viewing patient medical records and searching patients.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from collections import OrderedDict

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.models.user_models import User
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import Encounter
from app.models.scheduled_appointment_models import Appointment, AppointmentStatus
from app.models.triage_models import TriageVitals
from app.crud import patient_crud, opd_crud, antenatal_crud, birth_crud
from app.schemas.opd_schemas import OPDVisitCreate
from app.schemas.patient_schemas import PatientUpdate
from app.models.opd_models import OPDVisit, OPDVisitStatus


def _get_payment_mechanisms(nhis_enabled: bool = True, private_insurance_enabled: bool = True) -> list:
    """Helper function to get payment mechanisms based on insurance settings."""
    mechanisms = ["cash", "self_pay"]
    if nhis_enabled:
        mechanisms.append("nhis")
    if private_insurance_enabled:
        mechanisms.append("private_insurance")
    return mechanisms
from fastapi import Form

router = APIRouter(
    prefix="",
    tags=["Patient Records"]
)

# Register the age filter
from datetime import date
def calculate_age(dob):
    if not dob:
        return None
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age
templates.env.filters["age"] = calculate_age


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
    # Get hospital settings for insurance configuration
    from app.crud import hospital_settings_crud
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    nhis_enabled = hospital_settings.nhis_enabled if hospital_settings else True
    private_insurance_enabled = hospital_settings.private_insurance_enabled if hospital_settings else True
    
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

    # Batch: which patients are returning (have OPD visits) - for revisit badge
    # Count ALL OPD visits for the patient
    returning_patient_ids = set()
    patient_visit_counts = {}
    if patients:
        from app.models.opd_models import OPDVisit
        from sqlalchemy import func
        pids = [p.id for p in patients]
        
        # Get patients who have any OPD visit
        visits_exist = (
            db.query(OPDVisit.patient_id)
            .filter(
                OPDVisit.patient_id.in_(pids),
                OPDVisit.is_active == True,
            )
            .distinct()
            .all()
        )
        returning_patient_ids = {r[0] for r in visits_exist}
        
        # Count all OPD visits per patient
        visit_counts_query = (
            db.query(OPDVisit.patient_id, func.count(OPDVisit.id).label("cnt"))
            .filter(
                OPDVisit.patient_id.in_(pids),
                OPDVisit.is_active == True,
            )
            .group_by(OPDVisit.patient_id)
            .all()
        )
        patient_visit_counts = {r[0]: r[1] for r in visit_counts_query}
    
    context = {
        "request": request,
        "title": "Search Patients",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patients": patients,
        "returning_patient_ids": returning_patient_ids,
        "patient_visit_counts": patient_visit_counts if patients else {},
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
        "payment_mechanisms": _get_payment_mechanisms(nhis_enabled, private_insurance_enabled),
        "nhis_enabled": nhis_enabled,
        "private_insurance_enabled": private_insurance_enabled
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
    
    # Batch compute: which patients are in triage or doctor's queue (Start New Visit disabled)
    from app.models.appointment_models import OPDQueue, QueueStatus
    patient_ids = [p.id for p in patients] if patients else []
    start_visit_disabled_ids = set()
    returning_patient_ids = set()
    patient_visit_counts = {}
    if patient_ids:
        in_queue = db.query(OPDQueue.patient_id).filter(
            OPDQueue.patient_id.in_(patient_ids),
            OPDQueue.is_active == True,
            OPDQueue.status.in_([QueueStatus.WAITING.value, QueueStatus.IN_PROGRESS.value]),
        ).distinct().all()
        start_visit_disabled_ids = {r[0] for r in in_queue}
        from app.models.encounter_models import Encounter, EncounterStatus
        from app.models.billing_models import Charge, Invoice, InvoiceStatus, ChargeType
        from sqlalchemy import func
        
        # Returning patient = has at least one paid consultation charge
        # This determines whether to show the Revisit badge
        revisit_visits = (
            db.query(Invoice.patient_id)
            .join(Charge, Charge.invoice_id == Invoice.id)
            .filter(
                Invoice.patient_id.in_(patient_ids),
                Invoice.is_active == True,
                Invoice.status == InvoiceStatus.PAID.value,
                Charge.charge_type == ChargeType.CONSULTATION,
            )
            .distinct()
            .all()
        )
        returning_patient_ids = {r[0] for r in revisit_visits}

        # Visit count = total number of OPD visits for the patient (including all statuses)
        # This counts ALL visits regardless of payment status or visit type
        from app.models.opd_models import OPDVisit
        visit_counts_query = (
            db.query(OPDVisit.patient_id, func.count(OPDVisit.id).label("cnt"))
            .filter(
                OPDVisit.patient_id.in_(patient_ids),
                OPDVisit.is_active == True,
            )
            .group_by(OPDVisit.patient_id)
            .all()
        )
        patient_visit_counts = {r[0]: r[1] for r in visit_counts_query}

    context = {
        "request": request,
        "title": "Patients List",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patients": patients,
        "start_visit_disabled_ids": start_visit_disabled_ids,
        "returning_patient_ids": returning_patient_ids,
        "patient_visit_counts": patient_visit_counts if patient_ids else {},
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
    from app.models.encounter_models import Encounter, EncounterStatus
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
    
    # Get antenatal visits for this patient
    from app.models.antenatal_models import AntenatalVisit
    antenatal_visits = db.query(AntenatalVisit).options(
        joinedload(AntenatalVisit.recorded_by)
    ).filter(
        AntenatalVisit.patient_id == patient_id,
        AntenatalVisit.is_active == True
    ).order_by(AntenatalVisit.visit_date.desc()).limit(100).all()
    
    # Check if patient is female (used for antenatal/birth records visibility)
    patient_gender = patient.gender if patient else None
    is_female = patient_gender and str(patient_gender).lower() == 'female'
    
    # Get birth records for this patient (as mother)
    from app.models.birth_models import BirthRecord
    birth_records = birth_crud.get_birth_records_by_mother(db, patient_id)
    
    # Get all lab orders for this patient
    # Include both direct patient_id links (walk-in orders) AND encounter-based orders
    from app.models.encounter_models import LabOrder
    lab_orders = db.query(LabOrder).outerjoin(Encounter, LabOrder.encounter_id == Encounter.id).filter(
        or_(
            LabOrder.patient_id == patient_id,
            Encounter.patient_id == patient_id
        )
    ).order_by(LabOrder.ordered_at.desc()).limit(100).all()
    
    # Get all prescriptions for this patient
    from app.models.encounter_models import Prescription
    prescriptions = db.query(Prescription).filter(
        Prescription.encounter_id.in_(
            db.query(Encounter.id).filter(Encounter.patient_id == patient_id)
        )
    ).order_by(Prescription.prescribed_at.desc()).limit(100).all()
    
    # If no prescriptions from encounters, also check direct prescriptions via OPD/IPD visits
    if not prescriptions:
        prescriptions = db.query(Prescription).filter(
            Prescription.opd_visit_id.in_(
                db.query(OPDVisit.id).filter(OPDVisit.patient_id == patient_id)
            )
        ).order_by(Prescription.prescribed_at.desc()).limit(100).all()
    
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
    
    # Add antenatal visits to timeline (only for female patients)
    if is_female:
        for visit in antenatal_visits:
            bp = f"{visit.blood_pressure_systolic or '–'}/{visit.blood_pressure_diastolic or '–'}" if (visit.blood_pressure_systolic or visit.blood_pressure_diastolic) else "N/A"
            timeline.append({
                "date": visit.visit_date,
                "type": "antenatal",
                "title": f"Antenatal Visit #{visit.visit_number or visit.id}",
                "description": f"Gestational: {visit.gestational_weeks or 'N/A'} weeks, BP: {bp}, Weight: {visit.weight_kg or 'N/A'} kg",
                "details": visit,
            })
        
        # Add birth records to timeline
        for record in birth_records:
            timeline.append({
                "date": record.birth_date,
                "type": "birth",
                "title": f"Birth: {record.delivery_type}",
                "description": f"Outcome: {record.birth_outcome}, Baby: {record.gender or 'N/A'}",
                "details": record,
            })
    
    # Sort timeline by date (most recent first)
    # Normalize all dates to datetime for consistent comparison
    from datetime import datetime
    timeline.sort(key=lambda x: (
        x["date"] if isinstance(x["date"], datetime) else
        datetime.combine(x["date"], datetime.min.time())
    ), reverse=True)
    
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
    lab_orders_count = len(lab_orders)
    prescriptions_count = len(prescriptions)
    
    # Check workflow completion status for encounter creation
    from app.utils.payment_verification import verify_encounter_workflow
    workflow_complete, missing_step, vitals_record, appointment_record, payment_info = verify_encounter_workflow(
        db, patient_id, check_vitals=True, check_checkin=True, check_payment=True
    )
    has_checked_in_appointment = appointment_record is not None
    
    # Disable Start New Visit when: patient is in triage or doctor's queue (in OPDQueue)
    start_new_visit_disabled = has_checked_in_appointment
    
    # Get Lab Test Catalog for Direct Lab Request dropdown
    from app.models.lab_catalog_models import LabTest
    lab_tests_catalog = db.query(LabTest).filter(
        LabTest.is_active == True
    ).order_by(LabTest.test_category, LabTest.test_name).all()
    
    # Get unique categories for quick filters
    from sqlalchemy import func
    lab_test_categories = db.query(
        LabTest.test_category,
        func.count(LabTest.id).label('count')
    ).filter(
        LabTest.is_active == True,
        LabTest.test_category.isnot(None)
    ).group_by(LabTest.test_category).all()
    lab_test_categories = [{"category": c[0], "count": c[1]} for c in lab_test_categories if c[0]]
    
    # Get Service Pricing for lab tests (includes pricing info)
    from app.models.service_pricing_models import ServicePricing
    lab_tests_pricing = db.query(ServicePricing).filter(
        ServicePricing.charge_type == "lab_test",
        ServicePricing.is_active == True
    ).order_by(ServicePricing.service_name).all()
    
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
        "antenatal_visits": antenatal_visits,
        "birth_records": birth_records,
        "is_female": is_female,
        "lab_orders": lab_orders,
        "prescriptions": prescriptions,
        "invoices": invoices,
        "invoice_summary": invoice_summary,
        "timeline": timeline,
        "bp_chart_data": bp_chart_data,
        "vitals_chart_data": vitals_chart_data,
        "appointment_count": appointment_count,
        "vitals_count": vitals_count,
        "admissions_count": admissions_count,
        "lab_orders_count": lab_orders_count,
        "prescriptions_count": prescriptions_count,
        "workflow_complete": workflow_complete,
        "missing_step": missing_step,
        "has_checked_in_appointment": has_checked_in_appointment,
        "start_new_visit_disabled": start_new_visit_disabled,
        "lab_tests_catalog": lab_tests_catalog,
        "lab_tests_pricing": lab_tests_pricing,
        "lab_test_categories": lab_test_categories,
    }
    
    return templates.TemplateResponse("clinical/patient_records.html", context)


@router.post("/patients/{patient_id}/opd-visits/{opd_visit_id}/complete", name="complete_opd_visit")
def complete_opd_visit(
    request: Request,
    patient_id: int,
    opd_visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Nurse", "Doctor", "Clinician"])),
    completion_outcome: Optional[str] = Form(None),
):
    """
    Complete an OPD visit.
    Marks the visit as completed. Optional completion_outcome: death, transfer, absconded.
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
        completed_visit = opd_crud.complete_opd_visit(db, opd_visit_id, completion_outcome=completion_outcome)
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


@router.post("/patients/start-visit-from-registration", name="start_visit_from_registration")
def start_visit_from_registration(
    request: Request,
    patient_id: int = Form(...),
    service_pricing_id: Optional[int] = Form(None),
    visit_type: str = Form("new"),
    department: Optional[str] = Form(None),
    # Optional payment method override for revisit patients
    payment_mechanism: Optional[str] = Form(None),
    nhis_number: Optional[str] = Form(None),
    nhis_expiry_date: Optional[str] = Form(None),
    # Purpose of visit — consultation (default) or direct_service
    purpose_of_visit: Optional[str] = Form("consultation"),
    direct_service_type: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Nurse", "Finance"])),
):
    """
    Start a visit for an existing patient from the registration page.
    Creates OPD visit and redirects to collect_payment with service_pricing_id and visit type.
    Optional payment_mechanism allows updating patient payment method during revisit.
    """
    from urllib.parse import quote
    from app.crud import appointment_crud

    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Handle optional payment method update (for revisit patients who want to change payment method)
    if payment_mechanism and payment_mechanism.strip():
        try:
            # Convert to uppercase to match enum values (form may send lowercase)
            payment_mechanism_enum = PaymentMechanism(payment_mechanism.strip().upper())
            # Build update data for patient
            update_data = {"payment_mechanism": payment_mechanism_enum}
            if nhis_number is not None:
                update_data["nhis_number"] = nhis_number.strip() if nhis_number.strip() else None
            if nhis_expiry_date is not None:
                if nhis_expiry_date.strip():
                    try:
                        update_data["nhis_expiry_date"] = datetime.strptime(nhis_expiry_date.strip(), "%Y-%m-%d").date()
                    except ValueError:
                        pass  # Ignore invalid date format
                else:
                    update_data["nhis_expiry_date"] = None
            # Update patient record
            patient_update = PatientUpdate(**update_data)
            patient = patient_crud.update_patient(db, patient_id, patient_update)
        except ValueError:
            pass  # Invalid payment mechanism, use existing
    from urllib.parse import quote
    from app.crud import appointment_crud

    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Direct Service path — skip consultation, create DirectServiceRegistration, redirect to service dashboard
    is_direct_service = (purpose_of_visit or "consultation").strip().lower() == "direct_service"
    if is_direct_service:
        valid_service_types = ("lab", "pharmacy", "radiology", "procedure")
        if not direct_service_type or direct_service_type.strip().lower() not in valid_service_types:
            return RedirectResponse(
                url=str(request.url_for("register_patient")) + "?error=Please+select+a+service+type+for+direct+service",
                status_code=status.HTTP_302_FOUND
            )
        from app.crud import direct_service_registration_crud
        from app.schemas.direct_service_registration_schemas import DirectServiceRegistrationCreate
        _SERVICE_LABELS = {"lab": "Laboratory", "pharmacy": "Pharmacy", "radiology": "Radiology", "procedure": "Procedure"}
        stype = direct_service_type.strip().lower()
        reg_data = DirectServiceRegistrationCreate(
            patient_id=patient.id,
            service_type=stype,
            service_type_label=_SERVICE_LABELS.get(stype, stype.title()),
            registration_notes="Registered via front office (existing patient, direct service)",
        )
        registration = direct_service_registration_crud.create_direct_service_registration(db, reg_data, current_user.id)
        return RedirectResponse(
            url=f"/direct-service-registration?patient_id={patient.id}&registration_id={registration.id}&success=1",
            status_code=status.HTTP_302_FOUND
        )

    # Guard: consultation path requires a service pricing selection
    if not service_pricing_id:
        return RedirectResponse(
            url=str(request.url_for("register_patient")) + "?error=Please+select+a+consultation+service",
            status_code=status.HTTP_302_FOUND
        )

    queue_entry = appointment_crud.get_recent_checked_in_queue_entry(db, patient_id, within_hours=24)
    if queue_entry:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id))
            + "?error=Patient+is+in+the+triage+queue.+Complete+this+visit+before+starting+a+new+one",
            status_code=status.HTTP_302_FOUND
        )

    active_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    if active_visit:
        return RedirectResponse(
            url=str(request.url_for("collect_payment", patient_id=patient_id))
            + f"?opd_visit_id={active_visit.id}&new_visit=true&return_to=triage"
            + f"&service_pricing_id={service_pricing_id}"
            + f"&visit_type={quote((visit_type or 'new').strip().lower())}",
            status_code=status.HTTP_302_FOUND
        )

    visit_type_clean = (visit_type or "new").strip().lower()
    if visit_type_clean not in ("revisit", "follow_up"):
        visit_type_clean = "new"

    payment_status = "pending"
    if patient.payment_mechanism and patient.payment_mechanism.value in ["nhis", "private_insurance"]:
        payment_status = "paid"

    try:
        opd_visit_data = OPDVisitCreate(
            visit_type="revisit" if visit_type_clean in ("revisit", "follow_up") else "opd",
            payment_status=payment_status
        )
        opd_visit = opd_crud.create_opd_visit(db, opd_visit_data, patient_id)

        if patient.payment_mechanism and patient.payment_mechanism.value == "cash":
            vt_param = "revisit" if visit_type_clean in ("revisit", "follow_up") else "new"
            return RedirectResponse(
                url=str(request.url_for("collect_payment", patient_id=patient_id))
                + f"?opd_visit_id={opd_visit.id}&new_visit=true&return_to=triage"
                + f"&service_pricing_id={service_pricing_id}&visit_type={vt_param}",
                status_code=status.HTTP_302_FOUND
            )
        return RedirectResponse(
            url=str(request.url_for("patient_triage", patient_id=patient_id))
            + f"?opd_visit_id={opd_visit.id}&new_visit=true",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("register_patient")) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/patients/{patient_id}/opd-visit/new", name="start_new_opd_visit")
def start_new_opd_visit(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Nurse"])),
    # Optional payment method override for revisit patients
    payment_mechanism: Optional[str] = Form(None),
    nhis_number: Optional[str] = Form(None),
    nhis_expiry_date: Optional[str] = Form(None),
):
    """
    Start a new OPD visit for a patient.
    Creates an OPD visit record and redirects to triage page.
    Optional payment_mechanism allows updating patient payment method during revisit.
    """
    from app.crud import appointment_crud
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Handle optional payment method update (for revisit patients who want to change payment method)
    if payment_mechanism and payment_mechanism.strip():
        try:
            # Convert to uppercase to match enum values (form may send lowercase)
            payment_mechanism_enum = PaymentMechanism(payment_mechanism.strip().upper())
            # Build update data for patient
            update_data = {"payment_mechanism": payment_mechanism_enum}
            if nhis_number is not None:
                update_data["nhis_number"] = nhis_number.strip() if nhis_number.strip() else None
            if nhis_expiry_date is not None:
                if nhis_expiry_date.strip():
                    try:
                        update_data["nhis_expiry_date"] = datetime.strptime(nhis_expiry_date.strip(), "%Y-%m-%d").date()
                    except ValueError:
                        pass  # Ignore invalid date format
                else:
                    update_data["nhis_expiry_date"] = None
            # Update patient record
            patient_update = PatientUpdate(**update_data)
            patient = patient_crud.update_patient(db, patient_id, patient_update)
        except ValueError:
            pass  # Invalid payment mechanism, use existing
    from app.crud import appointment_crud
    # Verify patient exists
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Reject if patient is in triage or doctor's queue (must complete current visit first)
    queue_entry = appointment_crud.get_recent_checked_in_queue_entry(db, patient_id, within_hours=24)
    if queue_entry:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id))
            + "?error=Patient+is+in+the+triage+queue.+Complete+this+visit+before+starting+a+new+one",
            status_code=status.HTTP_302_FOUND
        )
    
    # Check if there's an active OPD visit
    active_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    if active_visit:
        # Cash patients: go to collect_payment to select department, then pay (department-based fee)
        if patient.payment_mechanism and patient.payment_mechanism.value == "cash":
            return RedirectResponse(
                url=str(request.url_for("collect_payment", patient_id=patient_id))
                + f"?opd_visit_id={active_visit.id}&new_visit=true&return_to=triage",
                status_code=status.HTTP_302_FOUND
            )
        # Insurance patient with active visit: redirect to nurse queue
        return RedirectResponse(
            url="/nurse/triage-queue?status=revisit",
            status_code=status.HTTP_302_FOUND
        )
    
    # Determine visit type based on payment mechanism
    visit_type = "opd"
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
        
        # For cash patients: redirect to collect_payment to select department, then pay (department-based fee)
        # Charge is created in pay_consultation with correct department price
        if patient.payment_mechanism and patient.payment_mechanism.value == "cash":
            return RedirectResponse(
                url=str(request.url_for("collect_payment", patient_id=patient_id))
                + f"?opd_visit_id={opd_visit.id}&new_visit=true&return_to=triage",
                status_code=status.HTTP_302_FOUND
            )
        # Insurance patient: add to vitals queue and redirect to nurse queue
        from app.schemas.appointment_schemas import QueueCreate
        from app.models.appointment_models import VisitType
        queue_data = QueueCreate(
            patient_id=patient_id,
            department="General Medicine",
            department_type="opd",
            visit_type=VisitType.WALK_IN,
            priority=5,
            chief_complaint=None,
            notes="Registered from front office (new visit)",
            assigned_clinician_id=None,
            created_by_id=current_user.id
        )
        appointment_crud.create_queue_entry(db, queue_data)
        return RedirectResponse(
            url="/nurse/triage-queue?status=registered",
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
    nhis_expiry_date: Optional[str] = Form(None),
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
                # Convert to uppercase to match enum values (form may send lowercase)
                payment_mechanism_enum = PaymentMechanism(payment_mechanism.strip().upper())
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
        if nhis_expiry_date is not None:
            if nhis_expiry_date.strip():
                try:
                    update_data["nhis_expiry_date"] = datetime.strptime(nhis_expiry_date.strip(), "%Y-%m-%d").date()
                except ValueError:
                    update_data["nhis_expiry_date"] = None
            else:
                update_data["nhis_expiry_date"] = None
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


@router.get("/clinical/allergies", name="allergies_list")
def allergies_list_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Allergies Registry page - placeholder under construction.
    """
    context = {
        "request": request,
        "title": "Allergies Registry",
        "current_user": current_user,
        "user_role": current_user.role.name if current_user.role else ""
    }
    return templates.TemplateResponse("clinical/allergies_list.html", context)


@router.get("/clinical/medical-history", name="medical_history_list")
def medical_history_list_page(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Medical History page - placeholder under construction.
    """
    context = {
        "request": request,
        "title": "Medical History",
        "current_user": current_user,
        "user_role": current_user.role.name if current_user.role else ""
    }
    return templates.TemplateResponse("clinical/medical_history_list.html", context)
