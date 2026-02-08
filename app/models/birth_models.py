"""
Birth / Delivery Models

SQLAlchemy models for birth records and delivery tracking.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date, Time, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class DeliveryType(str, enum.Enum):
    """Delivery type enumeration"""
    VAGINAL = "vaginal"
    CAESAREAN = "caesarean"
    ASSISTED = "assisted"
    VACUUM = "vacuum"
    FORCEPS = "forceps"
    OTHER = "other"


class BirthOutcome(str, enum.Enum):
    """Birth outcome enumeration"""
    LIVE = "live"
    STILLBIRTH = "stillbirth"
    NEONATAL_DEATH = "neonatal_death"


class Gender(str, enum.Enum):
    """Baby gender enumeration"""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class BirthRecord(Base):
    """
    SQLAlchemy Model for birth records.
    Tracks deliveries and newborn details.
    """
    __tablename__ = "birth_records"

    id = Column(Integer, primary_key=True, index=True)

    # Mother
    mother_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # If mother was IPD
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)

    # Delivery Info
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=True)
    delivery_type = Column(String(20), nullable=False, default=DeliveryType.VAGINAL.value)
    birth_outcome = Column(String(20), nullable=False, default=BirthOutcome.LIVE.value)

    # Baby
    gender = Column(String(10), nullable=True)
    weight_kg = Column(Numeric(5, 3), nullable=True)
    length_cm = Column(Numeric(5, 2), nullable=True)
    head_circumference_cm = Column(Numeric(5, 2), nullable=True)

    # Apgar
    apgar_1min = Column(Integer, nullable=True)
    apgar_5min = Column(Integer, nullable=True)
    apgar_10min = Column(Integer, nullable=True)

    # Staff
    delivered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assisted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Additional
    birth_number = Column(String(50), unique=True, nullable=True, index=True)  # e.g. BIRTH-2024-0001
    gravida = Column(Integer, nullable=True)
    para = Column(Integer, nullable=True)
    complications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    mother = relationship("Patient", foreign_keys=[mother_patient_id], back_populates="birth_records_as_mother")
    admission = relationship("Admission", foreign_keys=[admission_id])
    encounter = relationship("Encounter", foreign_keys=[encounter_id])
    delivered_by = relationship("User", foreign_keys=[delivered_by_id])
    assisted_by = relationship("User", foreign_keys=[assisted_by_id])
