from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.appointment_models import AppointmentStatus, AppointmentType
from app.crud import appointment_crud
from app.schemas.appointment_schemas import AppointmentCreate, AppointmentUpdate, Appointment

router = APIRouter(
    prefix="/api/v1/appointments",
    tags=["Appointments"]
)

templates = Jinja2Templates(directory="app/templates")


@router.post("/check-in/{patient_id}", name="check_in_patient")
def check_in_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Nurse", "Admin"])),
    department: Optional[str] = Form("General Medicine"),
    chief_complaint: Optional[str] = Form(None),
    appointment_id: Optional[int] = Form(None),
):
    """
    Check in a patient after vitals are taken.
    Creates an appointment if one doesn't exist, then checks the patient in.
    This makes the patient appear in the doctor's queue.
    """
    from app.models.patient_models import Patient
    from app.models.triage_models import TriageVitals
    
    # Get patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if appointment already exists
    appointment = None
    if appointment_id:
        appointment = appointment_crud.get_appointment(db, appointment_id)
    
    # If no appointment exists, create one
    if not appointment:
        # Determine department from chief complaint or use default
        if chief_complaint:
            complaint_lower = chief_complaint.lower()
            if any(word in complaint_lower for word in ["pediatric", "child", "baby", "infant"]):
                department = "Pediatrics"
            elif any(word in complaint_lower for word in ["antenatal", "prenatal", "pregnancy check", "maternity check"]):
                department = "Antenatal"
            elif any(word in complaint_lower for word in ["pregnant", "pregnancy", "obstetric", "gynec"]):
                department = "Obstetrics & Gynecology"
            elif any(word in complaint_lower for word in ["emergency", "urgent", "trauma", "accident"]):
                department = "Emergency"
        
        # Create appointment
        appointment_data = AppointmentCreate(
            patient_id=patient_id,
            department=department,
            department_type="opd",
            appointment_type=AppointmentType.WALK_IN,
            scheduled_date=datetime.now(),
            chief_complaint=chief_complaint,
            notes="Auto-created from check-in after vitals",
            priority=5,
            assigned_clinician_id=None,  # Will be auto-assigned
            created_by_id=current_user.id
        )
        
        appointment = appointment_crud.create_appointment(db, appointment_data)
    
    # Check in the patient
    appointment_update = AppointmentUpdate(
        status=AppointmentStatus.CHECKED_IN,
        checked_in_at=datetime.now()
    )
    
    updated_appointment = appointment_crud.update_appointment(db, appointment.id, appointment_update)
    
    if not updated_appointment:
        raise HTTPException(status_code=500, detail="Failed to check in patient")
    
    # Redirect back to triage page with success message
    return RedirectResponse(
        url=f"/patients/{patient_id}/triage?appointment_id={appointment.id}&status=checked_in",
        status_code=status.HTTP_302_FOUND
    )


@router.post("", response_model=Appointment, status_code=status.HTTP_201_CREATED, name="create_appointment_api")
def create_appointment_api(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Nurse", "Admin"]))
):
    """
    Create a new appointment (JSON API).
    """
    try:
        # Ensure created_by_id is set from current user if not provided
        if not appointment.created_by_id:
            appointment.created_by_id = current_user.id
        
        # Create appointment
        new_appointment = appointment_crud.create_appointment(db, appointment)
        return new_appointment
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create appointment: {str(e)}"
        )


@router.post("/create", name="create_appointment")
def create_appointment_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required("Front Office")),
    
    # Form fields
    patient_id: int = Form(...),
    department: str = Form(...),
    department_type: str = Form("opd"),  # OPD or IPD - default to OPD
    appointment_type: str = Form(...),
    scheduled_date: str = Form(...),  # Will be parsed as datetime
    scheduled_time: str = Form(...),  # Time component
    chief_complaint: str = Form(""),
    notes: str = Form(""),
    priority: int = Form(5),
    assigned_clinician_id: Optional[int] = Form(None),
):
    """
    Handles HTML form submission for creating a new appointment.
    Workflow Step 2: Appointment/Queue
    Supports OPD and IPD appointments.
    """
    try:
        # Parse scheduled datetime
        scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
        scheduled_datetime = datetime.strptime(scheduled_datetime_str, "%Y-%m-%d %H:%M")
        
        # Validate appointment type
        appointment_type_enum = AppointmentType(appointment_type)
        
        # Validate department_type
        if department_type not in ["opd", "ipd", "both"]:
            department_type = "opd"  # Default to OPD if invalid
        
        # Auto-assign doctor if not provided and doctors are on duty
        final_assigned_clinician_id = assigned_clinician_id
        if not assigned_clinician_id:
            from app.crud import ipd_crud
            # Get doctors on duty for the department and scheduled time
            doctors_on_duty = ipd_crud.get_doctors_on_duty(db, department=department)
            
            # Filter doctors who are on duty at the scheduled time
            scheduled_time_only = scheduled_datetime.time()
            available_doctors = [
                duty for duty in doctors_on_duty
                if duty.shift_start.time() <= scheduled_time_only <= duty.shift_end.time()
                and duty.department == department
            ]
            
            # Assign the first available doctor if any
            if available_doctors:
                final_assigned_clinician_id = available_doctors[0].doctor_id
        
        # Create appointment data
        appointment_data = AppointmentCreate(
            patient_id=patient_id,
            department=department,
            department_type=department_type,
            appointment_type=appointment_type_enum,
            scheduled_date=scheduled_datetime,
            chief_complaint=chief_complaint if chief_complaint else None,
            notes=notes if notes else None,
            priority=priority,
            assigned_clinician_id=final_assigned_clinician_id,
            created_by_id=current_user.id
        )
        
        # Create appointment
        new_appointment = appointment_crud.create_appointment(db, appointment_data)
        
        # Redirect to queue view or patient triage page
        return RedirectResponse(
            url=f"/patients/{patient_id}/triage?appointment_id={new_appointment.id}&status=appointment_created",
            status_code=status.HTTP_302_FOUND
        )
        
    except ValueError as e:
        # Handle validation errors
        return RedirectResponse(
            url=f"/patients/{patient_id}/triage?error=appointment_validation",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create appointment: {str(e)}"
        )


@router.post("/{appointment_id}/update-status", name="update_appointment_status")
def update_appointment_status(
    appointment_id: int,
    request: Request,
    appointment_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates the status of an appointment (e.g., check-in, start, complete).
    """
    try:
        status_enum = AppointmentStatus(appointment_status)
        update_data = AppointmentUpdate(status=status_enum)
        
        updated_appointment = appointment_crud.update_appointment(
            db, appointment_id, update_data
        )
        
        if not updated_appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Redirect back to queue or appointment view
        # Note: Router prefix is overridden in main.py to "", so route is at /queue
        from urllib.parse import urlencode
        # Use direct path since router prefix is overridden in main.py
        base_url = "/queue"
        query_params = urlencode({"department": updated_appointment.department, "status": "updated"})
        redirect_url = f"{base_url}?{query_params}"
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid appointment status"
        )


@router.get("/queue", name="view_queue")
def view_queue_page(
    request: Request,
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by patient name, number, or phone"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Displays the appointment queue for today and unfulfilled queues from previous days.
    Workflow Step 2: Appointment/Queue Management
    """
    # Get today's queue
    queue_today = appointment_crud.get_queue_today(db, department, search)
    
    # Get unfulfilled queues from previous days (last 7 days)
    queue_previous = appointment_crud.get_unfulfilled_queues_previous_days(
        db, department, search, days_back=7
    )
    
    # Calculate wait times for today's queue
    queue_today_with_wait = []
    for appointment in queue_today:
        wait_time = appointment_crud.calculate_wait_time(appointment)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        queue_today_with_wait.append({
            "appointment": appointment,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Calculate wait times for previous days' queues
    queue_previous_with_wait = []
    for appointment in queue_previous:
        wait_time = appointment_crud.calculate_wait_time(appointment)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        queue_previous_with_wait.append({
            "appointment": appointment,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Get unique departments for filter
    from app.models.appointment_models import Appointment
    departments = db.query(Appointment.department).distinct().all()
    departments = [d[0] for d in departments]
    
    context = {
        "request": request,
        "title": "Appointment Queue",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "queue_today": queue_today_with_wait,
        "queue_previous": queue_previous_with_wait,
        "departments": departments,
        "selected_department": department,
        "search_query": search or "",
    }
    
    return templates.TemplateResponse("front_office/queue.html", context)

