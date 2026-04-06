"""
Nurse API Routes

Routes for nurse-specific functionality:
- Triage queue (patients awaiting vitals)
- Nurse dashboard
- IPD workflow for nurses
- Auto-clear stale vitals queue
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
from app.models.triage_models import TriageVitals
from app.models.patient_models import Patient
from app.crud import appointment_crud, triage_crud, patient_crud
from app.models.ipd_models import Admission, AdmissionStatus

router = APIRouter(
    prefix="/nurse",
    tags=["Nurse"]
)



@router.get("/dashboard", name="nurse_dashboard")
def nurse_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin", "Front Office"]))
):
    """Nurse dashboard with triage queue and IPD workflow"""
    from datetime import datetime, date, timedelta
    from app.models.triage_models import TriageVitals
    from app.models.ipd_models import Admission, AdmissionStatus
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get queue entries that need triage (checked in but no recent vitals)
    # Patients in queue today who either:
    # 1. Have no vitals recorded today, OR
    # 2. Have queue entries but vitals were recorded before check-in time
    
    queue_today = db.query(OPDQueue).options(
        joinedload(OPDQueue.patient)
    ).filter(
        func.date(OPDQueue.created_at) == today,
        OPDQueue.status.in_([
            QueueStatus.WAITING.value,
            QueueStatus.IN_PROGRESS.value
        ]),
        OPDQueue.is_active == True
    ).order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc()
    ).all()
    
    # Filter to get patients who need triage
    triage_queue = []
    for queue_entry in queue_today:
        # Check if patient has vitals recorded today
        recent_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == queue_entry.patient_id,
            func.date(TriageVitals.recorded_at) == today
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        # If no vitals today, add to queue
        if not recent_vitals:
            triage_queue.append(queue_entry)
    
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


@router.get("/triage-queue", name="triage_queue", dependencies=[Depends(permission_required("view_triage_queue"))])
def nurse_triage_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None)
):
    """Triage queue for nurses - patients awaiting vital signs"""
    from datetime import datetime, date
    from app.models.triage_models import TriageVitals
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Get queue entries that need triage
    query = db.query(OPDQueue).options(
        joinedload(OPDQueue.patient)
    ).filter(
        func.date(OPDQueue.created_at) == today,
        OPDQueue.status.in_([
            QueueStatus.WAITING.value,
            QueueStatus.IN_PROGRESS.value
        ]),
        OPDQueue.is_active == True
    )
    
    if department:
        query = query.filter(OPDQueue.department == department)
    
    queue_entries = query.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc()
    ).all()
    
    # Filter to get patients who need triage (no recent vitals today)
    from app.crud import appointment_crud
    triage_queue = []
    for queue_entry in queue_entries:
        # Check if patient has vitals recorded today
        recent_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == queue_entry.patient_id,
            func.date(TriageVitals.recorded_at) == today
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        # Calculate wait time
        wait_time = appointment_crud.calculate_wait_time(queue_entry)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        
        # Add to queue if no vitals today, or if status filter requires it
        if status_filter == "needs_triage" and not recent_vitals:
            triage_queue.append({
                "queue_entry": queue_entry,
                "has_vitals": False,
                "last_vitals": None,
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
        elif status_filter == "completed" and recent_vitals:
            triage_queue.append({
                "queue_entry": queue_entry,
                "has_vitals": True,
                "last_vitals": recent_vitals,
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
        elif not status_filter:
            # Show all - mark which need triage
            triage_queue.append({
                "queue_entry": queue_entry,
                "has_vitals": recent_vitals is not None,
                "last_vitals": recent_vitals,
                "wait_time": wait_time,
                "wait_time_str": wait_time_str
            })
    
    # Get unfulfilled queues from previous days
    previous_queue_entries = appointment_crud.get_unfulfilled_queues_previous_days(
        db, department, None, days_back=7
    )
    
    # Filter previous queue entries to only WAITING or IN_PROGRESS (need triage)
    previous_queue_entries = [
        entry for entry in previous_queue_entries 
        if entry.status.value in [QueueStatus.WAITING.value, QueueStatus.IN_PROGRESS.value]
    ]
    
    # Calculate wait times and check vitals for previous day queues
    triage_queue_previous = []
    for queue_entry in previous_queue_entries:
        # Check if patient has vitals recorded
        recent_vitals = db.query(TriageVitals).filter(
            TriageVitals.patient_id == queue_entry.patient_id
        ).order_by(TriageVitals.recorded_at.desc()).first()
        
        wait_time = appointment_crud.calculate_wait_time(queue_entry)
        wait_time_str = appointment_crud.format_wait_time(wait_time)
        
        triage_queue_previous.append({
            "queue_entry": queue_entry,
            "has_vitals": recent_vitals is not None,
            "last_vitals": recent_vitals,
            "wait_time": wait_time,
            "wait_time_str": wait_time_str
        })
    
    # Get unique departments for filter
    departments = db.query(OPDQueue.department).distinct().all()
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


@router.get("/admissions/{admission_id}/billing", name="nurse_admission_billing")
def nurse_admission_billing(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin", "Front Office"]))
):
    """Nurse billing page for adding charges to an admission"""
    from app.crud import billing_crud, service_pricing_crud, ipd_crud
    
    # Get admission with patient details
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    
    # Get available services for admission - filter by 'other' charge type
    from app.models.service_pricing_models import ServicePricing
    admission_services = db.query(ServicePricing).filter(
        ServicePricing.is_active == True,
        ServicePricing.charge_type.in_([
            'other'
        ])
    ).all()
    
    # Get existing invoice with creator info
    invoice = billing_crud.get_invoice_by_admission(db, admission_id)
    
    context = {
        "request": request,
        "title": "Admission Billing",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "admission": admission,
        "invoice": invoice,
        "available_services": admission_services,
    }
    return templates.TemplateResponse("nurse/admission_billing.html", context)


@router.post("/admissions/{admission_id}/billing", name="nurse_admission_billing_post")
async def nurse_admission_billing_post(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin", "Front Office"]))
):
    """Handle form submission for adding charges to an admission"""
    from app.crud import billing_crud, service_pricing_crud, ipd_crud
    from app.models.billing_models import ChargeType
    from fastapi import Form
    from decimal import Decimal
    
    # Get admission
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    
    # Parse form data
    form_data = await request.form()
    
    # Get selected services and quantities
    charges_data = []
    for key, value in form_data.items():
        if key.startswith('service_'):
            service_id = int(key.replace('service_', ''))
            quantity_key = f'quantity_{service_id}'
            quantity = int(form_data.get(quantity_key, 1))
            
            if quantity > 0:
                # Get service pricing
                service = service_pricing_crud.get_service_pricing(db, service_id)
                if service:
                    charges_data.append({
                        'description': service.service_name,
                        'quantity': quantity,
                        'unit_price': service.unit_price
                    })
    
    if not charges_data:
        # No charges selected, redirect back
        return RedirectResponse(
            url=f"/nurse/admissions/{admission_id}/billing?error=no_services",
            status_code=302
        )
    
    # Add charges to admission invoice
    invoice = billing_crud.add_charges_to_admission(
        db, admission_id, charges_data, current_user.id
    )
    
    return RedirectResponse(
        url=f"/nurse/admissions/{admission_id}/billing?success=added",
        status_code=302
    )


@router.post("/auto-clear-vitals-queue", name="auto_clear_vitals_queue", dependencies=[Depends(permission_required("view_triage_queue"))])
def auto_clear_stale_vitals_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin"])),
    hours_threshold: int = Query(48, ge=1, le=168, description="Hours after which to clear stale queue entries"),
    dry_run: bool = Query(False, description="If true, only return entries that would be cleared without actually clearing them")
):
    """
    Auto-clear patients from vitals queue who have not had vitals recorded 
    after the specified threshold (default 48 hours).
    
    This endpoint:
    - Finds queue entries where status is WAITING or IN_PROGRESS
    - Checks if the queue entry is older than the threshold
    - Checks if any vitals were recorded for that patient after the queue entry was created
    - If no vitals recorded, marks the queue entry as NO_SHOW
    
    Use dry_run=true to preview what would be cleared without making changes.
    """
    from app.crud import appointment_crud
    
    cleared_count, cleared_entries = appointment_crud.auto_clear_stale_vitals_queue(
        db=db,
        hours_threshold=hours_threshold,
        dry_run=dry_run
    )
    
    action = "Would clear" if dry_run else "Cleared"
    message = f"{action} {cleared_count} stale vitals queue entries"
    
    return {
        "success": True,
        "message": message,
        "cleared_count": cleared_count,
        "cleared_entries": cleared_entries,
        "hours_threshold": hours_threshold,
        "dry_run": dry_run
    }


@router.post("/auto-close-encounters", name="auto_close_encounters", dependencies=[Depends(permission_required("view_triage_queue"))])
def auto_close_uncompleted_encounters(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Admin"])),
    hours_threshold: int = Query(48, ge=1, le=168, description="Hours after which to auto-close uncompleted encounters"),
    dry_run: bool = Query(False, description="If true, only return entries that would be closed without actually closing them")
):
    """
    Auto-close uncompleted encounters that have been in progress for longer than 
    the specified threshold (default 48 hours).
    
    This endpoint:
    - Finds encounters with status IN_PROGRESS that started before the threshold
    - Marks them as AUTO_CLOSED
    - Sets completed_at timestamp
    
    Use dry_run=true to preview what would be closed without making changes.
    """
    from app.crud import encounter_crud
    
    closed_count, closed_encounters = encounter_crud.auto_close_uncompleted_encounters(
        db=db,
        hours_threshold=hours_threshold,
        dry_run=dry_run
    )
    
    action = "Would close" if dry_run else "Closed"
    message = f"{action} {closed_count} uncompleted encounters"
    
    return {
        "success": True,
        "message": message,
        "closed_count": closed_count,
        "closed_encounters": closed_encounters,
        "hours_threshold": hours_threshold,
        "dry_run": dry_run
    }


@router.post("/auto-close-encounters/install-cron", name="install_encounter_auto_close_cron")
def install_encounter_auto_close_cron(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    hour: int = Query(1, ge=0, le=23, description="Hour of day to run the cron job (0-23)"),
    minute: int = Query(0, ge=0, le=59, description="Minute of hour to run the cron job (0-59)")
):
    """
    Install a cron job to automatically close uncompleted encounters.
    """
    from app.services.encounter_auto_close_service import install_cron_job, get_cron_job_status
    
    success, message = install_cron_job(hour=hour, minute=minute)
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@router.post("/auto-close-encounters/remove-cron", name="remove_encounter_auto_close_cron")
def remove_encounter_auto_close_cron(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """
    Remove the cron job for automatic encounter auto-close.
    """
    from app.services.encounter_auto_close_service import remove_cron_job
    
    success, message = remove_cron_job()
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@router.get("/auto-close-encounters/cron-status", name="encounter_auto_close_cron_status")
def encounter_auto_close_cron_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """
    Get the status of the encounter auto-close cron job.
    """
    from app.services.encounter_auto_close_service import get_cron_job_status
    
    return get_cron_job_status()


@router.post("/auto-clear-vitals-queue/install-cron", name="install_vitals_queue_auto_clear_cron")
def install_vitals_queue_auto_clear_cron(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    hour: int = Query(1, ge=0, le=23, description="Hour of day to run the cron job (0-23)"),
    minute: int = Query(30, ge=0, le=59, description="Minute of hour to run the cron job (0-59)")
):
    """
    Install a cron job to automatically clear stale vitals queue entries.
    """
    from app.services.vitals_queue_auto_clear_service import install_cron_job, get_cron_job_status
    
    success, message = install_cron_job(hour=hour, minute=minute)
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@router.post("/auto-clear-vitals-queue/remove-cron", name="remove_vitals_queue_auto_clear_cron")
def remove_vitals_queue_auto_clear_cron(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """
    Remove the cron job for automatic vitals queue auto-clear.
    """
    from app.services.vitals_queue_auto_clear_service import remove_cron_job
    
    success, message = remove_cron_job()
    
    if success:
        return {"success": True, "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


@router.get("/auto-clear-vitals-queue/cron-status", name="vitals_queue_auto_clear_cron_status")
def vitals_queue_auto_clear_cron_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """
    Get the status of the vitals queue auto-clear cron job.
    """
    from app.services.vitals_queue_auto_clear_service import get_cron_job_status
    
    return get_cron_job_status()

