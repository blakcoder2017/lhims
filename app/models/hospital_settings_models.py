from sqlalchemy import Column, Integer, String, Text, DateTime
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Only one record should exist (singleton pattern)
    # We'll enforce this in the application logic

