"""
Direct Service Registration Models

Models for patients to access services directly without consultation.
Services: Antenatal, Lab, Pharmacy, Radiology, Procedures
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class DirectServiceType(str, enum.Enum):
    """Types of services available for direct registration"""
    ANTENATAL = "antenatal"
    LAB = "lab"
    PHARMACY = "pharmacy"
    RADIOLOGY = "radiology"
    PROCEDURE = "procedure"


class DirectServiceRegistrationStatus(str, enum.Enum):
    """Status of direct service registration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DirectServiceRegistration(Base):
    """
    Model for Direct Service Registration.
    Tracks patients who register directly for services without consultation.
    """
    __tablename__ = "direct_service_registrations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Patient Information
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    
    # Service Details
    service_type = Column(String(50), nullable=False)  # antenatal, lab, pharmacy, radiology, procedure
    service_type_label = Column(String(200), nullable=True)  # Human-readable service name
    
    # Status
    status = Column(String(50), default=DirectServiceRegistrationStatus.PENDING.value)
    
    # For Antenatal specific
    gestational_weeks = Column(Numeric(5, 2), nullable=True)
    lmp = Column(Date, nullable=True)
    edd = Column(Date, nullable=True)
    
    # For Lab/Radiology/Procedure - store order ID
    order_id = Column(Integer, nullable=True)
    order_type = Column(String(50), nullable=True)  # lab_order, radiology_order, procedure, prescription
    
    # Registration Details
    registered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    registration_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="direct_service_registrations")
    registered_by = relationship("User", foreign_keys=[registered_by_id])
    
    def __repr__(self):
        return f"<DirectServiceRegistration(id={self.id}, patient_id={self.patient_id}, service_type={self.service_type})>"
