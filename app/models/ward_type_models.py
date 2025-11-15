"""
Ward Type Models

Models for managing ward types (e.g., General, ICU, Pediatric, Maternity).
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class WardType(Base):
    """
    SQLAlchemy Model for ward types.
    Stores predefined ward types that can be assigned to wards.
    """
    __tablename__ = "ward_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "General", "ICU", "Pediatric"
    code = Column(String(50), nullable=True, unique=True, index=True)  # Short code (e.g., "GEN", "ICU")
    description = Column(Text, nullable=True)  # Description of the ward type
    is_active = Column(Boolean, default=True)  # Soft delete flag
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<WardType(id={self.id}, name='{self.name}')>"

