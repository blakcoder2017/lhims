"""
NHIS Claims Models

This module defines models for NHIS (National Health Insurance Scheme) claims.
Note: Actual API integration is pending NHIA API availability.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from decimal import Decimal
import json


class ClaimStatus(str, enum.Enum):
    """NHIS claim status enumeration"""
    DRAFT = "draft"
    PENDING = "pending"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class NHISClaim(Base):
    """
    SQLAlchemy Model for NHIS claims.
    Represents a claim package for submission to NHIA.
    """
    __tablename__ = "nhis_claims"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)  # Optional link to invoice
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Claim Information
    claim_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique claim number
    nhis_number = Column(String(50), nullable=False)  # Patient NHIS number
    facility_code = Column(String(50), nullable=True)  # Facility NHIS code
    claim_date = Column(DateTime, nullable=False, server_default=func.now())
    
    # Claim Status
    status = Column(postgresql.ENUM(ClaimStatus, values_callable=lambda x: [e.value for e in x], name='claimstatus', create_type=False), nullable=False, default=ClaimStatus.DRAFT)
    
    # Claim Data (JSON format for flexibility)
    claim_data = Column(Text, nullable=True)  # JSON structure of claim data
    diagnosis_codes = Column(Text, nullable=True)  # JSON array of ICD-10 codes
    service_codes = Column(Text, nullable=True)  # JSON array of service codes
    
    # Financial Information
    total_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    nhis_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Amount covered by NHIS
    co_pay_amount = Column(Numeric(10, 2), nullable=False, default=Decimal('0.00'))  # Co-pay amount
    
    # Submission Information
    submitted_at = Column(DateTime, nullable=True)  # When claim was submitted
    submission_reference = Column(String(100), nullable=True)  # Reference from NHIA system
    response_data = Column(Text, nullable=True)  # JSON response from NHIA
    
    # Processing Information
    processed_at = Column(DateTime, nullable=True)  # When claim was processed
    approved_amount = Column(Numeric(10, 2), nullable=True)  # Amount approved by NHIA
    rejection_reason = Column(Text, nullable=True)  # Reason if rejected
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    encounter = relationship("Encounter")
    patient = relationship("Patient")
    invoice = relationship("Invoice")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<NHISClaim(id={self.id}, claim_number='{self.claim_number}', status={self.status.value})>"
    
    def to_claim_format(self) -> dict:
        """
        Convert claim to NHIA claim format (structure ready for API integration).
        This is a placeholder structure - actual format depends on NHIA API specification.
        """
        return {
            "claim_number": self.claim_number,
            "nhis_number": self.nhis_number,
            "facility_code": self.facility_code,
            "claim_date": self.claim_date.isoformat() if self.claim_date else None,
            "diagnosis_codes": json.loads(self.diagnosis_codes) if self.diagnosis_codes else [],
            "service_codes": json.loads(self.service_codes) if self.service_codes else [],
            "total_amount": str(self.total_amount),
            "nhis_amount": str(self.nhis_amount),
            "co_pay_amount": str(self.co_pay_amount),
            "claim_data": json.loads(self.claim_data) if self.claim_data else {}
        }

