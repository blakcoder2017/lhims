"""
Doctor API Routes

Routes for doctor/clinician-specific functionality:
- Doctor queue (patients assigned to doctor)
- Doctor dashboard
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
from app.models.encounter_models import Encounter, EncounterStatus
from app.models.patient_models import Patient
from app.crud import appointment_crud, encounter_crud

router = APIRouter(
    prefix="/doctor",
    tags=["Doctor"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", name="doctor_dashboard")
def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Doctor dashboard with patient queue and pending encounters"""
    from datetime import datetime, date
    from app.models.appointment_models import AppointmentStatus
    from app.models.encounter_models import EncounterStatus
    from app.models.ipd_models import Admission, AdmissionStatus
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get all currently admitted patients - INCLUDING them in dashboard for doctors
    current_admissions = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.initial_encounter)
    ).filter(
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).order_by(Admission.admission_date.desc()).all()
    admitted_patient_ids = {admission.patient_id for admission in current_admissions}
    
    # Get appointments assigned to this doctor
    assigned_appointments = db.query(Appointment).options(
        joinedload(Appointment.patient)
    ).filter(
        Appointment.assigned_clinician_id == current_user.id,
        Appointment.scheduled_date >= today_start,
        Appointment.scheduled_date <= today_end,
        Appointment.status.in_([
            AppointmentStatus.CHECKED_IN.value,
            AppointmentStatus.IN_PROGRESS.value
        ]),
        Appointment.is_active == True
    ).order_by(
        Appointment.priority.asc(),
        Appointment.scheduled_date.asc()
    ).all()
    
    # Filter out admitted patients from assigned appointments
    assigned_appointments = [appt for appt in assigned_appointments if appt.patient_id not in admitted_patient_ids]
    
    # Get all checked-in appointments for doctor's department (if not assigned)
    # Or all checked-in appointments if doctor has no specific department
    department_appointments = db.query(Appointment).options(
        joinedload(Appointment.patient)
    ).filter(
        Appointment.scheduled_date >= today_start,
        Appointment.scheduled_date <= today_end,
        Appointment.status == AppointmentStatus.CHECKED_IN.value,
        Appointment.is_active == True
    ).order_by(
        Appointment.priority.asc(),
        Appointment.scheduled_date.asc()
    ).all()
    
    # Filter out admitted patients from department appointments
    department_appointments = [appt for appt in department_appointments if appt.patient_id not in admitted_patient_ids]
    
    # Get pending encounters for this doctor
    pending_encounters = db.query(Encounter).options(
        joinedload(Encounter.patient),
        joinedload(Encounter.appointment)
    ).filter(
        Encounter.clinician_id == current_user.id,
        Encounter.status == EncounterStatus.IN_PROGRESS.value,
        Encounter.is_active == True,
        Encounter.encounter_date >= today_start,
        Encounter.encounter_date <= today_end
    ).order_by(Encounter.encounter_date.desc()).all()
    
    # Filter out admitted patients from pending encounters
    pending_encounters = [enc for enc in pending_encounters if enc.patient_id not in admitted_patient_ids]
    
    # Get completed encounters today
    completed_encounters_today = db.query(Encounter).filter(
        Encounter.clinician_id == current_user.id,
        Encounter.status == EncounterStatus.COMPLETED.value,
        Encounter.is_active == True,
        func.date(Encounter.encounter_date) == today
    ).count()
    
    # Calculate length of stay for current admissions
    from datetime import datetime
    admissions_with_stay_days = []
    for admission in current_admissions:
        stay_days = (datetime.now().date() - admission.admission_date.date()).days + 1 if admission.admission_date else 0
        admissions_with_stay_days.append({
            "admission": admission,
            "stay_days": stay_days
        })
    
    context = {
        "request": request,
        "title": "Doctor Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "assigned_appointments": assigned_appointments,
        "department_appointments": department_appointments,
        "pending_encounters": pending_encounters,
        "completed_encounters_today": completed_encounters_today,
        "assigned_count": len(assigned_appointments),
        "pending_encounters_count": len(pending_encounters),
        "current_admissions": admissions_with_stay_days,  # Include current admission cases
        "admissions_count": len(current_admissions)
    }
    return templates.TemplateResponse("doctor/dashboard.html", context)


@router.get("/queue", name="doctor_queue")
def doctor_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    department: Optional[str] = Query(None),
    show_assigned_only: Optional[bool] = Query(False),
    search: Optional[str] = Query(None, description="Search by patient name or patient number")
):
    """Doctor queue - patients checked in and ready to see doctor"""
    from datetime import datetime, date
    from app.models.appointment_models import AppointmentStatus
    from app.models.encounter_models import Encounter, EncounterStatus
    from app.models.ipd_models import Admission
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Build query for appointments
    query = db.query(Appointment).options(
        joinedload(Appointment.patient)
    ).filter(
        Appointment.scheduled_date >= today_start,
        Appointment.scheduled_date <= today_end,
        Appointment.status.in_([
            AppointmentStatus.CHECKED_IN.value,
            AppointmentStatus.IN_PROGRESS.value
        ]),
        Appointment.is_active == True
    )
    
    # Add search filter for patient name or patient number
    if search:
        search_term = f"%{search.strip()}%"
        query = query.join(Patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term)
            )
        )
    
    # Filter by assigned clinician if show_assigned_only is True
    if show_assigned_only:
        query = query.filter(Appointment.assigned_clinician_id == current_user.id)
    elif not show_assigned_only:
        # Show all checked-in appointments (doctor can see all)
        pass
    
    # Filter by department if provided
    if department:
        query = query.filter(Appointment.department == department)
    
    appointments = query.order_by(
        Appointment.priority.asc(),
        Appointment.scheduled_date.asc()
    ).all()
    
    # NEW WORKFLOW: Also get patients with encounters (created by nurses) that need doctor attention
    # These are encounters in progress or detained that don't have completed status
    encounters_query = db.query(Encounter).options(
        joinedload(Encounter.patient),
        joinedload(Encounter.appointment)
    ).filter(
        Encounter.status.in_([
            EncounterStatus.IN_PROGRESS.value,
            EncounterStatus.DETAINED.value
        ]),
        Encounter.is_active == True,
        func.date(Encounter.encounter_date) == today
    )
    
    # Add search filter for encounters
    if search:
        search_term = f"%{search.strip()}%"
        encounters_query = encounters_query.join(Patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term)
            )
        )
    
    encounters_needing_doctor = encounters_query.order_by(Encounter.encounter_date.asc()).all()
    
    # Get all currently admitted patients (exclude them from queue)
    from app.models.ipd_models import AdmissionStatus
    admitted_patients = db.query(Admission).filter(
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).all()
    admitted_patient_ids = {admission.patient_id for admission in admitted_patients}
    
    # Filter out appointments for admitted patients
    appointments = [appt for appt in appointments if appt.patient_id not in admitted_patient_ids]
    
    # Filter out encounters for admitted patients
    encounters_needing_doctor = [enc for enc in encounters_needing_doctor if enc.patient_id not in admitted_patient_ids]
    
    # Check which patients already have encounters from appointments
    patient_ids = [appt.patient_id for appt in appointments]
    existing_encounters = db.query(Encounter).filter(
        Encounter.patient_id.in_(patient_ids),
        Encounter.status.in_([
            EncounterStatus.IN_PROGRESS.value,
            EncounterStatus.DETAINED.value
        ]),
        Encounter.is_active == True,
        func.date(Encounter.encounter_date) == today
    ).all()
    
    encounter_map = {enc.patient_id: enc for enc in existing_encounters}
    
    # Enrich appointments with encounter info, wait time, and triage level
    queue_items = []
    appointment_patient_ids = set()
    from app.models.triage_models import TriageVitals
    from app.services.triage_level_calculator import get_triage_level_priority
    
    for appointment in appointments:
        appointment_patient_ids.add(appointment.patient_id)
        has_encounter = appointment.patient_id in encounter_map
        wait_time = appointment_crud.calculate_wait_time(appointment)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        
        # Get most recent vitals with triage level for this patient
        latest_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == appointment.patient_id
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        triage_level = latest_vitals.triage_level if latest_vitals else None
        triage_category = latest_vitals.triage_category if latest_vitals else None
        triage_priority = get_triage_level_priority(triage_level)
        
        queue_items.append({
            "appointment": appointment,
            "has_encounter": has_encounter,
            "encounter": encounter_map.get(appointment.patient_id),
            "type": "appointment",
            "wait_time": wait_time,
            "wait_time_str": wait_time_str,
            "triage_level": triage_level,
            "triage_category": triage_category,
            "triage_priority": triage_priority
        })
    
    # Sort queue items by triage level first (P1 > P2 > P3), then by arrival time
    queue_items.sort(key=lambda x: (x.get("triage_priority", 4), x["appointment"].checked_in_at or x["appointment"].scheduled_date))
    
    # Add patients with encounters but no appointments (from nurse workflow)
    for encounter in encounters_needing_doctor:
        if encounter.patient_id not in appointment_patient_ids:
            # Calculate wait time from encounter date
            wait_time = None
            wait_time_str = "N/A"
            if encounter.encounter_date:
                wait_time = datetime.now() - encounter.encounter_date
                wait_time_str = appointment_crud.format_wait_time(wait_time)
            queue_items.append({
                "appointment": None,
                "has_encounter": True,
                "encounter": encounter,
                "type": "encounter_only",
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
    
    # Get unfulfilled queues from previous days
    previous_appointments = appointment_crud.get_unfulfilled_queues_previous_days(
        db, department, search, days_back=7
    )
    
    # Filter previous appointments to only CHECKED_IN or IN_PROGRESS
    previous_appointments = [
        appt for appt in previous_appointments 
        if appt.status.value in [AppointmentStatus.CHECKED_IN.value, AppointmentStatus.IN_PROGRESS.value]
    ]
    
    # Filter out admitted patients from previous queues
    previous_appointments = [appt for appt in previous_appointments if appt.patient_id not in admitted_patient_ids]
    
    # Calculate wait times for previous day queues
    queue_previous = []
    for appointment in previous_appointments:
        wait_time = appointment_crud.calculate_wait_time(appointment)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        queue_previous.append({
            "appointment": appointment,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Get unique departments for filter
    departments = db.query(Appointment.department).distinct().all()
    departments = [d[0] for d in departments]
    
    context = {
        "request": request,
        "title": "Doctor Queue",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "queue_items": queue_items,
        "queue_previous": queue_previous,
        "departments": departments,
        "selected_department": department,
        "show_assigned_only": show_assigned_only,
        "search": search
    }
    return templates.TemplateResponse("doctor/queue.html", context)

