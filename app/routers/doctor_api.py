"""
Doctor API Routes

Routes for doctor/clinician-specific functionality:
- Doctor queue (patients assigned to doctor)
- Doctor dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta, date

from app.db.database import get_db
from app.core.deps import get_current_user, role_required, permission_required
from app.models.user_models import User
from app.models.appointment_models import OPDQueue, QueueStatus
from app.models.scheduled_appointment_models import ScheduledAppointment
from app.models.encounter_models import Encounter, EncounterStatus
from app.models.patient_models import Patient
from app.crud import appointment_crud, encounter_crud

router = APIRouter(
    prefix="/doctor",
    tags=["Doctor"]
)



@router.get("/dashboard", name="doctor_dashboard", dependencies=[Depends(permission_required("doctor_dashboard"))])
def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    start_date: Optional[str] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (YYYY-MM-DD)")
):
    """Doctor dashboard with patient queue, pending encounters, lab results, and statistics"""
    from datetime import datetime, date
    from app.models.scheduled_appointment_models import ScheduledAppointmentStatus
    from app.models.encounter_models import EncounterStatus, OrderStatus
    from app.models.ipd_models import Admission, AdmissionStatus
    from app.models.encounter_models import LabOrder, RadiologyOrder
    from app.models.triage_models import TriageVitals
    
    # Handle date range filtering
    if start_date and end_date:
        try:
            filter_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            filter_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            filter_start = date.today()
            filter_end = date.today()
    else:
        filter_start = date.today()
        filter_end = date.today()
    
    filter_start_datetime = datetime.combine(filter_start, datetime.min.time())
    filter_end_datetime = datetime.combine(filter_end, datetime.max.time())
    today = date.today()
    today_start = filter_start_datetime
    today_end = filter_end_datetime
    
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
    assigned_appointments = db.query(ScheduledAppointment).options(
        joinedload(ScheduledAppointment.patient)
    ).filter(
        ScheduledAppointment.assigned_doctor_id == current_user.id,
        ScheduledAppointment.scheduled_date >= today_start,
        ScheduledAppointment.scheduled_date <= today_end,
        ScheduledAppointment.status.in_([
            ScheduledAppointmentStatus.CHECKED_IN.value,
            ScheduledAppointmentStatus.IN_PROGRESS.value
        ]),
        ScheduledAppointment.is_active == True
    ).order_by(
        ScheduledAppointment.priority.asc(),
        ScheduledAppointment.scheduled_date.asc()
    ).all()
    
    # Filter out admitted patients from assigned appointments
    assigned_appointments = [appt for appt in assigned_appointments if appt.patient_id not in admitted_patient_ids]
    
    # Get all checked-in appointments for doctor's department (if not assigned)
    # Or all checked-in appointments if doctor has no specific department
    department_appointments = db.query(ScheduledAppointment).options(
        joinedload(ScheduledAppointment.patient)
    ).filter(
        ScheduledAppointment.scheduled_date >= today_start,
        ScheduledAppointment.scheduled_date <= today_end,
        ScheduledAppointment.status == ScheduledAppointmentStatus.CHECKED_IN.value,
        ScheduledAppointment.is_active == True
    ).order_by(
        ScheduledAppointment.priority.asc(),
        ScheduledAppointment.scheduled_date.asc()
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
    
    # ==========================================
    # NEW: Pending Lab Results for Doctor
    # ==========================================
    pending_lab_results = db.query(LabOrder).options(
        joinedload(LabOrder.patient),
        joinedload(LabOrder.ordered_by)
    ).filter(
        LabOrder.ordered_by_id == current_user.id,
        LabOrder.status == OrderStatus.COMPLETED.value,
        LabOrder.result_status.in_(['SUBMITTED', 'VERIFIED'])
    ).order_by(LabOrder.completed_at.desc()).limit(10).all()
    
    pending_lab_count = db.query(LabOrder).filter(
        LabOrder.ordered_by_id == current_user.id,
        LabOrder.status == OrderStatus.COMPLETED.value,
        LabOrder.result_status.in_(['SUBMITTED', 'VERIFIED'])
    ).count()
    
    # ==========================================
    # NEW: Recent Patient History
    # ==========================================
    recent_encounters = db.query(Encounter).options(
        joinedload(Encounter.patient)
    ).filter(
        Encounter.clinician_id == current_user.id,
        Encounter.is_active == True
    ).order_by(Encounter.encounter_date.desc()).limit(5).all()
    
    recent_patients = []
    seen_patient_ids = set()
    for enc in recent_encounters:
        if enc.patient_id not in seen_patient_ids:
            seen_patient_ids.add(enc.patient_id)
            recent_patients.append({
                "encounter": enc,
                "patient": enc.patient
            })
    
    # ==========================================
    # NEW: Patient Vitals Summary for Queue Patients
    # ==========================================
    # Get patient IDs from various sources
    all_patient_ids = set()
    for appt in assigned_appointments:
        all_patient_ids.add(appt.patient_id)
    for enc in pending_encounters:
        all_patient_ids.add(enc.patient_id)
    for appt in department_appointments:
        all_patient_ids.add(appt.patient_id)
    
    # Get latest vitals for each patient
    patient_vitals_map = {}
    for pid in all_patient_ids:
        latest_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == pid
        ).order_by(TriageVitals.recorded_at.desc()).first()
        if latest_vitals:
            patient_vitals_map[pid] = {
                "blood_pressure": f"{latest_vitals.systolic_bp}/{latest_vitals.diastolic_bp}" if latest_vitals.systolic_bp and latest_vitals.diastolic_bp else None,
                "heart_rate": latest_vitals.heart_rate,
                "temperature": latest_vitals.temperature,
                "respiratory_rate": latest_vitals.respiratory_rate,
                "oxygen_saturation": latest_vitals.oxygen_saturation,
                "triage_level": latest_vitals.triage_level,
                "recorded_at": latest_vitals.recorded_at
            }
    
    # ==========================================
    # NEW: Weekly Statistics
    # ==========================================
    # Get last 7 days of encounter data
    week_ago = today - timedelta(days=7)
    weekly_encounters = db.query(
        func.date(Encounter.encounter_date).label('date'),
        func.count(Encounter.id).label('count')
    ).filter(
        Encounter.clinician_id == current_user.id,
        Encounter.is_active == True,
        func.date(Encounter.encounter_date) >= week_ago,
        func.date(Encounter.encounter_date) <= today
    ).group_by(func.date(Encounter.encounter_date)).all()
    
    # Format for chart
    weekly_stats = {}
    for i in range(7):
        day = today - timedelta(days=6-i)
        weekly_stats[day.strftime('%Y-%m-%d')] = 0
    for date_obj, count in weekly_encounters:
        if date_obj:
            weekly_stats[date_obj.strftime('%Y-%m-%d')] = count
    
    # Calculate totals
    total_encounters_week = sum(weekly_stats.values())
    
    # For new vs follow-up, we'll check if patient has previous encounters
    # This is a simplified approach - checking if this is first encounter for each patient this week
    new_patients_this_week = 0
    followup_patients_this_week = 0
    
    # Get unique patients seen this week
    patients_this_week = db.query(Encounter.patient_id).filter(
        Encounter.clinician_id == current_user.id,
        Encounter.is_active == True,
        func.date(Encounter.encounter_date) >= week_ago,
        func.date(Encounter.encounter_date) <= today
    ).distinct().all()
    
    for (patient_id,) in patients_this_week:
        # Check if patient has any previous encounters
        previous_encounter = db.query(Encounter).filter(
            Encounter.clinician_id == current_user.id,
            Encounter.patient_id == patient_id,
            Encounter.is_active == True,
            func.date(Encounter.encounter_date) < week_ago
        ).first()
        
        if previous_encounter:
            followup_patients_this_week += 1
        else:
            new_patients_this_week += 1
    
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
        "current_admissions": admissions_with_stay_days,
        "admissions_count": len(current_admissions),
        # New data for enhanced dashboard
        "pending_lab_results": pending_lab_results,
        "pending_lab_count": pending_lab_count,
        "recent_patients": recent_patients,
        "patient_vitals_map": patient_vitals_map,
        "weekly_stats": weekly_stats,
        "total_encounters_week": total_encounters_week,
        "new_patients_this_week": new_patients_this_week,
        "followup_patients_this_week": followup_patients_this_week,
        "filter_start": filter_start.strftime('%Y-%m-%d'),
        "filter_end": filter_end.strftime('%Y-%m-%d')
    }
    return templates.TemplateResponse("doctor/dashboard.html", context)


@router.get("/queue", name="doctor_queue", dependencies=[Depends(permission_required("doctor_queue"))])
def doctor_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    department: Optional[str] = Query(None),
    show_assigned_only: Optional[bool] = Query(False),
    search: Optional[str] = Query(None, description="Search by patient name or patient number")
):
    """Doctor queue - patients in OPD queue ready to see doctor"""
    from datetime import datetime, date
    from app.models.appointment_models import OPDQueue, QueueStatus
    from app.models.encounter_models import Encounter, EncounterStatus
    from app.models.ipd_models import Admission
    from sqlalchemy.orm import joinedload
    
    today = date.today()
    
    # Build query for queue entries — only show patients checked in after vitals (consciously added to doctor queue)
    # Patients in vitals/triage queue (checked_in_at=None) do NOT appear until nurse records vitals and checks them in
    query = db.query(OPDQueue).options(
        joinedload(OPDQueue.patient)
    ).filter(
        func.date(OPDQueue.created_at) == today,
        OPDQueue.status.in_([
            QueueStatus.WAITING.value,
            QueueStatus.IN_PROGRESS.value
        ]),
        OPDQueue.is_active == True,
        OPDQueue.checked_in_at.isnot(None)  # Only patients checked in after vitals (ready for doctor)
    )
    
    # Add search filter for patient name or patient number
    if search:
        search_term = f"%{search.strip()}%"
        query = query.join(OPDQueue.patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term)
            )
        )
    
    # Filter by assigned clinician if show_assigned_only is True
    if show_assigned_only:
        query = query.filter(OPDQueue.assigned_clinician_id == current_user.id)
    
    # Filter by department if provided
    if department:
        query = query.filter(OPDQueue.department == department)
    
    queue_entries = query.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc(),
        OPDQueue.created_at.asc()
    ).all()
    
    # Also get patients with encounters (created by nurses) that need doctor attention
    encounters_query = db.query(Encounter).options(
        joinedload(Encounter.patient),
        joinedload(Encounter.queue_entry)
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
        encounters_query = encounters_query.join(Encounter.patient).filter(
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
    
    # Filter out queue entries for admitted patients
    queue_entries = [entry for entry in queue_entries if entry.patient_id not in admitted_patient_ids]
    
    # Filter out encounters for admitted patients
    encounters_needing_doctor = [enc for enc in encounters_needing_doctor if enc.patient_id not in admitted_patient_ids]
    
    # Check which patients already have encounters from queue entries
    patient_ids = [entry.patient_id for entry in queue_entries]
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
    
    # Enrich queue entries with encounter info, wait time, and triage level
    queue_items = []
    queue_patient_ids = set()
    from app.models.triage_models import TriageVitals
    from app.services.triage_level_calculator import get_triage_level_priority
    
    for queue_entry in queue_entries:
        queue_patient_ids.add(queue_entry.patient_id)
        has_encounter = queue_entry.patient_id in encounter_map
        wait_time = datetime.now() - queue_entry.created_at
        wait_time_str = f"{wait_time.seconds // 3600}h {(wait_time.seconds % 3600) // 60}m" if wait_time.seconds > 0 else "Just now"
        
        # Get most recent vitals with triage level for this patient
        latest_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == queue_entry.patient_id
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        triage_level = latest_vitals.triage_level if latest_vitals else None
        triage_category = latest_vitals.triage_category if latest_vitals else None
        triage_priority = get_triage_level_priority(triage_level)
        
        queue_items.append({
            "queue_entry": queue_entry,
            "has_encounter": has_encounter,
            "encounter": encounter_map.get(queue_entry.patient_id),
            "type": "queue",
            "wait_time": wait_time,
            "wait_time_str": wait_time_str,
            "triage_level": triage_level,
            "triage_category": triage_category,
            "triage_priority": triage_priority
        })
    
    # Sort queue items by triage level first (P1 > P2 > P3), then by priority and queue number
    queue_items.sort(key=lambda x: (
        x.get("triage_priority", 4), 
        x["queue_entry"].priority,
        x["queue_entry"].queue_number or 999
    ))
    
    # Add patients with encounters but no queue entries (from nurse workflow)
    for encounter in encounters_needing_doctor:
        if encounter.patient_id not in queue_patient_ids:
            # Calculate wait time from encounter date
            wait_time = None
            wait_time_str = "N/A"
            if encounter.encounter_date:
                wait_time = datetime.now() - encounter.encounter_date
                wait_time_str = f"{wait_time.seconds // 3600}h {(wait_time.seconds % 3600) // 60}m" if wait_time.seconds > 0 else "Just now"
            queue_items.append({
                "queue_entry": None,
                "has_encounter": True,
                "encounter": encounter,
                "type": "encounter_only",
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
    
    # Get unfulfilled queues from previous days
    from datetime import timedelta
    previous_date = date.today() - timedelta(days=7)
    previous_queue_query = db.query(OPDQueue).filter(
        OPDQueue.is_active == True,
        OPDQueue.status.in_([QueueStatus.WAITING, QueueStatus.IN_PROGRESS]),
        func.date(OPDQueue.created_at) >= previous_date,
        func.date(OPDQueue.created_at) < today
    )
    
    if department:
        previous_queue_query = previous_queue_query.filter(OPDQueue.department == department)
    
    previous_queue_entries = previous_queue_query.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc(),
        OPDQueue.created_at.asc()
    ).all()
    
    # Filter out admitted patients from previous queues
    previous_queue_entries = [entry for entry in previous_queue_entries if entry.patient_id not in admitted_patient_ids]
    
    # Calculate wait times for previous day queues
    queue_previous = []
    for queue_entry in previous_queue_entries:
        wait_time = datetime.now() - queue_entry.created_at
        wait_time_str = f"{wait_time.days}d {wait_time.seconds // 3600}h" if wait_time.days > 0 else f"{wait_time.seconds // 3600}h {(wait_time.seconds % 3600) // 60}m"
        queue_previous.append({
            "queue_entry": queue_entry,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Get unique departments for filter
    departments = db.query(OPDQueue.department).distinct().all()
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

