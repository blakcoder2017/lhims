"""
Procedure Models

SQLAlchemy models for tracking surgical and non-surgical procedures.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class ProcedureType(str, enum.Enum):
    """Procedure type enumeration"""
    SURGICAL = "surgical"
    NON_SURGICAL = "non_surgical"
    DIAGNOSTIC = "diagnostic"
    THERAPEUTIC = "therapeutic"
    MINOR = "minor"
    MAJOR = "major"


class ProcedureStatus(str, enum.Enum):
    """Procedure status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class Procedure(Base):
    """
    SQLAlchemy Model for tracking procedures (surgical and non-surgical).
    """
    __tablename__ = "procedures"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Direct link to admission
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)  # Optional link to encounter
    procedure_catalog_id = Column(Integer, ForeignKey("procedure_catalog.id"), nullable=True)  # Link to procedure catalog
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Doctor who performed the procedure
    ordered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Doctor who ordered the procedure
    
    # Procedure Details
    procedure_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique procedure number
    procedure_name = Column(String(200), nullable=False)  # Name of the procedure
    procedure_code = Column(String(50), nullable=True)  # Procedure code (e.g., CPT, ICD-10-PCS)
    procedure_type = Column(Enum(ProcedureType), nullable=False)  # Type of procedure
    description = Column(Text, nullable=True)  # Detailed description
    
    # Status and Timing
    status = Column(Enum(ProcedureStatus), nullable=False, default=ProcedureStatus.SCHEDULED)
    scheduled_date = Column(DateTime, nullable=True)  # Scheduled date/time
    start_time = Column(DateTime, nullable=True)  # Actual start time
    end_time = Column(DateTime, nullable=True)  # Actual end time
    duration_minutes = Column(Integer, nullable=True)  # Duration in minutes
    
    # Procedure Details
    indication = Column(Text, nullable=True)  # Clinical indication for procedure
    findings = Column(Text, nullable=True)  # Findings during procedure
    complications = Column(Text, nullable=True)  # Any complications
    outcome = Column(Text, nullable=True)  # Procedure outcome
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Anesthesia Information
    anesthesia_type = Column(String(100), nullable=True)  # Type of anesthesia used
    anesthesia_provider = Column(String(200), nullable=True)  # Anesthesia provider name
    
    # Location
    location = Column(String(200), nullable=True)  # Where procedure was performed (e.g., "Operating Room 1", "Procedure Room")
    
    # Walk-in Support
    is_walk_in = Column(Boolean, default=False, server_default='false')  # True if this is a walk-in procedure
    checked_in_at = Column(DateTime, nullable=True)  # When front desk checked in the walk-in procedure
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Front desk staff who checked in
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True, server_default='true')
    
    # Relationships
    patient = relationship("Patient", back_populates="procedures")
    admission = relationship("Admission", back_populates="procedure_records")
    encounter = relationship("Encounter", back_populates="procedures")
    procedure_catalog = relationship("ProcedureCatalog", foreign_keys=[procedure_catalog_id])
    performed_by = relationship("User", foreign_keys=[performed_by_id])
    ordered_by = relationship("User", foreign_keys=[ordered_by_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    
    def __repr__(self):
        return f"<Procedure(id={self.id}, procedure_number='{self.procedure_number}', procedure_name='{self.procedure_name}', status={self.status.value})>"

