"""
IPD (Inpatient Department) UI Routes
Handles all UI endpoints for IPD management including wards, beds, admissions, and doctor duties.
"""
from fastapi import APIRouter, Request, Depends, status, Query, Form, HTTPException
from typing import Optional, List
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from datetime import datetime, timedelta, date
from urllib.parse import urlencode

from app.core.deps import get_current_user, role_required
from app.db.database import get_db
from app.crud import ipd_crud, patient_crud, drug_administration_crud
from app.services.ipd_billing_service import calculate_ward_bed_charges, get_or_create_invoice_for_admission
from app.models.ipd_models import WardStatus, BedStatus, AdmissionStatus
from app.models.user_models import User
from app.models.patient_models import Patient
from app.schemas.ipd_schemas import WardCreate, WardUpdate, BedCreate, BedUpdate, AdmissionCreate, DoctorDutyCreate

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


# ==================== Ward Management Routes ====================

@router.get("/ipd/wards", name="ipd_wards_list")
def list_wards(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None)
):
    """List all wards with optional status filter"""
    ward_status = None
    if status_filter:
        try:
            ward_status = WardStatus(status_filter)
        except ValueError:
            ward_status = None
    
    wards = ipd_crud.get_wards(db, skip=0, limit=100, status=ward_status)
    
    context = {
        "request": request,
        "title": "Ward Management",
        "current_user": current_user,
        "wards": wards,
        "status_filter": status_filter,
        "ward_statuses": [s.value for s in WardStatus]
    }
    return templates.TemplateResponse("ipd/wards_list.html", context)


@router.get("/ipd/wards/create", name="ipd_ward_create_form")
def create_ward_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create ward form"""
    from app.crud import ward_type_crud
    
    # Get active ward types for dropdown
    ward_types, _ = ward_type_crud.get_ward_types(db, active_only=True)
    
    context = {
        "request": request,
        "title": "Create Ward",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "ward_statuses": [s.value for s in WardStatus],
        "ward_types": ward_types
    }
    return templates.TemplateResponse("ipd/ward_form.html", context)


@router.post("/ipd/wards/create", name="ipd_ward_create")
def create_ward(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    name: str = Form(...),
    ward_number: Optional[str] = Form(None),
    ward_type: Optional[str] = Form(None),
    capacity: int = Form(0),
    ward_status: str = Form("active"),
    floor: Optional[str] = Form(None),
    building: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    charge_per_day: str = Form(...),
):
    """Create a new ward"""
    try:
        ward_status_enum = WardStatus(ward_status)
        
        # Generate ward_number if not provided or empty
        if not ward_number or not ward_number.strip():
            # Generate a unique ward number
            from app.models.ipd_models import Ward as WardModel
            today = date.today()
            existing_wards = db.query(WardModel).filter(
                WardModel.ward_number.like(f"WARD-{today.strftime('%Y%m%d')}-%")
            ).count()
            ward_number = f"WARD-{today.strftime('%Y%m%d')}-{str(existing_wards + 1).zfill(3)}"
        else:
            ward_number = ward_number.strip()
        
        # Convert charge_per_day from string to float, required field
        try:
            charge_per_day_float = float(charge_per_day.strip()) if charge_per_day.strip() else 0.0
        except ValueError:
            charge_per_day_float = 0.0
        
        ward_data = WardCreate(
            name=name,
            ward_number=ward_number,
            ward_type=ward_type,
            capacity=capacity,
            status=ward_status_enum,
            floor=floor,
            building=building,
            description=description,
            charge_per_day=charge_per_day_float
        )
        ward = ipd_crud.create_ward(db, ward_data)
        return RedirectResponse(
            url=str(request.url_for("ipd_wards_list")) + f"?status=ward_created&ward_id={ward.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ipd_ward_create_form")) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/ipd/wards/{ward_id}", name="ipd_ward_detail")
def ward_detail(
    request: Request,
    ward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Show ward details including beds and current admissions"""
    ward = ipd_crud.get_ward(db, ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")
    
    beds = ipd_crud.get_beds_by_ward(db, ward_id)
    admissions = ipd_crud.get_admissions_by_ward(db, ward_id)
    
    context = {
        "request": request,
        "title": f"Ward: {ward.name}",
        "current_user": current_user,
        "ward": ward,
        "beds": beds,
        "admissions": admissions,
        "bed_statuses": [s.value for s in BedStatus]
    }
    return templates.TemplateResponse("ipd/ward_detail.html", context)


# ==================== Bed Management Routes ====================

@router.get("/ipd/beds", name="ipd_beds_list")
def list_beds(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ward_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None)
):
    """List all beds with optional filters"""
    from app.models.ipd_models import BedStatus
    
    bed_status = None
    if status_filter:
        try:
            bed_status = BedStatus(status_filter)
        except ValueError:
            bed_status = None
    
    from app.models.ipd_models import Bed
    from sqlalchemy.orm import joinedload
    
    # Build query with ward relationship loaded
    query = db.query(Bed).options(joinedload(Bed.ward)).filter(Bed.is_active == True)
    
    if ward_id:
        query = query.filter(Bed.ward_id == ward_id)
    
    if bed_status:
        query = query.filter(Bed.status == bed_status.value)
    
    beds = query.limit(500).all()
    
    # Get wards for filter dropdown
    wards = ipd_crud.get_wards(db)
    
    context = {
        "request": request,
        "title": "Beds",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "beds": beds,
        "wards": wards,
        "ward_id": ward_id,
        "status_filter": status_filter,
        "bed_statuses": [s.value for s in BedStatus]
    }
    return templates.TemplateResponse("ipd/beds_list.html", context)


@router.get("/ipd/beds/create", name="ipd_bed_create_form")
def create_bed_form(
    request: Request,
    ward_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create bed form"""
    from app.crud import bed_type_crud
    
    wards = ipd_crud.get_wards(db) if not ward_id else []
    ward = ipd_crud.get_ward(db, ward_id) if ward_id else None
    
    # Get active bed types for dropdown
    bed_types, _ = bed_type_crud.get_bed_types(db, active_only=True)
    
    context = {
        "request": request,
        "title": "Create Bed",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "wards": wards,
        "ward": ward,
        "bed_statuses": [s.value for s in BedStatus],
        "bed_types": bed_types
    }
    return templates.TemplateResponse("ipd/bed_form.html", context)


@router.post("/ipd/beds/create", name="ipd_bed_create")
def create_bed(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    ward_id: int = Form(...),
    bed_number: str = Form(...),
    bed_name: Optional[str] = Form(None),
    bed_status: str = Form("available"),
    bed_type: Optional[str] = Form(None),
    charge_per_day: str = Form(...),
    notes: Optional[str] = Form(None),
):
    """Create a new bed"""
    try:
        bed_status_enum = BedStatus(bed_status)
        
        # Convert charge_per_day from string to float, required field
        try:
            charge_per_day_float = float(charge_per_day.strip()) if charge_per_day.strip() else 0.0
        except ValueError:
            charge_per_day_float = 0.0
        
        bed_data = BedCreate(
            ward_id=ward_id,
            bed_number=bed_number,
            bed_name=bed_name,
            status=bed_status_enum,
            bed_type=bed_type,
            charge_per_day=charge_per_day_float,
            notes=notes
        )
        bed = ipd_crud.create_bed(db, bed_data)
        return RedirectResponse(
            url=str(request.url_for("ipd_ward_detail", ward_id=ward_id)) + f"?status=bed_created&bed_id={bed.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ipd_bed_create_form")) + f"?ward_id={ward_id}&error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


# ==================== Admission Management Routes ====================

@router.get("/ipd/admissions", name="ipd_admissions_list")
def list_admissions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search by patient name, admission number, or patient number"),
    patient_id: Optional[int] = Query(None),
    ward_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
):
    """List all admissions with search and filter options"""
    from app.models.ipd_models import Admission, Ward
    from app.models.patient_models import Patient
    from sqlalchemy import or_, func, and_
    from sqlalchemy.orm import joinedload
    
    # Build query with joins
    query = db.query(Admission).options(
        joinedload(Admission.patient),
        joinedload(Admission.ward),
        joinedload(Admission.bed)
    ).filter(Admission.is_active == True)
    
    # Search functionality
    if search:
        search_term = f"%{search.strip()}%"
        query = query.join(Patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Admission.admission_number.ilike(search_term)
            )
        )
    
    # Filter by patient_id
    if patient_id:
        query = query.filter(Admission.patient_id == patient_id)
    
    # Filter by ward_id
    if ward_id:
        query = query.filter(Admission.ward_id == ward_id)
    
    # Filter by status
    admission_status = None
    if status_filter:
        try:
            admission_status = AdmissionStatus(status_filter)
            query = query.filter(Admission.status == admission_status)
        except ValueError:
            pass
    
    # Filter by date range
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(func.date(Admission.admission_date) >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(func.date(Admission.admission_date) <= date_to_obj)
        except ValueError:
            pass
    
    # Order by admission date (most recent first) and limit
    admissions = query.order_by(Admission.admission_date.desc()).limit(500).all()
    
    # Get all wards for filter dropdown
    wards = db.query(Ward).filter(Ward.is_active == True).order_by(Ward.name).all()
    
    context = {
        "request": request,
        "title": "Admissions",
        "current_user": current_user,
        "admissions": admissions,
        "wards": wards,
        "search": search,
        "patient_id": patient_id,
        "ward_id": ward_id,
        "status_filter": status_filter,
        "date_from": date_from,
        "date_to": date_to,
        "admission_statuses": [s.value for s in AdmissionStatus]
    }
    return templates.TemplateResponse("ipd/admissions_list.html", context)


@router.get("/ipd/admissions/create", name="ipd_admission_create_form")
def create_admission_form(
    request: Request,
    patient_id: Optional[int] = Query(None),
    encounter_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor"]))
):
    """Show create admission form"""
    patient = None
    is_emergency = False
    if patient_id:
        patient = patient_crud.get_patient(db, patient_id)
        
        # Check if patient has an active emergency appointment
        from app.models.appointment_models import Appointment, AppointmentType, AppointmentStatus
        emergency_appointment = db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.appointment_type == AppointmentType.EMERGENCY,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CHECKED_IN]),
            Appointment.is_active == True
        ).first()
        
        if emergency_appointment:
            is_emergency = True
    
    # Get available beds
    available_beds = ipd_crud.get_available_beds(db)
    wards = ipd_crud.get_wards(db)
    
    # Get doctors on duty
    doctors_on_duty = ipd_crud.get_doctors_on_duty(db)
    
    context = {
        "request": request,
        "title": "Admit Patient",
        "current_user": current_user,
        "patient": patient,
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "available_beds": available_beds,
        "wards": wards,
        "doctors_on_duty": doctors_on_duty,
        "is_emergency": is_emergency
    }
    return templates.TemplateResponse("ipd/admission_form.html", context)


@router.post("/ipd/admissions/create", name="ipd_admission_create")
def create_admission(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor"])),
    patient_id: int = Form(...),
    encounter_id: Optional[str] = Form(None),
    ward_id: int = Form(...),
    bed_id: int = Form(...),
    admission_reason: Optional[str] = Form(None),
    diagnosis: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    expected_discharge_date: Optional[str] = Form(None),
):
    """Create a new admission"""
    try:
        # Parse encounter_id - handle empty strings and convert to int or None
        encounter_id_int = None
        if encounter_id and encounter_id.strip():
            try:
                encounter_id_int = int(encounter_id.strip())
            except ValueError:
                raise ValueError(f"Invalid encounter_id: {encounter_id}")
        
        # Parse expected discharge date
        expected_discharge = None
        if expected_discharge_date:
            expected_discharge = datetime.strptime(expected_discharge_date, "%Y-%m-%d")
        
        admission_data = AdmissionCreate(
            patient_id=patient_id,
            encounter_id=encounter_id_int,
            ward_id=ward_id,
            bed_id=bed_id,
            admitted_by_id=current_user.id,
            admission_reason=admission_reason,
            diagnosis=diagnosis,
            notes=notes,
            expected_discharge_date=expected_discharge
        )
        admission = ipd_crud.create_admission(db, admission_data)
        
        # Immediately seed ward/bed charges so invoice reflects occupancy
        try:
            calculate_ward_bed_charges(db, admission, current_user.id)
        except Exception as billing_sync_error:
            print(f"Warning: Unable to seed ward/bed charges for admission {admission.id}: {billing_sync_error}")
        
        # Remove patient from OPD queue (both appointment and doctor queue)
        # Update any active appointments to completed status
        from app.models.appointment_models import Appointment, AppointmentStatus
        from app.crud import appointment_crud
        from app.schemas.appointment_schemas import AppointmentUpdate
        
        active_appointments = db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CHECKED_IN]),
            Appointment.is_active == True
        ).all()
        
        for appointment in active_appointments:
            appointment_update = AppointmentUpdate(
                status=AppointmentStatus.COMPLETED,
                completed_at=datetime.now(),
                notes=(appointment.notes or "") + f"\n[Auto-completed] Patient admitted to IPD on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            appointment_crud.update_appointment(db, appointment.id, appointment_update)
        
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission.id)) + "?status=admission_created",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        # Build query parameters properly
        query_params = {"patient_id": patient_id}
        if encounter_id is not None and encounter_id.strip():
            query_params["encounter_id"] = encounter_id.strip()
        query_params["error"] = str(e)
        
        redirect_url = str(request.url_for("ipd_admission_create_form")) + "?" + urlencode(query_params)
        return RedirectResponse(
            url=redirect_url,
            status_code=status.HTTP_302_FOUND
        )


@router.get("/ipd/admissions/{admission_id}", name="ipd_admission_detail")
def admission_detail(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Show admission details"""
    from app.crud import encounter_crud
    from app.models.encounter_models import Prescription, OrderStatus, Encounter
    from sqlalchemy.orm import joinedload
    from app.models.ipd_models import AdmissionNote
    
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    
    invoice = admission.invoice
    invoice_summary = None
    if invoice:
        invoice_summary = {
            "id": invoice.id,
            "number": invoice.invoice_number,
            "status": invoice.status.value if getattr(invoice, "status", None) else "pending",
            "total": invoice.total_amount or 0,
            "paid": invoice.paid_amount or 0,
            "balance": invoice.balance or 0,
            "url": f"/billing/invoices/{invoice.id}"
        }
    
    # Get ALL prescriptions for this patient (not just from admission encounter)
    # Get prescriptions from admission encounter and any other active prescriptions
    prescriptions = []
    
    # Get prescriptions from admission encounter
    if admission.encounter_id:
        encounter_prescriptions = db.query(Prescription).options(
            joinedload(Prescription.prescribed_by),
            joinedload(Prescription.dispensed_by),
            joinedload(Prescription.medication)
        ).filter(Prescription.encounter_id == admission.encounter_id).all()
        prescriptions.extend(encounter_prescriptions)
    
    # Also get other active prescriptions for this patient (from other encounters during admission period)
    # Get prescriptions from encounters on or after admission date
    # Include cancelled prescriptions for historical/audit purposes
    other_prescriptions = db.query(Prescription).options(
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.dispensed_by),
        joinedload(Prescription.medication),
        joinedload(Prescription.encounter)
    ).join(Encounter).filter(
        Encounter.patient_id == admission.patient_id,
        Encounter.encounter_date >= admission.admission_date.date()
    ).all()
    
    # Add prescriptions that aren't already in the list (avoid duplicates)
    existing_prescription_ids = {p.id for p in prescriptions}
    for presc in other_prescriptions:
        if presc.id not in existing_prescription_ids:
            prescriptions.append(presc)
    
    # Sort by prescribed date (most recent first)
    prescriptions.sort(key=lambda p: p.prescribed_at if p.prescribed_at else datetime.min, reverse=True)
    
    # Check stock availability for pending prescriptions to determine if they should show as "Dispensed"
    # If medication is available in pharmacy inventory, show as "Dispensed" instead of "Pending dispense"
    from app.crud import inventory_crud
    prescription_stock_status = {}
    for presc in prescriptions:
        if presc.status == OrderStatus.PENDING:
            is_available = False
            medication = None
            
            # Try to find medication by ID first
            if presc.medication_id:
                try:
                    medication = inventory_crud.get_medication(db, presc.medication_id)
                except Exception:
                    pass
            
            # If not found by ID, try by code
            if not medication and presc.medication_code:
                try:
                    medication = inventory_crud.get_medication_by_code(db, presc.medication_code)
                except Exception:
                    pass
            
            # If still not found, try by name
            if not medication and presc.medication_name:
                try:
                    medications = inventory_crud.get_medications(db, search=presc.medication_name, limit=1)
                    if medications:
                        medication = medications[0]
                except Exception:
                    pass
            
            # If medication found, check stock availability
            if medication:
                try:
                    stock_check = inventory_crud.check_stock_availability(db, medication.id, 1)
                    is_available = stock_check.is_available if stock_check else False
                except Exception:
                    is_available = False
            
            prescription_stock_status[presc.id] = is_available
    
    # Get admission notes (ordered by most recent first)
    from app.models.ipd_models import AdmissionNote
    admission_notes = db.query(AdmissionNote).options(
        joinedload(AdmissionNote.created_by)
    ).filter(
        AdmissionNote.admission_id == admission_id,
        AdmissionNote.is_active == True
    ).order_by(AdmissionNote.created_at.desc()).all()
    
    # Get drug administrations for this admission, grouped by prescription
    from app.crud import drug_administration_crud
    from app.models.drug_administration_models import DrugAdministration
    from sqlalchemy.orm import joinedload as drug_joinedload
    from collections import defaultdict
    
    drug_administrations = db.query(DrugAdministration).options(
        drug_joinedload(DrugAdministration.administered_by),
        drug_joinedload(DrugAdministration.prescription)
    ).filter(
        DrugAdministration.admission_id == admission_id,
        DrugAdministration.is_active == True
    ).order_by(DrugAdministration.administration_time.desc()).all()
    
    # Group administrations by prescription_id for easy lookup
    administrations_by_prescription = defaultdict(list)
    for admin in drug_administrations:
        administrations_by_prescription[admin.prescription_id].append(admin)
    
    context = {
        "request": request,
        "title": f"Admission: {admission.admission_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "admission": admission,
        "ready_for_discharge": admission.ready_for_discharge_at is not None,
        "invoice_summary": invoice_summary,
        "prescription_stock_status": prescription_stock_status,
        "prescriptions": prescriptions,
        "admission_notes": admission_notes,
        "drug_administrations": drug_administrations,
        "administrations_by_prescription": dict(administrations_by_prescription)
    }
    return templates.TemplateResponse("ipd/admission_detail.html", context)


@router.get("/ipd/admissions/{admission_id}/medications/record", name="ipd_record_drug_administration_form")
def record_drug_administration_form(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Doctor", "Admin"]))
):
    """Show page to record a drug administration"""
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    prescription_options = drug_administration_crud.get_dispensed_drugs_by_admission(db, admission.admission_number)

    context = {
        "request": request,
        "title": "Record Drug Administration",
        "current_user": current_user,
        "admission": admission,
        "prescription_options": prescription_options,
        "default_admin_time": datetime.now().strftime("%Y-%m-%dT%H:%M")
    }
    return templates.TemplateResponse("ipd/record_drug_administration.html", context)


@router.post("/ipd/admissions/{admission_id}/medications/record", name="ipd_record_drug_administration")
def record_drug_administration(
    request: Request,
    admission_id: int,
    medication_identifier: int = Form(...),
    administration_time: str = Form(...),
    dosage_given: Optional[str] = Form(None),
    route: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Doctor", "Admin"]))
):
    """Handle submission of drug administration"""
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")

    redirect_back = request.url_for("ipd_record_drug_administration_form", admission_id=admission_id)

    try:
        admin_datetime = datetime.strptime(administration_time, "%Y-%m-%dT%H:%M")
    except ValueError:
        url = f"{redirect_back}?error=Invalid+administration+date/time"
        return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

    created = drug_administration_crud.create_drug_administration(
        db=db,
        admission_number=admission.admission_number,
        medication_identifier=medication_identifier,
        administration_time=admin_datetime,
        administered_by_id=current_user.id,
        dosage_given=dosage_given or None,
        route=route or None,
        notes=notes or None
    )

    if not created:
        url = f"{redirect_back}?error=Unable+to+record+administration.+Please+verify+the+selected+drug."
        return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

    detail_url = request.url_for("ipd_admission_detail", admission_id=admission_id)
    detail_url = f"{detail_url}?medication_recorded=1"
    return RedirectResponse(url=detail_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/ipd/admissions/{admission_id}/transfer", name="ipd_admission_transfer_form")
def admission_transfer_form(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor"]))
):
    """Show transfer admission form"""
    admission = ipd_crud.get_admission(db, admission_id)
    if not admission:
        raise HTTPException(status_code=404, detail="Admission not found")
    
    if admission.status != AdmissionStatus.ADMITTED:
        raise HTTPException(status_code=400, detail="Only admitted patients can be transferred")
    
    # Get available beds (excluding current bed)
    available_beds = ipd_crud.get_available_beds(db)
    # Also include the current bed as an option
    current_bed = ipd_crud.get_bed(db, admission.bed_id)
    if current_bed:
        available_beds = [current_bed] + [bed for bed in available_beds if bed.id != admission.bed_id]
    
    wards = ipd_crud.get_wards(db)
    
    context = {
        "request": request,
        "title": f"Transfer Admission: {admission.admission_number}",
        "current_user": current_user,
        "admission": admission,
        "wards": wards,
        "available_beds": available_beds
    }
    return templates.TemplateResponse("ipd/admission_transfer_form.html", context)


@router.post("/ipd/admissions/{admission_id}/transfer", name="ipd_admission_transfer")
def transfer_admission(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor"])),
    transfer_type: str = Form(...),
    ward_id: Optional[int] = Form(None),
    bed_id: Optional[int] = Form(None),
    transfer_reason: str = Form(...),
    external_hospital_name: Optional[str] = Form(None),
    external_hospital_address: Optional[str] = Form(None),
    external_hospital_contact: Optional[str] = Form(None),
    external_ward_department: Optional[str] = Form(None),
):
    """Transfer a patient to a different ward/bed (internal) or to a different hospital (external)"""
    try:
        from app.schemas.ipd_schemas import AdmissionUpdate
        from app.models.ipd_models import AdmissionStatus
        
        admission = ipd_crud.get_admission(db, admission_id)
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        
        try:
            calculate_ward_bed_charges(db, admission, current_user.id)
        except Exception as billing_sync_error:
            print(f"Warning: Unable to sync ward/bed charges before discharge for admission {admission_id}: {billing_sync_error}")
        
        if transfer_type == "external":
            # External hospital transfer
            # Build comprehensive transfer reason with external hospital details
            external_details = []
            if external_hospital_name:
                external_details.append(f"Hospital: {external_hospital_name}")
            if external_hospital_address:
                external_details.append(f"Address: {external_hospital_address}")
            if external_hospital_contact:
                external_details.append(f"Contact: {external_hospital_contact}")
            if external_ward_department:
                external_details.append(f"Ward/Department: {external_ward_department}")
            
            full_transfer_reason = f"EXTERNAL TRANSFER - {transfer_reason}"
            if external_details:
                full_transfer_reason += "\n\nExternal Hospital Details:\n" + "\n".join(external_details)
            
            # For external transfers, we discharge the patient and update status
            # Store external hospital info in notes/transfer_reason
            admission_update = AdmissionUpdate(
                status=AdmissionStatus.TRANSFERRED,
                transfer_reason=full_transfer_reason,
                notes=(admission.notes or "") + f"\n\n[EXTERNAL TRANSFER] Transferred to {external_hospital_name or 'External Hospital'} on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            # Internal transfer (within hospital)
            if not ward_id or not bed_id:
                raise ValueError("Ward and bed are required for internal transfers")
            
            admission_update = AdmissionUpdate(
                ward_id=ward_id,
                bed_id=bed_id,
                transfer_reason=transfer_reason
            )
        
        updated_admission = ipd_crud.update_admission(db, admission_id, admission_update)
        if not updated_admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        
        # Reset discharge preparation if transfer occurs
        updated_admission.ready_for_discharge_at = None
        db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + "?status=transferred",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
                url=str(request.url_for("ipd_admission_transfer_form", admission_id=admission_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/ipd/admissions/{admission_id}/prepare-discharge", name="ipd_admission_prepare_discharge")
def prepare_admission_discharge(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor"]))
):
    """Prepare discharge by syncing ward/bed charges and linking invoice."""
    try:
        admission = ipd_crud.get_admission(db, admission_id)
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        
        # Sync ward/bed charges and ensure invoice is linked
        calculate_ward_bed_charges(db, admission, current_user.id)
        invoice = get_or_create_invoice_for_admission(db, admission, current_user.id)
        
        admission.ready_for_discharge_at = datetime.now()
        db.commit()
        message = "?status=discharge_prepared"
        if invoice:
            message += f"&invoice_id={invoice.id}"
        
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + message,
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/ipd/admissions/{admission_id}/discharge", name="ipd_admission_discharge")
def discharge_admission(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Doctor"]))
):
    """Discharge a patient and process billing"""
    try:
        admission = ipd_crud.get_admission(db, admission_id)
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        
        # Ensure discharge has been prepared recently
        if not admission.ready_for_discharge_at:
            return RedirectResponse(
                url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + 
                    "?error=Please prepare discharge before discharging the patient.",
                status_code=status.HTTP_302_FOUND
            )
        
        if admission.ready_for_discharge_at < datetime.now() - timedelta(hours=2):
            admission.ready_for_discharge_at = None
            db.commit()
            return RedirectResponse(
                url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + 
                    "?error=Discharge preparation expired. Please prepare discharge again.",
                status_code=status.HTTP_302_FOUND
            )
        
        # Ensure an invoice exists for this admission
        invoice = admission.invoice
        if not invoice:
            invoice = get_or_create_invoice_for_admission(db, admission, current_user.id)
            db.refresh(admission)
        
        # Check if cash patient has unsettled bills - prevent discharge if bills not settled
        from app.utils.payment_verification import is_cash_patient
        from app.crud import billing_crud
        from app.models.billing_models import InvoiceStatus
        
        if is_cash_patient(db, admission.patient_id):
            # Get all invoices for this admission
            patient_invoices = billing_crud.get_invoices_by_patient(db, admission.patient_id)
            admission_invoices = [inv for inv in patient_invoices 
                                if inv.encounter_id == admission.encounter_id or 
                                (hasattr(inv, 'invoice_date') and inv.invoice_date and inv.invoice_date >= admission.admission_date)]
            
            # Check for unpaid or partially paid invoices
            unpaid_invoices = [inv for inv in admission_invoices 
                             if inv.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIALLY_PAID] 
                             and inv.balance > 0]
            
            if unpaid_invoices:
                total_unpaid = sum([inv.balance for inv in unpaid_invoices])
                return RedirectResponse(
                    url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + 
                        f"?error=Cannot discharge patient. Outstanding bills of GHS {total_unpaid:.2f} must be settled first. Please process payment before discharge.",
                    status_code=status.HTTP_302_FOUND
                )
        
        # Discharge the patient
        admission = ipd_crud.discharge_patient(db, admission_id, current_user.id)
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        admission.ready_for_discharge_at = None
        
        # Automatically complete the encounter if it's still in progress
        if admission.encounter_id:
            from app.crud import encounter_crud
            from app.models.encounter_models import EncounterStatus
            from app.schemas.encounter_schemas import EncounterUpdate
            
            encounter = encounter_crud.get_encounter(db, admission.encounter_id)
            if encounter and encounter.status == EncounterStatus.IN_PROGRESS:
                encounter_update = EncounterUpdate(
                    status=EncounterStatus.COMPLETED,
                    completed_at=datetime.now()
                )
                encounter_crud.update_encounter(db, admission.encounter_id, encounter_update)
        
        # Commit both discharge and encounter completion
        db.commit()
        
        # Process billing for ward/bed charges
        from app.services.ipd_billing_service import process_discharge_billing
        try:
            invoice = process_discharge_billing(db, admission_id, current_user.id)
            # Redirect with billing info
            return RedirectResponse(
                url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + f"?status=discharged&invoice_id={invoice.id}",
                status_code=status.HTTP_302_FOUND
            )
        except Exception as billing_error:
            # Log billing error but don't fail discharge
            # In production, you might want to log this to an error tracking system
            return RedirectResponse(
                url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + f"?status=discharged&billing_warning={str(billing_error)}",
                status_code=status.HTTP_302_FOUND
            )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/ipd/admissions/{admission_id}/notes", name="add_admission_note", status_code=status.HTTP_302_FOUND)
def add_admission_note(
    request: Request,
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Nurse", "Doctor", "Admin"])),
    note: str = Form(...),
    note_type: Optional[str] = Form("general")
):
    """Add a note to an admission"""
    try:
        admission = ipd_crud.get_admission(db, admission_id)
        if not admission:
            raise HTTPException(status_code=404, detail="Admission not found")
        
        # Create admission note
        from app.models.ipd_models import AdmissionNote
        admission_note = AdmissionNote(
            admission_id=admission_id,
            created_by_id=current_user.id,
            note=note.strip(),
            note_type=note_type or "general"
        )
        
        db.add(admission_note)
        db.commit()
        db.refresh(admission_note)
        
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + "?status=note_added",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ipd_admission_detail", admission_id=admission_id)) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


# ==================== Doctor Duty Management Routes ====================

@router.get("/ipd/doctor-duties", name="ipd_doctor_duties_list")
def list_doctor_duties(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doctor_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    date: Optional[str] = Query(None)
):
    """List all doctor duties with optional filters"""
    duty_date = None
    if date:
        try:
            duty_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            duty_date = None
    
    # Get doctor duties with doctor relationship eagerly loaded
    from sqlalchemy.orm import joinedload
    from app.models.ipd_models import DoctorDuty
    
    query = db.query(DoctorDuty).options(joinedload(DoctorDuty.doctor)).filter(DoctorDuty.is_active == True)
    
    if doctor_id:
        query = query.filter(DoctorDuty.doctor_id == doctor_id)
    if department:
        query = query.filter(DoctorDuty.department == department)
    if duty_date:
        # Filter by date (ignore time)
        date_start = datetime.combine(duty_date.date(), datetime.min.time())
        date_end = datetime.combine(duty_date.date(), datetime.max.time())
        query = query.filter(DoctorDuty.duty_date >= date_start, DoctorDuty.duty_date <= date_end)
    
    duties = query.order_by(DoctorDuty.duty_date.desc()).all()
    
    # Get all doctors for filter (only Doctor role, not Clinician or Nurse)
    from app.models.user_models import User
    from app.models.user_models import Role
    doctors = db.query(User).join(Role).filter(Role.name == "Doctor").all()
    
    context = {
        "request": request,
        "title": "Doctor Duties",
        "current_user": current_user,
        "duties": duties,
        "doctors": doctors,
        "doctor_id": doctor_id,
        "department": department,
        "date": date
    }
    return templates.TemplateResponse("ipd/doctor_duties_list.html", context)


@router.get("/ipd/doctor-duties/create", name="ipd_doctor_duty_create_form")
def create_doctor_duty_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"]))
):
    """Show create doctor duty form"""
    from app.models.user_models import User, Role
    from app.crud import department_crud, shift_type_crud
    from sqlalchemy.orm import joinedload
    
    # Get only doctors (not nurses or clinicians)
    try:
        doctors = db.query(User).options(joinedload(User.role)).join(Role).filter(Role.name == "Doctor").all()
    except Exception as e:
        # Fallback: get all users and filter by role name in Python
        all_users = db.query(User).options(joinedload(User.role)).all()
        doctors = [u for u in all_users if u.role and u.role.name == "Doctor"]
    
    # Get active departments and shift types
    departments, _ = department_crud.get_departments(db, active_only=True)
    shift_types, _ = shift_type_crud.get_shift_types(db, active_only=True)
    
    context = {
        "request": request,
        "title": "Create Doctor Duty",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "doctors": doctors,
        "departments": departments,
        "shift_types": shift_types
    }
    return templates.TemplateResponse("ipd/doctor_duty_form.html", context)


@router.post("/ipd/doctor-duties/create", name="ipd_doctor_duty_create")
def create_doctor_duty(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin"])),
    doctor_id: int = Form(...),
    department: str = Form(...),
    duty_date: str = Form(...),
    shift_start: str = Form(...),
    shift_end: str = Form(...),
    shift_type: Optional[str] = Form(None),
    is_on_duty: bool = Form(True),
    notes: Optional[str] = Form(None),
):
    """Create a new doctor duty"""
    try:
        from app.crud import department_crud
        
        # Parse dates
        duty_date_obj = datetime.strptime(duty_date, "%Y-%m-%d")
        shift_start_obj = datetime.strptime(f"{duty_date} {shift_start}", "%Y-%m-%d %H:%M")
        shift_end_obj = datetime.strptime(f"{duty_date} {shift_end}", "%Y-%m-%d %H:%M")
        
        # Handle overnight shifts: if shift_end < shift_start, add 1 day
        if shift_end_obj < shift_start_obj:
            shift_end_obj = shift_end_obj + timedelta(days=1)
        
        # Verify department exists
        dept = department_crud.get_department_by_name(db, department)
        if not dept:
            raise ValueError(f"Department '{department}' not found. Please create it first.")
        
        duty_data = DoctorDutyCreate(
            doctor_id=doctor_id,
            department=department,
            duty_date=duty_date_obj,
            shift_start=shift_start_obj,
            shift_end=shift_end_obj,
            shift_type=shift_type,
            is_on_duty=is_on_duty,
            notes=notes
        )
        duty = ipd_crud.create_doctor_duty(db, duty_data)
        return RedirectResponse(
            url=str(request.url_for("ipd_doctor_duties_list")) + f"?status=duty_created&duty_id={duty.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        return RedirectResponse(
            url=str(request.url_for("ipd_doctor_duty_create_form")) + f"?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


# ==================== Ward Occupancy Dashboard ====================

@router.get("/ipd/dashboard", name="ipd_dashboard")
def ipd_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """IPD dashboard showing ward occupancy and statistics"""
    wards = ipd_crud.get_wards(db)
    
    # Calculate statistics
    total_wards = len(wards)
    total_beds = 0
    occupied_beds = 0
    available_beds = 0
    
    for ward in wards:
        total_beds += ward.capacity
        occupied_beds += ward.current_occupancy
        available_beds += (ward.capacity - ward.current_occupancy)
    
    # Get current admissions
    from app.models.ipd_models import Admission
    current_admissions = db.query(Admission).filter(
        Admission.status == AdmissionStatus.ADMITTED,
        Admission.is_active == True
    ).count()
    
    # Get doctors on duty
    doctors_on_duty = ipd_crud.get_doctors_on_duty(db)
    
    context = {
        "request": request,
        "title": "IPD Dashboard",
        "current_user": current_user,
        "wards": wards,
        "total_wards": total_wards,
        "total_beds": total_beds,
        "occupied_beds": occupied_beds,
        "available_beds": available_beds,
        "current_admissions": current_admissions,
        "doctors_on_duty": doctors_on_duty,
        "occupancy_rate": (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    }
    return templates.TemplateResponse("ipd/dashboard.html", context)

