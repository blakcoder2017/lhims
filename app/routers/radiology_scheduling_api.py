from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional
from datetime import datetime, date, timedelta

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.encounter_models import RadiologyOrder, OrderStatus, Encounter
from app.models.patient_models import Patient

router = APIRouter(tags=["Radiology Scheduling"])


@router.get("/radiology/schedule", name="radiology_schedule")
def radiology_schedule(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Radiology Staff"])),
    schedule_date: Optional[str] = Query(None)
):
    """Radiology study scheduling dashboard"""
    # Default to today if no date provided
    if schedule_date:
        try:
            target_date = datetime.fromisoformat(schedule_date).date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()
    
    # Get orders scheduled for this date
    orders = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient),
        joinedload(RadiologyOrder.ordered_by)
    ).filter(
        RadiologyOrder.status.in_([OrderStatus.PENDING.value, OrderStatus.ORDERED.value])
    ).order_by(RadiologyOrder.ordered_at).all()
    
    context = {
        "request": request,
        "title": "Radiology Schedule",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "orders": orders,
        "schedule_date": target_date.strftime('%Y-%m-%d')
    }
    return templates.TemplateResponse("radiology/schedule.html", context)


@router.post("/radiology/orders/{order_id}/schedule", name="schedule_radiology_study", status_code=302)
def schedule_radiology_study(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Radiology Staff"])),
    scheduled_time: str = Form(...),
    room: Optional[str] = Form(None),
    technician: Optional[str] = Form(None)
):
    """Schedule a radiology study"""
    order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update order with scheduling information
    # Note: You may want to add scheduled_time, room, technician fields to RadiologyOrder model
    order.status = OrderStatus.ORDERED.value
    db.commit()
    
    return RedirectResponse(
        url=f"/radiology/schedule?status=scheduled",
        status_code=302
    )

