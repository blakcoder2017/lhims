"""
Procedure Catalog Models

SQLAlchemy models for procedure catalog management.
Similar to lab tests and radiology studies catalog.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ProcedureCatalog(Base):
    """
    SQLAlchemy Model for procedure catalog.
    Master catalog of all available procedures with pricing.
    """
    __tablename__ = "procedure_catalog"

    id = Column(Integer, primary_key=True, index=True)
    
    # Procedure Information
    procedure_name = Column(String(255), nullable=False, index=True)  # Procedure name
    procedure_code = Column(String(50), unique=True, nullable=True, index=True)  # Procedure code (e.g., CPT, ICD-10-PCS)
    procedure_category = Column(String(100), nullable=True)  # Category (e.g., Surgery, Diagnostic, Therapeutic)
    procedure_type = Column(String(100), nullable=True)  # Type (e.g., Surgical, Non-Surgical, Diagnostic, Therapeutic, Minor, Major)
    
    # Charge Type Association (replaces department for billing)
    charge_type = Column(String(50), nullable=True, index=True)  # Maps to ChargeType: consultation, lab_test, radiology, pharmacy, procedure, admission, antenatal, other
    
    # Department Association (kept for reference but charge_type is primary)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # Department this procedure belongs to
    
    # Procedure Details
    description = Column(Text, nullable=True)  # Procedure description
    indication = Column(Text, nullable=True)  # Common indications
    preparation_instructions = Column(Text, nullable=True)  # Pre-procedure instructions
    post_procedure_care = Column(Text, nullable=True)  # Post-procedure care instructions
    
    # Duration Information
    estimated_duration_minutes = Column(Integer, nullable=True)  # Estimated duration in minutes
    typical_duration_minutes = Column(Integer, nullable=True)  # Typical duration range
    
    # Pricing - Cash
    cash_price = Column(Numeric(10, 2), nullable=True)  # Cash price
    cash_currency = Column(String(10), nullable=True, default="GHS")  # Currency for cash price
    
    # Pricing - Insurance Packages
    nhis_covered = Column(Boolean, default=False)  # NHIS coverage
    nhis_code = Column(String(50), nullable=True)  # NHIS procedure code
    nhis_price = Column(Numeric(10, 2), nullable=True)  # NHIS negotiated price
    
    private_insurance_covered = Column(Boolean, default=False)  # Private insurance coverage
    private_insurance_price = Column(Numeric(10, 2), nullable=True)  # Private insurance negotiated price
    
    # Anesthesia Information
    requires_anesthesia = Column(Boolean, default=False)  # Does procedure require anesthesia
    typical_anesthesia_type = Column(String(100), nullable=True)  # Typical anesthesia type (e.g., General, Local, Regional)
    
    # Location Requirements
    requires_operating_room = Column(Boolean, default=False)  # Requires operating room
    typical_location = Column(String(200), nullable=True)  # Typical location (e.g., "Operating Room", "Procedure Room")
    
    # Restrictions
    is_specialized = Column(Boolean, default=False)  # Is this a specialized procedure (requires special approval)
    requires_consultation = Column(Boolean, default=False)  # Requires pre-procedure consultation
    
    # Status
    is_active = Column(Boolean, default=True)  # Is procedure active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    department = relationship("Department", foreign_keys=[department_id])
    
    def __repr__(self):
        return f"<ProcedureCatalog(id={self.id}, procedure_name='{self.procedure_name}')>"

