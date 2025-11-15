from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app.db.database import Base 
import enum


class PaymentMechanism(str, enum.Enum):
    """Payment mechanism enumeration for Financial Screening (Workflow Step 3)"""
    CASH = "cash"
    NHIS = "nhis"  # National Health Insurance Scheme
    PRIVATE_INSURANCE = "private_insurance"
    SELF_PAY = "self_pay"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_number = Column(String, unique=True, index=True, nullable=True)  # Auto-generated: DGMS + sequential number
    
    # Core Demographics
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String, nullable=False) # e.g., 'Male', 'Female', 'Other'
    national_id = Column(String, unique=True, index=True, nullable=True) # E.g., Ghana Card ID or NHIS number (optional)
    
    # Contact
    phone_number = Column(String, index=True)
    address = Column(String)
    
    # Financial Screening (Workflow Step 3: Financial Screening)
    payment_mechanism = Column(Enum(PaymentMechanism), nullable=True)  # Cash, NHIS, Private Insurance
    nhis_number = Column(String, index=True, nullable=True)  # NHIS membership number if applicable
    insurance_provider = Column(String, nullable=True)  # Private insurance provider name
    insurance_policy_number = Column(String, nullable=True)  # Insurance policy number
    
    # Languages
    languages_spoken = Column(String, nullable=True)  # Comma-separated list of languages (e.g., "English, Twi, Ga")
    
    # Audit Fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Patient Status
    is_active = Column(Boolean, default=True) # For deactivating records
    vitals_records = relationship("TriageVitals", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    encounters = relationship("Encounter", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    admissions = relationship("Admission", back_populates="patient")
    procedures = relationship("Procedure", back_populates="patient")
    lab_orders = relationship("LabOrder", back_populates="patient")
    radiology_orders = relationship("RadiologyOrder", back_populates="patient")

    def __repr__(self):
        return f"<Patient(id={self.id}, name='{self.first_name} {self.last_name}')>"