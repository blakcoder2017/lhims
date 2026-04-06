"""
Lab Template System Models
- LabTemplate: Template metadata (DRAFT/PUBLISHED/ARCHIVED)
- LabTemplateVersion: Immutable versioned schema (schema_json)
- LabReferenceRange: Field-based reference ranges (field_code, sex, age)
- LabOptionSet: Reusable picklists (DIPSTICK_SCALE, etc.)
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class LabOptionSet(Base):
    """Reusable option sets for choice/multichoice fields (e.g. DIPSTICK_SCALE)."""
    __tablename__ = "lab_option_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    options_json = Column(JSONB, nullable=False)  # e.g. ["Negative","Trace","+","++","+++"]
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class LabTemplate(Base):
    """Lab test template (metadata). Published versions are immutable."""
    __tablename__ = "lab_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    discipline = Column(String(100), nullable=False)  # HEMATOLOGY, CHEMISTRY, MICROBIOLOGY, etc.
    status = Column(String(50), nullable=False, default="DRAFT")  # DRAFT, PUBLISHED, ARCHIVED
    current_version = Column(Integer, nullable=True)  # Latest published version number
    
    # Usage tracking
    usage_count = Column(Integer, nullable=True, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    created_by = relationship("User", foreign_keys=[created_by_id])
    versions = relationship("LabTemplateVersion", back_populates="template", order_by="LabTemplateVersion.version")


class LabTemplateVersion(Base):
    """Immutable version of a template. PUBLISHED versions cannot be changed."""
    __tablename__ = "lab_template_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("lab_templates.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="DRAFT")  # DRAFT, PUBLISHED
    schema_json = Column(JSONB, nullable=False)
    change_note = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    checksum = Column(String(64), nullable=True)

    template = relationship("LabTemplate", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_id])


class LabAuditEvent(Base):
    """Lab-specific audit trail for result/workflow changes."""
    __tablename__ = "lab_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)  # lab_order, lab_template
    entity_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # create, update, submit, verify, authorize, amend
    old_json = Column(JSONB, nullable=True)
    new_json = Column(JSONB, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class LabReferenceRange(Base):
    """Field-based reference ranges for template fields (field_code = template field code)."""
    __tablename__ = "lab_reference_ranges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_code = Column(String(100), nullable=False, index=True)
    sex = Column(String(10), nullable=True, default="ANY")  # M, F, ANY
    
    # Postnatal age (days)
    age_min_days = Column(Integer, nullable=True)
    age_max_days = Column(Integer, nullable=True)
    
    # Gestational age (weeks) - for preterm neonates
    gestational_age_min_weeks = Column(Integer, nullable=True)
    gestational_age_max_weeks = Column(Integer, nullable=True)
    is_gestational_age_based = Column(Boolean, default=False)
    
    # Reference values
    low = Column(Numeric(20, 6), nullable=True)
    high = Column(Numeric(20, 6), nullable=True)
    critical_low = Column(Numeric(20, 6), nullable=True)
    critical_high = Column(Numeric(20, 6), nullable=True)
    text_range = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    facility_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class LabTemplateDocument(Base):
    """Document attachments for lab templates (SOPs, instructions, forms, etc.)"""
    __tablename__ = "lab_template_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("lab_templates.id", ondelete="CASCADE"), nullable=False)
    
    # Document metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)  # MIME type
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_path = Column(String(500), nullable=False)  # Storage path
    
    # Description and category
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # SOP, FORM, INSTRUCTION, REFERENCE, OTHER
    
    # Metadata
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    template = relationship("LabTemplate")
    uploaded_by = relationship("User")
