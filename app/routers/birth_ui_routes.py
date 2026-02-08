"""
Birth / Delivery UI Routes

Birth records and delivery tracking.
"""
from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import date, time, datetime
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.birth_models import BirthRecord, DeliveryType, BirthOutcome, Gender
from app.crud import birth_crud, patient_crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/births/dashboard", name="births_dashboard")
def births_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Births dashboard with stats."""
    today = date.today()

    total_births = (
        db.query(BirthRecord).filter(BirthRecord.is_active == True).count()
    )
    births_today = (
        db.query(BirthRecord)
        .filter(BirthRecord.birth_date == today, BirthRecord.is_active == True)
        .count()
    )
    live_births_today = (
        db.query(BirthRecord)
        .filter(
            BirthRecord.birth_date == today,
            BirthRecord.birth_outcome == BirthOutcome.LIVE.value,
            BirthRecord.is_active == True,
        )
        .count()
    )

    recent_births, _ = birth_crud.get_birth_records(db, skip=0, limit=15)

    context = {
        "request": request,
        "title": "Births / Delivery Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "total_births": total_births,
        "births_today": births_today,
        "live_births_today": live_births_today,
        "recent_births": recent_births,
    }
    return templates.TemplateResponse("births/births_dashboard.html", context)


@router.get("/births", name="births_list")
def births_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    mother_id: Optional[int] = Query(None),
    birth_outcome: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """List birth records."""
    records, total = birth_crud.get_birth_records(
        db, skip=0, limit=limit, mother_id=mother_id, birth_outcome=birth_outcome
    )
    context = {
        "request": request,
        "title": "Birth Records",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "birth_records": records,
        "total": total,
        "mother_id": mother_id,
        "birth_outcome_filter": birth_outcome,
    }
    return templates.TemplateResponse("births/births_list.html", context)


@router.get("/births/create", name="birth_record_create_form")
def birth_record_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    mother_id: Optional[int] = Query(None),
):
    """Form to create birth record."""
    mother = patient_crud.get_patient(db, mother_id) if mother_id else None
    today = date.today()
    # Get mother's antenatal visits if she's selected
    antenatal_visits = []
    if mother_id:
        from app.crud import antenatal_crud
        antenatal_visits = antenatal_crud.get_antenatal_visits_by_patient(db, mother_id, limit=10)
    context = {
        "request": request,
        "title": "Record Birth / Delivery",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "mother": mother,
        "mother_id": mother_id,
        "today": today.strftime("%Y-%m-%d"),
        "antenatal_visits": antenatal_visits,
        "delivery_types": [t.value for t in DeliveryType],
        "birth_outcomes": [o.value for o in BirthOutcome],
        "genders": [g.value for g in Gender],
    }
    return templates.TemplateResponse("births/birth_record_form.html", context)


@router.post("/births/create", name="birth_record_create_submit")
def birth_record_create_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    mother_patient_id: int = Form(...),
    birth_date: date = Form(...),
    birth_time: Optional[str] = Form(None),
    delivery_type: str = Form("vaginal"),
    birth_outcome: str = Form("live"),
    gender: Optional[str] = Form(None),
    weight_kg: Optional[float] = Form(None),
    length_cm: Optional[float] = Form(None),
    head_circumference_cm: Optional[float] = Form(None),
    apgar_1min: Optional[int] = Form(None),
    apgar_5min: Optional[int] = Form(None),
    apgar_10min: Optional[int] = Form(None),
    gravida: Optional[int] = Form(None),
    para: Optional[int] = Form(None),
    complications: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
):
    """Create birth record."""
    birth_time_obj = None
    if birth_time:
        try:
            parts = birth_time.split(":")
            birth_time_obj = time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            pass

    birth_crud.create_birth_record(
        db,
        mother_patient_id=mother_patient_id,
        birth_date=birth_date,
        birth_time=birth_time_obj,
        delivery_type=delivery_type,
        birth_outcome=birth_outcome,
        gender=gender,
        weight_kg=Decimal(str(weight_kg)) if weight_kg else None,
        length_cm=Decimal(str(length_cm)) if length_cm else None,
        head_circumference_cm=Decimal(str(head_circumference_cm)) if head_circumference_cm else None,
        apgar_1min=apgar_1min,
        apgar_5min=apgar_5min,
        apgar_10min=apgar_10min,
        gravida=gravida,
        para=para,
        complications=complications,
        notes=notes,
        delivered_by_id=current_user.id,
    )
    return RedirectResponse(
        url=request.url_for("births_dashboard") + "?status=birth_recorded",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/births/{record_id}", name="birth_record_detail")
def birth_record_detail(
    request: Request,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """View birth record detail."""
    record = birth_crud.get_birth_record(db, record_id)
    if not record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Birth record not found")
    # Get mother's antenatal visits
    antenatal_visits = []
    if record.mother_patient_id:
        from app.crud import antenatal_crud
        antenatal_visits = antenatal_crud.get_antenatal_visits_by_patient(db, record.mother_patient_id, limit=10)
    context = {
        "request": request,
        "title": f"Birth Record – {record.birth_number or 'N/A'}",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "record": record,
        "antenatal_visits": antenatal_visits,
    }
    return templates.TemplateResponse("births/birth_record_detail.html", context)
