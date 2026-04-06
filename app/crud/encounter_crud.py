from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
import json

from app.models.encounter_models import Encounter, LabOrder, RadiologyOrder, Prescription, EncounterStatus, OrderStatus, EncounterAddendum
from app.models.disease_models import EncounterDisease
from app.schemas.encounter_schemas import (
    EncounterCreate, EncounterUpdate,
    LabOrderCreate, LabOrderUpdate,
    RadiologyOrderCreate, RadiologyOrderUpdate,
    PrescriptionCreate, PrescriptionUpdate,
    AddendumCreate, AddendumUpdate
)


# Encounter CRUD Operations
def create_encounter(db: Session, encounter: EncounterCreate):
    """
    Creates a new clinical encounter in the database.
    Validates OPD/IPD linkage before creation.
    Auto-creates OPD visit if needed for OPD encounters.
    Handles diagnoses by creating EncounterDisease records.
    
    Business Rule: For cash patients, encounter can only be created if OPD payment is made.
    Insurance patients are exempt from this requirement.
    """
    from app.services.opd_validation import validate_encounter_creation, auto_link_opd_visit
    from app.models.scheduled_appointment_models import ScheduledAppointment
    from app.models.patient_models import Patient, PaymentMechanism
    from app.models.opd_models import OPDVisit
    
    # Validate appointment_id if provided
    if encounter.appointment_id:
        existing = db.query(ScheduledAppointment).filter(ScheduledAppointment.id == encounter.appointment_id).first()
        if not existing:
            # Invalid appointment_id, set to None
            encounter.appointment_id = None
    
    # Auto-link or create OPD visit if not provided and this is an OPD encounter (not IPD)
    if not encounter.opd_visit_id and not encounter.admission_id:
        # Try to auto-link/create OPD visit (will create if doesn't exist)
        opd_visit_id = auto_link_opd_visit(db, encounter.patient_id, encounter.appointment_id)
        if opd_visit_id:
            encounter.opd_visit_id = opd_visit_id
    
    # Validate encounter creation
    is_valid, error_message = validate_encounter_creation(
        db,
        encounter.patient_id,
        encounter.opd_visit_id,
        encounter.admission_id
    )
    
    if not is_valid:
        raise ValueError(error_message)
    
    # Check if OPD payment is made for cash patients (not insurance)
    if encounter.opd_visit_id and not encounter.admission_id:
        # Get patient to check payment mechanism
        patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
        # Insurance patients (NHIS, PRIVATE_INSURANCE) are exempt from payment requirement
        is_insurance = patient and (
            patient.payment_mechanism == PaymentMechanism.NHIS or 
            patient.payment_mechanism == PaymentMechanism.PRIVATE_INSURANCE
        )
        if patient and not is_insurance:
            # This is a cash/self-pay patient - check if OPD visit is paid or emergency
            opd_visit = db.query(OPDVisit).filter(OPDVisit.id == encounter.opd_visit_id).first()
            if opd_visit and opd_visit.payment_status not in ['paid', 'emergency']:
                raise ValueError(
                    "Cannot create encounter: Patient has not paid OPD consultation fee. "
                    "Please make payment at the front office first."
                )
    
    # Extract diagnoses before creating encounter
    diagnoses = encounter.diagnoses
    
    # Create encounter without diagnoses field
    encounter_data = encounter.model_dump(exclude={'diagnoses'})
    db_encounter = Encounter(**encounter_data)
    db.add(db_encounter)
    db.flush()  # Get the encounter ID
    
    # Create EncounterDisease records for each diagnosis
    if diagnoses:
        for disease_id in diagnoses:
            encounter_disease = EncounterDisease(
                encounter_id=db_encounter.id,
                disease_id=disease_id,
                is_primary=False  # Can be updated later if needed
            )
            db.add(encounter_disease)
    
    db.commit()
    db.refresh(db_encounter)
    return db_encounter


def get_encounter(db: Session, encounter_id: int):
    """Retrieves a single encounter by ID."""
    from sqlalchemy.orm import joinedload
    return db.query(Encounter).options(
        joinedload(Encounter.clinician),
        joinedload(Encounter.addendum_by)
    ).filter(Encounter.id == encounter_id, Encounter.is_active == True).first()


def get_encounters_by_patient(db: Session, patient_id: int, skip: int = 0, limit: int = 100):
    """Retrieves all encounters for a specific patient, ordered by date (newest first)."""
    return db.query(Encounter).filter(
        Encounter.patient_id == patient_id,
        Encounter.is_active == True
    ).order_by(Encounter.encounter_date.desc()).offset(skip).limit(limit).all()


def get_encounters_by_appointment(db: Session, appointment_id: int):
    """Retrieves all encounters associated with an appointment."""
    return db.query(Encounter).filter(
        Encounter.appointment_id == appointment_id,
        Encounter.is_active == True
    ).order_by(Encounter.encounter_date.desc()).all()


def get_encounter_with_orders(db: Session, encounter_id: int):
    """Retrieves an encounter with all related orders (lab, radiology, prescriptions) and radiology images."""
    from app.models.pacs_models import RadiologyImage
    return db.query(Encounter).options(
        joinedload(Encounter.lab_orders),
        joinedload(Encounter.radiology_orders).joinedload(RadiologyOrder.images),
        joinedload(Encounter.prescriptions).joinedload(Prescription.prescribed_by),
        joinedload(Encounter.prescriptions).joinedload(Prescription.pharmacy_drug),
        joinedload(Encounter.procedures),
        joinedload(Encounter.patient),
        joinedload(Encounter.appointment),
        joinedload(Encounter.clinician),
        joinedload(Encounter.admission),
        joinedload(Encounter.diseases)
    ).filter(
        Encounter.id == encounter_id,
        Encounter.is_active == True
    ).first()


def update_encounter(db: Session, encounter_id: int, encounter_update: EncounterUpdate):
    """Updates an existing encounter."""
    db_encounter = get_encounter(db, encounter_id)
    if not db_encounter:
        return None
    
    update_data = encounter_update.model_dump(exclude_unset=True)
    
    # Handle diagnoses update - extract before setting other fields
    diagnoses = update_data.pop('diagnoses', None)
    
    # Handle status change to completed
    if update_data.get("status") == EncounterStatus.COMPLETED and not db_encounter.completed_at:
        update_data["completed_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(db_encounter, field, value)
    
    # Update diagnoses if provided
    if diagnoses is not None:
        # Remove existing diagnosis associations
        db.query(EncounterDisease).filter(
            EncounterDisease.encounter_id == encounter_id
        ).delete()
        
        # Add new diagnosis associations
        if diagnoses:
            for disease_id in diagnoses:
                encounter_disease = EncounterDisease(
                    encounter_id=encounter_id,
                    disease_id=disease_id,
                    is_primary=False
                )
                db.add(encounter_disease)
    
    db.commit()
    db.refresh(db_encounter)
    return db_encounter


def delete_encounter(db: Session, encounter_id: int):
    """Soft deletes an encounter by setting is_active to False."""
    db_encounter = get_encounter(db, encounter_id)
    if not db_encounter:
        return None
    
    db_encounter.is_active = False
    db.commit()
    return db_encounter


# Lab Order CRUD Operations
def create_lab_order(db: Session, lab_order: LabOrderCreate):
    """Creates a new lab order."""
    order_data = lab_order.model_dump()
    
    # For walk-in orders, ensure patient_id is set
    if order_data.get('is_walk_in') and not order_data.get('patient_id'):
        raise ValueError("patient_id is required for walk-in lab orders")
    
    # For non-walk-in orders, get patient_id from encounter if not provided
    if not order_data.get('is_walk_in') and not order_data.get('patient_id') and order_data.get('encounter_id'):
        encounter = get_encounter(db, order_data['encounter_id'])
        if encounter:
            order_data['patient_id'] = encounter.patient_id
    
    # Auto-link opd_visit_id and admission_id from encounter if not provided
    if order_data.get("encounter_id") and not order_data.get("opd_visit_id") and not order_data.get("admission_id"):
        encounter = get_encounter(db, order_data["encounter_id"])
        if encounter:
            if encounter.opd_visit_id:
                order_data["opd_visit_id"] = encounter.opd_visit_id
            if encounter.admission_id:
                order_data["admission_id"] = encounter.admission_id
    
    # Auto-link template from test catalog
    test_code = order_data.get('test_code')
    test_name = order_data.get('test_name')
    if test_code or test_name:
        from app.models.lab_catalog_models import LabTest
        from sqlalchemy import or_
        conditions = []
        if test_code:
            conditions.append(LabTest.test_code == test_code)
        if test_name:
            conditions.append(LabTest.test_name.ilike(f"%{test_name}%"))
        if conditions:
            lab_test = db.query(LabTest).filter(or_(*conditions), LabTest.template_id.isnot(None)).first()
            if lab_test:
                order_data['lab_test_id'] = lab_test.id
                order_data['template_id'] = lab_test.template_id
                order_data['template_version_used'] = lab_test.template_version or 1
    
    db_lab_order = LabOrder(**order_data)
    db.add(db_lab_order)
    db.commit()
    db.refresh(db_lab_order)
    return db_lab_order


def get_lab_order(db: Session, lab_order_id: int):
    """Retrieves a single lab order by ID."""
    return db.query(LabOrder).filter(LabOrder.id == lab_order_id).first()


def get_lab_orders_by_encounter(db: Session, encounter_id: int):
    """Retrieves all lab orders for a specific encounter."""
    return db.query(LabOrder).filter(LabOrder.encounter_id == encounter_id).all()


def update_lab_order(db: Session, lab_order_id: int, lab_order_update: LabOrderUpdate):
    """Updates an existing lab order."""
    db_lab_order = get_lab_order(db, lab_order_id)
    if not db_lab_order:
        return None
    
    update_data = lab_order_update.model_dump(exclude_unset=True)
    
    # Handle status change to completed
    if update_data.get("status") == OrderStatus.COMPLETED and not db_lab_order.completed_at:
        update_data["completed_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(db_lab_order, field, value)
    
    db.commit()
    db.refresh(db_lab_order)
    return db_lab_order


# Radiology Order CRUD Operations
def create_radiology_order(db: Session, radiology_order: RadiologyOrderCreate):
    """Creates a new radiology order."""
    order_data = radiology_order.model_dump()
    
    # For walk-in orders, ensure patient_id is set
    if order_data.get('is_walk_in') and not order_data.get('patient_id'):
        raise ValueError("patient_id is required for walk-in radiology orders")
    
    # For non-walk-in orders, get patient_id from encounter if not provided
    if not order_data.get('is_walk_in') and not order_data.get('patient_id') and order_data.get('encounter_id'):
        encounter = get_encounter(db, order_data['encounter_id'])
        if encounter:
            order_data['patient_id'] = encounter.patient_id
    
    # Auto-link opd_visit_id and admission_id from encounter if not provided
    if order_data.get("encounter_id") and not order_data.get("opd_visit_id") and not order_data.get("admission_id"):
        encounter = get_encounter(db, order_data["encounter_id"])
        if encounter:
            if encounter.opd_visit_id:
                order_data["opd_visit_id"] = encounter.opd_visit_id
            if encounter.admission_id:
                order_data["admission_id"] = encounter.admission_id
    
    db_radiology_order = RadiologyOrder(**order_data)
    db.add(db_radiology_order)
    db.commit()
    db.refresh(db_radiology_order)
    return db_radiology_order


def get_radiology_order(db: Session, radiology_order_id: int):
    """Retrieves a single radiology order by ID."""
    return db.query(RadiologyOrder).filter(RadiologyOrder.id == radiology_order_id).first()


def get_radiology_orders_by_encounter(db: Session, encounter_id: int):
    """Retrieves all radiology orders for a specific encounter."""
    return db.query(RadiologyOrder).filter(RadiologyOrder.encounter_id == encounter_id).all()


def update_radiology_order(db: Session, radiology_order_id: int, radiology_order_update: RadiologyOrderUpdate):
    """Updates an existing radiology order."""
    db_radiology_order = get_radiology_order(db, radiology_order_id)
    if not db_radiology_order:
        return None
    
    update_data = radiology_order_update.model_dump(exclude_unset=True)
    
    # Handle status change to completed
    if update_data.get("status") == OrderStatus.COMPLETED and not db_radiology_order.completed_at:
        update_data["completed_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(db_radiology_order, field, value)
    
    db.commit()
    db.refresh(db_radiology_order)
    return db_radiology_order


# Prescription CRUD Operations
def create_prescription(db: Session, prescription: PrescriptionCreate):
    """Creates a new prescription."""
    prescription_data = prescription.model_dump()
    
    # Convert pharmacy_drug_id from str to UUID if present (Ghana formulation)
    if prescription_data.get("pharmacy_drug_id"):
        from uuid import UUID
        try:
            pid = prescription_data["pharmacy_drug_id"]
            # Handle already-converted UUID objects
            if isinstance(pid, UUID):
                prescription_data["pharmacy_drug_id"] = pid
            else:
                prescription_data["pharmacy_drug_id"] = UUID(str(pid))
        except (ValueError, TypeError, AttributeError):
            prescription_data["pharmacy_drug_id"] = None
    
    # Auto-link opd_visit_id and admission_id from encounter if not provided
    if prescription_data.get("encounter_id") and not prescription_data.get("opd_visit_id") and not prescription_data.get("admission_id"):
        encounter = get_encounter(db, prescription_data["encounter_id"])
        if encounter:
            if encounter.opd_visit_id:
                prescription_data["opd_visit_id"] = encounter.opd_visit_id
            if encounter.admission_id:
                prescription_data["admission_id"] = encounter.admission_id
    
    db_prescription = Prescription(**prescription_data)
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription


# Differential diagnosis helpers
def save_differential_data(db: Session, encounter_id: int, payload: dict):
    """Persist differential diagnosis payload as JSON on the encounter."""
    db_encounter = get_encounter(db, encounter_id)
    if not db_encounter:
        return None
    db_encounter.differential_diagnosis_data = json.dumps(payload)
    db_encounter.updated_at = datetime.now()
    db.commit()
    db.refresh(db_encounter)
    return db_encounter.differential_diagnosis_data


def load_differential_data(encounter: Encounter):
    """Return parsed differential payload for a given encounter instance."""
    if not encounter or not encounter.differential_diagnosis_data:
        return None
    try:
        return json.loads(encounter.differential_diagnosis_data)
    except (json.JSONDecodeError, TypeError):
        return None


def get_encounters_with_differentials(db: Session, limit: int = 200, skip: int = 0):
    """Return encounters that have saved differential diagnosis data."""
    return (
        db.query(Encounter)
        .options(
            joinedload(Encounter.patient),
            joinedload(Encounter.clinician),
        )
        .filter(
            Encounter.is_active == True,
            Encounter.differential_diagnosis_data.isnot(None),
        )
        .order_by(Encounter.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_prescription(db: Session, prescription_id: int):
    """Retrieves a single prescription by ID."""
    return db.query(Prescription).filter(Prescription.id == prescription_id).first()


def get_prescriptions_by_encounter(db: Session, encounter_id: int):
    """Retrieves all prescriptions for a specific encounter."""
    return db.query(Prescription).filter(Prescription.encounter_id == encounter_id).all()


def update_prescription(db: Session, prescription_id: int, prescription_update: PrescriptionUpdate):
    """Updates an existing prescription."""
    db_prescription = get_prescription(db, prescription_id)
    if not db_prescription:
        return None
    
    update_data = prescription_update.model_dump(exclude_unset=True)
    
    # Handle status change to completed
    if update_data.get("status") == OrderStatus.COMPLETED and not db_prescription.dispensed_at:
        update_data["dispensed_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(db_prescription, field, value)
    
    db.commit()
    db.refresh(db_prescription)
    return db_prescription


# Addendum CRUD Operations
def create_addendum(db: Session, addendum: AddendumCreate, encounter_id: int, added_by_id: int):
    """Creates a new addendum for an encounter."""
    db_addendum = EncounterAddendum(
        encounter_id=encounter_id,
        added_by_id=added_by_id,
        content=addendum.content,
        note_type=addendum.note_type,
        tags=addendum.tags
    )
    db.add(db_addendum)
    db.commit()
    db.refresh(db_addendum)
    return db_addendum


def update_addendum(db: Session, addendum_id: int, addendum_update: AddendumUpdate):
    """Updates an existing addendum."""
    db_addendum = db.query(EncounterAddendum).filter(EncounterAddendum.id == addendum_id).first()
    if not db_addendum:
        return None
    
    db_addendum.content = addendum_update.content
    if addendum_update.note_type is not None:
        db_addendum.note_type = addendum_update.note_type
    if addendum_update.tags is not None:
        db_addendum.tags = addendum_update.tags
    
    db.commit()
    db.refresh(db_addendum)
    return db_addendum


def get_addendums_by_encounter(db: Session, encounter_id: int):
    """Retrieves all addendums for an encounter, ordered by creation date (newest first)."""
    return db.query(EncounterAddendum).options(
        joinedload(EncounterAddendum.added_by)
    ).filter(
        EncounterAddendum.encounter_id == encounter_id,
        EncounterAddendum.is_active == True
    ).order_by(EncounterAddendum.created_at.desc()).all()


def soft_delete_addendum(db: Session, addendum_id: int):
    """Soft deletes an addendum by setting is_active to false."""
    db_addendum = db.query(EncounterAddendum).filter(EncounterAddendum.id == addendum_id).first()
    if not db_addendum:
        return None
    
    db_addendum.is_active = False
    db.commit()
    db.refresh(db_addendum)
    return db_addendum


def auto_close_uncompleted_encounters(
    db: Session, 
    hours_threshold: int = 48,
    dry_run: bool = False
):
    """
    Auto-close uncompleted encounters that have been in progress for longer than 
    the specified threshold (default 48 hours).
    
    This function:
    1. Finds encounters with status IN_PROGRESS that started before the threshold
    2. Marks them as AUTO_CLOSED
    3. Sets completed_at timestamp
    
    Args:
        db: Database session
        hours_threshold: Hours after which to auto-close encounters (default 48)
        dry_run: If True, only return the entries that would be closed without actually closing them
    
    Returns:
        Tuple of (count of closed encounters, list of details)
    """
    from datetime import datetime, timedelta
    from typing import Tuple, List
    
    # Calculate the threshold time
    threshold_time = datetime.now() - timedelta(hours=hours_threshold)
    
    # Find all uncompleted encounters that started before the threshold
    stale_encounters = db.query(Encounter).options(
        joinedload(Encounter.patient)
    ).filter(
        Encounter.started_at < threshold_time,
        Encounter.status == EncounterStatus.IN_PROGRESS,
        Encounter.is_active == True
    ).all()
    
    closed_encounters = []
    closed_count = 0
    
    for encounter in stale_encounters:
        encounter_details = {
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "patient_name": f"{encounter.patient.first_name} {encounter.patient.last_name}" if encounter.patient else "Unknown",
            "patient_number": encounter.patient.patient_number if encounter.patient else "Unknown",
            "started_at": encounter.started_at.isoformat() if encounter.started_at else None,
            "status": encounter.status.value,
            "clinician_id": encounter.clinician_id
        }
        
        if not dry_run:
            # Mark as AUTO_CLOSED
            encounter.status = EncounterStatus.AUTO_CLOSED
            encounter.completed_at = datetime.now()
            encounter.notes = (encounter.notes or "") + f" [Auto-closed: No activity after {hours_threshold} hours]"
            db.commit()
            db.refresh(encounter)
        
        closed_encounters.append(encounter_details)
        closed_count += 1
    
    return closed_count, closed_encounters

