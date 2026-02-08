"""
API routes for scheduled appointments management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.crud import scheduled_appointment_crud
from app.schemas import scheduled_appointment_schemas
from app.models.user_models import User
from app.models.scheduled_appointment_models import ScheduledAppointmentStatus

router = APIRouter(
    prefix="/api/v1/appointments",
    tags=["Scheduled Appointments"]
)


@router.post("/scheduled/create", status_code=status.HTTP_201_CREATED)
def create_scheduled_appointment(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"])),
    
    # Form fields for HTML form submission
    patient_id: Optional[int] = Form(None),
    patient_name: Optional[str] = Form(None),
    patient_phone: Optional[str] = Form(None),
    assigned_doctor_id: int = Form(...),
    appointment_date: str = Form(...),
    appointment_time: str = Form(...),
    duration_minutes: int = Form(30),
    reason_complaint: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    priority: int = Form(5)
):
    """Create a new scheduled appointment (HTML form endpoint)"""
    try:
        # Parse appointment date and time
        appointment_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        
        appointment_data = {
            "patient_id": patient_id if patient_id else None,
            "patient_name": patient_name.strip() if patient_name else None,
            "patient_phone": patient_phone.strip() if patient_phone else None,
            "assigned_doctor_id": assigned_doctor_id,
            "appointment_date": appointment_datetime,
            "duration_minutes": duration_minutes,
            "reason_complaint": reason_complaint.strip() if reason_complaint else None,
            "notes": notes.strip() if notes else None,
            "priority": priority
        }
        
        appointment = scheduled_appointment_crud.create_scheduled_appointment(
            db, appointment_data, current_user.id
        )
        
        # Appointment approved SMS - only if valid phone
        try:
            from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
            from app.models.patient_models import Patient
            phone_to_use = None
            name_to_use = None
            if appointment.patient_id:
                patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
                if patient and patient.phone_number and is_valid_phone(patient.phone_number):
                    phone_to_use = patient.phone_number
                    name_to_use = f"{patient.first_name} {patient.last_name}"
            elif appointment.patient_phone and is_valid_phone(appointment.patient_phone):
                phone_to_use = appointment.patient_phone
                name_to_use = appointment.patient_name or "Patient"
            if phone_to_use and name_to_use:
                dt_str = appointment.appointment_date.strftime("%Y-%m-%d %H:%M") if hasattr(appointment.appointment_date, "strftime") else str(appointment.appointment_date)
                msg = "Hello {$name}. Your appointment has been approved for {$date}. Please arrive on time. Thank you!"
                send_personalized_sms_notification(msg, [{"number": phone_to_use, "values": [name_to_use, dt_str]}])
        except Exception as e:
            print(f"Warning: Appointment approved SMS failed: {e}")
        
        return RedirectResponse(
            url=f"/appointments?success=created&appointment_id={appointment.id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except ValueError as e:
        return RedirectResponse(
            url="/appointments/create?error=validation&message=" + str(e),
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url="/appointments/create?error=server&message=Failed to create appointment",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/scheduled", response_model=List[scheduled_appointment_schemas.ScheduledAppointmentResponse])
def get_scheduled_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    doctor_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """Get scheduled appointments with optional filtering"""
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    try:
        status_enum = ScheduledAppointmentStatus(status) if status else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status}"
        )
    
    appointments = scheduled_appointment_crud.get_scheduled_appointments_for_date_range(
        db, start_date, end_date, doctor_id, status_enum
    )
    
    return appointments[:limit]


@router.get("/scheduled/{appointment_id}", response_model=scheduled_appointment_schemas.ScheduledAppointmentResponse)
def get_scheduled_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific scheduled appointment"""
    appointment = scheduled_appointment_crud.get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.put("/scheduled/{appointment_id}", response_model=scheduled_appointment_schemas.ScheduledAppointmentResponse)
def update_scheduled_appointment(
    appointment_id: int,
    update_data: scheduled_appointment_schemas.ScheduledAppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"]))
):
    """Update a scheduled appointment"""
    appointment = scheduled_appointment_crud.update_scheduled_appointment(
        db, appointment_id, update_data.dict(exclude_unset=True)
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.post("/scheduled/{appointment_id}/cancel", response_model=scheduled_appointment_schemas.ScheduledAppointmentResponse)
def cancel_scheduled_appointment(
    appointment_id: int,
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"]))
):
    """Cancel a scheduled appointment"""
    appointment = scheduled_appointment_crud.cancel_scheduled_appointment(
        db, appointment_id, current_user.id, reason
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.post("/scheduled/{appointment_id}/confirm", response_model=scheduled_appointment_schemas.ScheduledAppointmentResponse)
def confirm_scheduled_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"]))
):
    """Confirm a scheduled appointment"""
    appointment = scheduled_appointment_crud.confirm_scheduled_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.post("/scheduled/{appointment_id}/complete", response_model=scheduled_appointment_schemas.ScheduledAppointmentResponse)
def complete_scheduled_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Admin"]))
):
    """Mark a scheduled appointment as completed"""
    appointment = scheduled_appointment_crud.complete_scheduled_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    return appointment


@router.get("/scheduled/doctor/{doctor_id}", response_model=List[scheduled_appointment_schemas.ScheduledAppointmentResponse])
def get_doctor_appointments(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """Get scheduled appointments for a specific doctor"""
    appointments = scheduled_appointment_crud.get_scheduled_appointments_for_doctor(
        db, doctor_id, start_date, end_date
    )
    return appointments


@router.get("/scheduled/today", response_model=List[scheduled_appointment_schemas.ScheduledAppointmentResponse])
def get_today_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doctor_id: Optional[int] = Query(None)
):
    """Get today's scheduled appointments"""
    appointments = scheduled_appointment_crud.get_today_scheduled_appointments(db, doctor_id)
    return appointments


@router.get("/scheduled/upcoming", response_model=List[scheduled_appointment_schemas.ScheduledAppointmentResponse])
def get_upcoming_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doctor_id: Optional[int] = Query(None),
    days_ahead: int = Query(7, ge=1, le=30)
):
    """Get upcoming scheduled appointments"""
    appointments = scheduled_appointment_crud.get_upcoming_scheduled_appointments(
        db, doctor_id, days_ahead
    )
    return appointments


@router.get("/scheduled/search", response_model=List[scheduled_appointment_schemas.ScheduledAppointmentResponse])
def search_appointments(
    query: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doctor_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """Search scheduled appointments"""
    appointments = scheduled_appointment_crud.search_scheduled_appointments(
        db, query, limit, doctor_id
    )
    return appointments


@router.get("/scheduled/statistics", response_model=scheduled_appointment_schemas.AppointmentStatistics)
def get_appointment_statistics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doctor_id: Optional[int] = Query(None)
):
    """Get appointment statistics for a date range"""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    stats = scheduled_appointment_crud.get_appointment_statistics(
        db, start_date, end_date, doctor_id
    )
    return stats
