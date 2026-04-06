from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from app.models.appointment_models import OPDQueue, QueueStatus, VisitType
from app.schemas.appointment_schemas import QueueCreate, QueueUpdate, AppointmentCreate, AppointmentUpdate
from app.models.scheduled_appointment_models import ScheduledAppointment, AppointmentStatus, AppointmentType
from app.models.patient_models import Patient
from app.models.triage_models import TriageVitals


def create_queue_entry(db: Session, queue_data: QueueCreate) -> OPDQueue:
    """Creates a new queue entry and assigns a queue number"""
    
    # Get the next queue number for the department today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    
    # Count existing queue entries for the department today
    existing_count = db.query(func.count(OPDQueue.id)).filter(
        OPDQueue.department == queue_data.department,
        OPDQueue.created_at >= today_start,
        OPDQueue.created_at <= today_end,
        OPDQueue.is_active == True
    ).scalar() or 0
    
    # Assign next queue number
    queue_number = existing_count + 1
    
    # Create queue entry
    queue_entry = OPDQueue(
        patient_id=queue_data.patient_id,
        department=queue_data.department,
        department_type=queue_data.department_type,
        visit_type=queue_data.visit_type,
        priority=queue_data.priority,
        chief_complaint=queue_data.chief_complaint,
        notes=queue_data.notes,
        assigned_clinician_id=queue_data.assigned_clinician_id,
        queue_number=queue_number,
        created_by_id=queue_data.created_by_id
    )
    
    db.add(queue_entry)
    db.commit()
    db.refresh(queue_entry)
    
    return queue_entry


def generate_queue_number(db: Session, department: str) -> int:
    """Generate next queue number for department today"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    
    existing_count = db.query(func.count(OPDQueue.id)).filter(
        OPDQueue.department == department,
        OPDQueue.created_at >= today_start,
        OPDQueue.created_at <= today_end,
        OPDQueue.is_active == True
    ).scalar() or 0
    
    return existing_count + 1


def get_queue_entry(db: Session, queue_id: int) -> Optional[OPDQueue]:
    """Retrieves a single queue entry by ID"""
    return db.query(OPDQueue).filter(
        OPDQueue.id == queue_id,
        OPDQueue.is_active == True
    ).first()


def get_queue_entries_by_patient(db: Session, patient_id: int) -> List[OPDQueue]:
    """Retrieves all queue entries for a specific patient"""
    return db.query(OPDQueue).filter(
        OPDQueue.patient_id == patient_id,
        OPDQueue.is_active == True
    ).order_by(desc(OPDQueue.created_at)).all()


def get_queue_entries_by_department(
    db: Session, 
    department: str,
    status: Optional[QueueStatus] = None,
    date: Optional[datetime] = None
) -> List[OPDQueue]:
    """Retrieves queue entries for a department, optionally filtered by status and date"""
    query = db.query(OPDQueue).filter(
        OPDQueue.department == department,
        OPDQueue.is_active == True
    )
    
    if status:
        query = query.filter(OPDQueue.status == status)
    
    if date:
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start.replace(hour=23, minute=59, second=59)
        query = query.filter(
            OPDQueue.created_at >= date_start,
            OPDQueue.created_at <= date_end
        )
    
    return query.order_by(OPDQueue.created_at.asc()).all()


def calculate_wait_time(queue_entry: OPDQueue) -> Optional[timedelta]:
    """Calculate how long a patient has been waiting in the queue"""
    if not queue_entry:
        return None
    
    # Use checked_in_at if available, otherwise use created_at
    start_time = queue_entry.checked_in_at or queue_entry.created_at
    if not start_time:
        return None
    
    return datetime.now() - start_time


def format_wait_time(wait_time: Optional[timedelta]) -> str:
    """Format wait time as a human-readable string"""
    if not wait_time:
        return "N/A"
    
    total_seconds = int(wait_time.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return "< 1m"


def get_unfulfilled_queues_previous_days(
    db: Session, 
    department: Optional[str] = None, 
    search: Optional[str] = None,
    days_back: int = 7
) -> List[OPDQueue]:
    """Gets unfulfilled queues from previous days (not completed or cancelled)"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=days_back)
    
    query = db.query(OPDQueue).options(joinedload(OPDQueue.patient)).filter(
        OPDQueue.created_at >= start_date,
        OPDQueue.created_at < today,
        OPDQueue.is_active == True,
        OPDQueue.status.in_([
            QueueStatus.WAITING,
            QueueStatus.IN_PROGRESS
        ])
    )
    
    if department:
        query = query.filter(OPDQueue.department == department)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.join(OPDQueue.patient).filter(
            or_(
                OPDQueue.patient.first_name.ilike(search_pattern),
                OPDQueue.patient.last_name.ilike(search_pattern),
                OPDQueue.patient.patient_number.ilike(search_pattern),
                OPDQueue.patient.phone_number.ilike(search_pattern)
            )
        )
    
    return query.order_by(OPDQueue.created_at.asc()).all()


def get_queue_today(db: Session, department: Optional[str] = None, search: Optional[str] = None) -> List[OPDQueue]:
    """Gets today's queue, optionally filtered by department and patient search"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today.replace(hour=23, minute=59, second=59)
    
    query = db.query(OPDQueue).options(joinedload(OPDQueue.patient)).filter(
        OPDQueue.created_at >= today,
        OPDQueue.created_at <= today_end,
        OPDQueue.is_active == True,
        OPDQueue.status.in_([
            QueueStatus.WAITING,
            QueueStatus.IN_PROGRESS
        ])
    )
    
    if department:
        query = query.filter(OPDQueue.department == department)
    
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.join(OPDQueue.patient).filter(
            or_(
                OPDQueue.patient.first_name.ilike(search_pattern),
                OPDQueue.patient.last_name.ilike(search_pattern),
                func.concat(OPDQueue.patient.first_name, " ", OPDQueue.patient.last_name).ilike(search_pattern),
                OPDQueue.patient.patient_number.ilike(search_pattern),
                OPDQueue.patient.phone_number.ilike(search_pattern)
            )
        )
    
    return query.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc(),
        OPDQueue.created_at.asc()
    ).all()


def update_queue_entry(
    db: Session, 
    queue_id: int, 
    queue_update: QueueUpdate
) -> Optional[OPDQueue]:
    """Updates a queue entry"""
    db_queue = get_queue_entry(db, queue_id)
    if not db_queue:
        return None
    
    update_data = queue_update.model_dump(exclude_unset=True)
    
    # Handle status changes with timestamps
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == QueueStatus.IN_PROGRESS and not db_queue.started_at:
            update_data["started_at"] = datetime.now()
        elif new_status == QueueStatus.COMPLETED and not db_queue.completed_at:
            update_data["completed_at"] = datetime.now()
    
    for key, value in update_data.items():
        setattr(db_queue, key, value)
    
    db.commit()
    db.refresh(db_queue)
    return db_queue


def cancel_queue_entry(db: Session, queue_id: int) -> Optional[OPDQueue]:
    """Cancels a queue entry"""
    db_queue = get_queue_entry(db, queue_id)
    if not db_queue:
        return None
    
    db_queue.status = QueueStatus.CANCELLED
    db.commit()
    db.refresh(db_queue)
    return db_queue


def get_recent_checked_in_queue_entry(
    db: Session,
    patient_id: int,
    within_hours: int = 12
) -> Optional[OPDQueue]:
    """Fetch the most recent queue entry that has been checked in (or is in progress)."""
    threshold = datetime.now() - timedelta(hours=within_hours)
    return (
        db.query(OPDQueue)
        .filter(
            OPDQueue.patient_id == patient_id,
            OPDQueue.is_active == True,
            OPDQueue.status.in_([
                QueueStatus.WAITING,
                QueueStatus.IN_PROGRESS
            ]),
            OPDQueue.created_at >= threshold
        )
        .order_by(OPDQueue.created_at.desc())
        .first()
    )


# Scheduled Appointment functions
def create_appointment(db: Session, appointment_data: AppointmentCreate) -> ScheduledAppointment:
    """Creates a new scheduled appointment"""
    appointment = ScheduledAppointment(
        patient_id=appointment_data.patient_id,
        department=appointment_data.department,
        assigned_doctor_id=appointment_data.assigned_clinician_id or appointment_data.created_by_id,
        scheduled_date=appointment_data.scheduled_date or datetime.now(),
        appointment_type=appointment_data.appointment_type or AppointmentType.WALK_IN,
        reason_complaint=appointment_data.chief_complaint,
        notes=appointment_data.notes,
        priority=appointment_data.priority,
        status=AppointmentStatus.SCHEDULED,
        created_by_id=appointment_data.created_by_id
    )
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    return appointment


def get_appointment(db: Session, appointment_id: int) -> Optional[ScheduledAppointment]:
    """Retrieves a single appointment by ID"""
    return db.query(ScheduledAppointment).filter(
        ScheduledAppointment.id == appointment_id,
        ScheduledAppointment.is_active == True
    ).first()


def update_appointment(
    db: Session, 
    appointment_id: int, 
    appointment_update: AppointmentUpdate
) -> Optional[ScheduledAppointment]:
    """Updates an appointment"""
    db_appointment = get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    update_data = appointment_update.model_dump(exclude_unset=True)
    
    # Handle status changes with timestamps
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == AppointmentStatus.COMPLETED and not db_appointment.completed_at:
            update_data["completed_at"] = datetime.now()
    
    for key, value in update_data.items():
        setattr(db_appointment, key, value)
    
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def get_appointments_by_patient(db: Session, patient_id: int) -> List[ScheduledAppointment]:
    """Retrieves all appointments for a specific patient"""
    return db.query(ScheduledAppointment).filter(
        ScheduledAppointment.patient_id == patient_id,
        ScheduledAppointment.is_active == True
    ).order_by(desc(ScheduledAppointment.scheduled_date)).all()


def auto_clear_stale_vitals_queue(
    db: Session, 
    hours_threshold: int = 48,
    dry_run: bool = False
) -> Tuple[int, List[dict]]:
    """
    Auto-clear patients from vitals queue who have not had vitals recorded 
    after a specified time threshold (default 48 hours).
    
    This function:
    1. Finds queue entries where status is WAITING or IN_PROGRESS
    2. Checks if the queue entry is older than the threshold (default 48 hours)
    3. Checks if any vitals were recorded for that patient after the queue entry was created
    4. If no vitals recorded, marks the queue entry as NO_SHOW
    
    Args:
        db: Database session
        hours_threshold: Hours after which to clear stale entries (default 48)
        dry_run: If True, only return the entries that would be cleared without actually clearing them
    
    Returns:
        Tuple of (count of cleared entries, list of details)
    """
    from datetime import datetime, timedelta
    
    # Calculate the threshold time
    threshold_time = datetime.now() - timedelta(hours=hours_threshold)
    
    # Find all active queue entries that are WAITING or IN_PROGRESS
    # and were created before the threshold
    stale_queue_entries = db.query(OPDQueue).options(
        joinedload(OPDQueue.patient)
    ).filter(
        OPDQueue.created_at < threshold_time,
        OPDQueue.status.in_([
            QueueStatus.WAITING.value,
            QueueStatus.IN_PROGRESS.value
        ]),
        OPDQueue.is_active == True
    ).all()
    
    cleared_entries = []
    cleared_count = 0
    
    for queue_entry in stale_queue_entries:
        # Check if any vitals were recorded for this patient after the queue entry was created
        vitals_recorded = db.query(TriageVitals).filter(
            TriageVitals.patient_id == queue_entry.patient_id,
            TriageVitals.recorded_at > queue_entry.created_at
        ).first()
        
        # If no vitals recorded after queue entry was created, mark as NO_SHOW
        if not vitals_recorded:
            entry_details = {
                "queue_id": queue_entry.id,
                "patient_id": queue_entry.patient_id,
                "patient_name": f"{queue_entry.patient.first_name} {queue_entry.patient.last_name}" if queue_entry.patient else "Unknown",
                "patient_number": queue_entry.patient.patient_number if queue_entry.patient else "Unknown",
                "created_at": queue_entry.created_at.isoformat() if queue_entry.created_at else None,
                "status": queue_entry.status.value,
                "department": queue_entry.department
            }
            
            if not dry_run:
                # Mark as NO_SHOW
                queue_entry.status = QueueStatus.NO_SHOW
                queue_entry.notes = (queue_entry.notes or "") + f" [Auto-cleared: No vitals recorded after {hours_threshold} hours]"
                db.commit()
                db.refresh(queue_entry)
            
            cleared_entries.append(entry_details)
            cleared_count += 1
    
    return cleared_count, cleared_entries

