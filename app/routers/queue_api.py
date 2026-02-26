"""
API routes for OPD queue management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.crud import appointment_crud
from app.models.user_models import User
from app.models.appointment_models import OPDQueue, QueueStatus, VisitType

router = APIRouter(
    prefix="/api/v1/queue",
    tags=["OPD Queue"]
)


@router.post("/add")
def add_to_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Nurse"])),
    
    # Form fields for HTML form submission
    patient_id: int = Form(...),
    department_type: str = Form("opd"),
    department: str = Form(...),
    visit_type: str = Form("walk_in"),
    priority: int = Form(5),
    chief_complaint: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Add patient to OPD queue (HTML form endpoint)"""
    try:
        # Validate visit type
        try:
            visit_type_enum = VisitType(visit_type)
        except ValueError:
            visit_type_enum = VisitType.WALK_IN
        
        # Create queue entry
        queue_entry = OPDQueue(
            patient_id=patient_id,
            department=department,
            department_type=department_type,
            visit_type=visit_type_enum,
            priority=priority,
            chief_complaint=chief_complaint.strip() if chief_complaint else None,
            notes=notes.strip() if notes else None,
            created_by_id=current_user.id
        )
        
        db.add(queue_entry)
        db.commit()
        db.refresh(queue_entry)
        
        # Generate queue number
        queue_number = appointment_crud.generate_queue_number(db, department)
        queue_entry.queue_number = queue_number
        db.commit()
        
        return RedirectResponse(
            url=f"/?success=queued&patient_id={patient_id}&queue_id={queue_entry.id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        return RedirectResponse(
            url=f"/patients/{patient_id}/triage?error=queue_failed&message=Failed to add to queue",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/list")
def get_queue_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    department: Optional[str] = None,
    status: Optional[str] = None
):
    """Get queue list with optional filtering"""
    query = db.query(OPDQueue).filter(OPDQueue.is_active == True)
    
    if department:
        query = query.filter(OPDQueue.department == department)
    
    if status:
        try:
            status_enum = QueueStatus(status)
            query = query.filter(OPDQueue.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter
    
    # Order by priority and queue number
    queue_entries = query.order_by(
        OPDQueue.priority.asc(),
        OPDQueue.queue_number.asc(),
        OPDQueue.created_at.asc()
    ).all()
    
    return queue_entries


@router.get("/{queue_id}")
def get_queue_entry(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific queue entry"""
    queue_entry = db.query(OPDQueue).filter(
        OPDQueue.id == queue_id,
        OPDQueue.is_active == True
    ).first()
    
    if not queue_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue entry not found"
        )
    
    return queue_entry


@router.post("/{queue_id}/start")
def start_queue_entry(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Mark queue entry as in progress (doctor starts seeing patient)"""
    queue_entry = db.query(OPDQueue).filter(
        OPDQueue.id == queue_id,
        OPDQueue.is_active == True
    ).first()
    
    if not queue_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue entry not found"
        )
    
    queue_entry.status = QueueStatus.IN_PROGRESS
    queue_entry.started_at = datetime.now()
    queue_entry.assigned_clinician_id = current_user.id
    
    db.commit()
    db.refresh(queue_entry)
    
    return queue_entry


@router.post("/{queue_id}/complete")
def complete_queue_entry(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Mark queue entry as completed"""
    queue_entry = db.query(OPDQueue).filter(
        OPDQueue.id == queue_id,
        OPDQueue.is_active == True
    ).first()
    
    if not queue_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue entry not found"
        )
    
    queue_entry.status = QueueStatus.COMPLETED
    queue_entry.completed_at = datetime.now()
    
    db.commit()
    db.refresh(queue_entry)
    
    return queue_entry


@router.post("/{queue_id}/cancel")
def cancel_queue_entry(
    queue_id: int,
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Nurse"]))
):
    """Cancel queue entry"""
    queue_entry = db.query(OPDQueue).filter(
        OPDQueue.id == queue_id,
        OPDQueue.is_active == True
    ).first()
    
    if not queue_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue entry not found"
        )
    
    queue_entry.status = QueueStatus.CANCELLED
    
    if reason:
        queue_entry.notes = f"Cancelled: {reason}\n\n{queue_entry.notes or ''}"
    
    db.commit()
    db.refresh(queue_entry)
    
    return queue_entry


@router.post("/{queue_id}/check-in")
def check_in_patient(
    queue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Nurse"]))
):
    """Check in patient (vitals completed) and mark as in_progress"""
    queue_entry = db.query(OPDQueue).filter(
        OPDQueue.id == queue_id,
        OPDQueue.is_active == True
    ).first()
    
    if not queue_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue entry not found"
        )
    
    # Update status to in_progress
    queue_entry.status = QueueStatus.IN_PROGRESS
    queue_entry.started_at = datetime.now()
    
    db.commit()
    db.refresh(queue_entry)
    
    # Redirect back to queue page
    from urllib.parse import urlencode
    query_params = urlencode({"status": "updated"})
    return RedirectResponse(
        url=f"/api/v1/appointments/queue?{query_params}",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/department/{department}/stats")
def get_department_queue_stats(
    department: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get queue statistics for a department"""
    from datetime import date
    
    today = date.today()
    
    total_waiting = db.query(OPDQueue).filter(
        OPDQueue.department == department,
        OPDQueue.status == QueueStatus.WAITING,
        OPDQueue.is_active == True
    ).count()
    
    total_in_progress = db.query(OPDQueue).filter(
        OPDQueue.department == department,
        OPDQueue.status == QueueStatus.IN_PROGRESS,
        OPDQueue.is_active == True
    ).count()
    
    total_completed_today = db.query(OPDQueue).filter(
        OPDQueue.department == department,
        OPDQueue.status == QueueStatus.COMPLETED,
        OPDQueue.completed_at >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        OPDQueue.is_active == True
    ).count()
    
    return {
        "department": department,
        "waiting": total_waiting,
        "in_progress": total_in_progress,
        "completed_today": total_completed_today,
        "total_active": total_waiting + total_in_progress
    }
