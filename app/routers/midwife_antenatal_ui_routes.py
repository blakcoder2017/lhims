"""
Midwife / Antenatal UI Routes

Antenatal care (ANC) visit tracking and midwife module.
"""
from fastapi import APIRouter, Request, Depends, Query, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, JSONResponse
from app.core.templates import templates
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
    high_risk_count = (
        db.query(func.count(AntenatalVisit.id))
        .filter(AntenatalVisit.risk_factors.isnot(None), AntenatalVisit.risk_factors != '', AntenatalVisit.is_active == True)
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
        "high_risk_count": high_risk_count,
        "recent_visits": recent_visits,
        "upcoming_visits": upcoming_visits,
    }
    return templates.TemplateResponse("midwife/antenatal_dashboard.html", context)


@router.get("/midwife/visits/all", name="midwife_antenatal_visits_list")
def antenatal_visits_list_all(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    limit: int = Query(50, le=200),
):
    """List all antenatal visits."""
    visits, total = antenatal_crud.get_antenatal_visits(
        db, skip=0, limit=limit, patient_id=None
    )
    context = {
        "request": request,
        "title": "All Antenatal Visits",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "visits": visits,
        "total": total,
        "patient_id": None,
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


# =====================================================
# SPECIFIC VISIT ROUTES - Must come before {patient_id} route
# =====================================================

@router.get("/midwife/visits/{visit_id}", name="midwife_antenatal_visit_detail")
def antenatal_visit_detail(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """View antenatal visit detail."""
    visit = antenatal_crud.get_antenatal_visit(db, visit_id)
    print(f"[MIDWIFE_DETAIL] Fetched visit {visit_id}: {visit}")
    if not visit:
        print(f"[MIDWIFE_DETAIL] Visit {visit_id} NOT FOUND")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Antenatal visit not found")
    print(f"[MIDWIFE_DETAIL] Visit {visit_id} - patient: {visit.patient}, visit_date: {visit.visit_date}")
    print(f"[MIDWIFE_DETAIL] Vitals - BP: {visit.blood_pressure_systolic}/{visit.blood_pressure_diastolic}, Weight: {visit.weight_kg}, FHR: {visit.fetal_heart_rate}")
    print(f"[MIDWIFE_DETAIL] Template vars - visit.id: {visit.id}, visit.patient_id: {visit.patient_id}")
    context = {
        "request": request,
        "title": f"Antenatal Visit – {visit.patient.first_name if visit.patient else 'N/A'}",
        "current_user": current_user,
        "user_role": current_user.role.name if (current_user and current_user.role) else "Guest",
        "visit": visit,
    }
    return templates.TemplateResponse("midwife/antenatal_visit_detail.html", context)


@router.get("/midwife/visits/{visit_id}/json", name="midwife_antenatal_visit_json")
def antenatal_visit_json(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """Debug endpoint to return visit data as JSON."""
    visit = antenatal_crud.get_antenatal_visit(db, visit_id)
    if not visit:
        return JSONResponse(status_code=404, content={"detail": "Visit not found"})
    
    # Force fetch all attributes to ensure they're loaded
    data = {
        "id": visit.id,
        "patient_id": visit.patient_id,
        "visit_date": str(visit.visit_date) if visit.visit_date else None,
        "blood_pressure_systolic": visit.blood_pressure_systolic,
        "blood_pressure_diastolic": visit.blood_pressure_diastolic,
        "weight_kg": float(visit.weight_kg) if visit.weight_kg else None,
        "fetal_heart_rate": visit.fetal_heart_rate,
        "fundal_height_cm": float(visit.fundal_height_cm) if visit.fundal_height_cm else None,
        "hemoglobin": float(visit.hemoglobin) if visit.hemoglobin else None,
    }
    print(f"[MIDWIFE_JSON] Visit {visit_id} data: {data}")
    return JSONResponse(content=data)


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
    visit_number: Optional[int] = Form(default=None),
    gestational_weeks: Optional[float] = Form(default=None),
    lmp: Optional[str] = Form(default=None),
    edd: Optional[str] = Form(default=None),
    blood_pressure_systolic: Optional[int] = Form(default=None),
    blood_pressure_diastolic: Optional[int] = Form(default=None),
    weight_kg: Optional[float] = Form(default=None),
    height_cm: Optional[float] = Form(default=None),
    fetal_heart_rate: Optional[int] = Form(default=None),
    fundal_height_cm: Optional[float] = Form(default=None),
    fetal_position: Optional[str] = Form(default=None),
    fetal_movement: Optional[str] = Form(default=None),
    hemoglobin: Optional[float] = Form(default=None),
    urine_protein: Optional[str] = Form(default=None),
    blood_group: Optional[str] = Form(default=None),
    rhesus_factor: Optional[str] = Form(default=None),
    supplements_prescribed: Optional[str] = Form(default=None),
    counseling_given: Optional[str] = Form(default=None),
    risk_factors: Optional[str] = Form(default=None),
    next_visit_date: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
):
    """Update antenatal visit."""
    
    # Convert date strings to date objects
    def to_date(value):
        """Convert string to date object, returning None for empty/invalid values."""
        if value is None or value == '':
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            try:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S').date()
            except ValueError:
                return None
    
    lmp_date = to_date(lmp)
    edd_date = to_date(edd)
    next_visit = to_date(next_visit_date)
    
    visit = antenatal_crud.update_antenatal_visit(
        db,
        visit_id,
        visit_date=visit_date,
        visit_number=visit_number,
        gestational_weeks=Decimal(str(gestational_weeks)) if gestational_weeks else None,
        lmp=lmp_date,
        edd=edd_date,
        blood_pressure_systolic=blood_pressure_systolic,
        blood_pressure_diastolic=blood_pressure_diastolic,
        weight_kg=Decimal(str(weight_kg)) if weight_kg else None,
        height_cm=Decimal(str(height_cm)) if height_cm else None,
        fetal_heart_rate=fetal_heart_rate,
        fundal_height_cm=Decimal(str(fundal_height_cm)) if fundal_height_cm else None,
        fetal_position=fetal_position,
        fetal_movement=fetal_movement,
        hemoglobin=Decimal(str(hemoglobin)) if hemoglobin else None,
        urine_protein=urine_protein,
        blood_group=blood_group,
        rhesus_factor=rhesus_factor,
        supplements_prescribed=supplements_prescribed,
        counseling_given=counseling_given,
        risk_factors=risk_factors,
        next_visit_date=next_visit,
        notes=notes,
    )
    if not visit:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Antenatal visit not found")
    return RedirectResponse(
        url=str(request.url_for("midwife_antenatal_visit_detail", visit_id=visit_id)) + "?status=updated",
        status_code=status.HTTP_302_FOUND,
    )


# =====================================================
# GENERAL PATIENT ROUTES - Must come after specific routes
# =====================================================

@router.get("/midwife/visits/{patient_id}", name="midwife_antenatal_visits_list_patient")
def antenatal_visits_list_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    limit: int = Query(50, le=200),
):
    """List antenatal visits for a specific patient."""
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


import logging

logger = logging.getLogger(__name__)

# =====================================================
# CREATE VISIT POST ROUTE
# =====================================================

@router.post("/midwife/visits/create", name="midwife_antenatal_visit_create_submit")
def antenatal_visit_create_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
    patient_id: int = Form(...),
    visit_date: date = Form(...),
    visit_number: Optional[str] = Form(default=None),
    gestational_weeks: Optional[str] = Form(default=None),
    lmp: Optional[str] = Form(default=None),
    edd: Optional[str] = Form(default=None),
    blood_pressure_systolic: Optional[str] = Form(default=None),
    blood_pressure_diastolic: Optional[str] = Form(default=None),
    weight_kg: Optional[str] = Form(default=None),
    height_cm: Optional[str] = Form(default=None),
    fetal_heart_rate: Optional[str] = Form(default=None),
    fundal_height_cm: Optional[str] = Form(default=None),
    fetal_position: Optional[str] = Form(default=None),
    fetal_movement: Optional[str] = Form(default=None),
    hemoglobin: Optional[str] = Form(default=None),
    urine_protein: Optional[str] = Form(default=None),
    blood_group: Optional[str] = Form(default=None),
    rhesus_factor: Optional[str] = Form(default=None),
    supplements_prescribed: Optional[str] = Form(default=None),
    counseling_given: Optional[str] = Form(default=None),
    risk_factors: Optional[str] = Form(default=None),
    next_visit_date: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
):
    """Create antenatal visit."""
    print(f"[MIDWIFE_CREATE] patient_id={patient_id}, visit_date={visit_date}, fundal_height_cm={fundal_height_cm}, hemoglobin={hemoglobin}")
    
    # Validate required fields
    if not patient_id or patient_id <= 0:
        print(f"[MIDWIFE_CREATE] Invalid patient_id: {patient_id}")
        return RedirectResponse(
            url=str(request.url_for("midwife_antenatal_visit_create_form")) + "?error=" + "Patient+is+required",
            status_code=status.HTTP_302_FOUND,
        )
    
    if not visit_date:
        print(f"[MIDWIFE_CREATE] Missing visit_date")
        return RedirectResponse(
            url=str(request.url_for("midwife_antenatal_visit_create_form")) + "?error=" + "Visit+date+is+required",
            status_code=status.HTTP_302_FOUND,
        )
    
    # Convert string values to appropriate types
    def to_int(value):
        if value is None or value == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def to_float(value):
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def to_date(value):
        """Convert string to date object, returning None for empty/invalid values."""
        if value is None or value == '':
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try with time component
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S').date()
            except ValueError:
                return None
    
    # Convert date strings to date objects
    lmp_date = to_date(lmp)
    edd_date = to_date(edd)
    next_visit = to_date(next_visit_date)
    
    try:
        antenatal_crud.create_antenatal_visit(
            db,
            patient_id=patient_id,
            visit_date=visit_date,
            visit_number=to_int(visit_number),
            gestational_weeks=Decimal(str(to_float(gestational_weeks))) if to_float(gestational_weeks) else None,
            lmp=lmp_date,
            edd=edd_date,
            blood_pressure_systolic=to_int(blood_pressure_systolic),
            blood_pressure_diastolic=to_int(blood_pressure_diastolic),
            weight_kg=Decimal(str(to_float(weight_kg))) if to_float(weight_kg) else None,
            height_cm=Decimal(str(to_float(height_cm))) if to_float(height_cm) else None,
            fetal_heart_rate=to_int(fetal_heart_rate),
            fundal_height_cm=Decimal(str(to_float(fundal_height_cm))) if to_float(fundal_height_cm) else None,
            fetal_position=fetal_position,
            fetal_movement=fetal_movement,
            hemoglobin=Decimal(str(to_float(hemoglobin))) if to_float(hemoglobin) else None,
            urine_protein=urine_protein,
            blood_group=blood_group,
            rhesus_factor=rhesus_factor,
            supplements_prescribed=supplements_prescribed,
            counseling_given=counseling_given,
            risk_factors=risk_factors,
            next_visit_date=next_visit,
            notes=notes,
            recorded_by_id=current_user.id,
        )
        return RedirectResponse(
            url=str(request.url_for("midwife_antenatal_dashboard")) + "?status=visit_created",
            status_code=status.HTTP_302_FOUND,
        )
    except ValueError as ve:
        print(f"[MIDWIFE_CREATE] Validation error: {ve}")
        return RedirectResponse(
            url=str(request.url_for("midwife_antenatal_visit_create_form")) + f"?error={str(ve).replace(' ', '+')}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        print(f"[MIDWIFE_CREATE] Unexpected error: {e}")
        return RedirectResponse(
            url=str(request.url_for("midwife_antenatal_visit_create_form")) + "?error=An+unexpected+error+occurred",
            status_code=status.HTTP_302_FOUND,
        )
