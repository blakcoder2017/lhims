"""
OPD (Outpatient Department) UI Routes
Handles all OPD-related user interface routes.
"""
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.encounter_models import Encounter, EncounterStatus
from app.models.appointment_models import OPDQueue, QueueStatus
from app.models.billing_models import Invoice, InvoiceStatus, Payment, PaymentStatus
from app.crud import opd_crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/opd/dashboard", name="opd_dashboard")
def opd_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """OPD dashboard showing visit statistics and active visits"""
    
    today = date.today()
    this_month_start = datetime(today.year, today.month, 1)
    
    # OPD Visit Statistics
    total_visits = db.query(func.count(OPDVisit.id)).filter(
        OPDVisit.is_active == True
    ).scalar() or 0
    
    active_visits = db.query(func.count(OPDVisit.id)).filter(
        OPDVisit.status == OPDVisitStatus.ACTIVE.value,
        OPDVisit.is_active == True
    ).scalar() or 0
    
    completed_visits_today = db.query(func.count(OPDVisit.id)).filter(
        OPDVisit.status == OPDVisitStatus.COMPLETED.value,
        func.date(OPDVisit.completed_at) == today,
        OPDVisit.is_active == True
    ).scalar() or 0
    
    visits_this_month = db.query(func.count(OPDVisit.id)).filter(
        OPDVisit.visit_date >= this_month_start,
        OPDVisit.is_active == True
    ).scalar() or 0
    
    # Queue Statistics
    waiting_patients = db.query(func.count(OPDQueue.id)).filter(
        OPDQueue.status == QueueStatus.WAITING.value,
        OPDQueue.is_active == True
    ).scalar() or 0
    
    checked_in_today = db.query(func.count(OPDQueue.id)).filter(
        OPDQueue.status == QueueStatus.IN_PROGRESS.value,
        func.date(OPDQueue.checked_in_at) == today,
        OPDQueue.is_active == True
    ).scalar() or 0
    
    # Encounter Statistics
    pending_encounters = db.query(func.count(Encounter.id)).filter(
        Encounter.status == EncounterStatus.IN_PROGRESS.value,
        Encounter.opd_visit_id.isnot(None),
        Encounter.is_active == True
    ).scalar() or 0
    
    # Financial Statistics
    revenue_today = db.query(func.sum(Payment.amount)).filter(
        func.date(Payment.payment_date) == today,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).scalar() or Decimal('0.00')
    
    revenue_this_month = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_date >= this_month_start,
        Payment.status == PaymentStatus.COMPLETED.value,
        Payment.is_active == True
    ).scalar() or Decimal('0.00')
    
    # Get recent active visits
    recent_active_visits = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient)
    ).filter(
        OPDVisit.status == OPDVisitStatus.ACTIVE.value,
        OPDVisit.is_active == True
    ).order_by(OPDVisit.visit_date.desc()).limit(10).all()
    
    # Get recent completed visits
    recent_completed_visits = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient)
    ).filter(
        OPDVisit.status == OPDVisitStatus.COMPLETED.value,
        OPDVisit.is_active == True
    ).order_by(OPDVisit.completed_at.desc()).limit(10).all()
    
    # Calculate completion rate (visits completed today / active visits)
    completion_rate = (completed_visits_today / active_visits * 100) if active_visits > 0 else 0
    
    context = {
        "request": request,
        "title": "OPD Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        # Statistics
        "total_visits": total_visits,
        "active_visits": active_visits,
        "completed_visits_today": completed_visits_today,
        "visits_this_month": visits_this_month,
        "waiting_patients": waiting_patients,
        "checked_in_today": checked_in_today,
        "pending_encounters": pending_encounters,
        "revenue_today": revenue_today,
        "revenue_this_month": revenue_this_month,
        "completion_rate": completion_rate,
        # Recent data
        "recent_active_visits": recent_active_visits,
        "recent_completed_visits": recent_completed_visits,
    }
    
    return templates.TemplateResponse("opd/dashboard.html", context)

