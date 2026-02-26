"""
DHIMS2 Integration Database Models

This module contains SQLAlchemy models for the DHIMS2 (DHIS2-based) reporting integration.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class DHIMS2InstanceStatus(str, enum.Enum):
    """Status for DHIMS2 instance"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class SubmissionRunStatus(str, enum.Enum):
    """Status for DHIMS2 submission run"""
    DRAFT = "draft"
    VALIDATION_FAILED = "validation_failed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    SUBMIT_FAILED = "submit_failed"
    LOCKED = "locked"


class ValidationStatus(str, enum.Enum):
    """Validation status for submission items"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DHIMS2Instance(Base):
    """
    Stores configuration for DHIMS2/DHIS2 instances.
    """
    __tablename__ = "dhims2_instances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    base_url = Column(String(500), nullable=False)
    username = Column(String(255), nullable=False)  # encrypted in production
    password = Column(String(255), nullable=False)   # encrypted in production
    is_active = Column(Boolean, default=True, nullable=False)
    timeout_seconds = Column(Integer, default=30)
    verify_tls = Column(Boolean, default=True)
    max_retries = Column(Integer, default=5)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    submission_runs = relationship("DHIMS2SubmissionRun", back_populates="instance")
    mappings = relationship("DHIMS2Mapping", back_populates="instance")

    def __repr__(self):
        return f"<DHIMS2Instance(id={self.id}, name='{self.name}', base_url='{self.base_url}')>"


class DHIMS2Mapping(Base):
    """
    Maps internal metric keys to DHIMS2 data elements and category option combos.
    """
    __tablename__ = "dhims2_mappings"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("dhims2_instances.id"), nullable=False)
    
    # Internal metric identifier (e.g., "OPD_TOTAL", "ANC1", "IPD_ADMISSIONS")
    internal_metric_key = Column(String(100), nullable=False, index=True)
    
    # DHIMS2/DHIS2 identifiers
    dhis2_data_element_uid = Column(String(20), nullable=False)
    dhis2_category_option_combo_uid = Column(String(20), nullable=True)  # Optional disaggregation
    dhis2_attribute_option_combo_uid = Column(String(20), nullable=True)  # For org unit disaggregation
    dhis2_dataset_uid = Column(String(20), nullable=True)  # Dataset if applicable
    
    # Value type for validation
    value_type = Column(String(20), default="numeric")  # numeric, text, boolean
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_required = Column(Boolean, default=False)  # Required for submission
    description = Column(Text, nullable=True)
    
    # Cross-check configuration (for validation rules)
    # Format: {"rule": "total_ge_parts", "parts": ["OPD_MALE", "OPD_FEMALE"], "total": "OPD_TOTAL"}
    validation_config = Column(JSON, nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    instance = relationship("DHIMS2Instance", back_populates="mappings")
    created_by_user = relationship("User")

    def __repr__(self):
        return f"<DHIMS2Mapping(id={self.id}, key='{self.internal_metric_key}', de_uid='{self.dhis2_data_element_uid}')>"


class DHIMS2OrgUnitMapping(Base):
    """
    Maps internal organization units (facilities/branches) to DHIMS2 orgUnit UIDs.
    """
    __tablename__ = "dhims2_org_unit_mappings"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("dhims2_instances.id"), nullable=False)
    
    # Internal organization identifier
    # Could be department_id, ward_id, or a facility/branch identifier
    internal_org_id = Column(Integer, nullable=False)  # Can reference various tables
    internal_org_type = Column(String(50), nullable=False)  # e.g., "department", "ward", "facility"
    
    # DHIMS2/DHIS2 org unit UID
    dhis2_org_unit_uid = Column(String(20), nullable=False)
    
    # Metadata from DHIS2 (cached)
    dhis2_org_unit_name = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    instance = relationship("DHIMS2Instance")

    def __repr__(self):
        return f"<DHIMS2OrgUnitMapping(id={self.id}, internal_org_id={self.internal_org_id}, dhis2_uid='{self.dhis2_org_unit_uid}')>"


class DHIMS2SubmissionRun(Base):
    """
    Represents a single submission package to DHIMS2.
    """
    __tablename__ = "dhims2_submission_runs"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey("dhims2_instances.id"), nullable=False)
    
    # Submission identification
    org_unit_uid = Column(String(20), nullable=False)  # DHIS2 org unit UID
    period = Column(String(20), nullable=False)  # e.g., "2026-01" or "2026Q1"
    report_type = Column(String(100), nullable=False)  # e.g., "monthly_service", "quarterly_anc"
    dataset_uid = Column(String(20), nullable=True)  # DHIS2 dataset UID if applicable
    
    # Status tracking
    status = Column(
        Enum(SubmissionRunStatus, values_callable=lambda x: [e.value for e in x], name='submissionrunstatus'),
        default=SubmissionRunStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Payload hash for idempotency
    payload_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash
    
    # Approval workflow
    prepared_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    prepared_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Submission details
    submitted_at = Column(DateTime, nullable=True)
    dhis2_import_count = Column(JSON, nullable=True)  # Store import counts from DHIS2 response
    dhis2_response = Column(Text, nullable=True)  # Sanitized DHIS2 response
    error_summary = Column(Text, nullable=True)
    
    # Locking
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    lock_justification = Column(Text, nullable=True)
    
    # Override tracking
    override_justification = Column(Text, nullable=True)
    override_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    override_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    instance = relationship("DHIMS2Instance", back_populates="submission_runs")
    prepared_by_user = relationship("User", foreign_keys=[prepared_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    locked_by_user = relationship("User", foreign_keys=[locked_by])
    override_by_user = relationship("User", foreign_keys=[override_by])
    items = relationship("DHIMS2SubmissionItem", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DHIMS2SubmissionRun(id={self.id}, org_unit='{self.org_unit_uid}', period='{self.period}', status='{self.status.value}')>"


class DHIMS2SubmissionItem(Base):
    """
    Individual data values within a submission run.
    """
    __tablename__ = "dhims2_submission_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("dhims2_submission_runs.id"), nullable=False)
    
    # Internal metric
    internal_metric_key = Column(String(100), nullable=False, index=True)
    value = Column(String(500), nullable=False)  # Stored as string for flexibility
    
    # DHIMS2 identifiers (denormalized from mapping for audit)
    dhis2_data_element_uid = Column(String(20), nullable=False)
    dhis2_category_option_combo_uid = Column(String(20), nullable=True)
    dhis2_attribute_option_combo_uid = Column(String(20), nullable=True)
    
    # Validation
    validation_status = Column(
        Enum(ValidationStatus, values_callable=lambda x: [e.value for e in x], name='validationstatus'),
        default=ValidationStatus.PASS,
        nullable=False
    )
    validation_notes = Column(Text, nullable=True)
    
    # Source tracking
    source_table = Column(String(100), nullable=True)  # e.g., "opd_visits", "ipd_admissions"
    source_record_id = Column(Integer, nullable=True)  # ID of source record
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    run = relationship("DHIMS2SubmissionRun", back_populates="items")

    def __repr__(self):
        return f"<DHIMS2SubmissionItem(id={self.id}, key='{self.internal_metric_key}', value='{self.value}', status='{self.validation_status.value}')>"


class DHIMS2AuditLog(Base):
    """
    Audit log for DHIMS2 operations.
    Extends the general audit log with DHIMS2-specific actions.
    """
    __tablename__ = "dhims2_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String(100), nullable=True)
    
    # Action type specific to DHIMS2
    action = Column(String(50), nullable=False)  # BUILD, VALIDATE, APPROVE, SUBMIT, RESUBMIT, LOCK, UNLOCK, OVERRIDE
    
    # Entity references
    run_id = Column(Integer, ForeignKey("dhims2_submission_runs.id"), nullable=True)
    mapping_id = Column(Integer, ForeignKey("dhims2_mappings.id"), nullable=True)
    instance_id = Column(Integer, ForeignKey("dhims2_instances.id"), nullable=True)
    
    # Change tracking
    before_status = Column(String(50), nullable=True)
    after_status = Column(String(50), nullable=True)
    justification = Column(Text, nullable=True)  # Required for overrides/resubmissions
    
    # Request context
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User")
    run = relationship("DHIMS2SubmissionRun")
    mapping = relationship("DHIMS2Mapping")
    instance = relationship("DHIMS2Instance")

    def __repr__(self):
        return f"<DHIMS2AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', run_id={self.run_id})>"
