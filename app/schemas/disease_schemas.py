"""
Disease Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DiseaseCategory(str):
    """Disease categories for DHIMS2 reporting"""
    INFECTIOUS = "infectious"
    NCD = "ncd"
    MATERNAL = "maternal"
    CHILD_HEALTH = "child_health"
    INJURY = "injury"
    MENTAL_HEALTH = "mental_health"
    EYE_CONDITIONS = "eye_conditions"
    DENTAL = "dental"
    SKIN = "skin"
    RESPIRATORY = "respiratory"
    OTHER = "other"

    @classmethod
    def choices(cls):
        return [cls.INFECTIOUS, cls.NCD, cls.MATERNAL, cls.CHILD_HEALTH, cls.INJURY, 
                cls.MENTAL_HEALTH, cls.EYE_CONDITIONS, cls.DENTAL, cls.SKIN, 
                cls.RESPIRATORY, cls.OTHER]


class DiseaseBase(BaseModel):
    """Base schema for disease data"""
    name: str = Field(..., max_length=500)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    category: str = DiseaseCategory.OTHER
    dhis2_data_element_uid: Optional[str] = Field(None, max_length=20)
    dhis2_category_option_combo_uid: Optional[str] = Field(None, max_length=20)


class DiseaseCreate(DiseaseBase):
    """Schema for creating a new disease"""
    pass


class DiseaseUpdate(BaseModel):
    """Schema for updating a disease"""
    name: Optional[str] = Field(None, max_length=500)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    category: Optional[str] = None
    dhis2_data_element_uid: Optional[str] = Field(None, max_length=20)
    dhis2_category_option_combo_uid: Optional[str] = Field(None, max_length=20)


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

