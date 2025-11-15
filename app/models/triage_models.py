from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base # Assuming Base is defined here

class TriageVitals(Base):
    """
    SQLAlchemy Model for storing patient Triage (Vital Signs) records.
    Includes comprehensive vital signs tracking with automatic BMI calculation.
    """
    __tablename__ = "triage_vitals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Vital Signs Data
    # Temperature measurement
    temperature = Column(Float, nullable=False)  # in Celsius
    
    # Blood pressure (Systolic/Diastolic)
    systolic_bp = Column(Integer, nullable=True)  # Systolic BP in mmHg
    diastolic_bp = Column(Integer, nullable=True)  # Diastolic BP in mmHg
    blood_pressure = Column(String(50), nullable=True)  # Legacy field for backward compatibility
    
    # Pulse rate
    pulse_rate = Column(Integer, nullable=True)  # Heart rate in bpm
    
    # Respiratory rate
    respiratory_rate = Column(Integer, nullable=True)  # Breaths per minute
    
    # Oxygen saturation (SpO2)
    oxygen_saturation = Column(Integer, nullable=True)  # SpO2 percentage
    
    # Weight and height
    weight = Column(Numeric(5, 2), nullable=True)  # Weight in kg
    height = Column(Numeric(5, 2), nullable=True)  # Height in cm
    
    # BMI calculation (automatically calculated)
    bmi = Column(Numeric(5, 2), nullable=True)  # Body Mass Index
    
    # Pain scale (1-10)
    pain_scale = Column(Integer, nullable=True)  # Pain scale from 1-10
    
    # Timestamps
    recorded_at = Column(DateTime, default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="vitals_records")
    recorded_by = relationship("User")
    
    def calculate_bmi(self):
        """Calculate BMI from weight (kg) and height (cm)."""
        if self.weight and self.height and self.height > 0:
            # Convert height from cm to meters
            height_m = float(self.height) / 100.0
            weight_kg = float(self.weight)
            bmi_value = weight_kg / (height_m ** 2)
            return round(bmi_value, 2)
        return None


# Note: You need to ensure a 'patients' table and 'users' table exist 
# and have the necessary relationships defined in their respective models.