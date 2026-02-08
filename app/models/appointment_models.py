from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class QueueStatus(str, enum.Enum):
    """Queue status enumeration"""
    WAITING = "waiting"  # Patient in queue waiting to be seen
    IN_PROGRESS = "in_progress"  # Doctor currently seeing patient
    COMPLETED = "completed"  # Patient finished consultation
    CANCELLED = "cancelled"  # Patient left queue
    NO_SHOW = "no_show"  # Patient didn't show up for vitals/queue


class VisitType(str, enum.Enum):
    """Visit type enumeration for queue patients"""
    WALK_IN = "walk_in"
    EMERGENCY = "emergency"
    FOLLOW_UP = "follow_up"


class OPDQueue(Base):
    """
    SQLAlchemy Model for OPD walk-in queue management.
    This is for walk-in patients who get checked in and queued to see doctors.
    Maps to workflow Step 2: Queue Management (not appointments)
    """
    __tablename__ = "opd_queue"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    department = Column(String(100), nullable=False)  # e.g., "General Medicine", "Pediatrics", "Emergency"
    department_type = Column(String(20), nullable=True, default="opd")  # "opd", "ipd", or "both" - for OPD/IPD distinction
    assigned_clinician_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional: assigned doctor/nurse
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Front office staff who created it
    
    # Queue Details
    visit_type = Column(Enum(VisitType), nullable=False, default=VisitType.WALK_IN)
    status = Column(Enum(QueueStatus), nullable=False, default=QueueStatus.WAITING)
    priority = Column(Integer, default=5)  # 1-10 scale, 1 being highest priority
    
    # Queue Management
    queue_number = Column(Integer, nullable=True)  # Position in queue
    checked_in_at = Column(DateTime, nullable=True)  # When patient checked in (vitals completed)
    started_at = Column(DateTime, nullable=True)  # When clinician started seeing patient
    completed_at = Column(DateTime, nullable=True)  # When queue entry was completed
    
    # Notes
    chief_complaint = Column(String(500), nullable=True)  # Patient's main complaint from triage
    notes = Column(String(1000), nullable=True)  # Additional notes
    
    # Soft delete
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="queue_entries")
    assigned_clinician = relationship("User", foreign_keys=[assigned_clinician_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    encounters = relationship("Encounter", back_populates="queue_entry")
    
    def __repr__(self):
        return f"<OPDQueue(id={self.id}, patient_id={self.patient_id}, status={self.status.value}, queue_number={self.queue_number})>"

