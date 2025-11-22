from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
import json

from app.models.encounter_models import Encounter, LabOrder, RadiologyOrder, Prescription, EncounterStatus, OrderStatus
from app.schemas.encounter_schemas import (
    EncounterCreate, EncounterUpdate,
    LabOrderCreate, LabOrderUpdate,
    RadiologyOrderCreate, RadiologyOrderUpdate,
    PrescriptionCreate, PrescriptionUpdate
)


# Encounter CRUD Operations
def create_encounter(db: Session, encounter: EncounterCreate):
    """
    Creates a new clinical encounter in the database.
    Validates OPD/IPD linkage before creation.
    Auto-creates OPD visit if needed for OPD encounters.
    """
    from app.services.opd_validation import validate_encounter_creation, auto_link_opd_visit
    
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
    
    db_encounter = Encounter(**encounter.model_dump())
    db.add(db_encounter)
    db.commit()
    db.refresh(db_encounter)
    return db_encounter


def get_encounter(db: Session, encounter_id: int):
    """Retrieves a single encounter by ID."""
    return db.query(Encounter).filter(Encounter.id == encounter_id, Encounter.is_active == True).first()


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
        joinedload(Encounter.prescriptions),
        joinedload(Encounter.patient),
        joinedload(Encounter.appointment),
        joinedload(Encounter.clinician)
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
    
    # Handle status change to completed
    if update_data.get("status") == EncounterStatus.COMPLETED and not db_encounter.completed_at:
        update_data["completed_at"] = datetime.now()
    
    for field, value in update_data.items():
        setattr(db_encounter, field, value)
    
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

