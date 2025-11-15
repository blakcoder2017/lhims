from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from app.models.drug_administration_models import DrugAdministration
from app.models.ipd_models import Admission
from app.models.encounter_models import Prescription
from app.schemas.drug_administration_schemas import DrugAdministrationCreate


def get_dispensed_drugs_by_admission(db: Session, admission_number: str) -> List[dict]:
    """
    Get all prescriptions for a given admission.
    Returns all prescriptions regardless of status (no filtering by Completed or Dispensed By).
    """
    # Find admission by admission_number
    admission = db.query(Admission).filter(
        Admission.admission_number == admission_number,
        Admission.is_active == True
    ).first()
    
    if not admission:
        print(f"Admission not found for admission_number: {admission_number}")
        return []
    
    print(f"Found admission ID: {admission.id}, Patient ID: {admission.patient_id}, Encounter ID: {admission.encounter_id}")
    
    # Get all prescriptions from encounters during admission period
    from app.models.encounter_models import Encounter
    from sqlalchemy.orm import joinedload
    from datetime import datetime
    
    prescriptions = []
    
    # Get prescriptions from admission encounter
    if admission.encounter_id:
        encounter_prescriptions = db.query(Prescription).options(
            joinedload(Prescription.prescribed_by)
        ).filter(Prescription.encounter_id == admission.encounter_id).all()
        prescriptions.extend(encounter_prescriptions)
        print(f"Found {len(encounter_prescriptions)} prescriptions from admission encounter")
    
    # Get prescriptions from other encounters during admission period
    # Include all encounters on or after admission date
    other_prescriptions = db.query(Prescription).options(
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.encounter)
    ).join(Encounter).filter(
        Encounter.patient_id == admission.patient_id,
        Encounter.encounter_date >= admission.admission_date.date()
    ).all()
    
    print(f"Found {len(other_prescriptions)} prescriptions from other encounters during admission period")
    
    # Add prescriptions that aren't already in the list (avoid duplicates)
    existing_prescription_ids = {p.id for p in prescriptions}
    for presc in other_prescriptions:
        if presc.id not in existing_prescription_ids:
            prescriptions.append(presc)
    
    print(f"Total unique prescriptions: {len(prescriptions)}")
    
    # Return unique list with medication_identifier, medication_name, and dosage
    result = []
    seen_ids = set()
    for presc in prescriptions:
        if presc.id not in seen_ids:
            seen_ids.add(presc.id)
            result.append({
                "medication_identifier": presc.id,
                "medication_name": presc.medication_name,
                "dosage": presc.dosage
            })
            print(f"Added prescription: {presc.id} - {presc.medication_name} - {presc.dosage}")
    
    print(f"Returning {len(result)} drugs")
    return result


def create_drug_administration(
    db: Session,
    admission_number: str,
    medication_identifier: int,
    administration_time: datetime,
    administered_by_id: int,
    dosage_given: Optional[str] = None,
    route: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[DrugAdministration]:
    """
    Create a new drug administration record.
    """
    # Find admission by admission_number
    admission = db.query(Admission).filter(
        Admission.admission_number == admission_number,
        Admission.is_active == True
    ).first()
    
    if not admission:
        return None
    
    # Verify prescription exists
    prescription = db.query(Prescription).filter(Prescription.id == medication_identifier).first()
    if not prescription:
        return None
    
    # Create drug administration record
    drug_administration = DrugAdministration(
        admission_id=admission.id,
        prescription_id=medication_identifier,
        administered_by_id=administered_by_id,
        administration_time=administration_time,
        dosage_given=dosage_given,
        route=route,
        notes=notes
    )
    
    db.add(drug_administration)
    db.commit()
    db.refresh(drug_administration)
    
    return drug_administration


def get_drug_administrations_by_admission(
    db: Session,
    admission_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[DrugAdministration]:
    """Get all drug administrations for an admission"""
    return db.query(DrugAdministration).filter(
        DrugAdministration.admission_id == admission_id,
        DrugAdministration.is_active == True
    ).order_by(DrugAdministration.administration_time.desc()).offset(skip).limit(limit).all()

