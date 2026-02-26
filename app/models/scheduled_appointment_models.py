from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class AppointmentType(str, enum.Enum):
    """Appointment type enumeration"""
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    PROCEDURE = "procedure"
    EMERGENCY = "emergency"
    LAB_WORK = "lab_work"
    RADIOLOGY = "radiology"
    OTHER = "other"
    WALK_IN = "walk_in"


class AppointmentStatus(str, enum.Enum):
    """Appointment status enumeration (alias for ScheduledAppointmentStatus)"""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


# Keep old name for backward compatibility
ScheduledAppointmentStatus = AppointmentStatus


class ScheduledAppointment(Base):
    """
    SQLAlchemy Model for scheduled appointments (separate from walk-in queue).
    This is for proper scheduled appointments, not walk-in queue patients.
    """
    __tablename__ = "scheduled_appointments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Patient Information - can be existing patient or new patient name
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # Optional - for existing patients
    patient_name = Column(String(255), nullable=True)  # For patients not in system
    patient_phone = Column(String(20), nullable=True)  # Contact for non-system patients
    
    # Department and Doctor Assignment
    department = Column(String(100), nullable=True)  # Department for the appointment
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Scheduling
    scheduled_date = Column(DateTime, nullable=False)  # Appointment date/time
    duration_minutes = Column(Integer, default=30)  # Default 30 minutes
    
    # For backward compatibility with code using appointment_date
    @property
    def appointment_date(self):
        """Alias for scheduled_date - kept for backward compatibility"""
        return self.scheduled_date
    
    @appointment_date.setter
    def appointment_date(self, value):
        """Set scheduled_date via appointment_date for backward compatibility"""
        self.scheduled_date = value
    
    # Appointment Details
    appointment_type = Column(Enum(AppointmentType), nullable=False, default=AppointmentType.CONSULTATION)
    reason_complaint = Column(Text, nullable=True)  # Reason for appointment
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Status and Management
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED)
    priority = Column(Integer, default=5)  # 1-10 scale, 1 being highest priority
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    cancelled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Audit fields
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Soft delete
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", foreign_keys=[patient_id], back_populates="scheduled_appointments")
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id])
    encounters = relationship("Encounter", back_populates="appointment")
    opd_visits = relationship("OPDVisit", back_populates="appointment")
    
    def __repr__(self):
        if self.patient:
            patient_info = f"Patient({self.patient.first_name} {self.patient.last_name})"
        else:
            patient_info = f"Patient({self.patient_name})"
        dept = f", department={self.department}" if self.department else ""
        return f"<ScheduledAppointment(id={self.id}, {patient_info}, doctor={self.assigned_doctor.full_name if self.assigned_doctor else 'N/A'}{dept}, status={self.status.value})>"


# Alias for backward compatibility - allows importing Appointment from this module
Appointment = ScheduledAppointment
