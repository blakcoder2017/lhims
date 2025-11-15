from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class ShiftType(Base):
    """
    SQLAlchemy Model for shift types.
    Manages shift type information for doctor duties.
    """
    __tablename__ = "shift_types"

    id = Column(Integer, primary_key=True, index=True)
    
    # Shift Type Details
    name = Column(String(50), nullable=False, unique=True, index=True)  # Shift type name (e.g., "Morning", "Evening", "Night", "Full Day")
    code = Column(String(20), nullable=True, unique=True, index=True)  # Shift type code (e.g., "MORN", "EVE", "NIGHT", "FULL")
    description = Column(Text, nullable=True)  # Shift type description
    default_start_hour = Column(Integer, nullable=True)  # Default start hour (0-23)
    default_end_hour = Column(Integer, nullable=True)  # Default end hour (0-23)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)  # Whether this shift type is active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    def __repr__(self):
        return f"<ShiftType(id={self.id}, name='{self.name}', code='{self.code}')>"

