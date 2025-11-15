from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration"""
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(str, enum.Enum):
    """Appointment type enumeration"""
    WALK_IN = "walk_in"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    FOLLOW_UP = "follow_up"


class Appointment(Base):
    """
    SQLAlchemy Model for patient appointments and queue management.
    Maps to workflow Step 2: Appointment/Queue
    """
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    department = Column(String(100), nullable=False)  # e.g., "General Medicine", "Pediatrics", "Emergency"
    department_type = Column(String(20), nullable=True, default="opd")  # "opd", "ipd", or "both" - for OPD/IPD distinction
    assigned_clinician_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional: assigned doctor/nurse
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Front office staff who created it
    
    # Appointment Details
    appointment_type = Column(Enum(AppointmentType), nullable=False, default=AppointmentType.WALK_IN)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED)
    priority = Column(Integer, default=5)  # 1-10 scale, 1 being highest priority
    
    # Scheduling
    scheduled_date = Column(DateTime, nullable=False)  # When the appointment is scheduled
    checked_in_at = Column(DateTime, nullable=True)  # When patient checked in
    started_at = Column(DateTime, nullable=True)  # When clinician started seeing patient
    completed_at = Column(DateTime, nullable=True)  # When appointment was completed
    
    # Notes
    chief_complaint = Column(String(500), nullable=True)  # Patient's main complaint
    notes = Column(String(1000), nullable=True)  # Additional notes
    
    # Queue Management
    queue_number = Column(Integer, nullable=True)  # Position in queue
    is_active = Column(Boolean, default=True)  # For soft deletion
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    assigned_clinician = relationship("User", foreign_keys=[assigned_clinician_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    encounters = relationship("Encounter", back_populates="appointment")
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, patient_id={self.patient_id}, status={self.status.value})>"

