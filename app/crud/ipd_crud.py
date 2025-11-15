from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.ipd_models import Ward, Bed, Admission, DoctorDuty, WardStatus, BedStatus, AdmissionStatus
from app.models.patient_models import Patient
from app.models.encounter_models import Encounter
from app.models.user_models import User
from app.schemas.ipd_schemas import (
    WardCreate, WardUpdate,
    BedCreate, BedUpdate,
    AdmissionCreate, AdmissionUpdate,
    DoctorDutyCreate, DoctorDutyUpdate
)


# Ward CRUD Operations
def generate_admission_number(db: Session) -> str:
    """Generate a unique admission number"""
    prefix = "ADM"
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Get the last admission number for today
    last_admission = db.query(Admission).filter(
        Admission.admission_number.like(f"{prefix}-{date_str}-%")
    ).order_by(Admission.id.desc()).first()
    
    if last_admission:
        # Extract sequence number and increment
        try:
            sequence = int(last_admission.admission_number.split('-')[-1])
            sequence += 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1
    
    return f"{prefix}-{date_str}-{sequence:04d}"


def create_ward(db: Session, ward: WardCreate) -> Ward:
    """Create a new ward"""
    db_ward = Ward(**ward.model_dump())
    db.add(db_ward)
    db.commit()
    db.refresh(db_ward)
    return db_ward


def get_ward(db: Session, ward_id: int) -> Optional[Ward]:
    """Get a ward by ID"""
    return db.query(Ward).filter(Ward.id == ward_id, Ward.is_active == True).first()


def get_wards(db: Session, skip: int = 0, limit: int = 100, status: Optional[WardStatus] = None) -> List[Ward]:
    """Get all wards with optional status filter"""
    query = db.query(Ward).filter(Ward.is_active == True)
    if status:
        query = query.filter(Ward.status == status)
    return query.offset(skip).limit(limit).all()


def update_ward(db: Session, ward_id: int, ward_update: WardUpdate) -> Optional[Ward]:
    """Update a ward"""
    db_ward = get_ward(db, ward_id)
    if not db_ward:
        return None
    
    update_data = ward_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_ward, field, value)
    
    db.commit()
    db.refresh(db_ward)
    return db_ward


def delete_ward(db: Session, ward_id: int) -> bool:
    """Soft delete a ward"""
    db_ward = get_ward(db, ward_id)
    if not db_ward:
        return False
    
    db_ward.is_active = False
    db.commit()
    return True


# Bed CRUD Operations
def create_bed(db: Session, bed: BedCreate) -> Bed:
    """Create a new bed"""
    db_bed = Bed(**bed.model_dump())
    db.add(db_bed)
    
    # Update ward occupancy if bed is created as occupied
    if bed.status == BedStatus.OCCUPIED:
        ward = get_ward(db, bed.ward_id)
        if ward:
            ward.current_occupancy += 1
    
    db.commit()
    db.refresh(db_bed)
    return db_bed


def get_bed(db: Session, bed_id: int) -> Optional[Bed]:
    """Get a bed by ID"""
    return db.query(Bed).options(joinedload(Bed.ward)).filter(Bed.id == bed_id, Bed.is_active == True).first()


def get_beds_by_ward(db: Session, ward_id: int, skip: int = 0, limit: int = 100, status: Optional[BedStatus] = None) -> List[Bed]:
    """Get all beds in a ward with optional status filter"""
    query = db.query(Bed).options(joinedload(Bed.ward)).filter(Bed.ward_id == ward_id, Bed.is_active == True)
    if status:
        query = query.filter(Bed.status == status)
    return query.offset(skip).limit(limit).all()


def get_available_beds(db: Session, ward_id: Optional[int] = None) -> List[Bed]:
    """Get all available beds, optionally filtered by ward"""
    query = db.query(Bed).filter(Bed.status == BedStatus.AVAILABLE, Bed.is_active == True)
    if ward_id:
        query = query.filter(Bed.ward_id == ward_id)
    return query.all()


def update_bed(db: Session, bed_id: int, bed_update: BedUpdate) -> Optional[Bed]:
    """Update a bed"""
    db_bed = get_bed(db, bed_id)
    if not db_bed:
        return None
    
    old_status = db_bed.status
    old_ward_id = db_bed.ward_id
    
    update_data = bed_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_bed, field, value)
    
    # Update ward occupancy if bed status changed
    if 'status' in update_data or 'ward_id' in update_data:
        new_status = db_bed.status
        new_ward_id = db_bed.ward_id
        
        # Update old ward occupancy
        if old_ward_id and old_status == BedStatus.OCCUPIED:
            old_ward = get_ward(db, old_ward_id)
            if old_ward and old_ward.current_occupancy > 0:
                old_ward.current_occupancy -= 1
        
        # Update new ward occupancy
        if new_ward_id and new_status == BedStatus.OCCUPIED:
            new_ward = get_ward(db, new_ward_id)
            if new_ward:
                new_ward.current_occupancy += 1
        
        # If ward changed, update both wards
        if old_ward_id != new_ward_id and old_ward_id:
            old_ward = get_ward(db, old_ward_id)
            if old_ward and old_status == BedStatus.OCCUPIED and old_ward.current_occupancy > 0:
                old_ward.current_occupancy -= 1
    
    db.commit()
    db.refresh(db_bed)
    return db_bed


def delete_bed(db: Session, bed_id: int) -> bool:
    """Soft delete a bed"""
    db_bed = get_bed(db, bed_id)
    if not db_bed:
        return False
    
    # Update ward occupancy if bed was occupied
    if db_bed.status == BedStatus.OCCUPIED:
        ward = get_ward(db, db_bed.ward_id)
        if ward and ward.current_occupancy > 0:
            ward.current_occupancy -= 1
    
    db_bed.is_active = False
    db.commit()
    return True


# Admission CRUD Operations
def create_admission(db: Session, admission: AdmissionCreate) -> Admission:
    """Create a new admission"""
    # Generate admission number
    admission_number = generate_admission_number(db)
    
    # Create admission
    admission_data = admission.model_dump()
    admission_data['admission_number'] = admission_number
    db_admission = Admission(**admission_data)
    db.add(db_admission)
    
    # Update bed status to occupied
    bed = get_bed(db, admission.bed_id)
    if bed:
        bed.status = BedStatus.OCCUPIED
        # Update ward occupancy
        ward = get_ward(db, admission.ward_id)
        if ward:
            ward.current_occupancy += 1
    
    db.commit()
    db.refresh(db_admission)
    return db_admission


def get_admission(db: Session, admission_id: int) -> Optional[Admission]:
    """Get an admission by ID"""
    return db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed),
        joinedload(Admission.encounter),
        joinedload(Admission.admitted_by),
        joinedload(Admission.transferred_from_ward),
        joinedload(Admission.transferred_to_ward),
        joinedload(Admission.invoice)
    ).filter(Admission.id == admission_id, Admission.is_active == True).first()


def get_admission_by_number(db: Session, admission_number: str) -> Optional[Admission]:
    """Get an admission by admission number"""
    return db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed)
    ).filter(Admission.admission_number == admission_number, Admission.is_active == True).first()


def get_admissions_by_patient(db: Session, patient_id: int, skip: int = 0, limit: int = 100) -> List[Admission]:
    """Get all admissions for a patient"""
    return db.query(Admission).options(
        joinedload(Admission.ward),
        joinedload(Admission.bed)
    ).filter(
        Admission.patient_id == patient_id,
        Admission.is_active == True
    ).order_by(Admission.admission_date.desc()).offset(skip).limit(limit).all()


def get_current_admission(db: Session, patient_id: int) -> Optional[Admission]:
    """Get the current active admission for a patient"""
    return db.query(Admission).options(
        joinedload(Admission.ward),
        joinedload(Admission.bed)
    ).filter(
        Admission.patient_id == patient_id,
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).first()


def get_admissions_by_ward(db: Session, ward_id: int, skip: int = 0, limit: int = 100) -> List[Admission]:
    """Get all admissions in a ward"""
    return db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.bed)
    ).filter(
        Admission.ward_id == ward_id,
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).order_by(Admission.admission_date.desc()).offset(skip).limit(limit).all()


def update_admission(db: Session, admission_id: int, admission_update: AdmissionUpdate) -> Optional[Admission]:
    """Update an admission"""
    db_admission = get_admission(db, admission_id)
    if not db_admission:
        return None
    
    old_ward_id = db_admission.ward_id
    old_bed_id = db_admission.bed_id
    old_status = db_admission.status
    
    update_data = admission_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_admission, field, value)
    
    # Handle status change to discharged
    if 'status' in update_data and admission_update.status == AdmissionStatus.DISCHARGED:
        if not db_admission.discharge_date:
            db_admission.discharge_date = datetime.now()
        
        # Update bed status to available
        bed = get_bed(db, db_admission.bed_id)
        if bed:
            bed.status = BedStatus.AVAILABLE
        
        # Update ward occupancy
        ward = get_ward(db, db_admission.ward_id)
        if ward and ward.current_occupancy > 0:
            ward.current_occupancy -= 1
    
    # Handle status change to transferred (external transfer)
    # For external transfers, release the bed and discharge the patient
    if 'status' in update_data and admission_update.status == AdmissionStatus.TRANSFERRED:
        # Check if status actually changed from ADMITTED to TRANSFERRED
        status_changed = old_status != AdmissionStatus.TRANSFERRED
        # Check if this is an external transfer (no bed_id or ward_id change)
        is_external_transfer = 'bed_id' not in update_data and 'ward_id' not in update_data
        
        if status_changed and is_external_transfer and old_status == AdmissionStatus.ADMITTED:
            # External transfer - release bed and update ward occupancy
            if not db_admission.discharge_date:
                db_admission.discharge_date = datetime.now()
            
            # Update bed status to available
            bed = get_bed(db, db_admission.bed_id)
            if bed:
                bed.status = BedStatus.AVAILABLE
            
            # Update ward occupancy
            ward = get_ward(db, db_admission.ward_id)
            if ward and ward.current_occupancy > 0:
                ward.current_occupancy -= 1
    
    # Handle ward/bed transfer
    if 'ward_id' in update_data or 'bed_id' in update_data:
        new_ward_id = db_admission.ward_id
        new_bed_id = db_admission.bed_id
        
        # Track transfer for billing purposes
        if old_ward_id != new_ward_id:
            db_admission.transferred_from_ward_id = old_ward_id
            db_admission.transferred_to_ward_id = new_ward_id
            # Update status to transferred if not already discharged
            if db_admission.status == AdmissionStatus.ADMITTED:
                db_admission.status = AdmissionStatus.TRANSFERRED
                # Create a new admission record for the transfer, or update current one
                # For now, we'll just update the current admission
        
        # Release old bed
        if old_bed_id and old_bed_id != new_bed_id:
            old_bed = get_bed(db, old_bed_id)
            if old_bed:
                old_bed.status = BedStatus.AVAILABLE
        
        # Update new bed
        if new_bed_id:
            new_bed = get_bed(db, new_bed_id)
            if new_bed:
                new_bed.status = BedStatus.OCCUPIED
        
        # Update ward occupancy
        if old_ward_id != new_ward_id:
            if old_ward_id:
                old_ward = get_ward(db, old_ward_id)
                if old_ward and old_ward.current_occupancy > 0:
                    old_ward.current_occupancy -= 1
            if new_ward_id:
                new_ward = get_ward(db, new_ward_id)
                if new_ward:
                    new_ward.current_occupancy += 1
    
    db.commit()
    db.refresh(db_admission)
    return db_admission


def discharge_patient(db: Session, admission_id: int, discharged_by_id: int, discharge_date: Optional[datetime] = None) -> Optional[Admission]:
    """Discharge a patient"""
    db_admission = get_admission(db, admission_id)
    if not db_admission:
        return None
    
    if db_admission.status == AdmissionStatus.DISCHARGED:
        return db_admission  # Already discharged
    
    db_admission.status = AdmissionStatus.DISCHARGED
    db_admission.discharged_by_id = discharged_by_id
    db_admission.discharge_date = discharge_date or datetime.now()
    
    # Update bed status to available
    bed = get_bed(db, db_admission.bed_id)
    if bed:
        bed.status = BedStatus.AVAILABLE
    
    # Update ward occupancy
    ward = get_ward(db, db_admission.ward_id)
    if ward and ward.current_occupancy > 0:
        ward.current_occupancy -= 1
    
    db.commit()
    db.refresh(db_admission)
    return db_admission


def delete_admission(db: Session, admission_id: int) -> bool:
    """Soft delete an admission"""
    db_admission = get_admission(db, admission_id)
    if not db_admission:
        return False
    
    # If admission was active, update bed and ward
    if db_admission.status == AdmissionStatus.ADMITTED:
        bed = get_bed(db, db_admission.bed_id)
        if bed:
            bed.status = BedStatus.AVAILABLE
        
        ward = get_ward(db, db_admission.ward_id)
        if ward and ward.current_occupancy > 0:
            ward.current_occupancy -= 1
    
    db_admission.is_active = False
    db.commit()
    return True


# Doctor Duty CRUD Operations
def create_doctor_duty(db: Session, doctor_duty: DoctorDutyCreate) -> DoctorDuty:
    """Create a new doctor duty"""
    db_duty = DoctorDuty(**doctor_duty.model_dump())
    db.add(db_duty)
    db.commit()
    db.refresh(db_duty)
    return db_duty


def get_doctor_duty(db: Session, duty_id: int) -> Optional[DoctorDuty]:
    """Get a doctor duty by ID"""
    return db.query(DoctorDuty).options(
        joinedload(DoctorDuty.doctor)
    ).filter(DoctorDuty.id == duty_id, DoctorDuty.is_active == True).first()


def get_doctor_duties(db: Session, skip: int = 0, limit: int = 100, doctor_id: Optional[int] = None, department: Optional[str] = None, date: Optional[datetime] = None) -> List[DoctorDuty]:
    """Get all doctor duties with optional filters"""
    query = db.query(DoctorDuty).options(joinedload(DoctorDuty.doctor)).filter(DoctorDuty.is_active == True)
    
    if doctor_id:
        query = query.filter(DoctorDuty.doctor_id == doctor_id)
    if department:
        query = query.filter(DoctorDuty.department == department)
    if date:
        # Filter by date (ignore time)
        date_start = datetime.combine(date.date(), datetime.min.time())
        date_end = datetime.combine(date.date(), datetime.max.time())
        query = query.filter(DoctorDuty.duty_date >= date_start, DoctorDuty.duty_date <= date_end)
    
    return query.order_by(DoctorDuty.duty_date.desc()).offset(skip).limit(limit).all()


def get_doctors_on_duty(db: Session, department: Optional[str] = None, current_time: Optional[datetime] = None) -> List[DoctorDuty]:
    """Get all doctors currently on duty"""
    if current_time is None:
        current_time = datetime.now()
    
    query = db.query(DoctorDuty).options(joinedload(DoctorDuty.doctor)).filter(
        DoctorDuty.is_on_duty == True,
        DoctorDuty.is_active == True,
        DoctorDuty.shift_start <= current_time,
        DoctorDuty.shift_end >= current_time
    )
    
    if department:
        query = query.filter(DoctorDuty.department == department)
    
    return query.all()


def update_doctor_duty(db: Session, duty_id: int, duty_update: DoctorDutyUpdate) -> Optional[DoctorDuty]:
    """Update a doctor duty"""
    db_duty = get_doctor_duty(db, duty_id)
    if not db_duty:
        return None
    
    update_data = duty_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_duty, field, value)
    
    db.commit()
    db.refresh(db_duty)
    return db_duty


def delete_doctor_duty(db: Session, duty_id: int) -> bool:
    """Soft delete a doctor duty"""
    db_duty = get_doctor_duty(db, duty_id)
    if not db_duty:
        return False
    
    db_duty.is_active = False
    db.commit()
    return True

