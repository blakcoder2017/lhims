"""Lab audit logging - records key actions to lab_audit_events."""
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.models.lab_template_models import LabAuditEvent


def log_lab_audit(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    user_id: Optional[int] = None,
    old_json: Optional[dict] = None,
    new_json: Optional[dict] = None,
) -> None:
    """Record a lab audit event."""
    evt = LabAuditEvent(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        user_id=user_id,
        old_json=old_json,
        new_json=new_json,
    )
    db.add(evt)
    db.flush()  # Don't commit - let caller commit
