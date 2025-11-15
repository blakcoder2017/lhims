from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.models.audit_models import AuditLog, AuditAction
from app.schemas.audit_schemas import AuditLogCreate


def create_audit_log(db: Session, log_data: AuditLogCreate) -> AuditLog:
    """Create an audit log entry"""
    db_log = AuditLog(**log_data.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_audit_logs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    action: Optional[AuditAction] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[AuditLog]:
    """Get audit logs with filters"""
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action:
        query = query.filter(AuditLog.action == action.value)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


def get_recent_audit_logs(db: Session, limit: int = 50) -> List[AuditLog]:
    """Get recent audit logs"""
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

