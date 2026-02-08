"""Birth record CRUD operations."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional, List, Tuple
from datetime import date, datetime

from app.models.birth_models import BirthRecord


def generate_birth_number(db: Session) -> str:
    """Generate unique birth number e.g. BIRTH-2024-0001."""
    today = date.today()
    count = (
        db.query(BirthRecord)
        .filter(func.date(BirthRecord.birth_date) == today, BirthRecord.is_active == True)
        .count()
    )
    return f"BIRTH-{today.strftime('%Y')}-{str(count + 1).zfill(4)}"


def create_birth_record(db: Session, **kwargs) -> BirthRecord:
    """Create a new birth record."""
    if "birth_number" not in kwargs or not kwargs["birth_number"]:
        kwargs["birth_number"] = generate_birth_number(db)
    record = BirthRecord(**kwargs)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_birth_record(db: Session, record_id: int) -> Optional[BirthRecord]:
    """Get birth record by ID."""
    return db.query(BirthRecord).options(
        joinedload(BirthRecord.mother),
        joinedload(BirthRecord.delivered_by),
        joinedload(BirthRecord.admission),
    ).filter(BirthRecord.id == record_id, BirthRecord.is_active == True).first()


def get_birth_records_by_mother(db: Session, mother_patient_id: int) -> List[BirthRecord]:
    """Get birth records for a mother."""
    return (
        db.query(BirthRecord)
        .filter(
            BirthRecord.mother_patient_id == mother_patient_id,
            BirthRecord.is_active == True,
        )
        .order_by(desc(BirthRecord.birth_date), desc(BirthRecord.birth_time))
        .all()
    )


def get_birth_records(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    mother_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    birth_outcome: Optional[str] = None,
) -> Tuple[List[BirthRecord], int]:
    """Get birth records with optional filters."""
    query = (
        db.query(BirthRecord)
        .options(joinedload(BirthRecord.mother), joinedload(BirthRecord.delivered_by))
        .filter(BirthRecord.is_active == True)
    )
    if mother_id:
        query = query.filter(BirthRecord.mother_patient_id == mother_id)
    if from_date:
        query = query.filter(BirthRecord.birth_date >= from_date)
    if to_date:
        query = query.filter(BirthRecord.birth_date <= to_date)
    if birth_outcome:
        query = query.filter(BirthRecord.birth_outcome == birth_outcome)
    total = query.count()
    records = query.order_by(desc(BirthRecord.birth_date), desc(BirthRecord.birth_time)).offset(skip).limit(limit).all()
    return records, total
