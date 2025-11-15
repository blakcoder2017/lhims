from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class DrugAdministration(Base):
    """
    SQLAlchemy Model for drug administration records.
    Tracks when medications are administered to patients during admission.
    """
    __tablename__ = "drug_administrations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False)  # medication_identifier
    administered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Administration Details
    administration_time = Column(DateTime, nullable=False)  # When the drug was administered
    dosage_given = Column(String(100), nullable=True)  # Actual dosage given (may differ from prescribed)
    route = Column(String(50), nullable=True)  # Route of administration (oral, IV, IM, etc.)
    notes = Column(Text, nullable=True)  # Additional notes about administration
    
    # Status
    is_active = Column(Boolean, default=True)  # For soft deletion
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    admission = relationship("Admission", back_populates="drug_administrations")
    prescription = relationship("Prescription")
    administered_by = relationship("User", foreign_keys=[administered_by_id])
    
    def __repr__(self):
        return f"<DrugAdministration(id={self.id}, prescription_id={self.prescription_id}, administration_time={self.administration_time})>"

