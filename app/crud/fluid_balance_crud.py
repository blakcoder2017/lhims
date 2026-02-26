"""CRUD for fluid balance (intake/output) entries."""
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from app.models.fluid_balance_models import FluidBalance


def create_fluid_entry(
    db: Session,
    admission_id: int,
    recorded_by_id: int,
    entry_type: str,
    volume_ml: int,
    recorded_at: Optional[datetime] = None,
    notes: Optional[str] = None,
    color: Optional[str] = None,
) -> Optional[FluidBalance]:
    """Create a fluid intake or output entry. entry_type must be 'intake' or 'output'."""
    if entry_type not in ("intake", "output"):
        return None
    if volume_ml < 0:
        return None
    entry = FluidBalance(
        admission_id=admission_id,
        recorded_by_id=recorded_by_id,
        entry_type=entry_type,
        volume_ml=volume_ml,
        recorded_at=recorded_at or datetime.now(),
        notes=notes,
        color=color,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_fluid_entries_by_admission(
    db: Session,
    admission_id: int,
    limit: int = 200,
) -> List[FluidBalance]:
    """Get fluid balance entries for an admission, most recent first."""
    return (
        db.query(FluidBalance)
        .options(joinedload(FluidBalance.recorded_by))
        .filter(
            FluidBalance.admission_id == admission_id,
            FluidBalance.is_active == True,
        )
        .order_by(FluidBalance.recorded_at.desc())
        .limit(limit)
        .all()
    )
