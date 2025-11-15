"""
Disease Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DiseaseBase(BaseModel):
    """Base schema for disease data"""
    name: str = Field(..., max_length=500)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class DiseaseCreate(DiseaseBase):
    """Schema for creating a new disease"""
    pass


class DiseaseUpdate(BaseModel):
    """Schema for updating a disease"""
    name: Optional[str] = Field(None, max_length=500)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class Disease(DiseaseBase):
    """Schema for disease response"""
    id: int
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class EncounterDiseaseCreate(BaseModel):
    """Schema for adding a disease to an encounter"""
    disease_id: Optional[int] = None
    custom_name: Optional[str] = Field(None, max_length=500)
    is_primary: bool = False


class EncounterDisease(BaseModel):
    """Schema for encounter disease response"""
    id: int
    encounter_id: int
    disease_id: Optional[int] = None
    custom_name: Optional[str] = None
    is_primary: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

