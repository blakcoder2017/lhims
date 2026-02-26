"""
Disease Models

SQLAlchemy models for tracking diseases and ailments.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class DiseaseCategory(str, enum.Enum):
    """Disease categories for DHIMS2 reporting"""
    INFECTIOUS = "infectious"
    NCD = "ncd"  # Non-Communicable Diseases
    MATERNAL = "maternal"
    CHILD_HEALTH = "child_health"
    INJURY = "injury"
    MENTAL_HEALTH = "mental_health"
    EYE_CONDITIONS = "eye_conditions"
    DENTAL = "dental"
    SKIN = "skin"
    RESPIRATORY = "respiratory"
    OTHER = "other"


class Disease(Base):
    """
    SQLAlchemy Model for diseases and ailments.
    Used for diagnosis selection during encounters.
    """
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, index=True)
    
    # Disease Details
    name = Column(String(500), nullable=False, unique=True, index=True)  # Disease name (unique)
    code = Column(String(50), nullable=True)  # Optional ICD-10 or other code
    description = Column(Text, nullable=True)  # Optional description
    
    # Category for DHIMS2 reporting
    category = Column(
        Enum(DiseaseCategory, values_callable=lambda x: [e.value for e in x], name='diseasecategory'),
        default=DiseaseCategory.OTHER,
        nullable=False
    )
    
    # DHIMS2 mapping fields
    dhis2_data_element_uid = Column(String(20), nullable=True)  # DHIS2 data element UID for disease reporting
    dhis2_category_option_combo_uid = Column(String(20), nullable=True)  # For disaggregation
    
    # Metadata
    is_active = Column(Boolean, default=True, server_default='true')  # Soft deletion
    is_system = Column(Boolean, default=False, server_default='false')  # True if imported from CSV/system, False if user-added
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who added (if custom)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    encounter_diseases = relationship("EncounterDisease", back_populates="disease", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Disease(id={self.id}, name='{self.name}', code='{self.code}', category='{self.category.value}')>"


class EncounterDisease(Base):
    """
    Junction table for many-to-many relationship between Encounters and Diseases.
    Allows multiple diseases per encounter and tracks if it's primary or secondary.
    """
    __tablename__ = "encounter_diseases"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    disease_id = Column(Integer, ForeignKey("diseases.id"), nullable=False)
    
    # Classification
    is_primary = Column(Boolean, default=False, server_default='false')  # True if primary diagnosis
    custom_name = Column(String(500), nullable=True)  # If disease was added custom during encounter
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="diseases")
    disease = relationship("Disease", back_populates="encounter_diseases")
    
    def __repr__(self):
        return f"<EncounterDisease(encounter_id={self.encounter_id}, disease_id={self.disease_id}, is_primary={self.is_primary})>"

