from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from decimal import Decimal


class ServicePricing(Base):
    """
    SQLAlchemy Model for service pricing configuration.
    Allows hospital to set default prices for various services.
    """
    __tablename__ = "service_pricing"

    id = Column(Integer, primary_key=True, index=True)
    
    # Service Information
    service_name = Column(String(200), unique=True, nullable=False, index=True)  # e.g., "Consultation", "Chest X-Ray", "CBC Test"
    service_code = Column(String(50), unique=True, nullable=True, index=True)  # Service code for reference
    charge_type = Column(String(50), nullable=False, index=True)  # Maps to ChargeType enum: consultation, lab_test, radiology, pharmacy, procedure, admission, other
    category = Column(String(100), nullable=True)  # Category for grouping (e.g., "Imaging", "Laboratory", "Consultation")
    
    # Pricing
    unit_price = Column(Numeric(10, 2), nullable=False)  # Default unit price
    currency = Column(String(10), nullable=False, default="GHS")  # Currency code
    
    # Additional Information
    description = Column(Text, nullable=True)  # Description of the service
    is_active = Column(Boolean, default=True, nullable=False)  # Whether this pricing is active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    
    def __repr__(self):
        return f"<ServicePricing(id={self.id}, service_name='{self.service_name}', price={self.unit_price})>"

