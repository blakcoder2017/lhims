from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class HospitalSettingsBase(BaseModel):
    hospital_name: Optional[str] = None
    hospital_address: Optional[str] = None
    hospital_phone: Optional[str] = None
    hospital_email: Optional[EmailStr] = None
    hospital_website: Optional[str] = None
    logo_path: Optional[str] = None
    logo_url: Optional[str] = None


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

