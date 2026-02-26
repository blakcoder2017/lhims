"""
API routes for PACS (Picture Archiving and Communication System).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.pacs_models import RadiologyImage, ImageType, ImageStatus
from app.models.encounter_models import RadiologyOrder
from app.crud import pacs_crud
from app.schemas.pacs_schemas import RadiologyImageCreate, RadiologyImageUpdate

router = APIRouter(tags=["PACS"])


@router.get("/pacs/images", name="pacs_dashboard")
def pacs_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"])),
    order_id: Optional[int] = Query(None),
    patient_id: Optional[int] = Query(None)
):
    """PACS dashboard for viewing radiology images"""
    if order_id:
        images = pacs_crud.get_images_by_order(db, order_id)
        radiology_order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    elif patient_id:
        images = pacs_crud.get_images_by_patient(db, patient_id)
        radiology_order = None
    else:
        # Get recent images
        images = db.query(RadiologyImage).filter(
            RadiologyImage.is_active == True
        ).order_by(RadiologyImage.uploaded_at.desc()).limit(50).all()
        radiology_order = None
    
    context = {
        "request": request,
        "title": "PACS - Radiology Images",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "images": images,
        "radiology_order": radiology_order,
        "order_id": order_id,
        "patient_id": patient_id
    }
    return templates.TemplateResponse("pacs/dashboard.html", context)


@router.get("/pacs/images/upload", name="upload_image_page")
def upload_image_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Radiology Staff"])),
    order_id: Optional[int] = Query(None)
):
    """Upload image page"""
    from sqlalchemy.orm import joinedload
    from app.models.encounter_models import Encounter, OrderStatus
    
    radiology_order = None
    recent_orders = []
    
    if order_id:
        radiology_order = db.query(RadiologyOrder).options(
            joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient)
        ).filter(RadiologyOrder.id == order_id).first()
        if not radiology_order:
            raise HTTPException(status_code=404, detail="Radiology order not found")
    else:
        # Get recent pending/in-progress orders for selection
        recent_orders = db.query(RadiologyOrder).options(
            joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient)
        ).filter(
            RadiologyOrder.status.in_([OrderStatus.PENDING.value, OrderStatus.IN_PROGRESS.value])
        ).order_by(RadiologyOrder.ordered_at.desc()).limit(20).all()
    
    context = {
        "request": request,
        "title": "Upload Radiology Image",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_order": radiology_order,
        "order_id": order_id,
        "recent_orders": recent_orders
    }
    return templates.TemplateResponse("pacs/upload_image.html", context)


@router.post("/pacs/images/upload", name="upload_image", status_code=302)
def upload_image(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Radiology Staff"])),
    radiology_order_id: int = Form(...),
    image_type: str = Form(...),
    file: UploadFile = File(...),
    body_part: Optional[str] = Form(None),
    study_description: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Upload a radiology image"""
    # Get radiology order
    radiology_order = db.query(RadiologyOrder).filter(RadiologyOrder.id == radiology_order_id).first()
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    patient_id = radiology_order.encounter.patient_id
    
    # Save file
    file_path, file_name = pacs_crud.save_image_file(file, radiology_order_id, patient_id)
    
    # Determine file format and MIME type
    file_ext = os.path.splitext(file_name)[1].lower()
    file_format_map = {
        ".dcm": "DICOM",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".tiff": "TIFF",
        ".tif": "TIFF"
    }
    file_format = file_format_map.get(file_ext, "UNKNOWN")
    
    mime_type_map = {
        ".dcm": "application/dicom",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tiff": "image/tiff",
        ".tif": "image/tiff"
    }
    mime_type = mime_type_map.get(file_ext, "application/octet-stream")
    
    # Create image record
    image_data = RadiologyImageCreate(
        radiology_order_id=radiology_order_id,
        image_type=ImageType(image_type),
        file_name=file_name,
        file_size=file.size if hasattr(file, 'size') else None,
        file_format=file_format,
        mime_type=mime_type,
        body_part=body_part,
        study_description=study_description,
        notes=notes
    )
    
    image = pacs_crud.create_radiology_image(
        db, image_data, patient_id, current_user.id, file_path
    )
    
    return RedirectResponse(
        url=f"/pacs/images/{image.id}?status=uploaded",
        status_code=302
    )


@router.get("/pacs/images/{image_id}", name="view_image")
def view_image(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"]))
):
    """View a specific radiology image"""
    image = pacs_crud.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Get annotations
    from app.crud.pacs_crud import get_annotations_by_image
    annotations = get_annotations_by_image(db, image_id)
    
    context = {
        "request": request,
        "title": f"Image {image.image_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "image": image,
        "annotations": annotations,
        "radiology_order": image.radiology_order,
        "patient": image.patient
    }
    return templates.TemplateResponse("pacs/image_viewer.html", context)


@router.get("/pacs/images/{image_id}/download", name="download_image")
def download_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"]))
):
    """Download a radiology image file"""
    image = pacs_crud.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if not os.path.exists(image.file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(
        path=image.file_path,
        filename=image.file_name,
        media_type=image.mime_type or "application/dicom"
    )


@router.post("/pacs/images/{image_id}/annotate", name="create_annotation", status_code=302)
def create_annotation(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"])),
    annotation_type: str = Form(...),
    annotation_data: str = Form(...),
    measurement_value: Optional[str] = Form(None),
    measurement_unit: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Create an annotation on an image"""
    from app.schemas.pacs_schemas import ImageAnnotationCreate
    from decimal import Decimal
    
    annotation_data_obj = ImageAnnotationCreate(
        image_id=image_id,
        annotation_type=annotation_type,
        annotation_data=annotation_data,
        measurement_value=Decimal(measurement_value) if measurement_value else None,
        measurement_unit=measurement_unit,
        notes=notes
    )
    
    pacs_crud.create_annotation(db, annotation_data_obj, current_user.id)
    
    return RedirectResponse(
        url=f"/pacs/images/{image_id}?status=annotated",
        status_code=302
    )

