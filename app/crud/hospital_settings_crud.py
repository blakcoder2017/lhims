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
    logo_url: Optional[str] = None
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
    
    db.commit()
    db.refresh(settings)
    return settings

