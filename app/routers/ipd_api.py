from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.ipd_models import WardStatus, BedStatus, AdmissionStatus
from app.crud import ipd_crud
from app.schemas.ipd_schemas import (
    WardCreate, WardUpdate, Ward,
    BedCreate, BedUpdate, Bed,
    AdmissionCreate, AdmissionUpdate, Admission,
    DoctorDutyCreate, DoctorDutyUpdate, DoctorDuty
)

router = APIRouter(tags=["IPD"])
templates = Jinja2Templates(directory="app/templates")


# Ward Routes
@router.post("/api/v1/wards", response_model=Ward, status_code=status.HTTP_201_CREATED)
def create_ward_endpoint(
    ward: WardCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Create a new ward (JSON API)."""
    return ipd_crud.create_ward(db, ward)


@router.get("/api/v1/wards", response_model=List[Ward])
def get_wards_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[WardStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all wards."""
    return ipd_crud.get_wards(db, skip=skip, limit=limit, status=status)


@router.get("/api/v1/wards/{ward_id}", response_model=Ward)
def get_ward_endpoint(
    ward_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a ward by ID."""
    ward = ipd_crud.get_ward(db, ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    return ward


@router.put("/api/v1/wards/{ward_id}", response_model=Ward)
def update_ward_endpoint(
    ward_id: int,
    ward_update: WardUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Update a ward."""
    ward = ipd_crud.update_ward(db, ward_id, ward_update)
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    return ward


@router.delete("/api/v1/wards/{ward_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ward_endpoint(
    ward_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Delete a ward."""
    success = ipd_crud.delete_ward(db, ward_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ward not found")
    return None


# Bed Routes
@router.post("/api/v1/beds", response_model=Bed, status_code=status.HTTP_201_CREATED)
def create_bed_endpoint(
    bed: BedCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Create a new bed (JSON API)."""
    return ipd_crud.create_bed(db, bed)


@router.get("/api/v1/beds", response_model=List[Bed])
def get_beds_endpoint(
    ward_id: Optional[int] = Query(None),
    status: Optional[BedStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all beds, optionally filtered by ward."""
    if ward_id:
        return ipd_crud.get_beds_by_ward(db, ward_id, skip=skip, limit=limit, status=status)
    # If no ward_id, get all beds (would need a new function)
    from app.models.ipd_models import Bed
    query = db.query(Bed).filter(Bed.is_active == True)
    if status:
        query = query.filter(Bed.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/api/v1/beds/{bed_id}", response_model=Bed)
def get_bed_endpoint(
    bed_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a bed by ID."""
    bed = ipd_crud.get_bed(db, bed_id)
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    return bed


@router.get("/api/v1/beds/available", response_model=List[Bed])
def get_available_beds_endpoint(
    ward_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all available beds."""
    return ipd_crud.get_available_beds(db, ward_id=ward_id)


@router.put("/api/v1/beds/{bed_id}", response_model=Bed)
def update_bed_endpoint(
    bed_id: int,
    bed_update: BedUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Update a bed."""
    bed = ipd_crud.update_bed(db, bed_id, bed_update)
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    return bed


@router.delete("/api/v1/beds/{bed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bed_endpoint(
    bed_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Delete a bed."""
    success = ipd_crud.delete_bed(db, bed_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bed not found")
    return None


# Admission Routes
@router.post("/api/v1/admissions", response_model=Admission, status_code=status.HTTP_201_CREATED)
def create_admission_endpoint(
    admission: AdmissionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Front Office"]))
):
    """Create a new admission (JSON API)."""
    # Check if bed is available
    bed = ipd_crud.get_bed(db, admission.bed_id)
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    if bed.status != BedStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="Bed is not available")
    
    # Set admitted_by_id to current user if not provided
    if not admission.admitted_by_id:
        admission.admitted_by_id = current_user.id
    
    return ipd_crud.create_admission(db, admission)


@router.get("/api/v1/admissions", response_model=List[Admission])
def get_admissions_endpoint(
    patient_id: Optional[int] = Query(None),
    ward_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all admissions, optionally filtered by patient or ward."""
    if patient_id:
        return ipd_crud.get_admissions_by_patient(db, patient_id, skip=skip, limit=limit)
    elif ward_id:
        return ipd_crud.get_admissions_by_ward(db, ward_id, skip=skip, limit=limit)
    else:
        from app.models.ipd_models import Admission
        return db.query(Admission).filter(Admission.is_active == True).offset(skip).limit(limit).all()


@router.get("/api/v1/admissions/{admission_id}", response_model=Admission)
def get_admission_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get an admission by ID."""
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    return admission


@router.get("/api/v1/admissions/patient/{patient_id}/current", response_model=Optional[Admission])
def get_current_admission_endpoint(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the current active admission for a patient."""
    return ipd_crud.get_current_admission(db, patient_id)


@router.put("/api/v1/admissions/{admission_id}", response_model=Admission)
def update_admission_endpoint(
    admission_id: int,
    admission_update: AdmissionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Front Office"]))
):
    """Update an admission."""
    admission = ipd_crud.update_admission(db, admission_id, admission_update)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    return admission


@router.post("/api/v1/admissions/{admission_id}/discharge", response_model=Admission)
def discharge_patient_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Front Office"]))
):
    """Discharge a patient."""
    admission = ipd_crud.discharge_patient(db, admission_id, current_user.id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    return admission


@router.delete("/api/v1/admissions/{admission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admission_endpoint(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Delete an admission."""
    success = ipd_crud.delete_admission(db, admission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Admission not found")
    return None


# Doctor Duty Routes
@router.post("/api/v1/doctor-duties", response_model=DoctorDuty, status_code=status.HTTP_201_CREATED)
def create_doctor_duty_endpoint(
    doctor_duty: DoctorDutyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Create a new doctor duty (JSON API)."""
    return ipd_crud.create_doctor_duty(db, doctor_duty)


@router.get("/api/v1/doctor-duties", response_model=List[DoctorDuty])
def get_doctor_duties_endpoint(
    doctor_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all doctor duties with optional filters."""
    return ipd_crud.get_doctor_duties(db, skip=skip, limit=limit, doctor_id=doctor_id, department=department, date=date)


@router.get("/api/v1/doctor-duties/on-duty", response_model=List[DoctorDuty])
def get_doctors_on_duty_endpoint(
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all doctors currently on duty."""
    return ipd_crud.get_doctors_on_duty(db, department=department)


@router.get("/api/v1/doctor-duties/{duty_id}", response_model=DoctorDuty)
def get_doctor_duty_endpoint(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a doctor duty by ID."""
    duty = ipd_crud.get_doctor_duty(db, duty_id)
    if not duty:
        raise HTTPException(status_code=404, detail="Doctor duty not found")
    return duty


@router.put("/api/v1/doctor-duties/{duty_id}", response_model=DoctorDuty)
def update_doctor_duty_endpoint(
    duty_id: int,
    duty_update: DoctorDutyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Update a doctor duty."""
    duty = ipd_crud.update_doctor_duty(db, duty_id, duty_update)
    if not duty:
        raise HTTPException(status_code=404, detail="Doctor duty not found")
    return duty


@router.delete("/api/v1/doctor-duties/{duty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor_duty_endpoint(
    duty_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin"]))
):
    """Delete a doctor duty."""
    success = ipd_crud.delete_doctor_duty(db, duty_id)
    if not success:
        raise HTTPException(status_code=404, detail="Doctor duty not found")
    return None

