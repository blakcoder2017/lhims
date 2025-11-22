"""
Discharge Clearance Models

This module defines models for tracking discharge clearance workflow,
including payment clearance and nursing clearance.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DischargeClearance(Base):
    """
    SQLAlchemy Model for tracking discharge clearance workflow.
    Ensures payment and nursing clearance before patient discharge.
    """
    __tablename__ = "discharge_clearances"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False, unique=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    
    # Clearance Status
    payment_cleared = Column(Boolean, default=False, nullable=False)  # Payment cleared
    payment_cleared_at = Column(DateTime, nullable=True)  # When payment was cleared
    payment_cleared_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who cleared payment
    
    nursing_cleared = Column(Boolean, default=False, nullable=False)  # Nursing clearance
    nursing_cleared_at = Column(DateTime, nullable=True)  # When nursing cleared
    nursing_cleared_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nurse who cleared
    
    # Clearance Notes
    payment_notes = Column(Text, nullable=True)  # Notes about payment clearance
    nursing_notes = Column(Text, nullable=True)  # Notes from nursing clearance
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    admission = relationship("Admission", foreign_keys=[admission_id])
    patient = relationship("Patient")
    payment_cleared_by = relationship("User", foreign_keys=[payment_cleared_by_id])
    nursing_cleared_by = relationship("User", foreign_keys=[nursing_cleared_by_id])
    
    def __repr__(self):
        return f"<DischargeClearance(id={self.id}, admission_id={self.admission_id}, payment_cleared={self.payment_cleared}, nursing_cleared={self.nursing_cleared})>"
    
    @property
    def is_cleared(self) -> bool:
        """Check if both payment and nursing clearance are complete"""
        return self.payment_cleared and self.nursing_cleared

