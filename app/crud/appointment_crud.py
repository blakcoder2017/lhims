from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func, or_
from datetime import datetime
from typing import List, Optional
from app.models.appointment_models import Appointment, AppointmentStatus, AppointmentType
from app.schemas.appointment_schemas import AppointmentCreate, AppointmentUpdate
from app.models.patient_models import Patient


def create_appointment(db: Session, appointment: AppointmentCreate) -> Appointment:
    """Creates a new appointment and assigns a queue number"""
    
    # Get the next queue number for the department on the scheduled date
    scheduled_date_start = appointment.scheduled_date.replace(hour=0, minute=0, second=0, microsecond=0)
    scheduled_date_end = scheduled_date_start.replace(hour=23, minute=59, second=59)
    
    # Count existing appointments for the department on that day
    existing_count = db.query(func.count(Appointment.id)).filter(
        Appointment.department == appointment.department,
        Appointment.scheduled_date >= scheduled_date_start,
        Appointment.scheduled_date <= scheduled_date_end,
        Appointment.is_active == True
    ).scalar() or 0
    
    # Queue number is the count + 1
    queue_number = existing_count + 1
    
    db_appointment = Appointment(
        **appointment.model_dump(),
        queue_number=queue_number,
        status=AppointmentStatus.SCHEDULED
    )
    
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def get_appointment(db: Session, appointment_id: int) -> Optional[Appointment]:
    """Retrieves a single appointment by ID"""
    return db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.is_active == True
    ).first()


def get_appointments_by_patient(db: Session, patient_id: int) -> List[Appointment]:
    """Retrieves all appointments for a specific patient"""
    return db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.is_active == True
    ).order_by(desc(Appointment.scheduled_date)).all()


def get_appointments_by_department(
    db: Session, 
    department: str,
    status: Optional[AppointmentStatus] = None,
    date: Optional[datetime] = None
) -> List[Appointment]:
    """Retrieves appointments for a department, optionally filtered by status and date"""
    query = db.query(Appointment).filter(
        Appointment.department == department,
        Appointment.is_active == True
    )
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if date:
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start.replace(hour=23, minute=59, second=59)
        query = query.filter(
            Appointment.scheduled_date >= date_start,
            Appointment.scheduled_date <= date_end
        )
    
    return query.order_by(
        Appointment.priority.asc(),
        Appointment.queue_number.asc(),
        Appointment.scheduled_date.asc()
    ).all()


def get_queue_today(db: Session, department: Optional[str] = None, search: Optional[str] = None) -> List[Appointment]:
    """Gets today's queue, optionally filtered by department and patient search"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today.replace(hour=23, minute=59, second=59)
    
    query = db.query(Appointment).options(joinedload(Appointment.patient)).filter(
        Appointment.scheduled_date >= today,
        Appointment.scheduled_date <= today_end,
        Appointment.is_active == True,
        Appointment.status.in_([
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_PROGRESS
        ])
    )
    
    if department:
        query = query.filter(Appointment.department == department)
    
    if search:
        search_term = f"%{search.strip()}%"
        query = query.join(Patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term)
            )
        )
    
    return query.order_by(
        Appointment.priority.asc(),
        Appointment.queue_number.asc()
    ).all()


def update_appointment(
    db: Session, 
    appointment_id: int, 
    appointment_update: AppointmentUpdate
) -> Optional[Appointment]:
    """Updates an appointment"""
    db_appointment = get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    update_data = appointment_update.model_dump(exclude_unset=True)
    
    # Handle status changes with timestamps
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == AppointmentStatus.CHECKED_IN and not db_appointment.checked_in_at:
            update_data["checked_in_at"] = datetime.now()
        elif new_status == AppointmentStatus.IN_PROGRESS and not db_appointment.started_at:
            update_data["started_at"] = datetime.now()
        elif new_status == AppointmentStatus.COMPLETED and not db_appointment.completed_at:
            update_data["completed_at"] = datetime.now()
    
    for key, value in update_data.items():
        setattr(db_appointment, key, value)
    
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def cancel_appointment(db: Session, appointment_id: int) -> Optional[Appointment]:
    """Cancels an appointment"""
    db_appointment = get_appointment(db, appointment_id)
    if not db_appointment:
        return None
    
    db_appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

