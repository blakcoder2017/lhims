from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
from typing import Optional
from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.appointment_models import QueueStatus, VisitType
from app.models.scheduled_appointment_models import AppointmentType, AppointmentStatus
from app.crud import appointment_crud
from app.schemas.appointment_schemas import QueueCreate, QueueUpdate, Queue, AppointmentCreate, AppointmentUpdate

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
    Check in a patient after vitals are taken and payment is made.
    Creates an appointment if one doesn't exist, then checks the patient in.
    This makes the patient appear in the doctor's queue.
    
    Requirements:
    - Vitals must be recorded (within last 24 hours)
    - Payment must be made (for cash patients only)
    """
    from app.models.patient_models import Patient
    from app.models.triage_models import TriageVitals
    from app.utils.payment_verification import (
        is_cash_patient,
        has_paid_for_service,
        requires_payment_before_service
    )
    from app.models.billing_models import ChargeType
    from sqlalchemy import func
    from datetime import date, timedelta
    
    # Get patient
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Step 1: Verify vitals have been recorded (within last 24 hours)
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    vitals_record = db.query(TriageVitals).filter(
        TriageVitals.patient_id == patient_id,
        func.date(TriageVitals.recorded_at) >= yesterday
    ).order_by(TriageVitals.recorded_at.desc()).first()
    
    if not vitals_record:
        # Vitals not recorded, redirect back with error
        return RedirectResponse(
            url=f"/patients/{patient_id}/triage?error=Vitals must be recorded before check-in. Please record vital signs first.",
            status_code=status.HTTP_302_FOUND
        )
    
    # Step 2: Verify payment has been made (for cash patients only)
    if is_cash_patient(db, patient_id):
        payment_required = requires_payment_before_service(db, patient_id, ChargeType.CONSULTATION)
        
        if payment_required:
            # Check if payment has been made (for today's consultation)
            has_paid, charge, invoice = has_paid_for_service(
                db, patient_id, ChargeType.CONSULTATION,
                encounter_id=None,
                check_today_only=True  # Check for today's payment only
            )
            
            if not has_paid:
                # Payment not made, redirect back with error
                return RedirectResponse(
                    url=f"/patients/{patient_id}/triage?error=Payment must be completed before check-in. Please process payment first.",
                    status_code=status.HTTP_302_FOUND
                )
    
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
            appointment_type=AppointmentType.CONSULTATION,
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


@router.post("", response_model=Queue, status_code=status.HTTP_201_CREATED, name="create_appointment_api")
def create_appointment_api(
    appointment: QueueCreate,
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
        
        # Create queue entry
        new_queue_entry = appointment_crud.create_queue_entry(db, appointment)
        return new_queue_entry
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create appointment: {str(e)}"
        )


@router.get("/create", name="create_appointment_get")
def create_appointment_get(
    request: Request,
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"]))
):
    """
    GET endpoint for appointment creation page.
    This redirects to the UI page for creating appointments.
    """
    from fastapi.responses import RedirectResponse
    if patient_id:
        return RedirectResponse(url=f"/appointments/create?patient_id={patient_id}", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/appointments/create", status_code=status.HTTP_302_FOUND)


@router.post("/create", name="create_appointment")
def create_appointment_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin"])),

    # Form fields
    patient_id: Optional[str] = Form(None),  # Optional - for existing patients
    patient_name: str = Form(""),  # For patients not in system
    patient_phone: str = Form(""),  # Contact for non-system patients
    department: str = Form(...),
    department_type: str = Form("opd"),  # OPD or IPD - default to OPD
    appointment_type: str = Form(...),
    scheduled_date: str = Form(...),  # Will be parsed as datetime
    scheduled_time: str = Form(...),  # Time component
    reason_complaint: str = Form(""),
    notes: str = Form(""),
    priority: int = Form(5),
    assigned_doctor_id: Optional[str] = Form(None),
):
    """
    Handles HTML form submission for creating a new appointment.
    Workflow Step 2: Appointment/Queue
    Supports OPD and IPD appointments.
    """
    import logging
    logging.info(f"DEBUG: Creating appointment with data: patient_id={patient_id}, patient_name={patient_name}, department={department}, appointment_type={appointment_type}, scheduled_date={scheduled_date}, scheduled_time={scheduled_time}, assigned_doctor_id={assigned_doctor_id}")
    try:
        # Parse patient_id
        patient_id_int = None
        if patient_id and patient_id.strip():
            try:
                patient_id_int = int(patient_id)
            except ValueError:
                raise ValueError("Invalid patient ID")

        # Validate patient information - either existing patient OR new patient details
        if patient_id_int:
            # Existing patient selected - validation passes
            pass
        elif patient_name.strip() and patient_phone.strip():
            # New patient details provided - validation passes
            pass
        else:
            raise ValueError("Either select an existing patient OR provide both patient name and phone number")
        
        # Parse scheduled datetime
        scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
        logging.info(f"DEBUG: Parsing datetime: {scheduled_datetime_str}")
        scheduled_datetime = datetime.strptime(scheduled_datetime_str, "%Y-%m-%d %H:%M")
        logging.info(f"DEBUG: Parsed datetime: {scheduled_datetime}")

        # Validate required fields
        if not department or not department.strip():
            raise ValueError("Department is required")

        # Validate appointment type
        if not appointment_type or not appointment_type.strip():
            raise ValueError("Appointment type is required")
        appointment_type_enum = AppointmentType(appointment_type)
        logging.info(f"DEBUG: Appointment type enum: {appointment_type_enum}")

        # Validate department_type
        if department_type not in ["opd", "ipd", "both"]:
            department_type = "opd"  # Default to OPD if invalid

        # Auto-assign doctor if not provided and doctors are on duty
        final_assigned_doctor_id = None
        if assigned_doctor_id and assigned_doctor_id.strip():
            try:
                final_assigned_doctor_id = int(assigned_doctor_id)
            except ValueError:
                final_assigned_doctor_id = None
        
        # If no clinician assigned, try to auto-assign from doctors on duty
        if not final_assigned_doctor_id:
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
                final_assigned_doctor_id = available_doctors[0].doctor_id
        
        # Create appointment data for ScheduledAppointment
        appointment_data = {
            "patient_id": patient_id_int,
            "patient_name": patient_name.strip() if not patient_id_int and patient_name.strip() else None,
            "patient_phone": patient_phone.strip() if not patient_id_int and patient_phone.strip() else None,
            "department": department,
            "assigned_doctor_id": final_assigned_doctor_id,
            "appointment_date": scheduled_datetime,  # Use appointment_date for CRUD
            "duration_minutes": 30,  # Default duration
            "appointment_type": appointment_type_enum,
            "reason_complaint": reason_complaint if reason_complaint else None,
            "notes": notes if notes else None,
            "priority": priority
        }
        logging.info(f"DEBUG: Appointment data: {appointment_data}")

        # Create scheduled appointment
        from app.crud import scheduled_appointment_crud
        logging.info("DEBUG: Calling create_scheduled_appointment")
        new_appointment = scheduled_appointment_crud.create_scheduled_appointment(db, appointment_data, current_user.id)
        logging.info(f"DEBUG: Created appointment: {new_appointment}")
        
        # Send SMS notification (Appointment approved) - only if valid phone
        try:
            from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
            from app.models.patient_models import Patient
            
            patient_phone_to_use = None
            patient_name_to_use = None

            if patient_id_int:
                patient = db.query(Patient).filter(Patient.id == patient_id_int).first()
                if patient and patient.phone_number and is_valid_phone(patient.phone_number):
                    patient_phone_to_use = patient.phone_number
                    patient_name_to_use = f"{patient.first_name} {patient.last_name}"
            elif patient_phone and is_valid_phone(patient_phone.strip()):
                patient_phone_to_use = patient_phone.strip()
                patient_name_to_use = patient_name.strip() if patient_name else "Patient"
            
            if patient_phone_to_use and patient_name_to_use:
                scheduled_date_str = scheduled_datetime.strftime("%Y-%m-%d %H:%M")
                message_template = "Hello {$name}. Your appointment is scheduled for {$date} at {$department}. Appointment Type: {$type}. Please arrive on time. Thank you!"
                destinations = [{
                    "number": patient_phone_to_use,
                    "values": [
                        patient_name_to_use,
                        scheduled_date_str,
                        department,
                        appointment_type_enum.value.replace("_", " ").title()
                    ]
                }]
                send_personalized_sms_notification(message_template, destinations)
        except Exception as sms_error:
            print(f"Warning: Unable to send appointment SMS: {sms_error}")
        
        # Redirect to appointments list to show the created appointment
        redirect_url = f"/appointments?status=appointment_created&appointment_id=" + str(new_appointment.id)
        if patient_id_int:
            redirect_url += f"&patient_id={patient_id_int}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        
    except ValueError as e:
        # Handle validation errors
        logging.error(f"DEBUG: ValueError in appointment creation: {str(e)}")
        error_url = "/appointments/create?error=appointment_validation"
        if patient_id_int:
            error_url += f"&patient_id={patient_id_int}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logging.error(f"DEBUG: Exception in appointment creation: {str(e)}", exc_info=True)
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


@router.get("/doctor/appointments", name="doctor_appointments_api")
def doctor_appointments(
    request: Request,
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD). Defaults to today."),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"])),
):
    """
    View appointments for a specific date (for doctors).
    Shows appointments assigned to the current doctor or all appointments if admin.
    """
    from datetime import date as date_type
    from sqlalchemy import func, and_, or_
    from app.models.scheduled_appointment_models import Appointment
    
    # Parse date filter
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            filter_date = date_type.today()
    else:
        filter_date = date_type.today()
    
    # Build query
    from app.models.patient_models import Patient
    query = db.query(Appointment).join(Patient, Appointment.patient_id == Patient.id).filter(
        Appointment.is_active == True,
        func.date(Appointment.scheduled_date) == filter_date
    )
    
    # Filter by assigned clinician (doctors see their own appointments, admins see all)
    if current_user.role.name != "Admin":
        query = query.filter(
            or_(
                Appointment.assigned_clinician_id == current_user.id,
                Appointment.assigned_clinician_id.is_(None)
            )
        )
    
    # Filter by department if provided
    if department:
        query = query.filter(Appointment.department == department)
    
    appointments = query.order_by(Appointment.scheduled_date).all()
    
    # Get unique departments for filter
    departments = db.query(Appointment.department).distinct().all()
    departments = [d[0] for d in departments]
    
    context = {
        "request": request,
        "title": f"Appointments - {filter_date.strftime('%Y-%m-%d')}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "appointments": appointments,
        "filter_date": filter_date,
        "departments": departments,
        "selected_department": department,
    }
    
    return templates.TemplateResponse("appointments/doctor_appointments.html", context)


@router.get("/queue", name="view_queue")
def view_queue_page(
    request: Request,
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by patient name, number, or phone"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Displays the OPD queue for today and unfulfilled queues from previous days.
    Workflow Step 2: Queue Management
    """
    from app.models.appointment_models import OPDQueue, QueueStatus
    from app.models.triage_models import TriageVitals
    from app.services.triage_level_calculator import get_triage_level_priority
    from datetime import date, timedelta
    
    # Get today's queue
    query = db.query(OPDQueue).filter(
        OPDQueue.is_active == True,
        func.date(OPDQueue.created_at) == date.today()
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
    
    queue_today = query.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc(),
        OPDQueue.created_at.asc()
    ).all()
    
    # Get unfulfilled queues from previous days (last 7 days)
    previous_date = date.today() - timedelta(days=7)
    query_previous = db.query(OPDQueue).filter(
        OPDQueue.is_active == True,
        OPDQueue.status.in_([QueueStatus.WAITING, QueueStatus.IN_PROGRESS]),
        func.date(OPDQueue.created_at) >= previous_date,
        func.date(OPDQueue.created_at) < date.today()
    )
    
    if department:
        query_previous = query_previous.filter(OPDQueue.department == department)
    
    queue_previous = query_previous.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc(),
        OPDQueue.created_at.asc()
    ).all()
    
    # Calculate wait times and get triage info for today's queue
    queue_today_with_wait = []
    
    for queue_entry in queue_today:
        # Calculate wait time from creation
        wait_time = datetime.now() - queue_entry.created_at
        wait_time_str = f"{wait_time.seconds // 3600}h {(wait_time.seconds % 3600) // 60}m" if wait_time.seconds > 0 else "Just now"
        
        # Get most recent vitals with triage level for this patient
        latest_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == queue_entry.patient_id
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        triage_level = latest_vitals.triage_level if latest_vitals else None
        triage_category = latest_vitals.triage_category if latest_vitals else None
        triage_priority = get_triage_level_priority(triage_level)
        
        queue_today_with_wait.append({
            "appointment": queue_entry,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str,
            "triage_level": triage_level,
            "triage_category": triage_category,
            "triage_priority": triage_priority
        })
    
    # Sort by triage priority first (P1 > P2 > P3), then by priority and queue number
    queue_today_with_wait.sort(key=lambda x: (
        x.get("triage_priority", 4),
        x["appointment"].priority,
        x["appointment"].queue_number or 999
    ))
    
    # Calculate wait times for previous days' queues
    queue_previous_with_wait = []
    for queue_entry in queue_previous:
        wait_time = datetime.now() - queue_entry.created_at
        wait_time_str = f"{wait_time.days}d {wait_time.seconds // 3600}h" if wait_time.days > 0 else f"{wait_time.seconds // 3600}h {(wait_time.seconds % 3600) // 60}m"
        
        queue_previous_with_wait.append({
            "appointment": queue_entry,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Get unique departments for filter
    departments = db.query(OPDQueue.department).distinct().all()
    departments = [d[0] for d in departments]
    
    context = {
        "request": request,
        "title": "OPD Queue",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "queue_today": queue_today_with_wait,
        "queue_previous": queue_previous_with_wait,
        "departments": departments,
        "selected_department": department,
        "search_query": search or "",
    }
    
    return templates.TemplateResponse("front_office/queue.html", context)

