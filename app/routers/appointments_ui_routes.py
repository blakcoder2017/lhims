"""
UI routes for scheduled appointments management
"""
from fastapi import APIRouter, Request, Depends, Query, Form, HTTPException
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, timedelta

from app.db.database import get_db
from app.core.deps import get_current_user, role_required, permission_required
from app.crud import scheduled_appointment_crud
from app.crud import user_crud
from app.models.user_models import User
from app.models.scheduled_appointment_models import ScheduledAppointmentStatus

router = APIRouter(
    prefix="",
    tags=["Appointments UI"]
)



@router.get("/appointments", name="manage_appointments")
def appointments_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"])),
    date_filter: Optional[str] = Query(None),
    doctor_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None)
):
    """Main appointments management dashboard"""
    # Parse date filter
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            filter_date = date.today()
    else:
        filter_date = date.today()
    
    # Convert doctor_filter to int if provided
    doctor_id = None
    if doctor_filter:
        try:
            doctor_id = int(doctor_filter)
        except ValueError:
            doctor_id = None
    
    # Get appointments for the selected date
    start_date = filter_date
    end_date = filter_date
    
    # Parse status filter
    status_enum = None
    if status_filter:
        try:
            status_enum = ScheduledAppointmentStatus(status_filter)
        except ValueError:
            pass  # Invalid status, ignore filter
    
    appointments = scheduled_appointment_crud.get_scheduled_appointments_for_date_range(
        db, start_date, end_date, doctor_id, status_enum
    )
    
    # Get doctors for filter dropdown
    doctors = user_crud.get_doctors(db)
    
    # Get statistics
    stats = scheduled_appointment_crud.get_appointment_statistics(
        db, start_date, end_date, doctor_id
    )
    
    context = {
        "request": request,
        "title": "Appointments Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "appointments": appointments,
        "doctors": doctors,
        "selected_date": filter_date,
        "selected_doctor": doctor_filter,
        "selected_status": status_filter,
        "statistics": stats,
        "status_options": [
            {"value": "", "label": "All Status"},
            {"value": "scheduled", "label": "Scheduled"},
            {"value": "confirmed", "label": "Confirmed"},
            {"value": "completed", "label": "Completed"},
            {"value": "cancelled", "label": "Cancelled"},
            {"value": "no_show", "label": "No Show"}
        ]
    }
    
    return templates.TemplateResponse("appointments/appointments_dashboard.html", context)


@router.get("/appointments/create", name="create_appointment")
def create_appointment_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"])),
    patient_id: Optional[int] = Query(None)
):
    """Page to create a new scheduled appointment"""
    # Get doctors for assignment
    doctors_tuple = user_crud.get_doctors(db)
    doctors = doctors_tuple[0] if isinstance(doctors_tuple, tuple) else doctors_tuple
    
    # Get all active patients for dropdown
    from app.crud import patient_crud
    patients_tuple = patient_crud.search_patients(db, limit=100)
    patients = patients_tuple[0] if isinstance(patients_tuple, tuple) else patients_tuple
    
    # Pre-fill patient info if provided
    patient = None
    if patient_id:
        patient = patient_crud.get_patient(db, patient_id)
    
    context = {
        "request": request,
        "title": "Create Appointment",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "doctors": doctors,
        "patients": patients,
        "patient": patient,
        "default_duration": 30,
        "min_date": date.today().strftime("%Y-%m-%d"),
        "max_date": (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
    }
    
    return templates.TemplateResponse("appointments/create_appointment.html", context)


@router.get("/appointments/{appointment_id}", name="view_appointment")
def view_appointment(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """View appointment details"""
    appointment = scheduled_appointment_crud.get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    context = {
        "request": request,
        "title": f"Appointment - {appointment.patient_name or 'Patient'}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "appointment": appointment
    }
    
    return templates.TemplateResponse("appointments/view_appointment.html", context)


@router.get("/appointments/{appointment_id}/edit", name="edit_appointment")
def edit_appointment_page(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"]))
):
    """Page to edit an appointment"""
    appointment = scheduled_appointment_crud.get_scheduled_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Get doctors for assignment
    doctors = user_crud.get_doctors(db)
    
    context = {
        "request": request,
        "title": f"Edit Appointment - {appointment.patient_name or 'Patient'}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "appointment": appointment,
        "doctors": doctors,
        "min_date": date.today().strftime("%Y-%m-%d"),
        "max_date": (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
    }
    
    return templates.TemplateResponse("appointments/edit_appointment.html", context)


@router.post("/appointments/{appointment_id}/edit")
def update_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"])),
    
    # Form fields
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
    """Update appointment (form submission)"""
    try:
        # Parse appointment date and time
        appointment_datetime = datetime.strptime(f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M")
        
        update_data = {
            "patient_name": patient_name.strip() if patient_name else None,
            "patient_phone": patient_phone.strip() if patient_phone else None,
            "assigned_doctor_id": assigned_doctor_id,
            "appointment_date": appointment_datetime,
            "duration_minutes": duration_minutes,
            "reason_complaint": reason_complaint.strip() if reason_complaint else None,
            "notes": notes.strip() if notes else None,
            "priority": priority
        }
        
        appointment = scheduled_appointment_crud.update_scheduled_appointment(
            db, appointment_id, update_data
        )
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        return RedirectResponse(
            url=f"/appointments/{appointment_id}?success=updated",
            status_code=302
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/appointments/{appointment_id}/edit?error=validation&message=" + str(e),
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/appointments/{appointment_id}/edit?error=server",
            status_code=302
        )


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"]))
):
    """Cancel appointment (form submission)"""
    appointment = scheduled_appointment_crud.cancel_scheduled_appointment(
        db, appointment_id, current_user.id, reason
    )
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return RedirectResponse(
        url=f"/appointments/{appointment_id}?success=cancelled",
        status_code=302
    )


@router.post("/appointments/{appointment_id}/complete")
def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Admin"]))
):
    """Complete appointment (form submission)"""
    appointment = scheduled_appointment_crud.complete_scheduled_appointment(db, appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return RedirectResponse(
        url=f"/appointments/{appointment_id}?success=completed",
        status_code=302
    )


@router.post("/appointments/{appointment_id}/confirm")
def confirm_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Doctor"]))
):
    """Confirm appointment (form submission)"""
    appointment = scheduled_appointment_crud.confirm_scheduled_appointment(db, appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return RedirectResponse(
        url=f"/appointments/{appointment_id}?success=confirmed",
        status_code=302
    )


@router.get("/doctor/appointments", name="doctor_appointments", dependencies=[Depends(permission_required("doctor_appointments"))])
def doctor_appointments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_filter: Optional[str] = Query(None)
):
    """Doctor's appointments view"""
    # Parse date filter
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            filter_date = date.today()
    else:
        filter_date = date.today()
    
    # Get doctor's appointments for the selected date
    appointments = scheduled_appointment_crud.get_scheduled_appointments_for_doctor(
        db, current_user.id, filter_date, filter_date
    )
    
    # Get upcoming appointments
    upcoming = scheduled_appointment_crud.get_upcoming_scheduled_appointments(
        db, current_user.id, 7
    )
    
    context = {
        "request": request,
        "title": "My Appointments",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "appointments": appointments,
        "upcoming_appointments": upcoming,
        "selected_date": filter_date
    }
    
    return templates.TemplateResponse("appointments/doctor_appointments.html", context)
