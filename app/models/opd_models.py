from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from decimal import Decimal


class OPDVisitStatus(str, enum.Enum):
    """OPD visit status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OPDVisit(Base):
    """
    SQLAlchemy Model for OPD (Outpatient Department) visits.
    Tracks individual outpatient visits linked to patient_number.
    """
    __tablename__ = "opd_visits"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    queue_entry_id = Column(Integer, ForeignKey("opd_queue.id"), nullable=True)  # Optional link to queue entry
    appointment_id = Column(Integer, ForeignKey("scheduled_appointments.id"), nullable=True)  # Optional link to appointment
    
    # Visit Details
    opd_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique OPD number: "OPD-2024-0001"
    visit_date = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(postgresql.ENUM(OPDVisitStatus, values_callable=lambda x: [e.value for e in x], name='opdvisitstatus', create_type=False), nullable=False, default=OPDVisitStatus.ACTIVE)
    
    # Payment Status
    payment_status = Column(String(20), nullable=False, default="pending")  # "pending", "paid", "waived", "emergency"
    consultation_charge_created = Column(Boolean, default=False, server_default='false')
    
    # Financial Tracking
    total_charges = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    
    # Visit Information
    visit_type = Column(String(50), nullable=True)  # "routine", "emergency", "follow_up", "walk_in"
    chief_complaint = Column(Text, nullable=True)  # Initial chief complaint (can be updated in encounter)
    notes = Column(Text, nullable=True)  # Additional notes about the visit
    
    # Completion outcome (for emergency etc.): null=normal, "death", "transfer", "absconded"
    completion_outcome = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="opd_visits")
    queue_entry = relationship("OPDQueue")
    appointment = relationship("ScheduledAppointment", back_populates="opd_visits")
    encounters = relationship("Encounter", back_populates="opd_visit")
    invoices = relationship("Invoice", back_populates="opd_visit")
    
    def __repr__(self):
        return f"<OPDVisit(id={self.id}, opd_number='{self.opd_number}', patient_id={self.patient_id}, status={self.status.value})>"

