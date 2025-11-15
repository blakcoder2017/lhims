from sqlalchemy.orm import Session
from sqlalchemy import func, or_, String
from typing import List, Optional, Tuple

from app.models.patient_models import Patient
from app.schemas.patient_schemas import PatientCreate

def generate_patient_number(db: Session) -> str:
    """Generate a unique patient number starting with DGMS followed by sequential number."""
    # Get the highest existing patient number
    last_patient = db.query(Patient).order_by(Patient.id.desc()).first()
    
    if last_patient and last_patient.patient_number:
        # Extract the number part from the last patient number (e.g., "DGMS000123" -> 123)
        try:
            last_number = int(last_patient.patient_number.replace("DGMS", ""))
            next_number = last_number + 1
        except (ValueError, AttributeError):
            # If parsing fails, count total patients
            total_patients = db.query(func.count(Patient.id)).scalar()
            next_number = total_patients + 1
    else:
        # First patient or no patient_number exists
        total_patients = db.query(func.count(Patient.id)).scalar()
        next_number = total_patients + 1
    
    # Format as DGMS + 6-digit number (e.g., DGMS000001)
    return f"DGMS{next_number:06d}"

def create_patient(db: Session, patient: PatientCreate):
    """
    Create a new patient with auto-generated patient number.
    """
    # Generate patient number
    patient_number = generate_patient_number(db)
    
    # Create patient object
    db_patient = Patient(
        patient_number=patient_number,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        national_id=patient.national_id,
        phone_number=patient.phone_number,
        address=patient.address,
        payment_mechanism=patient.payment_mechanism,
        nhis_number=patient.nhis_number,
        insurance_provider=patient.insurance_provider,
        insurance_policy_number=patient.insurance_policy_number,
        languages_spoken=patient.languages_spoken,
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def get_patient_by_national_id(db: Session, national_id: str):
    """Get patient by national ID"""
    return db.query(Patient).filter(Patient.national_id == national_id, Patient.is_active == True).first()

def get_patient(db: Session, patient_id: int):
    """Get patient by ID"""
    return db.query(Patient).filter(Patient.id == patient_id, Patient.is_active == True).first()

def get_patient_by_patient_number(db: Session, patient_number: str):
    """Get patient by patient number"""
    return db.query(Patient).filter(Patient.patient_number == patient_number, Patient.is_active == True).first()

def search_patients(
    db: Session,
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    gender: Optional[str] = None,
    payment_mechanism: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "desc"
) -> Tuple[List[Patient], int]:
    """
    Search patients with pagination and filtering.
    Searches by patient_number, name (first_name, last_name, full name), phone_number, national_id, or patient ID.
    
    Returns:
        Tuple of (patients list, total count)
    """
    # Build base query
    base_query = db.query(Patient).filter(Patient.is_active == True)
    
    # Apply search query
    if query:
        search_term = f"%{query.strip()}%"
        base_query = base_query.filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.national_id.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(search_term),
                func.cast(Patient.id, String).ilike(search_term)  # Search by numeric ID as string
            )
        )
    
    # Apply filters
    if gender:
        base_query = base_query.filter(Patient.gender == gender)
    
    if payment_mechanism:
        base_query = base_query.filter(Patient.payment_mechanism == payment_mechanism)
    
    # Get total count before pagination
    total_count = base_query.count()
    
    # Apply sorting
    if sort_by == "name":
        if sort_order == "asc":
            base_query = base_query.order_by(Patient.first_name.asc(), Patient.last_name.asc())
        else:
            base_query = base_query.order_by(Patient.first_name.desc(), Patient.last_name.desc())
    elif sort_by == "patient_number":
        if sort_order == "asc":
            base_query = base_query.order_by(Patient.patient_number.asc())
        else:
            base_query = base_query.order_by(Patient.patient_number.desc())
    elif sort_by == "created_at":
        if sort_order == "asc":
            base_query = base_query.order_by(Patient.created_at.asc())
        else:
            base_query = base_query.order_by(Patient.created_at.desc())
    else:  # Default: sort by ID
        if sort_order == "asc":
            base_query = base_query.order_by(Patient.id.asc())
        else:
            base_query = base_query.order_by(Patient.id.desc())
    
    # Apply pagination
    patients = base_query.offset(skip).limit(limit).all()
    
    return patients, total_count

def get_patients(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    gender: Optional[str] = None,
    payment_mechanism: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "desc"
) -> Tuple[List[Patient], int]:
    """Get all patients with pagination and filtering"""
    return search_patients(db, query=None, skip=skip, limit=limit, gender=gender, 
                          payment_mechanism=payment_mechanism, sort_by=sort_by, sort_order=sort_order)
