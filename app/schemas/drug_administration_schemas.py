from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Union


class DispensedDrugResponse(BaseModel):
    """Response schema for dispensed drugs"""
    medication_identifier: int = Field(..., description="Prescription ID")
    medication_name: str = Field(..., description="Name of the medication")
    dosage: str = Field(..., description="Prescribed dosage")
    
    class Config:
        from_attributes = True


class DrugAdministrationCreate(BaseModel):
    """Schema for creating a drug administration record"""
    admission_number: str = Field(..., description="Admission number")
    medication_identifier: int = Field(..., description="Prescription ID")
    administration_time: Union[datetime, str] = Field(..., description="When the drug was administered")
    administered_by: int = Field(..., description="User ID of the person who administered")
    dosage_given: Optional[str] = Field(None, description="Actual dosage given")
    route: Optional[str] = Field(None, description="Route of administration")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator('administration_time', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            # Try parsing ISO format datetime string
            try:
                # Handle both with and without timezone
                if 'T' in v:
                    # Remove timezone if present (e.g., "2024-01-01T10:00" or "2024-01-01T10:00:00Z")
                    v = v.split('+')[0].split('Z')[0]
                    # Parse format: YYYY-MM-DDTHH:MM or YYYY-MM-DDTHH:MM:SS
                    if len(v) == 16:  # YYYY-MM-DDTHH:MM
                        return datetime.strptime(v, "%Y-%m-%dT%H:%M")
                    else:  # YYYY-MM-DDTHH:MM:SS
                        return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")
                else:
                    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError(f"Invalid datetime format: {v}. Expected format: YYYY-MM-DDTHH:MM")
        return v
    
    class Config:
        from_attributes = True


class DrugAdministrationResponse(BaseModel):
    """Response schema for drug administration record"""
    id: int
    admission_id: int
    prescription_id: int
    administered_by_id: int
    administration_time: datetime
    dosage_given: Optional[str]
    route: Optional[str]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

