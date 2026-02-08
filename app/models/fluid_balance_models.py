"""
Fluid balance (intake/output) model for IPD admissions.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class FluidBalance(Base):
    """
    Records fluid intake or output for an admission (IPD).
    Used for daily fluid balance charting.
    """
    __tablename__ = "fluid_balance"

    id = Column(Integer, primary_key=True, index=True)

    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False)
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 'intake' or 'output'
    entry_type = Column(String(20), nullable=False)
    volume_ml = Column(Integer, nullable=False)
    recorded_at = Column(DateTime, nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    admission = relationship("Admission", back_populates="fluid_balance_entries")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])

    def __repr__(self):
        return f"<FluidBalance(id={self.id}, admission_id={self.admission_id}, type={self.entry_type}, volume_ml={self.volume_ml})>"
