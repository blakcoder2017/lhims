"""
Procedure CRUD Operations

Database operations for procedure management.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date

from app.models.procedure_models import Procedure, ProcedureType, ProcedureStatus
from app.schemas.procedure_schemas import ProcedureCreate, ProcedureUpdate


def generate_procedure_number(db: Session) -> str:
    """Generate a unique procedure number with retry logic for edge cases."""
    from datetime import datetime
    today = date.today()
    today_str = today.strftime('%Y%m%d')
    
    # Get the maximum procedure number for today
    result = db.query(func.max(Procedure.procedure_number)).filter(
        Procedure.procedure_number.like(f"PROC-{today_str}%")
    ).scalar()
    
    if result:
        # Extract the sequence number from the last procedure number
        try:
            last_seq = int(result.split('-')[-1])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            # If parsing fails, start from 1
            new_seq = 1
    else:
        new_seq = 1
    
    # Format: PROC-YYYYMMDD-XXX
    procedure_number = f"PROC-{today_str}-{str(new_seq).zfill(3)}"
    
    # Retry logic: if number already exists, increment until we find a unique one
    max_retries = 10
    for _ in range(max_retries):
        existing = db.query(Procedure.procedure_number).filter(
            Procedure.procedure_number == procedure_number
        ).first()
        if not existing:
            break
        new_seq += 1
        procedure_number = f"PROC-{today_str}-{str(new_seq).zfill(3)}"
    
    return procedure_number


def create_procedure(db: Session, procedure: ProcedureCreate) -> Procedure:
    """Create a new procedure."""
    procedure_number = generate_procedure_number(db)
    
    procedure_data = procedure.model_dump()
    
    db_procedure = Procedure(
        procedure_number=procedure_number,
        patient_id=procedure_data['patient_id'],
        encounter_id=procedure_data.get('encounter_id'),
        ordered_by_id=procedure_data['ordered_by_id'],
        performed_by_id=procedure_data.get('performed_by_id'),
        procedure_name=procedure_data['procedure_name'],
        procedure_code=procedure_data.get('procedure_code'),
        procedure_type=procedure_data['procedure_type'],
        description=procedure_data.get('description'),
        indication=procedure_data.get('indication'),
        scheduled_date=procedure_data.get('scheduled_date'),
        location=procedure_data.get('location'),
        anesthesia_type=procedure_data.get('anesthesia_type'),
        anesthesia_provider=procedure_data.get('anesthesia_provider'),
        notes=procedure_data.get('notes'),
        status=procedure_data.get('status', ProcedureStatus.SCHEDULED),
        is_walk_in=procedure_data.get('is_walk_in', False),
        is_active=True
    )
    
    db.add(db_procedure)
    db.commit()
    db.refresh(db_procedure)
    return db_procedure


def get_procedure(db: Session, procedure_id: int) -> Optional[Procedure]:
    """Get a procedure by ID with patient relationship loaded."""
    return db.query(Procedure).options(
        joinedload(Procedure.patient)
    ).filter(
        Procedure.id == procedure_id,
        Procedure.is_active == True
    ).first()


def get_procedures(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    patient_id: Optional[int] = None,
    encounter_id: Optional[int] = None,
    procedure_type: Optional[ProcedureType] = None,
    status: Optional[ProcedureStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> tuple[List[Procedure], int]:
    """Get procedures with filtering and pagination."""
    query = db.query(Procedure).filter(Procedure.is_active == True)
    
    if patient_id:
        query = query.filter(Procedure.patient_id == patient_id)
    
    if encounter_id:
        query = query.filter(Procedure.encounter_id == encounter_id)
    
    if procedure_type:
        query = query.filter(Procedure.procedure_type == procedure_type)
    
    if status:
        query = query.filter(Procedure.status == status)
    
    if start_date:
        query = query.filter(func.date(Procedure.scheduled_date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(Procedure.scheduled_date) <= end_date)
    
    total_count = query.count()
    procedures = query.order_by(Procedure.scheduled_date.desc()).offset(skip).limit(limit).all()
    
    return procedures, total_count


def update_procedure(db: Session, procedure_id: int, procedure_update: ProcedureUpdate) -> Optional[Procedure]:
    """Update a procedure."""
    db_procedure = get_procedure(db, procedure_id)
    if not db_procedure:
        return None
    
    update_data = procedure_update.model_dump(exclude_unset=True)
    
    # Calculate duration if start and end times are provided
    if "start_time" in update_data and "end_time" in update_data:
        if update_data["start_time"] and update_data["end_time"]:
            duration = (update_data["end_time"] - update_data["start_time"]).total_seconds() / 60
            update_data["duration_minutes"] = int(duration)
    
    # Auto-update status based on times
    if "start_time" in update_data and update_data["start_time"]:
        if db_procedure.status == ProcedureStatus.SCHEDULED:
            update_data["status"] = ProcedureStatus.IN_PROGRESS
    
    if "end_time" in update_data and update_data["end_time"]:
        if db_procedure.status in [ProcedureStatus.SCHEDULED, ProcedureStatus.IN_PROGRESS]:
            update_data["status"] = ProcedureStatus.COMPLETED
    
    for field, value in update_data.items():
        setattr(db_procedure, field, value)
    
    db.commit()
    db.refresh(db_procedure)
    return db_procedure


def delete_procedure(db: Session, procedure_id: int) -> bool:
    """Soft delete a procedure."""
    db_procedure = get_procedure(db, procedure_id)
    if not db_procedure:
        return False
    
    db_procedure.is_active = False
    db.commit()
    return True

