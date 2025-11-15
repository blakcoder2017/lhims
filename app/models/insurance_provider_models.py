"""
Insurance Provider Models

Models for managing private insurance providers.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class InsuranceProvider(Base):
    """
    SQLAlchemy Model for private insurance providers.
    """
    __tablename__ = "insurance_providers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Provider Details
    name = Column(String(200), nullable=False, unique=True, index=True)  # Insurance provider name
    code = Column(String(50), nullable=True, unique=True, index=True)  # Provider code (e.g., "NIC", "VHIS")
    contact_person = Column(String(100), nullable=True)  # Contact person name
    phone_number = Column(String(50), nullable=True)  # Contact phone
    email = Column(String(100), nullable=True)  # Contact email
    address = Column(Text, nullable=True)  # Provider address
    
    # Billing Details
    co_pay_rate = Column(String(20), nullable=True)  # Co-pay rate (e.g., "10%", "20%")
    billing_email = Column(String(100), nullable=True)  # Billing email
    billing_address = Column(Text, nullable=True)  # Billing address
    
    # Status
    is_active = Column(Boolean, default=True)  # For soft deletion
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<InsuranceProvider(id={self.id}, name='{self.name}', code='{self.code}')>"

