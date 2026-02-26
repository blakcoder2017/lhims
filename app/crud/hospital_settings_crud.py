"""
Hospital Settings CRUD Operations
"""
from sqlalchemy.orm import Session
from typing import Optional
from app.models.hospital_settings_models import HospitalSettings


def get_hospital_settings(db: Session) -> Optional[HospitalSettings]:
    """Get hospital settings (singleton - only one record should exist)"""
    return db.query(HospitalSettings).first()


def create_hospital_settings(db: Session, hospital_name: str = "Local Health Information Management System") -> HospitalSettings:
    """Create initial hospital settings"""
    # Check if settings already exist
    existing = get_hospital_settings(db)
    if existing:
        return existing
    
    db_settings = HospitalSettings(
        hospital_name=hospital_name
    )
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings


def update_hospital_settings(
    db: Session,
    hospital_name: Optional[str] = None,
    hospital_address: Optional[str] = None,
    hospital_phone: Optional[str] = None,
    hospital_email: Optional[str] = None,
    hospital_website: Optional[str] = None,
    logo_path: Optional[str] = None,
    logo_url: Optional[str] = None,
    revisit_follow_up_percentage: Optional[float] = None,
    nhis_enabled: Optional[bool] = None,
    private_insurance_enabled: Optional[bool] = None
) -> HospitalSettings:
    """Update hospital settings"""
    settings = get_hospital_settings(db)
    
    # If no settings exist, create them
    if not settings:
        settings = create_hospital_settings(db, hospital_name or "Local Health Information Management System")
    
    # Update fields if provided
    if hospital_name is not None:
        settings.hospital_name = hospital_name
    if hospital_address is not None:
        settings.hospital_address = hospital_address
    if hospital_phone is not None:
        settings.hospital_phone = hospital_phone
    if hospital_email is not None:
        settings.hospital_email = hospital_email
    if hospital_website is not None:
        settings.hospital_website = hospital_website
    if logo_path is not None:
        settings.logo_path = logo_path
    if logo_url is not None:
        settings.logo_url = logo_url
    if revisit_follow_up_percentage is not None:
        from decimal import Decimal
        settings.revisit_follow_up_percentage = Decimal(str(revisit_follow_up_percentage))
    if nhis_enabled is not None:
        settings.nhis_enabled = nhis_enabled
    if private_insurance_enabled is not None:
        settings.private_insurance_enabled = private_insurance_enabled
    if charge_types_config is not None:
        settings.charge_types_config = charge_types_config
    
    db.commit()
    db.refresh(settings)
    return settings


def update_charge_types(db: Session, charge_types_config: list) -> HospitalSettings:
    """Update charge types configuration"""
    settings = get_hospital_settings(db)
    
    # If no settings exist, create them
    if not settings:
        settings = create_hospital_settings(db)
    
    settings.charge_types_config = charge_types_config
    db.commit()
    db.refresh(settings)
    return settings

