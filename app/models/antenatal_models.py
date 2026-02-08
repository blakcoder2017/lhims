"""
Antenatal / Midwife Models

SQLAlchemy models for antenatal (ANC) visit tracking and midwife care.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AntenatalVisit(Base):
    """
    SQLAlchemy Model for antenatal (ANC) visits.
    Tracks pregnancy care visits for midwife/antenatal clinic.
    """
    __tablename__ = "antenatal_visits"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Visit Details
    visit_date = Column(Date, nullable=False)
    visit_number = Column(Integer, nullable=True)  # ANC visit number (e.g. 1, 2, 3...)

    # Pregnancy Info
    gestational_weeks = Column(Numeric(5, 2), nullable=True)
    lmp = Column(Date, nullable=True)  # Last menstrual period
    edd = Column(Date, nullable=True)  # Expected date of delivery

    # Vitals
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    weight_kg = Column(Numeric(6, 2), nullable=True)
    height_cm = Column(Numeric(5, 2), nullable=True)
    bmi = Column(Numeric(5, 2), nullable=True)

    # Fetal Assessment
    fetal_heart_rate = Column(Integer, nullable=True)
    fundal_height_cm = Column(Numeric(5, 2), nullable=True)
    fetal_position = Column(String(50), nullable=True)
    fetal_movement = Column(String(50), nullable=True)

    # Lab/Investigations
    hemoglobin = Column(Numeric(5, 2), nullable=True)
    urine_protein = Column(String(20), nullable=True)
    blood_group = Column(String(10), nullable=True)
    rhesus_factor = Column(String(5), nullable=True)

    # Risk Assessment
    risk_factors = Column(Text, nullable=True)
    complications = Column(Text, nullable=True)

    # Counseling & Education
    counseling_given = Column(Text, nullable=True)
    supplements_prescribed = Column(Text, nullable=True)

    # Follow-up
    next_visit_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    patient = relationship("Patient", back_populates="antenatal_visits")
    encounter = relationship("Encounter", back_populates="antenatal_visits")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
