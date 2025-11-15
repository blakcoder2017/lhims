from sqlalchemy.orm import Session, joinedload
from app.models.triage_models import TriageVitals
from app.schemas.triage_schemas import TriageVitalsCreate
from typing import List, Optional

def create_vitals(db: Session, vitals: TriageVitalsCreate):
    """
    Saves a new triage vital signs record to the database.
    Automatically calculates BMI if weight and height are provided.
    """
    vitals_data = vitals.model_dump()
    
    # Create the database object
    db_vitals = TriageVitals(**vitals_data)
    
    # Calculate BMI if weight and height are provided
    if db_vitals.weight and db_vitals.height:
        db_vitals.bmi = db_vitals.calculate_bmi()
    
    # Generate blood_pressure string from systolic/diastolic if not provided
    if not db_vitals.blood_pressure and db_vitals.systolic_bp and db_vitals.diastolic_bp:
        db_vitals.blood_pressure = f"{db_vitals.systolic_bp}/{db_vitals.diastolic_bp} mmHg"
    
    db.add(db_vitals)
    db.commit()
    db.refresh(db_vitals)
    return db_vitals

def get_vitals_history(db: Session, patient_id: int) -> List[TriageVitals]:
    """
    Retrieves all vital signs history for a specific patient, ordered by time (most recent first).
    Supports multiple vital signs per patient.
    Eager loads the recorded_by relationship for efficient querying.
    """
    return db.query(TriageVitals).options(
        joinedload(TriageVitals.recorded_by)
    ).filter(
        TriageVitals.patient_id == patient_id
    ).order_by(TriageVitals.recorded_at.desc()).all()

def get_latest_vitals(db: Session, patient_id: int) -> Optional[TriageVitals]:
    """Get the most recent vital signs record for a patient."""
    return db.query(TriageVitals).options(
        joinedload(TriageVitals.recorded_by)
    ).filter(
        TriageVitals.patient_id == patient_id
    ).order_by(TriageVitals.recorded_at.desc()).first()