import uuid
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class LabTest(Base):
    """
    SQLAlchemy Model for lab test catalog.
    Master catalog of all available lab tests.
    """
    __tablename__ = "lab_tests"

    id = Column(Integer, primary_key=True, index=True)
    
    # Test Information
    test_name = Column(String(255), nullable=False, index=True)  # Test name
    test_code = Column(String(50), unique=True, nullable=True, index=True)  # Test code (e.g., LOINC, internal code)
    loinc_code = Column(String(20), nullable=True, index=True)  # LOINC code for interoperability
    test_category = Column(String(100), nullable=True)  # Category (e.g., Hematology, Chemistry, Microbiology)
    test_type = Column(String(100), nullable=True)  # Type (e.g., Quantitative, Qualitative, Culture)
    
    # Test Details
    description = Column(Text, nullable=True)  # Test description
    specimen_type = Column(String(100), nullable=True)  # Required specimen type (e.g., Blood, Urine)
    specimen_volume = Column(String(50), nullable=True)  # Required volume
    collection_method = Column(String(200), nullable=True)  # Collection instructions
    storage_requirements = Column(String(200), nullable=True)  # Storage requirements
    
    # Turnaround Time
    routine_tat = Column(Integer, nullable=True)  # Routine turnaround time in hours
    urgent_tat = Column(Integer, nullable=True)  # Urgent turnaround time in hours
    stat_tat = Column(Integer, nullable=True)  # Stat turnaround time in hours
    
    # Pricing
    cost = Column(Numeric(10, 2), nullable=True)  # Test cost
    nhis_covered = Column(Boolean, default=False)  # NHIS coverage
    nhis_code = Column(String(50), nullable=True)  # NHIS test code
    
    # Restrictions
    is_specialized = Column(Boolean, default=False)  # Is this a specialized test (requires doctor approval)

    # Template mapping (for structured result entry)
    template_id = Column(UUID(as_uuid=True), ForeignKey("lab_templates.id", ondelete="SET NULL"), nullable=True)
    template_version = Column(Integer, nullable=True)  # If null, use latest published
    
    # Status
    is_active = Column(Boolean, default=True)  # Is test active
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    reference_ranges = relationship("ReferenceRange", back_populates="test")
    lab_orders = relationship("LabOrder", back_populates="lab_test")  # Link to lab orders
    
    def __repr__(self):
        return f"<LabTest(id={self.id}, test_name='{self.test_name}')>"

