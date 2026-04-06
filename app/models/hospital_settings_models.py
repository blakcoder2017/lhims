from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func
from app.db.database import Base


class HospitalSettings(Base):
    __tablename__ = "hospital_settings"

    id = Column(Integer, primary_key=True, index=True)
    hospital_name = Column(String(255), nullable=False, default="Local Health Information Management System")
    hospital_address = Column(Text, nullable=True)
    hospital_phone = Column(String(50), nullable=True)
    hospital_email = Column(String(255), nullable=True)
    hospital_website = Column(String(255), nullable=True)
    logo_path = Column(String(500), nullable=True)  # Path to logo file in static/uploads/logos/
    logo_url = Column(String(500), nullable=True)  # Full URL to logo
    # Laboratory-specific settings
    lab_contact_email = Column(String(255), nullable=True)  # Lab contact email for queries
    lab_contact_phone = Column(String(50), nullable=True)  # Lab contact phone
    accreditation = Column(String(255), nullable=True)  # Accreditation body name
    accreditation_number = Column(String(100), nullable=True)  # ISO/Accreditation number
    # Revisit/follow-up consultation discount: percentage of department consultation fee (e.g. 50 = 50%)
    revisit_follow_up_percentage = Column(Numeric(5, 2), nullable=True)
    # Insurance activation settings - enable/disable NHIS and Private Insurance
    nhis_enabled = Column(Boolean, nullable=True, default=True)
    private_insurance_enabled = Column(Boolean, nullable=True, default=True)
    # Charge Types configuration - JSON list of charge type values
    # Default charge types will be used if this is null
    charge_types_config = Column(postgresql.JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Only one record should exist (singleton pattern)
    # We'll enforce this in the application logic

