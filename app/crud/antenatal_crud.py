"""Antenatal visit CRUD operations."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional, List, Tuple
from datetime import date, datetime

from app.models.antenatal_models import AntenatalVisit


def create_antenatal_visit(db: Session, **kwargs) -> AntenatalVisit:
    """Create a new antenatal visit."""
    visit = AntenatalVisit(**kwargs)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def get_antenatal_visit(db: Session, visit_id: int) -> Optional[AntenatalVisit]:
    """Get antenatal visit by ID."""
    return db.query(AntenatalVisit).options(
        joinedload(AntenatalVisit.patient),
        joinedload(AntenatalVisit.recorded_by),
    ).filter(AntenatalVisit.id == visit_id, AntenatalVisit.is_active == True).first()


def get_antenatal_visits_by_patient(
    db: Session, patient_id: int, limit: int = 50
) -> List[AntenatalVisit]:
    """Get antenatal visits for a patient."""
    return (
        db.query(AntenatalVisit)
        .options(joinedload(AntenatalVisit.recorded_by))
        .filter(AntenatalVisit.patient_id == patient_id, AntenatalVisit.is_active == True)
        .order_by(desc(AntenatalVisit.visit_date))
        .limit(limit)
        .all()
    )


def get_antenatal_visits(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Tuple[List[AntenatalVisit], int]:
    """Get antenatal visits with optional filters."""
    query = (
        db.query(AntenatalVisit)
        .options(joinedload(AntenatalVisit.patient), joinedload(AntenatalVisit.recorded_by))
        .filter(AntenatalVisit.is_active == True)
    )
    if patient_id:
        query = query.filter(AntenatalVisit.patient_id == patient_id)
    if from_date:
        query = query.filter(AntenatalVisit.visit_date >= from_date)
    if to_date:
        query = query.filter(AntenatalVisit.visit_date <= to_date)
    total = query.count()
    visits = query.order_by(desc(AntenatalVisit.visit_date)).offset(skip).limit(limit).all()
    return visits, total


def update_antenatal_visit(db: Session, visit_id: int, **kwargs) -> Optional[AntenatalVisit]:
    """Update antenatal visit."""
    visit = db.query(AntenatalVisit).filter(AntenatalVisit.id == visit_id).first()
    if not visit:
        return None
    for k, v in kwargs.items():
        if hasattr(visit, k):
            setattr(visit, k, v)
    db.commit()
    db.refresh(visit)
    return visit
