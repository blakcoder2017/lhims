from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class BedType(Base):
    """
    SQLAlchemy Model for bed types.
    Manages bed type information for beds.
    """
    __tablename__ = "bed_types"

    id = Column(Integer, primary_key=True, index=True)
    
    # Bed Type Details
    name = Column(String(50), nullable=False, unique=True, index=True)  # Bed type name (e.g., "Standard", "ICU", "Private", "Semi-Private")
    code = Column(String(20), nullable=True, unique=True, index=True)  # Bed type code (e.g., "STD", "ICU", "PRIV", "SEMI")
    description = Column(Text, nullable=True)  # Bed type description
    default_charge_per_day = Column(String(20), nullable=True)  # Default charge per day (as string for display)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)  # Whether this bed type is active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<BedType(id={self.id}, name='{self.name}', code='{self.code}')>"

