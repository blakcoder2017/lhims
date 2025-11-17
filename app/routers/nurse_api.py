"""
Nurse API Routes

Routes for nurse-specific functionality:
- Triage queue (patients awaiting vitals)
- Nurse dashboard
- IPD workflow for nurses
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta, date

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.appointment_models import Appointment, AppointmentStatus
from app.models.triage_models import TriageVitals
from app.models.patient_models import Patient
from app.crud import appointment_crud, triage_crud, patient_crud
from app.models.ipd_models import Admission, AdmissionStatus

router = APIRouter(
    prefix="/nurse",
    tags=["Nurse"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", name="nurse_dashboard")
def nurse_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin", "Front Office"]))
):
    """Nurse dashboard with triage queue and IPD workflow"""
    from datetime import datetime, date, timedelta
    from app.models.appointment_models import AppointmentStatus
    from app.models.triage_models import TriageVitals
    from app.models.ipd_models import Admission, AdmissionStatus
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get appointments that need triage (checked in but no recent vitals)
    # Patients with appointments today who either:
    # 1. Have no vitals recorded today, OR
    # 2. Have appointments but vitals were recorded before appointment time
    
    appointments_today = db.query(Appointment).options(
        joinedload(Appointment.patient)
    ).filter(
        Appointment.scheduled_date >= today_start,
        Appointment.scheduled_date <= today_end,
        Appointment.status.in_([
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CHECKED_IN.value
        ]),
        Appointment.is_active == True
    ).order_by(
        Appointment.priority.asc(),
        Appointment.scheduled_date.asc()
    ).all()
    
    # Filter to get patients who need triage
    triage_queue = []
    for appointment in appointments_today:
        # Check if patient has vitals recorded today
        recent_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == appointment.patient_id,
            func.date(TriageVitals.recorded_at) == today
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        # If no vitals today, or vitals recorded before appointment, add to queue
        if not recent_vitals or recent_vitals.recorded_at < appointment.scheduled_date:
            triage_queue.append(appointment)
    
    # Get IPD admissions needing nursing care
    ipd_admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed)
    ).filter(
        Admission.status == AdmissionStatus.ADMITTED.value,
        Admission.is_active == True
    ).order_by(Admission.admission_date.desc()).limit(20).all()
    
    # Get completed triages today
    completed_triages_today = db.query(TriageVitals).filter(
        func.date(TriageVitals.recorded_at) == today,
        TriageVitals.recorded_by_id == current_user.id
    ).count()
    
    context = {
        "request": request,
        "title": "Nurse Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "triage_queue": triage_queue,
        "ipd_admissions": ipd_admissions,
        "completed_triages_today": completed_triages_today,
        "triage_queue_count": len(triage_queue),
        "ipd_admissions_count": len(ipd_admissions)
    }
    return templates.TemplateResponse("nurse/dashboard.html", context)


@router.get("/triage-queue", name="nurse_triage_queue")
def nurse_triage_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin", "Front Office"])),
    department: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None)
):
    """Triage queue for nurses - patients awaiting vital signs"""
    from datetime import datetime, date
    from app.models.appointment_models import AppointmentStatus
    from app.models.triage_models import TriageVitals
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get appointments that need triage
    query = db.query(Appointment).options(
        joinedload(Appointment.patient)
    ).filter(
        Appointment.scheduled_date >= today_start,
        Appointment.scheduled_date <= today_end,
        Appointment.status.in_([
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.CHECKED_IN.value
        ]),
        Appointment.is_active == True
    )
    
    if department:
        query = query.filter(Appointment.department == department)
    
    appointments = query.order_by(
        Appointment.priority.asc(),
        Appointment.scheduled_date.asc()
    ).all()
    
    # Filter to get patients who need triage (no recent vitals today)
    from app.crud import appointment_crud
    triage_queue = []
    for appointment in appointments:
        # Check if patient has vitals recorded today
        recent_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == appointment.patient_id,
            func.date(TriageVitals.recorded_at) == today
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        # Calculate wait time
        wait_time = appointment_crud.calculate_wait_time(appointment)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        
        # Add to queue if no vitals today, or if status filter requires it
        if status_filter == "needs_triage" and not recent_vitals:
            triage_queue.append({
                "appointment": appointment,
                "has_vitals": False,
                "last_vitals": None,
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
        elif status_filter == "completed" and recent_vitals:
            triage_queue.append({
                "appointment": appointment,
                "has_vitals": True,
                "last_vitals": recent_vitals,
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
        elif not status_filter:
            # Show all - mark which need triage
            triage_queue.append({
                "appointment": appointment,
                "has_vitals": recent_vitals is not None,
                "last_vitals": recent_vitals,
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
    
    # Get unfulfilled queues from previous days
    previous_appointments = appointment_crud.get_unfulfilled_queues_previous_days(
        db, department, None, days_back=7
    )
    
    # Filter previous appointments to only SCHEDULED or CHECKED_IN (need triage)
    previous_appointments = [
        appt for appt in previous_appointments 
        if appt.status.value in [AppointmentStatus.SCHEDULED.value, AppointmentStatus.CHECKED_IN.value]
    ]
    
    # Calculate wait times and check vitals for previous day queues
    triage_queue_previous = []
    for appointment in previous_appointments:
        # Check if patient has vitals recorded
        recent_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == appointment.patient_id
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        wait_time = appointment_crud.calculate_wait_time(appointment)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        
        triage_queue_previous.append({
            "appointment": appointment,
            "has_vitals": recent_vitals is not None,
            "last_vitals": recent_vitals,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Get unique departments for filter
    departments = db.query(Appointment.department).distinct().all()
    departments = [d[0] for d in departments]
    
    context = {
        "request": request,
        "title": "Triage Queue",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "triage_queue": triage_queue,
        "triage_queue_previous": triage_queue_previous,
        "departments": departments,
        "selected_department": department,
        "status_filter": status_filter
    }
    return templates.TemplateResponse("nurse/triage_queue.html", context)

