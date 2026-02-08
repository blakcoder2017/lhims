"""
Midwife / Antenatal UI Routes

Antenatal care (ANC) visit tracking and midwife module.
"""
from fastapi import APIRouter, Request, Depends, Query, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.antenatal_models import AntenatalVisit
from app.models.patient_models import Patient
from app.crud import antenatal_crud, patient_crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/midwife/dashboard", name="midwife_antenatal_dashboard")
def midwife_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Midwife/Antenatal dashboard with stats and upcoming visits."""
    today = date.today()

    # Stats
    total_visits = (
        db.query(func.count(AntenatalVisit.id))
        .filter(AntenatalVisit.is_active == True)
        .scalar()
        or 0
    )
    visits_today = (
        db.query(func.count(AntenatalVisit.id))
        .filter(AntenatalVisit.visit_date == today, AntenatalVisit.is_active == True)
        .scalar()
        or 0
    )
    upcoming_visits_count = (
        db.query(func.count(AntenatalVisit.id))
        .filter(AntenatalVisit.next_visit_date >= today, AntenatalVisit.is_active == True)
        .scalar()
        or 0
    )

    # Recent visits
    recent_visits, _ = antenatal_crud.get_antenatal_visits(
        db, skip=0, limit=15, to_date=today
    )
    upcoming_visits = (
        db.query(AntenatalVisit)
        .options(joinedload(AntenatalVisit.patient), joinedload(AntenatalVisit.recorded_by))
        .filter(AntenatalVisit.next_visit_date >= today, AntenatalVisit.is_active == True)
        .order_by(AntenatalVisit.next_visit_date.asc())
        .limit(15)
        .all()
    )

    context = {
        "request": request,
        "title": "Midwife / Antenatal Dashboard",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "total_visits": total_visits,
        "visits_today": visits_today,
        "upcoming_visits_count": upcoming_visits_count,
        "recent_visits": recent_visits,
        "upcoming_visits": upcoming_visits,
    }
    return templates.TemplateResponse("midwife/antenatal_dashboard.html", context)


@router.get("/midwife/visits", name="midwife_antenatal_visits_list")
def antenatal_visits_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    patient_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
):
    """List antenatal visits."""
    visits, total = antenatal_crud.get_antenatal_visits(
        db, skip=0, limit=limit, patient_id=patient_id
    )
    context = {
        "request": request,
        "title": "Antenatal Visits",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "visits": visits,
        "total": total,
        "patient_id": patient_id,
    }
    return templates.TemplateResponse("midwife/antenatal_visits_list.html", context)


@router.get("/midwife/visits/create", name="midwife_antenatal_visit_create_form")
def antenatal_visit_create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    patient_id: Optional[int] = Query(None),
):
    """Form to create antenatal visit."""
    patient = patient_crud.get_patient(db, patient_id) if patient_id else None
    today = date.today()
    context = {
        "request": request,
        "title": "New Antenatal Visit",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "patient": patient,
        "patient_id": patient_id,
        "today": today.strftime("%Y-%m-%d"),
        "visit": None,
    }
    return templates.TemplateResponse("midwife/antenatal_visit_form.html", context)


@router.post("/midwife/visits/create", name="midwife_antenatal_visit_create_submit")
def antenatal_visit_create_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    patient_id: int = Form(...),
    visit_date: date = Form(...),
    visit_number: Optional[int] = Form(None),
    gestational_weeks: Optional[float] = Form(None),
    lmp: Optional[date] = Form(None),
    edd: Optional[date] = Form(None),
    blood_pressure_systolic: Optional[int] = Form(None),
    blood_pressure_diastolic: Optional[int] = Form(None),
    weight_kg: Optional[float] = Form(None),
    height_cm: Optional[float] = Form(None),
    fetal_heart_rate: Optional[int] = Form(None),
    fundal_height_cm: Optional[float] = Form(None),
    fetal_position: Optional[str] = Form(None),
    hemoglobin: Optional[float] = Form(None),
    urine_protein: Optional[str] = Form(None),
    blood_group: Optional[str] = Form(None),
    rhesus_factor: Optional[str] = Form(None),
    supplements_prescribed: Optional[str] = Form(None),
    counseling_given: Optional[str] = Form(None),
    risk_factors: Optional[str] = Form(None),
    next_visit_date: Optional[date] = Form(None),
    notes: Optional[str] = Form(None),
):
    """Create antenatal visit."""
    antenatal_crud.create_antenatal_visit(
        db,
        patient_id=patient_id,
        visit_date=visit_date,
        visit_number=visit_number,
        gestational_weeks=Decimal(str(gestational_weeks)) if gestational_weeks else None,
        lmp=lmp,
        edd=edd,
        blood_pressure_systolic=blood_pressure_systolic,
        blood_pressure_diastolic=blood_pressure_diastolic,
        weight_kg=Decimal(str(weight_kg)) if weight_kg else None,
        height_cm=Decimal(str(height_cm)) if height_cm else None,
        fetal_heart_rate=fetal_heart_rate,
        fundal_height_cm=Decimal(str(fundal_height_cm)) if fundal_height_cm else None,
        fetal_position=fetal_position,
        hemoglobin=Decimal(str(hemoglobin)) if hemoglobin else None,
        urine_protein=urine_protein,
        blood_group=blood_group,
        rhesus_factor=rhesus_factor,
        supplements_prescribed=supplements_prescribed,
        counseling_given=counseling_given,
        risk_factors=risk_factors,
        next_visit_date=next_visit_date,
        notes=notes,
        recorded_by_id=current_user.id,
    )
    return RedirectResponse(
        url=request.url_for("midwife_antenatal_dashboard") + "?status=visit_created",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/midwife/visits/{visit_id}", name="midwife_antenatal_visit_detail")
def antenatal_visit_detail(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """View antenatal visit detail."""
    visit = antenatal_crud.get_antenatal_visit(db, visit_id)
    if not visit:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Antenatal visit not found")
    context = {
        "request": request,
        "title": f"Antenatal Visit – {visit.patient.first_name if visit.patient else 'N/A'}",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "visit": visit,
    }
    return templates.TemplateResponse("midwife/antenatal_visit_detail.html", context)


@router.get("/midwife/visits/{visit_id}/edit", name="midwife_antenatal_visit_edit_form")
def antenatal_visit_edit_form(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Form to edit antenatal visit."""
    visit = antenatal_crud.get_antenatal_visit(db, visit_id)
    if not visit:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Antenatal visit not found")
    today = date.today()
    context = {
        "request": request,
        "title": f"Edit Antenatal Visit – {visit.patient.first_name if visit.patient else 'N/A'}",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "visit": visit,
        "today": today.strftime("%Y-%m-%d"),
    }
    return templates.TemplateResponse("midwife/antenatal_visit_form.html", context)


@router.post("/midwife/visits/{visit_id}/edit", name="midwife_antenatal_visit_edit_submit")
def antenatal_visit_edit_submit(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    visit_date: date = Form(...),
    visit_number: Optional[int] = Form(None),
    gestational_weeks: Optional[float] = Form(None),
    lmp: Optional[date] = Form(None),
    edd: Optional[date] = Form(None),
    blood_pressure_systolic: Optional[int] = Form(None),
    blood_pressure_diastolic: Optional[int] = Form(None),
    weight_kg: Optional[float] = Form(None),
    height_cm: Optional[float] = Form(None),
    fetal_heart_rate: Optional[int] = Form(None),
    fundal_height_cm: Optional[float] = Form(None),
    fetal_position: Optional[str] = Form(None),
    hemoglobin: Optional[float] = Form(None),
    urine_protein: Optional[str] = Form(None),
    blood_group: Optional[str] = Form(None),
    rhesus_factor: Optional[str] = Form(None),
    supplements_prescribed: Optional[str] = Form(None),
    counseling_given: Optional[str] = Form(None),
    risk_factors: Optional[str] = Form(None),
    next_visit_date: Optional[date] = Form(None),
    notes: Optional[str] = Form(None),
):
    """Update antenatal visit."""
    visit = antenatal_crud.update_antenatal_visit(
        db,
        visit_id,
        visit_date=visit_date,
        visit_number=visit_number,
        gestational_weeks=Decimal(str(gestational_weeks)) if gestational_weeks else None,
        lmp=lmp,
        edd=edd,
        blood_pressure_systolic=blood_pressure_systolic,
        blood_pressure_diastolic=blood_pressure_diastolic,
        weight_kg=Decimal(str(weight_kg)) if weight_kg else None,
        height_cm=Decimal(str(height_cm)) if height_cm else None,
        fetal_heart_rate=fetal_heart_rate,
        fundal_height_cm=Decimal(str(fundal_height_cm)) if fundal_height_cm else None,
        fetal_position=fetal_position,
        hemoglobin=Decimal(str(hemoglobin)) if hemoglobin else None,
        urine_protein=urine_protein,
        blood_group=blood_group,
        rhesus_factor=rhesus_factor,
        supplements_prescribed=supplements_prescribed,
        counseling_given=counseling_given,
        risk_factors=risk_factors,
        next_visit_date=next_visit_date,
        notes=notes,
    )
    if not visit:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Antenatal visit not found")
    return RedirectResponse(
        url=request.url_for("midwife_antenatal_visit_detail", visit_id=visit_id) + "?status=updated",
        status_code=status.HTTP_302_FOUND,
    )
