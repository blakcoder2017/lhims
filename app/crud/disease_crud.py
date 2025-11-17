"""
Disease CRUD Operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case
from typing import Optional, List
from datetime import datetime

from app.models.disease_models import Disease, EncounterDisease
from app.models.encounter_models import Encounter


def get_disease(db: Session, disease_id: int) -> Optional[Disease]:
    """Get a disease by ID"""
    return db.query(Disease).filter(Disease.id == disease_id, Disease.is_active == True).first()


def get_disease_by_name(db: Session, name: str) -> Optional[Disease]:
    """Get a disease by name"""
    return db.query(Disease).filter(Disease.name == name, Disease.is_active == True).first()


def get_diseases(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> List[Disease]:
    """Get all active diseases with optional search"""
    query = db.query(Disease).filter(Disease.is_active == True)
    
    if search:
        query = query.filter(Disease.name.ilike(f"%{search}%"))
    
    return query.order_by(Disease.name).offset(skip).limit(limit).all()


def create_disease(
    db: Session,
    name: str,
    code: Optional[str] = None,
    description: Optional[str] = None,
    created_by_id: Optional[int] = None
) -> Disease:
    """Create a new disease"""
    # Check if disease with same name already exists
    existing = get_disease_by_name(db, name)
    if existing:
        raise ValueError(f"Disease with name '{name}' already exists")
    
    disease = Disease(
        name=name,
        code=code,
        description=description,
        is_system=False,  # User-created
        is_active=True,
        created_by_id=created_by_id
    )
    
    db.add(disease)
    db.commit()
    db.refresh(disease)
    return disease


def update_disease(
    db: Session,
    disease_id: int,
    name: Optional[str] = None,
    code: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[Disease]:
    """Update a disease"""
    disease = get_disease(db, disease_id)
    if not disease:
        return None
    
    if name and name != disease.name:
        # Check if new name already exists
        existing = get_disease_by_name(db, name)
        if existing:
            raise ValueError(f"Disease with name '{name}' already exists")
        disease.name = name
    
    if code is not None:
        disease.code = code
    if description is not None:
        disease.description = description
    
    db.commit()
    db.refresh(disease)
    return disease


def delete_disease(db: Session, disease_id: int) -> bool:
    """Soft delete a disease (set is_active to False)"""
    disease = get_disease(db, disease_id)
    if not disease:
        return False
    
    disease.is_active = False
    db.commit()
    return True


def add_disease_to_encounter(
    db: Session,
    encounter_id: int,
    disease_id: Optional[int] = None,
    custom_name: Optional[str] = None,
    is_primary: bool = False
) -> EncounterDisease:
    """Add a disease to an encounter"""
    if not disease_id and not custom_name:
        raise ValueError("Either disease_id or custom_name must be provided")
    
    encounter_disease = EncounterDisease(
        encounter_id=encounter_id,
        disease_id=disease_id,
        custom_name=custom_name,
        is_primary=is_primary
    )
    
    db.add(encounter_disease)
    db.commit()
    db.refresh(encounter_disease)
    return encounter_disease


def get_encounter_diseases(db: Session, encounter_id: int) -> List[EncounterDisease]:
    """Get all diseases for an encounter"""
    return db.query(EncounterDisease).filter(
        EncounterDisease.encounter_id == encounter_id
    ).all()


def remove_disease_from_encounter(db: Session, encounter_disease_id: int) -> bool:
    """Remove a disease from an encounter"""
    encounter_disease = db.query(EncounterDisease).filter(
        EncounterDisease.id == encounter_disease_id
    ).first()
    
    if not encounter_disease:
        return False
    
    db.delete(encounter_disease)
    db.commit()
    return True


def get_disease_encounter_stats(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """Aggregate encounter counts per disease within optional date range."""
    encounter_count = func.count(EncounterDisease.id)
    primary_count = func.sum(
        case(
            (EncounterDisease.is_primary == True, 1),
            else_=0
        )
    )
    unique_encounters = func.count(func.distinct(EncounterDisease.encounter_id))
    
    query = (
        db.query(
            Disease.id.label("disease_id"),
            Disease.name,
            Disease.code,
            encounter_count.label("encounter_count"),
            unique_encounters.label("unique_encounters"),
            primary_count.label("primary_count"),
            func.min(Encounter.encounter_date).label("first_recorded"),
            func.max(Encounter.encounter_date).label("last_recorded"),
        )
        .join(EncounterDisease, EncounterDisease.disease_id == Disease.id)
        .join(Encounter, Encounter.id == EncounterDisease.encounter_id)
        .filter(
            Disease.is_active == True,
            Encounter.is_active == True,
        )
    )
    
    if start_date:
        query = query.filter(Encounter.encounter_date >= start_date)
    if end_date:
        query = query.filter(Encounter.encounter_date <= end_date)
    if search:
        query = query.filter(Disease.name.ilike(f"%{search.strip()}%"))
    
    results = (
        query.group_by(Disease.id, Disease.name, Disease.code)
        .order_by(encounter_count.desc())
        .limit(limit)
        .all()
    )
    
    stats = []
    for row in results:
        stats.append(
            {
                "disease_id": row.disease_id,
                "name": row.name,
                "code": row.code,
                "encounter_count": int(row.encounter_count or 0),
                "unique_encounters": int(row.unique_encounters or 0),
                "primary_count": int(row.primary_count or 0),
                "first_recorded": row.first_recorded,
                "last_recorded": row.last_recorded,
            }
        )
    return stats

