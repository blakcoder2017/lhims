from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional
from datetime import datetime
import uuid

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.lab_models import LabSample, QCRecord, ReferenceRange, SampleStatus, QCStatus
from app.models.encounter_models import LabOrder, Encounter
from app.models.patient_models import Patient
from app.crud import encounter_crud

router = APIRouter(tags=["Lab Tracking"])
# Register the age filter
from datetime import date
def calculate_age(dob):
    if not dob:
        return None
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age
templates.env.filters["age"] = calculate_age


def generate_barcode() -> str:
    """Generate a unique barcode"""
    # Simple barcode generation - in production, use proper barcode library
    prefix = "LAB"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"{prefix}-{timestamp}-{unique_id}"


@router.get("/lab", name="lab_index")
def lab_index():
    """Redirect /lab to /lab/samples"""
    return RedirectResponse(url="/lab/samples", status_code=302)


@router.get("/lab/samples", name="lab_samples_dashboard")
def lab_samples_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    status_filter: Optional[str] = Query(None)
):
    """Lab samples dashboard"""
    query = db.query(LabSample).options(
        joinedload(LabSample.lab_order).joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabSample.collected_by),
        joinedload(LabSample.received_by)
    )
    
    if status_filter:
        # Normalize to lowercase to match database enum values
        status_filter = status_filter.lower()
        if status_filter == "all":
            # Show all samples when "all" is selected
            pass
        else:
            try:
                status_enum = SampleStatus(status_filter)
                query = query.filter(LabSample.status == status_enum.value)
            except ValueError:
                pass
    else:
        # Default: show only COLLECTED samples (pending - not yet received)
        query = query.filter(LabSample.status == SampleStatus.COLLECTED.value)
    
    samples = query.filter(
        LabSample.is_active == True,
        LabSample.lab_order.has(LabOrder.encounter_id != None)
    ).order_by(LabSample.created_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Lab Sample Tracking",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "samples": samples,
        "status_filter": status_filter
    }
    return templates.TemplateResponse("lab/samples_dashboard.html", context)


@router.get("/lab/samples/{sample_id}", name="view_lab_sample")
def view_lab_sample(
    request: Request,
    sample_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"]))
):
    """View a specific lab sample"""
    sample = db.query(LabSample).options(
        joinedload(LabSample.lab_order).joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabSample.collected_by),
        joinedload(LabSample.received_by),
        joinedload(LabSample.qc_records)
    ).filter(LabSample.id == sample_id).first()
    
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    context = {
        "request": request,
        "title": f"Sample {sample.barcode}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "sample": sample,
        "patient": sample.lab_order.encounter.patient if sample.lab_order.encounter else sample.lab_order.patient
    }
    return templates.TemplateResponse("lab/sample_detail.html", context)


@router.post("/lab/orders/{order_id}/create-sample", name="create_lab_sample", status_code=302)
def create_lab_sample(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    sample_type: str = Form(...),
    collection_method: Optional[str] = Form(None),
    collection_site: Optional[str] = Form(None),
    storage_location: Optional[str] = Form(None)
):
    """Create a lab sample with barcode"""
    from app.models.lab_models import LabSample
    
    lab_order = encounter_crud.get_lab_order(db, order_id)
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Generate barcode
    barcode = generate_barcode()
    
    # Create sample
    db_sample = LabSample(
        lab_order_id=order_id,
        collected_by_id=current_user.id,
        barcode=barcode,
        sample_type=sample_type,
        collection_method=collection_method,
        collection_site=collection_site,
        storage_location=storage_location,
        status=SampleStatus.COLLECTED.value,
        collected_at=datetime.now()
    )
    db.add(db_sample)
    db.commit()
    db.refresh(db_sample)
    
    return RedirectResponse(
        url=f"/lab/samples/{db_sample.id}",
        status_code=302
    )


@router.post("/lab/samples/{sample_id}/receive", name="receive_sample", status_code=302)
def receive_sample(
    request: Request,
    sample_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"]))
):
    """Mark sample as received in lab"""
    sample = db.query(LabSample).filter(LabSample.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    sample.status = SampleStatus.RECEIVED.value
    sample.received_by_id = current_user.id
    sample.received_at = datetime.now()
    
    db.commit()
    
    return RedirectResponse(
        url=f"/lab/samples/{sample_id}?status=received",
        status_code=302
    )


@router.get("/lab/qc", name="qc_dashboard")
def qc_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    status_filter: Optional[str] = Query(None)
):
    """Quality control dashboard"""
    query = db.query(QCRecord).options(
        joinedload(QCRecord.performed_by),
        joinedload(QCRecord.sample),
        joinedload(QCRecord.lab_order)
    )
    
    if status_filter:
        # Normalize to lowercase to match database enum values
        status_filter = status_filter.lower()
        try:
            status_enum = QCStatus(status_filter)
            query = query.filter(QCRecord.status == status_enum.value)
        except ValueError:
            pass
    
    qc_records = query.filter(QCRecord.is_active == True).order_by(QCRecord.performed_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Quality Control Records",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "qc_records": qc_records,
        "status_filter": status_filter
    }
    return templates.TemplateResponse("lab/qc_dashboard.html", context)


@router.get("/lab/analytics", name="lab_analytics_dashboard")
def lab_analytics_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor"])),
    days: int = 30
):
    """Lab Analytics Dashboard"""
    from datetime import timedelta
    from app.services.lab_analytics_service import get_lab_analytics
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    analytics = get_lab_analytics(db, start_date, end_date)
    
    context = {
        "request": request,
        "title": "Lab Analytics",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "analytics": analytics,
        "days": days
    }
    return templates.TemplateResponse("lab/analytics_dashboard.html", context)


@router.post("/lab/qc/create", name="create_qc_record", status_code=302)
def create_qc_record(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    qc_type: str = Form(...),
    qc_test_name: str = Form(...),
    equipment_name: Optional[str] = Form(None),
    reagent_lot: Optional[str] = Form(None),
    expected_value: Optional[str] = Form(None),
    actual_value: Optional[str] = Form(None),
    lower_limit: Optional[str] = Form(None),
    upper_limit: Optional[str] = Form(None),
    lab_order_id: Optional[int] = Form(None),
    sample_id: Optional[int] = Form(None),
    notes: Optional[str] = Form(None)
):
    """Create a QC record"""
    from app.models.lab_models import QCRecord
    from decimal import Decimal
    
    # Calculate deviation if both values provided
    deviation = None
    deviation_percentage = None
    status = QCStatus.PENDING.value
    
    if expected_value and actual_value:
        try:
            expected = Decimal(expected_value)
            actual = Decimal(actual_value)
            deviation = actual - expected
            if expected != 0:
                deviation_percentage = (deviation / expected) * 100
            
            # Determine status
            if lower_limit and upper_limit:
                lower = Decimal(lower_limit)
                upper = Decimal(upper_limit)
                if actual < lower or actual > upper:
                    status = QCStatus.OUT_OF_RANGE.value
                else:
                    status = QCStatus.PASSED.value
            elif abs(deviation_percentage) > 10:  # More than 10% deviation
                status = QCStatus.FAILED.value
            else:
                status = QCStatus.PASSED.value
        except (ValueError, TypeError):
            pass
    
    db_qc = QCRecord(
        lab_order_id=lab_order_id,
        sample_id=sample_id,
        performed_by_id=current_user.id,
        qc_type=qc_type,
        qc_test_name=qc_test_name,
        equipment_name=equipment_name,
        reagent_lot=reagent_lot,
        expected_value=Decimal(expected_value) if expected_value else None,
        actual_value=Decimal(actual_value) if actual_value else None,
        deviation=deviation,
        deviation_percentage=deviation_percentage,
        lower_limit=Decimal(lower_limit) if lower_limit else None,
        upper_limit=Decimal(upper_limit) if upper_limit else None,
        status=status,
        notes=notes
    )
    db.add(db_qc)
    db.commit()
    db.refresh(db_qc)
    
    return RedirectResponse(
        url=f"/lab/qc?status=created",
        status_code=302
    )

