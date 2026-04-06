from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class HospitalSettingsBase(BaseModel):
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    hospital_phone: Optional[str] = None
    hospital_email: Optional[EmailStr] = None
    hospital_website: Optional[str] = None
    logo_path: Optional[str] = None
    logo_url: Optional[str] = None
    # Laboratory-specific settings
    lab_contact_email: Optional[EmailStr] = None  # Lab contact email for queries
    lab_contact_phone: Optional[str] = None  # Lab contact phone
    accreditation: Optional[str] = None  # Accreditation body name
    accreditation_number: Optional[str] = None  # ISO/Accreditation number
    # Insurance activation settings
    nhis_enabled: Optional[bool] = True
    private_insurance_enabled: Optional[bool] = True
    # Charge Types configuration - list of charge type values
    charge_types_config: Optional[List[str]] = None


class HospitalSettingsCreate(HospitalSettingsBase):
    pass


class HospitalSettingsUpdate(HospitalSettingsBase):
    pass


class HospitalSettings(HospitalSettingsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

