"""
Pydantic schemas for PACS (Picture Archiving and Communication System).
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.models.pacs_models import ImageStatus, ImageType


class RadiologyImageBase(BaseModel):
    """Base schema for radiology image"""
    image_type: ImageType
    body_part: Optional[str] = None
    study_description: Optional[str] = None
    series_description: Optional[str] = None
    modality: Optional[str] = None
    notes: Optional[str] = None


class RadiologyImageCreate(RadiologyImageBase):
    """Schema for creating a radiology image"""
    radiology_order_id: int
    file_name: str
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    mime_type: Optional[str] = None
    dicom_series_uid: Optional[str] = None
    dicom_study_uid: Optional[str] = None
    dicom_instance_uid: Optional[str] = None


class RadiologyImageUpdate(BaseModel):
    """Schema for updating a radiology image"""
    status: Optional[ImageStatus] = None
    study_description: Optional[str] = None
    series_description: Optional[str] = None
    notes: Optional[str] = None
    storage_tier: Optional[str] = None
    is_public: Optional[bool] = None


class RadiologyImage(RadiologyImageBase):
    """Schema for reading radiology image data"""
    id: int
    image_number: str
    radiology_order_id: int
    patient_id: int
    uploaded_by_id: int
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    status: ImageStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ImageAnnotationBase(BaseModel):
    """Base schema for image annotation"""
    annotation_type: str
    annotation_data: str  # JSON string
    measurement_value: Optional[Decimal] = None
    measurement_unit: Optional[str] = None
    notes: Optional[str] = None


class ImageAnnotationCreate(ImageAnnotationBase):
    """Schema for creating an image annotation"""
    image_id: int


class ImageAnnotation(ImageAnnotationBase):
    """Schema for reading image annotation data"""
    id: int
    image_id: int
    created_by_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

