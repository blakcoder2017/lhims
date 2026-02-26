from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from decimal import Decimal


class Department(Base):
    """
    SQLAlchemy Model for hospital departments.
    Manages department information for appointments, doctor duties, etc.
    """
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Department Details
    name = Column(String(100), nullable=False, unique=True, index=True)  # Department name (e.g., "General Medicine", "Antenatal")
    code = Column(String(20), nullable=True, unique=True, index=True)  # Department code (e.g., "GEN-MED", "ANT")
    description = Column(Text, nullable=True)  # Department description
    
    # Consultation pricing (per-department; used for OPD consultation fee)
    consultation_price = Column(Numeric(10, 2), nullable=True)  # Unit price for consultation in this department
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)  # Whether this department is active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}', code='{self.code}')>"

