from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional
from decimal import Decimal

class TriageVitalsBase(BaseModel):
    """Base schema for vital signs with all required fields."""
    # Temperature measurement
    temperature: float = Field(..., description="Temperature in Celsius", ge=30.0, le=45.0)
    
    # Blood pressure (Systolic/Diastolic) - separate fields preferred
    systolic_bp: Optional[int] = Field(None, description="Systolic BP in mmHg", ge=50, le=250)
    diastolic_bp: Optional[int] = Field(None, description="Diastolic BP in mmHg", ge=30, le=150)
    blood_pressure: Optional[str] = Field(None, description="Legacy BP field (e.g., '120/80 mmHg')")
    
    # Pulse rate
    pulse_rate: Optional[int] = Field(None, description="Heart rate in bpm", ge=30, le=220)
    
    # Respiratory rate
    respiratory_rate: Optional[int] = Field(None, description="Respiratory rate per minute", ge=8, le=40)
    
    # Oxygen saturation (SpO2)
    oxygen_saturation: Optional[int] = Field(None, description="SpO2 percentage", ge=0, le=100)
    
    # Weight and height
    weight: Optional[Decimal] = Field(None, description="Weight in kg", ge=0.1, le=500)
    height: Optional[Decimal] = Field(None, description="Height in cm", ge=30, le=250)
    
    # BMI (calculated automatically, but can be provided)
    bmi: Optional[Decimal] = Field(None, description="Body Mass Index (calculated)")
    
    # Pain scale (1-10)
    pain_scale: Optional[int] = Field(None, description="Pain scale from 1-10", ge=0, le=10)
    
    @model_validator(mode='after')
    def validate_blood_pressure(self):
        """Validate and auto-correct blood pressure values if they appear to be swapped."""
        systolic = self.systolic_bp
        diastolic = self.diastolic_bp
        
        # Only validate if both values are provided and are not None
        if systolic is not None and diastolic is not None:
            # If values appear to be swapped (diastolic > systolic), auto-swap them
            if diastolic > systolic:
                # Swap the values - this handles common data entry errors
                self.systolic_bp = diastolic
                self.diastolic_bp = systolic
                # After swap, systolic should now be > diastolic, so we're good
            # After potential swap, validate that systolic > diastolic (strictly greater)
            elif systolic <= diastolic:
                raise ValueError(f'Systolic BP ({systolic}) must be greater than Diastolic BP ({diastolic})')
        
        return self

class TriageVitalsCreate(TriageVitalsBase):
    """Schema for creating new vital signs records."""
    patient_id: int
    recorded_by_id: int

class TriageVitals(TriageVitalsBase):
    """Schema for returning saved vital sign records."""
    id: int
    patient_id: int
    recorded_by_id: int
    recorded_at: datetime

    class Config:
        from_attributes = True