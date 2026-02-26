"""Birth record CRUD operations."""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional, List, Tuple
from datetime import date, datetime

from app.models.birth_models import BirthRecord


def generate_birth_number(db: Session) -> str:
    """Generate unique birth number e.g. BIRTH-2024-0001 with retry logic."""
    today = date.today()
    max_retries = 5
    
    for attempt in range(max_retries):
        count = (
            db.query(BirthRecord)
            .filter(BirthRecord.birth_date == today, BirthRecord.is_active == True)
            .count()
        )
        birth_number = f"BIRTH-{today.strftime('%Y')}-{str(count + 1).zfill(4)}"
        
        # Check if this birth_number already exists
        existing = db.query(BirthRecord).filter(BirthRecord.birth_number == birth_number).first()
        if not existing:
            return birth_number
        
        # If it exists (race condition), try again with incremented count
        print(f"[BIRTH_DEBUG] Birth number {birth_number} already exists, retrying...")
    
    # Fallback: use timestamp-based unique number
    import uuid
    return f"BIRTH-{today.strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"


def create_birth_record(db: Session, **kwargs) -> BirthRecord:
    """
    Create a new birth record with retry on duplicate birth_number.
    
    Supports all GHS birth record fields including:
    - Delivery Outcome: weeks_of_pregnancy, time_of_delivery_am_pm, time_of_placenta_delivery_am_pm,
      duration_labour_minutes, indication_for_vacuum_cs, anaesthesia, blood_transfusion,
      manual_removal_placenta, state_of_perineum, labour_delivery_complications, place_of_delivery,
      breastfeeding_30min, skin_to_skin, skin_to_skin_reason
    - Baby's Condition: number_of_babies_type, baby_complications, referred_to_facility
    - Baby Discharge: discharge_date_baby, discharge_heart_rate, discharge_respiratory_rate,
      discharge_temperature, discharge_weight, breastfeeding_initiated_discharge, baby_suckling_established,
      meconium_passed, urine_passed, eye_care_given, cord_care_date, vitamin_k_date, bcg_date,
      hepatitis_b_date, oral_polio_date, baby_condition_at_discharge, baby_condition_abnormal_specify
    - Mother's Discharge: discharge_date_mother, discharge_mother_bp, discharge_mother_pulse,
      discharge_mother_temperature, discharge_uterus_condition, discharge_fundal_height,
      discharge_lochia_colour, discharge_lochia_odour, discharge_perineum_condition, discharge_breast_condition
    - PNC Plan: next_visit_date, pnc1_date, pnc2_date, pnc3_date
    """
    if "birth_number" not in kwargs or not kwargs["birth_number"]:
        kwargs["birth_number"] = generate_birth_number(db)
    
    max_retries = 3
    for attempt in range(max_retries):
        record = BirthRecord(**kwargs)
        db.add(record)
        try:
            db.commit()
            print(f"[BIRTH_DEBUG] Created birth record ID: {record.id}, birth_number: {record.birth_number}")
            db.refresh(record)
            return record
        except Exception as e:
            db.rollback()
            if "duplicate key" in str(e).lower() and attempt < max_retries - 1:
                print(f"[BIRTH_DEBUG] Duplicate birth_number, regenerating and retrying...")
                kwargs["birth_number"] = generate_birth_number(db)
                continue
            print(f"[BIRTH_DEBUG] Failed to create birth record: {e}")
            raise


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
    
    print(f"[BIRTH_DEBUG] Query birth_records with filters: mother_id={mother_id}, birth_outcome={birth_outcome}")
    
    total = query.count()
    records = query.order_by(desc(BirthRecord.birth_date), desc(BirthRecord.birth_time)).offset(skip).limit(limit).all()
    
    print(f"[BIRTH_DEBUG] Found {total} total records, returning {len(records)} records")
    
    return records, total
