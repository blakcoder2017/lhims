"""
CRUD operations for PACS (Picture Archiving and Communication System).
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from datetime import datetime
import uuid
import os

from app.models.pacs_models import RadiologyImage, ImageAnnotation, ImageStatus, ImageType
from app.models.encounter_models import RadiologyOrder
from app.schemas.pacs_schemas import (
    RadiologyImageCreate, RadiologyImageUpdate,
    ImageAnnotationCreate
)


def generate_image_number(db: Session) -> str:
    """Generate a unique image number"""
    prefix = "IMG"
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Get the last image number for today
    last_image = db.query(RadiologyImage).filter(
        RadiologyImage.image_number.like(f"{prefix}-{date_str}-%")
    ).order_by(RadiologyImage.id.desc()).first()
    
    if last_image:
        try:
            sequence = int(last_image.image_number.split('-')[-1])
            sequence += 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1
    
    return f"{prefix}-{date_str}-{sequence:04d}"


def save_image_file(uploaded_file, radiology_order_id: int, patient_id: int) -> Tuple[str, str]:
    """
    Save uploaded image file to storage.
    Returns (file_path, file_name) tuple.
    """
    # Create storage directory structure: images/patient_id/order_id/
    storage_base = "static/images/radiology"
    storage_path = os.path.join(storage_base, str(patient_id), str(radiology_order_id))
    os.makedirs(storage_path, exist_ok=True)
    
    # Generate unique filename
    file_ext = os.path.splitext(uploaded_file.filename)[1] if uploaded_file.filename else ".dcm"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(storage_path, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        content = uploaded_file.file.read()
        f.write(content)
    
    return file_path, uploaded_file.filename


def create_radiology_image(
    db: Session,
    image_data: RadiologyImageCreate,
    patient_id: int,
    uploaded_by_id: int,
    file_path: str
) -> RadiologyImage:
    """Create a new radiology image record"""
    image_number = generate_image_number(db)
    
    image = RadiologyImage(
        image_number=image_number,
        radiology_order_id=image_data.radiology_order_id,
        patient_id=patient_id,
        uploaded_by_id=uploaded_by_id,
        image_type=image_data.image_type,
        file_path=file_path,
        file_name=image_data.file_name,
        file_size=image_data.file_size,
        file_format=image_data.file_format,
        mime_type=image_data.mime_type,
        dicom_series_uid=image_data.dicom_series_uid,
        dicom_study_uid=image_data.dicom_study_uid,
        dicom_instance_uid=image_data.dicom_instance_uid,
        modality=image_data.modality,
        body_part=image_data.body_part,
        study_description=image_data.study_description,
        series_description=image_data.series_description,
        status=ImageStatus.UPLOADED,
        notes=image_data.notes
    )
    
    db.add(image)
    db.commit()
    db.refresh(image)
    
    # Update status to available after processing
    image.status = ImageStatus.AVAILABLE
    image.processed_at = datetime.now()
    db.commit()
    db.refresh(image)
    
    return image


def get_image(db: Session, image_id: int) -> Optional[RadiologyImage]:
    """Get an image by ID"""
    return db.query(RadiologyImage).options(
        # Add joinedload if needed
    ).filter(RadiologyImage.id == image_id, RadiologyImage.is_active == True).first()


def get_images_by_order(db: Session, radiology_order_id: int) -> List[RadiologyImage]:
    """Get all images for a radiology order"""
    return db.query(RadiologyImage).filter(
        RadiologyImage.radiology_order_id == radiology_order_id,
        RadiologyImage.is_active == True
    ).order_by(RadiologyImage.uploaded_at.desc()).all()


def get_images_by_patient(db: Session, patient_id: int) -> List[RadiologyImage]:
    """Get all images for a patient"""
    return db.query(RadiologyImage).filter(
        RadiologyImage.patient_id == patient_id,
        RadiologyImage.is_active == True
    ).order_by(RadiologyImage.uploaded_at.desc()).all()


def update_image(db: Session, image_id: int, image_update: RadiologyImageUpdate) -> Optional[RadiologyImage]:
    """Update an image"""
    image = db.query(RadiologyImage).filter(RadiologyImage.id == image_id).first()
    if not image:
        return None
    
    update_data = image_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(image, field, value)
    
    db.commit()
    db.refresh(image)
    return image


def delete_image(db: Session, image_id: int) -> bool:
    """Soft delete an image"""
    image = db.query(RadiologyImage).filter(RadiologyImage.id == image_id).first()
    if not image:
        return False
    
    image.is_active = False
    image.status = ImageStatus.DELETED
    db.commit()
    return True


def create_annotation(
    db: Session,
    annotation_data: ImageAnnotationCreate,
    created_by_id: int
) -> ImageAnnotation:
    """Create an image annotation"""
    annotation = ImageAnnotation(
        image_id=annotation_data.image_id,
        created_by_id=created_by_id,
        annotation_type=annotation_data.annotation_type,
        annotation_data=annotation_data.annotation_data,
        measurement_value=annotation_data.measurement_value,
        measurement_unit=annotation_data.measurement_unit,
        notes=annotation_data.notes
    )
    
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


def get_annotations_by_image(db: Session, image_id: int) -> List[ImageAnnotation]:
    """Get all annotations for an image"""
    return db.query(ImageAnnotation).filter(
        ImageAnnotation.image_id == image_id,
        ImageAnnotation.is_active == True
    ).order_by(ImageAnnotation.created_at.desc()).all()

