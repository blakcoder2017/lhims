from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.crud import drug_administration_crud
from app.schemas.drug_administration_schemas import (
    DispensedDrugResponse,
    DrugAdministrationCreate,
    DrugAdministrationResponse
)

router = APIRouter(prefix="/api/v1", tags=["Drug Administration"])


@router.get("/admissions/{admission_number}/dispensed_drugs", response_model=List[DispensedDrugResponse])
def get_dispensed_drugs(
    admission_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all prescriptions (dispensed drugs) for a given admission.
    Returns all prescriptions regardless of status - no filtering by Completed or Dispensed By.
    """
    try:
        print(f"API: Fetching drugs for admission_number: {admission_number}")
        drugs = drug_administration_crud.get_dispensed_drugs_by_admission(db, admission_number)
        
        print(f"API: Received {len(drugs) if drugs else 0} drugs from CRUD")
        
        if not drugs:
            print(f"API: No drugs found, returning empty list")
            return []
        
        print(f"API: Returning {len(drugs)} drugs")
        return drugs
    except Exception as e:
        import traceback
        print(f"Error fetching dispensed drugs for admission {admission_number}: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching drugs: {str(e)}"
        )


@router.post("/drug_administrations/record", response_model=DrugAdministrationResponse, status_code=status.HTTP_201_CREATED)
def record_drug_administration(
    administration_data: DrugAdministrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Doctor", "Admin"]))
):
    """
    Record a drug administration.
    Creates a new drug administration record in the database.
    """
    # Verify prescription exists and is valid
    from app.models.encounter_models import Prescription
    prescription = db.query(Prescription).filter(Prescription.id == administration_data.medication_identifier).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription with ID {administration_data.medication_identifier} not found"
        )
    
    # Create drug administration record
    drug_administration = drug_administration_crud.create_drug_administration(
        db=db,
        admission_number=administration_data.admission_number,
        medication_identifier=administration_data.medication_identifier,
        administration_time=administration_data.administration_time,
        administered_by_id=administration_data.administered_by,
        dosage_given=administration_data.dosage_given,
        route=administration_data.route,
        notes=administration_data.notes
    )
    
    if not drug_administration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create drug administration record. Please verify admission number and prescription ID."
        )
    
    return drug_administration

