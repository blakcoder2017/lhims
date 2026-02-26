from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum


class AuditAction(str, enum.Enum):
    """Audit action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    PRINT = "print"
    APPROVE = "approve"
    REJECT = "reject"
    VOID = "void"  # Invoice/payment voiding


class AuditLog(Base):
    """
    SQLAlchemy Model for audit logging.
    Tracks all user actions for compliance and security.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # User Information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who performed action
    username = Column(String(100), nullable=True)  # Username at time of action (for historical reference)
    
    # Action Information
    action = Column(postgresql.ENUM(AuditAction, values_callable=lambda x: [e.value for e in x], name='auditaction', create_type=False), nullable=False)
    resource_type = Column(String(100), nullable=True)  # Type of resource (e.g., Patient, Invoice, Prescription)
    resource_id = Column(Integer, nullable=True)  # ID of the resource
    
    # Request Information
    ip_address = Column(String(50), nullable=True)  # IP address
    user_agent = Column(String(500), nullable=True)  # User agent string
    request_method = Column(String(10), nullable=True)  # HTTP method
    request_path = Column(String(500), nullable=True)  # Request path
    
    # Change Information
    old_values = Column(Text, nullable=True)  # JSON of old values (for updates)
    new_values = Column(Text, nullable=True)  # JSON of new values (for updates)
    description = Column(Text, nullable=True)  # Human-readable description
    
    # Status
    status = Column(String(50), nullable=True)  # Status (success, failed, error)
    error_message = Column(Text, nullable=True)  # Error message if action failed
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action.value}, resource_type={self.resource_type})>"

