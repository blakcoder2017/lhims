#!/usr/bin/env python3
"""
Seed script to update hospital settings for DEI GRATIA MEDICAL SERVICES
This script updates the hospital settings in the database with the correct
information for DEI GRATIA MEDICAL SERVICES.
"""
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.crud import hospital_settings_crud
from app.models.hospital_settings_models import HospitalSettings


def seed_hospital_settings():
    """Update hospital settings with DEI GRATIA MEDICAL SERVICES info"""
    db = SessionLocal()
    
    try:
        # Get existing settings or create new
        settings = hospital_settings_crud.get_hospital_settings(db)
        
        if not settings:
            print("Creating new hospital settings...")
            settings = hospital_settings_crud.create_hospital_settings(
                db, 
                hospital_name="DEI GRATIA MEDICAL SERVICES"
            )
        
        # Update with DEI GRATIA MEDICAL SERVICES information
        # Using the exact details from the lab report
        settings.hospital_name = "DEI GRATIA MEDICAL SERVICES"
        settings.hospital_address = "North Dungu, Opposite Quantum Filling Station, Wayamba Junction, BLK A121, Tamale - Bolgatanga Road"
        # Combine both phone numbers
        settings.hospital_phone = "0546731001 / 0207642170"
        settings.hospital_email = "deigratiamsl@gmail.com"
        
        # Logo will need to be uploaded through the admin interface
        # But we'll set a placeholder path
        settings.logo_path = "uploads/logos/hospital_logo.png"
        settings.logo_url = "/uploads/logos/hospital_logo.png"
        
        # Lab-specific settings
        settings.lab_contact_email = "deigratiamsl@gmail.com"
        settings.lab_contact_phone = "0546731001 / 0207642170"
        
        db.commit()
        db.refresh(settings)
        
        print("✅ Hospital settings updated successfully!")
        print(f"   Hospital Name: {settings.hospital_name}")
        print(f"   Address: {settings.hospital_address}")
        print(f"   Phone: {settings.hospital_phone}")
        print(f"   Email: {settings.hospital_email}")
        print(f"   Logo URL: {settings.logo_url}")
        
        return settings
        
    except Exception as e:
        print(f"❌ Error updating hospital settings: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_hospital_settings()
