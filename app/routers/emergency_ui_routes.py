"""
Emergency Department UI Routes
Handles Emergency-related UI: dashboard, visits list, and quick registration.
Emergency = care without full patient details first (like detention/IPD triage).
When stabilized, patient can be admitted to IPD.
Uses OPDVisit (visit_type='emergency') and OPDQueue (visit_type=EMERGENCY or department Emergency).
"""
from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.encounter_models import Encounter, EncounterStatus
from app.models.appointment_models import OPDQueue, QueueStatus, VisitType
from app.models.billing_models import Payment, PaymentStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

EMERGENCY_VISIT_TYPE = "emergency"
EMERGENCY_DEPARTMENT = "Emergency"


@router.get("/emergency/dashboard", name="emergency_dashboard")
def emergency_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Emergency dashboard: stats and lists for emergency visits only."""
    today = date.today()
    this_month_start = datetime(today.year, today.month, 1)

    # Emergency visits: OPDVisit where visit_type = 'emergency'
    total_visits = (
        db.query(func.count(OPDVisit.id))
        .filter(OPDVisit.is_active == True, OPDVisit.visit_type == EMERGENCY_VISIT_TYPE)
        .scalar()
        or 0
    )
    active_visits = (
        db.query(func.count(OPDVisit.id))
        .filter(
            OPDVisit.status == OPDVisitStatus.ACTIVE.value,
            OPDVisit.is_active == True,
            OPDVisit.visit_type == EMERGENCY_VISIT_TYPE,
        )
        .scalar()
        or 0
    )
    completed_visits_today = (
        db.query(func.count(OPDVisit.id))
        .filter(
            OPDVisit.status == OPDVisitStatus.COMPLETED.value,
            func.date(OPDVisit.completed_at) == today,
            OPDVisit.is_active == True,
            OPDVisit.visit_type == EMERGENCY_VISIT_TYPE,
        )
        .scalar()
        or 0
    )
    visits_this_month = (
        db.query(func.count(OPDVisit.id))
        .filter(
            OPDVisit.visit_date >= this_month_start,
            OPDVisit.is_active == True,
            OPDVisit.visit_type == EMERGENCY_VISIT_TYPE,
        )
        .scalar()
        or 0
    )

    # Emergency queue: OPDQueue where visit_type=EMERGENCY or department ilike Emergency
    waiting_patients = (
        db.query(func.count(OPDQueue.id))
        .filter(
            OPDQueue.status == QueueStatus.WAITING.value,
            OPDQueue.is_active == True,
            or_(
                OPDQueue.visit_type == VisitType.EMERGENCY,
                func.lower(OPDQueue.department).like("%emergency%"),
            ),
        )
        .scalar()
        or 0
    )
    in_progress_queue = (
        db.query(func.count(OPDQueue.id))
        .filter(
            OPDQueue.status == QueueStatus.IN_PROGRESS.value,
            OPDQueue.is_active == True,
            or_(
                OPDQueue.visit_type == VisitType.EMERGENCY,
                func.lower(OPDQueue.department).like("%emergency%"),
            ),
        )
        .scalar()
        or 0
    )

    # Pending encounters linked to emergency visits
    pending_encounters = (
        db.query(func.count(Encounter.id))
        .join(OPDVisit, Encounter.opd_visit_id == OPDVisit.id)
        .filter(
            Encounter.status == EncounterStatus.IN_PROGRESS.value,
            Encounter.is_active == True,
            OPDVisit.visit_type == EMERGENCY_VISIT_TYPE,
            OPDVisit.is_active == True,
        )
        .scalar()
        or 0
    )

    # Recent active emergency visits
    recent_active_visits = (
        db.query(OPDVisit)
        .options(joinedload(OPDVisit.patient))
        .filter(
            OPDVisit.status == OPDVisitStatus.ACTIVE.value,
            OPDVisit.is_active == True,
            OPDVisit.visit_type == EMERGENCY_VISIT_TYPE,
        )
        .order_by(OPDVisit.visit_date.desc())
        .limit(15)
        .all()
    )
    recent_completed_visits = (
        db.query(OPDVisit)
        .options(joinedload(OPDVisit.patient))
        .filter(
            OPDVisit.status == OPDVisitStatus.COMPLETED.value,
            OPDVisit.is_active == True,
            OPDVisit.visit_type == EMERGENCY_VISIT_TYPE,
        )
        .order_by(OPDVisit.completed_at.desc())
        .limit(15)
        .all()
    )

    completion_rate = (
        (completed_visits_today / active_visits * 100) if active_visits > 0 else 0
    )

    context = {
        "request": request,
        "title": "Emergency Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "total_visits": total_visits,
        "active_visits": active_visits,
        "completed_visits_today": completed_visits_today,
        "visits_this_month": visits_this_month,
        "waiting_patients": waiting_patients,
        "in_progress_queue": in_progress_queue,
        "pending_encounters": pending_encounters,
        "completion_rate": completion_rate,
        "recent_active_visits": recent_active_visits,
        "recent_completed_visits": recent_completed_visits,
    }
    return templates.TemplateResponse("emergency/dashboard.html", context)


@router.get("/emergency/visits", name="emergency_visits_list")
def emergency_visits_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, description="active, completed, or all"),
    limit: int = Query(50, le=200),
):
    """List emergency visits (OPDVisit with visit_type=emergency)."""
    query = (
        db.query(OPDVisit)
        .options(joinedload(OPDVisit.patient))
        .filter(OPDVisit.is_active == True, OPDVisit.visit_type == EMERGENCY_VISIT_TYPE)
    )
    if status_filter == "active":
        query = query.filter(OPDVisit.status == OPDVisitStatus.ACTIVE.value)
    elif status_filter == "completed":
        query = query.filter(OPDVisit.status == OPDVisitStatus.COMPLETED.value)
    visits = (
        query.order_by(OPDVisit.visit_date.desc())
        .limit(limit)
        .all()
    )
    context = {
        "request": request,
        "title": "Emergency Visits",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "visits": visits,
        "status_filter": status_filter,
    }
    return templates.TemplateResponse("emergency/visits_list.html", context)


@router.get("/emergency/quick-register", name="emergency_quick_register")
def emergency_quick_register_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor", "Nurse", "Clinician"])),
):
    """
    Quick registration for emergency: care without full patient details.
    Creates minimal patient (Unknown/Emergency) and sends to emergency triage.
    Details can be updated later when patient is stabilized or identified.
    """
    context = {
        "request": request,
        "title": "Emergency – Quick Register",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
    }
    return templates.TemplateResponse("emergency/quick_register.html", context)


@router.post("/emergency/quick-register", name="emergency_quick_register_submit")
def emergency_quick_register_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor", "Nurse", "Clinician"])),
    gender: str = Form("Unknown"),
    note: Optional[str] = Form(None),
):
    """
    Create minimal emergency patient (no full details) and redirect to emergency triage.
    Patient can receive care immediately; details can be updated later.
    """
    from app.crud import patient_crud, appointment_crud
    from app.schemas.patient_schemas import PatientCreate
    from app.schemas.appointment_schemas import AppointmentCreate
    from app.models.scheduled_appointment_models import AppointmentType, AppointmentStatus
    from app.services.opd_validation import auto_link_opd_visit

    today = date.today()
    gender_clean = (gender or "Unknown").strip() or "Unknown"
    if gender_clean not in ("Male", "Female", "Unknown"):
        gender_clean = "Unknown"

    # Minimal patient: no name/ID required for care
    patient_in = PatientCreate(
        first_name="Unknown",
        last_name="Emergency",
        date_of_birth=today,
        gender=gender_clean,
        national_id=None,
        phone_number=None,
        address=None,
        payment_mechanism=None,
        nhis_number=None,
        insurance_provider=None,
        insurance_policy_number=None,
        languages_spoken=None,
    )
    new_patient = patient_crud.create_patient(db=db, patient=patient_in)

    # Emergency appointment so visit is created as emergency
    emergency_appointment = AppointmentCreate(
        patient_id=new_patient.id,
        department=EMERGENCY_DEPARTMENT,
        department_type="opd",
        appointment_type=AppointmentType.EMERGENCY,
        scheduled_date=datetime.now(),
        chief_complaint=note or "Emergency – details to be taken when stabilized",
        notes="Quick-registered; full registration can be done later.",
        priority=1,
        assigned_clinician_id=None,
        created_by_id=current_user.id,
    )
    new_appointment = appointment_crud.create_appointment(db, emergency_appointment)
    from app.schemas.appointment_schemas import AppointmentUpdate
    appointment_crud.update_appointment(
        db,
        new_appointment.id,
        AppointmentUpdate(status=AppointmentStatus.CHECKED_IN, checked_in_at=datetime.now()),
    )

    # Ensure OPD visit exists with visit_type=emergency (so it appears on Emergency page)
    auto_link_opd_visit(db, new_patient.id, new_appointment.id)

    redirect_url = request.url_for("patient_triage", patient_id=new_patient.id)
    return RedirectResponse(
        url=f"{redirect_url}?status=registered&emergency=true&appointment_id={new_appointment.id}&from_registration=true",
        status_code=status.HTTP_302_FOUND,
    )
