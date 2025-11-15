"""
PACS (Picture Archiving and Communication System) Models

This module defines models for managing radiology images and DICOM files.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from decimal import Decimal


class ImageStatus(str, enum.Enum):
    """Radiology image status enumeration"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    AVAILABLE = "available"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ImageType(str, enum.Enum):
    """Radiology image type enumeration"""
    XRAY = "xray"
    CT = "ct"
    MRI = "mri"
    ULTRASOUND = "ultrasound"
    MAMMOGRAPHY = "mammography"
    FLUOROSCOPY = "fluoroscopy"
    OTHER = "other"


class RadiologyImage(Base):
    """
    SQLAlchemy Model for radiology images in PACS.
    Stores metadata and file references for DICOM images.
    """
    __tablename__ = "radiology_images"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    radiology_order_id = Column(Integer, ForeignKey("radiology_orders.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Image Information
    image_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique image number
    image_type = Column(postgresql.ENUM(ImageType, values_callable=lambda x: [e.value for e in x], name='imagetype', create_type=False), nullable=False)
    
    # DICOM Information
    dicom_series_uid = Column(String(100), nullable=True, index=True)  # DICOM Series Instance UID
    dicom_study_uid = Column(String(100), nullable=True, index=True)  # DICOM Study Instance UID
    dicom_instance_uid = Column(String(100), nullable=True, unique=True, index=True)  # DICOM SOP Instance UID
    
    # File Information
    file_path = Column(String(500), nullable=False)  # Path to image file
    file_name = Column(String(255), nullable=False)  # Original filename
    file_size = Column(Integer, nullable=True)  # File size in bytes
    file_format = Column(String(50), nullable=True)  # File format (DICOM, JPEG, PNG, etc.)
    mime_type = Column(String(100), nullable=True)  # MIME type
    
    # Image Metadata
    modality = Column(String(20), nullable=True)  # DICOM Modality (CR, CT, MR, US, etc.)
    body_part = Column(String(100), nullable=True)  # Body part examined
    study_description = Column(String(500), nullable=True)  # Study description
    series_description = Column(String(500), nullable=True)  # Series description
    
    # Image Properties
    image_width = Column(Integer, nullable=True)  # Image width in pixels
    image_height = Column(Integer, nullable=True)  # Image height in pixels
    bits_per_pixel = Column(Integer, nullable=True)  # Bits per pixel
    number_of_frames = Column(Integer, nullable=True, default=1)  # Number of frames (for multi-frame images)
    
    # Acquisition Information
    acquisition_date = Column(DateTime, nullable=True)  # When image was acquired
    acquisition_time = Column(String(20), nullable=True)  # Acquisition time
    
    # Status
    status = Column(postgresql.ENUM(ImageStatus, values_callable=lambda x: [e.value for e in x], name='imagestatus', create_type=False), nullable=False, default=ImageStatus.UPLOADED)
    
    # Storage Information
    storage_location = Column(String(200), nullable=True)  # Physical storage location
    storage_tier = Column(String(50), nullable=True, default="hot")  # Storage tier (hot, warm, cold, archive)
    thumbnail_path = Column(String(500), nullable=True)  # Path to thumbnail image
    
    # Access Control
    is_public = Column(Boolean, default=False)  # Publicly accessible
    access_level = Column(String(50), nullable=True, default="restricted")  # Access level
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)  # When image processing completed
    archived_at = Column(DateTime, nullable=True)  # When image was archived
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    radiology_order = relationship("RadiologyOrder", back_populates="images")
    patient = relationship("Patient")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    
    def __repr__(self):
        return f"<RadiologyImage(id={self.id}, image_number='{self.image_number}', type={self.image_type.value})>"


class ImageAnnotation(Base):
    """
    SQLAlchemy Model for image annotations.
    Stores annotations, measurements, and markings on radiology images.
    """
    __tablename__ = "image_annotations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    image_id = Column(Integer, ForeignKey("radiology_images.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Annotation Information
    annotation_type = Column(String(50), nullable=False)  # e.g., "measurement", "arrow", "text", "roi"
    annotation_data = Column(Text, nullable=False)  # JSON data for annotation coordinates, text, etc.
    
    # Measurement Data (if applicable)
    measurement_value = Column(Numeric(10, 2), nullable=True)  # Measurement value
    measurement_unit = Column(String(20), nullable=True)  # Measurement unit (mm, cm, etc.)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    image = relationship("RadiologyImage")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<ImageAnnotation(id={self.id}, type='{self.annotation_type}')>"

