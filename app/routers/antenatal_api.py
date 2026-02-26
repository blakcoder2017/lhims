"""
Antenatal Visits API Routes

API endpoints for antenatal visit data.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette import status
import logging

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.crud import antenatal_crud

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/v1/antenatal/visits/{visit_id}/vitals", name="get_antenatal_vitals")
def get_antenatal_vitals(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """API endpoint to fetch vitals data for a specific antenatal visit."""
    logger.info(f"[ANTENATAL_API] Fetching vitals for visit_id={visit_id}")
    visit = antenatal_crud.get_antenatal_visit(db, visit_id)
    logger.info(f"[ANTENATAL_API] Fetched visit: {visit}")
    if not visit:
        logger.warning(f"[ANTENATAL_API] Visit {visit_id} not found or inactive")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Antenatal visit not found"}
        )
    
    # Debug: Log raw vitals values
    logger.info(f"[ANTENATAL_API] Raw vitals - BP: {visit.blood_pressure_systolic}/{visit.blood_pressure_diastolic}, "
                f"Weight: {visit.weight_kg}, FHR: {visit.fetal_heart_rate}, Hb: {visit.hemoglobin}")
    
    vitals_data = {
        "visit_id": visit.id,
        "patient_id": visit.patient_id,
        "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
        "visit_number": visit.visit_number,
        "gestational_weeks": float(visit.gestational_weeks) if visit.gestational_weeks else None,
        "patient": {
            "id": visit.patient.id,
            "first_name": visit.patient.first_name,
            "last_name": visit.patient.last_name,
            "patient_number": visit.patient.patient_number,
        } if visit.patient else None,
        "vitals": {
            "blood_pressure": {
                "systolic": visit.blood_pressure_systolic,
                "diastolic": visit.blood_pressure_diastolic,
                "display": f"{visit.blood_pressure_systolic or '–'}/{visit.blood_pressure_diastolic or '–'}" if (visit.blood_pressure_systolic or visit.blood_pressure_diastolic) else "N/A",
                "is_elevated": (visit.blood_pressure_systolic or 0) >= 140 or (visit.blood_pressure_diastolic or 0) >= 90,
            },
            "weight_kg": float(visit.weight_kg) if visit.weight_kg else None,
            "height_cm": float(visit.height_cm) if visit.height_cm else None,
            "bmi": float(visit.bmi) if visit.bmi else None,
        },
        "fetal_assessment": {
            "fetal_heart_rate": visit.fetal_heart_rate,
            "fundal_height_cm": float(visit.fundal_height_cm) if visit.fundal_height_cm else None,
            "fetal_position": visit.fetal_position,
            "fetal_movement": visit.fetal_movement,
        },
        "lab_investigations": {
            "hemoglobin": float(visit.hemoglobin) if visit.hemoglobin else None,
            "urine_protein": visit.urine_protein,
            "blood_group": visit.blood_group,
            "rhesus_factor": visit.rhesus_factor,
        },
        "care": {
            "supplements_prescribed": visit.supplements_prescribed,
            "counseling_given": visit.counseling_given,
            "risk_factors": visit.risk_factors,
            "complications": visit.complications,
        },
        "follow_up": {
            "next_visit_date": visit.next_visit_date.isoformat() if visit.next_visit_date else None,
            "notes": visit.notes,
        },
        "recorded_by": {
            "id": visit.recorded_by.id,
            "full_name": visit.recorded_by.full_name if visit.recorded_by else None,
            "username": visit.recorded_by.username if visit.recorded_by else None,
        } if visit.recorded_by else None,
        "created_at": visit.created_at.isoformat() if visit.created_at else None,
        "updated_at": visit.updated_at.isoformat() if visit.updated_at else None,
    }
    
    return JSONResponse(content=vitals_data)


@router.get("/api/v1/antenatal/visits/{visit_id}", name="get_antenatal_visit")
def get_antenatal_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Doctor", "Nurse", "Clinician", "Midwife"])),
):
    """API endpoint to fetch complete antenatal visit data."""
    visit = antenatal_crud.get_antenatal_visit(db, visit_id)
    if not visit:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Antenatal visit not found"}
        )
    
    visit_data = {
        "id": visit.id,
        "patient_id": visit.patient_id,
        "encounter_id": visit.encounter_id,
        "recorded_by_id": visit.recorded_by_id,
        "visit_date": visit.visit_date.isoformat() if visit.visit_date else None,
        "visit_number": visit.visit_number,
        "gestational_weeks": float(visit.gestational_weeks) if visit.gestational_weeks else None,
        "lmp": visit.lmp.isoformat() if visit.lmp else None,
        "edd": visit.edd.isoformat() if visit.edd else None,
        "blood_pressure_systolic": visit.blood_pressure_systolic,
        "blood_pressure_diastolic": visit.blood_pressure_diastolic,
        "weight_kg": float(visit.weight_kg) if visit.weight_kg else None,
        "height_cm": float(visit.height_cm) if visit.height_cm else None,
        "bmi": float(visit.bmi) if visit.bmi else None,
        "fetal_heart_rate": visit.fetal_heart_rate,
        "fundal_height_cm": float(visit.fundal_height_cm) if visit.fundal_height_cm else None,
        "fetal_position": visit.fetal_position,
        "fetal_movement": visit.fetal_movement,
        "hemoglobin": float(visit.hemoglobin) if visit.hemoglobin else None,
        "urine_protein": visit.urine_protein,
        "blood_group": visit.blood_group,
        "rhesus_factor": visit.rhesus_factor,
        "risk_factors": visit.risk_factors,
        "complications": visit.complications,
        "counseling_given": visit.counseling_given,
        "supplements_prescribed": visit.supplements_prescribed,
        "next_visit_date": visit.next_visit_date.isoformat() if visit.next_visit_date else None,
        "notes": visit.notes,
        "is_active": visit.is_active,
        "created_at": visit.created_at.isoformat() if visit.created_at else None,
        "updated_at": visit.updated_at.isoformat() if visit.updated_at else None,
        "patient": {
            "id": visit.patient.id,
            "first_name": visit.patient.first_name,
            "last_name": visit.patient.last_name,
            "patient_number": visit.patient.patient_number,
            "date_of_birth": visit.patient.date_of_birth.isoformat() if visit.patient.date_of_birth else None,
            "gender": visit.patient.gender,
        } if visit.patient else None,
        "recorded_by": {
            "id": visit.recorded_by.id,
            "full_name": visit.recorded_by.full_name if visit.recorded_by else None,
            "username": visit.recorded_by.username if visit.recorded_by else None,
        } if visit.recorded_by else None,
    }
    
    return JSONResponse(content=visit_data)
