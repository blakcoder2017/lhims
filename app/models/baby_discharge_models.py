"""
Baby Discharge Summary Model
Tracks individual discharge information for each baby - essential for multiple births (twins, triplets)
where each baby may have different discharge dates, conditions, and outcomes.
"""
import enum
from datetime import date
from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from app.db.database import Base


class BabyConditionAtDischarge(str, enum.Enum):
    """Baby condition at discharge - GHS standard"""
    NORMAL = "Normal"
    ABNORMAL = "Abnormal"
    REFERRAL = "Referral"
    NICU = "NICU"
    DIED = "Died"


class EyeCareGiven(str, enum.Enum):
    """Eye care given - GHS standard"""
    CHLORAMPHENICOL = "Chloramphenicol"
    TETRACYCLINE = "Tetracycline"
    NONE = "None"


class BabyDischarge(Base):
    """
    SQLAlchemy Model for Baby Discharge Summary.
    Stores individual discharge information for each baby - essential for multiple births.
    """
    __tablename__ = "baby_discharge_summaries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to birth record (one-to-one, each baby has one discharge record)
    birth_record_id = Column(Integer, ForeignKey("birth_records.id"), nullable=False, unique=True)
    
    # Discharge Date
    discharge_date = Column(Date, nullable=True)
    
    # General Examination at Discharge
    heart_rate = Column(Integer, nullable=True)  # /min
    respiratory_rate = Column(Integer, nullable=True)  # /min
    temperature = Column(Numeric(5, 1), nullable=True)  # °C
    weight_at_discharge = Column(Numeric(6, 3), nullable=True)  # kg (especially for NICU)
    
    # Feeding Status
    breastfeeding_initiated = Column(Boolean, nullable=True)
    suckling_established = Column(Boolean, nullable=True)
    meconium_passed = Column(Boolean, nullable=True)
    urine_passed = Column(Boolean, nullable=True)
    
    # Eye Care
    eye_care_given = Column(String(50), nullable=True)
    
    # Immunisation Dates
    cord_care_date = Column(Date, nullable=True)
    vitamin_k_date = Column(Date, nullable=True)
    bcg_date = Column(Date, nullable=True)
    hepatitis_b_date = Column(Date, nullable=True)
    oral_polio_date = Column(Date, nullable=True)
    
    # Baby's Condition at Discharge
    condition = Column(String(50), nullable=True)  # Normal, Abnormal, Referral, NICU, Died
    abnormal_specify = Column(Text, nullable=True)  # If Abnormal, specify
    
    # Referred to facility (if Referral)
    referred_to = Column(String(200), nullable=True)
    
    # Additional notes
    notes = Column(Text, nullable=True)
    
    # Recording metadata
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(Date, nullable=True, default=date.today)
    updated_at = Column(Date, nullable=True)
    
    # Relationship
    birth_record = relationship("BirthRecord", back_populates="baby_discharge")
    recorded_by = relationship("User")
