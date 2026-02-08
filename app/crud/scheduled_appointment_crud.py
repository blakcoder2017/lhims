"""
CRUD operations for scheduled appointments
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional, Tuple
from datetime import datetime, date, timedelta

from app.models.scheduled_appointment_models import ScheduledAppointment, ScheduledAppointmentStatus
from app.models.user_models import User
from app.models.patient_models import Patient


def create_scheduled_appointment(db: Session, appointment_data: dict, created_by_id: int) -> ScheduledAppointment:
    """Create a new scheduled appointment"""
    import logging
    logging.info(f"DEBUG CRUD: Creating appointment with data: {appointment_data}")
    appointment = ScheduledAppointment(
        patient_id=appointment_data.get("patient_id"),
        patient_name=appointment_data.get("patient_name"),
        patient_phone=appointment_data.get("patient_phone"),
        assigned_doctor_id=appointment_data["assigned_doctor_id"],
        appointment_date=appointment_data["appointment_date"],
        duration_minutes=appointment_data.get("duration_minutes", 30),
        reason_complaint=appointment_data.get("reason_complaint"),
        notes=appointment_data.get("notes"),
        priority=appointment_data.get("priority", 5),
        created_by_id=created_by_id
    )
    logging.info(f"DEBUG CRUD: Created appointment object: patient_id={appointment.patient_id}, assigned_doctor_id={appointment.assigned_doctor_id}")

    db.add(appointment)
    logging.info("DEBUG CRUD: Added to session")
    db.commit()
    logging.info("DEBUG CRUD: Committed")
    db.refresh(appointment)
    logging.info(f"DEBUG CRUD: Refreshed, appointment id: {appointment.id}")
    return appointment


def get_scheduled_appointment_by_id(db: Session, appointment_id: int) -> Optional[ScheduledAppointment]:
    """Get a scheduled appointment by ID"""
    from sqlalchemy.orm import joinedload
    return db.query(ScheduledAppointment).options(
        joinedload(ScheduledAppointment.assigned_doctor),
        joinedload(ScheduledAppointment.patient),
        joinedload(ScheduledAppointment.created_by),
        joinedload(ScheduledAppointment.cancelled_by),
        joinedload(ScheduledAppointment.encounters)
    ).filter(
        ScheduledAppointment.id == appointment_id,
        ScheduledAppointment.is_active == True
    ).first()


def get_scheduled_appointments_for_date_range(
    db: Session,
    start_date: date,
    end_date: date,
    doctor_id: Optional[int] = None,
    status: Optional[ScheduledAppointmentStatus] = None
) -> List[ScheduledAppointment]:
    """Get scheduled appointments within a date range"""
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload

    # Extract date from datetime for proper comparison
    query = db.query(ScheduledAppointment).options(
        joinedload(ScheduledAppointment.assigned_doctor),
        joinedload(ScheduledAppointment.patient)
    ).filter(
        func.date(ScheduledAppointment.scheduled_date) >= start_date,
        func.date(ScheduledAppointment.scheduled_date) <= end_date,
        ScheduledAppointment.is_active == True
    )

    if doctor_id:
        query = query.filter(ScheduledAppointment.assigned_doctor_id == doctor_id)

    if status:
        query = query.filter(ScheduledAppointment.status == status)

    return query.order_by(ScheduledAppointment.scheduled_date).all()


def get_scheduled_appointments_for_doctor(
    db: Session,
    doctor_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[ScheduledAppointment]:
    """Get scheduled appointments for a specific doctor"""
    from sqlalchemy.orm import joinedload
    query = db.query(ScheduledAppointment).options(
        joinedload(ScheduledAppointment.assigned_doctor),
        joinedload(ScheduledAppointment.patient)
    ).filter(
        ScheduledAppointment.assigned_doctor_id == doctor_id,
        ScheduledAppointment.is_active == True
    )

    if start_date:
        query = query.filter(ScheduledAppointment.scheduled_date >= start_date)
    if end_date:
        query = query.filter(ScheduledAppointment.scheduled_date <= end_date)

    return query.order_by(ScheduledAppointment.scheduled_date).all()


def get_today_scheduled_appointments(db: Session, doctor_id: Optional[int] = None) -> List[ScheduledAppointment]:
    """Get today's scheduled appointments"""
    today = date.today()
    return get_scheduled_appointments_for_date_range(
        db, today, today, doctor_id=doctor_id
    )


def get_upcoming_scheduled_appointments(
    db: Session, 
    doctor_id: Optional[int] = None,
    days_ahead: int = 7
) -> List[ScheduledAppointment]:
    """Get upcoming scheduled appointments for the next N days"""
    start_date = date.today()
    end_date = start_date + timedelta(days=days_ahead)
    
    return get_scheduled_appointments_for_date_range(
        db, start_date, end_date, doctor_id=doctor_id
    )


def update_scheduled_appointment(
    db: Session, 
    appointment_id: int, 
    update_data: dict
) -> Optional[ScheduledAppointment]:
    """Update a scheduled appointment"""
    appointment = get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    for field, value in update_data.items():
        if hasattr(appointment, field) and value is not None:
            setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_scheduled_appointment(
    db: Session, 
    appointment_id: int, 
    cancelled_by_id: int,
    reason: Optional[str] = None
) -> Optional[ScheduledAppointment]:
    """Cancel a scheduled appointment"""
    appointment = get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    appointment.status = ScheduledAppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.now()
    appointment.cancelled_by_id = cancelled_by_id
    
    if reason:
        appointment.notes = f"Cancelled: {reason}\n\n{appointment.notes or ''}"
    
    db.commit()
    db.refresh(appointment)
    return appointment


def complete_scheduled_appointment(db: Session, appointment_id: int) -> Optional[ScheduledAppointment]:
    """Mark a scheduled appointment as completed"""
    appointment = get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    appointment.status = ScheduledAppointmentStatus.COMPLETED
    appointment.completed_at = datetime.now()
    
    db.commit()
    db.refresh(appointment)
    return appointment


def confirm_scheduled_appointment(db: Session, appointment_id: int) -> Optional[ScheduledAppointment]:
    """Confirm a scheduled appointment"""
    appointment = get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    appointment.status = ScheduledAppointmentStatus.CONFIRMED
    
    db.commit()
    db.refresh(appointment)
    return appointment


def search_scheduled_appointments(
    db: Session,
    query: str,
    limit: int = 50,
    doctor_id: Optional[int] = None
) -> List[ScheduledAppointment]:
    """Search scheduled appointments by patient name or reason"""
    search_pattern = f"%{query}%"
    
    db_query = db.query(ScheduledAppointment).filter(
        or_(
            ScheduledAppointment.patient_name.ilike(search_pattern),
            ScheduledAppointment.reason_complaint.ilike(search_pattern),
            ScheduledAppointment.patient_phone.ilike(search_pattern)
        ),
        ScheduledAppointment.is_active == True
    )
    
    if doctor_id:
        db_query = db_query.filter(ScheduledAppointment.assigned_doctor_id == doctor_id)
    
    return db_query.limit(limit).all()


def get_appointment_statistics(
    db: Session,
    start_date: date,
    end_date: date,
    doctor_id: Optional[int] = None
) -> dict:
    """Get appointment statistics for a date range"""
    from sqlalchemy import func
    
    query = db.query(ScheduledAppointment).filter(
        func.date(ScheduledAppointment.scheduled_date) >= start_date,
        func.date(ScheduledAppointment.scheduled_date) <= end_date,
        ScheduledAppointment.is_active == True
    )
    
    if doctor_id:
        query = query.filter(ScheduledAppointment.assigned_doctor_id == doctor_id)
    
    total = query.count()
    scheduled = query.filter(ScheduledAppointment.status == ScheduledAppointmentStatus.SCHEDULED).count()
    confirmed = query.filter(ScheduledAppointment.status == ScheduledAppointmentStatus.CONFIRMED).count()
    completed = query.filter(ScheduledAppointment.status == ScheduledAppointmentStatus.COMPLETED).count()
    cancelled = query.filter(ScheduledAppointment.status == ScheduledAppointmentStatus.CANCELLED).count()
    no_show = query.filter(ScheduledAppointment.status == ScheduledAppointmentStatus.NO_SHOW).count()
    
    return {
        "total": total,
        "scheduled": scheduled,
        "confirmed": confirmed,
        "completed": completed,
        "cancelled": cancelled,
        "no_show": no_show,
        "completion_rate": (completed / total * 100) if total > 0 else 0,
        "cancellation_rate": (cancelled / total * 100) if total > 0 else 0
    }
