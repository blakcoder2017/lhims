"""
Direct Service Request API Routes

Routes for patients to request services directly from their profile without consultation.
Supports Pharmacy, Lab, Radiology, and Procedures with restrictions and pricing display.
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from typing import Optional, Dict
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.patient_models import Patient, PaymentMechanism
from app.models.encounter_models import (
    LabOrder,
    RadiologyOrder,
    OrderStatus,
    Prescription,
    EncounterStatus,
    Encounter,
)
from app.models.procedure_models import Procedure, ProcedureStatus
from app.models.inventory_models import Medication
from app.models.lab_catalog_models import LabTest
from app.crud import encounter_crud, procedure_crud, service_pricing_crud, patient_crud, inventory_crud
from app.schemas.encounter_schemas import (
    LabOrderCreate,
    RadiologyOrderCreate,
    EncounterCreate,
    EncounterUpdate,
    PrescriptionCreate,
)
from app.schemas.procedure_schemas import ProcedureCreate
from app.services import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_procedure,
    create_charge_for_prescription,
)

router = APIRouter(tags=["Direct Service Requests"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/direct-service-requests", name="direct_service_requests_dashboard")
def direct_service_requests_dashboard(
    request: Request,
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Finance", "Pharmacy Staff", "Lab Staff", "Radiology Staff"])),
):
    """
    Direct Service Requests Dashboard
    Search for patients and create direct service requests (Pharmacy, Lab, Radiology, Procedures)
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_, or_
    
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Search patients with pagination
    patients, total_count = patient_crud.search_patients(
        db,
        query=query,
        skip=skip,
        limit=per_page,
        sort_by="id",
        sort_order="desc"
    )
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Get statistics for today
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Count direct requests today (walk-in orders)
    today_pharmacy = db.query(func.count(Prescription.id)).filter(
        Prescription.is_walk_in == True,
        Prescription.created_at >= today_start
    ).scalar() or 0
    
    today_lab = db.query(func.count(LabOrder.id)).filter(
        LabOrder.is_walk_in == True,
        LabOrder.created_at >= today_start
    ).scalar() or 0
    
    today_radiology = db.query(func.count(RadiologyOrder.id)).filter(
        RadiologyOrder.is_walk_in == True,
        RadiologyOrder.created_at >= today_start
    ).scalar() or 0
    
    today_procedures = db.query(func.count(Procedure.id)).filter(
        Procedure.is_walk_in == True,
        Procedure.created_at >= today_start
    ).scalar() or 0
    
    # Get recent direct requests (last 10)
    # Query encounters that have walk-in prescriptions, lab orders, radiology orders, or procedures
    from sqlalchemy import exists
    recent_encounters = db.query(Encounter).filter(
        Encounter.status == EncounterStatus.COMPLETED,
        Encounter.created_at >= today_start - timedelta(days=7),
        or_(
            exists().where(
                Prescription.encounter_id == Encounter.id,
                Prescription.is_walk_in == True
            ),
            exists().where(
                LabOrder.encounter_id == Encounter.id,
                LabOrder.is_walk_in == True
            ),
            exists().where(
                RadiologyOrder.encounter_id == Encounter.id,
                RadiologyOrder.is_walk_in == True
            ),
            exists().where(
                Procedure.encounter_id == Encounter.id,
                Procedure.is_walk_in == True
            )
        )
    ).options(
        joinedload(Encounter.patient)
    ).order_by(Encounter.created_at.desc()).limit(10).all()
    
    context = {
        "request": request,
        "title": "Direct Service Requests",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patients": patients,
        "search_query": query or "",
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "today_pharmacy": today_pharmacy,
        "today_lab": today_lab,
        "today_radiology": today_radiology,
        "today_procedures": today_procedures,
        "recent_requests": recent_encounters,
    }
    
    return templates.TemplateResponse("direct_requests/dashboard.html", context)


@router.get("/api/v1/direct-requests/patients/search", name="direct_requests_patient_search_api")
def direct_requests_patient_search_api(
    query: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    JSON API endpoint for patient search in direct service requests modal
    """
    if not query or len(query.strip()) < 2:
        return JSONResponse(content={"patients": []})
    
    # Search patients
    patients, total_count = patient_crud.search_patients(
        db,
        query=query,
        skip=0,
        limit=limit,
        sort_by="id",
        sort_order="desc"
    )
    
    # Format response
    patients_data = []
    for patient in patients:
        patients_data.append({
            "id": patient.id,
            "patient_number": patient.patient_number or "N/A",
            "name": f"{patient.first_name} {patient.last_name}",
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "phone_number": patient.phone_number or "N/A",
            "gender": patient.gender,
            "date_of_birth": patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else None,
        })
    
    return JSONResponse(content={
        "patients": patients_data,
        "total": total_count
    })


def check_medication_restriction(db: Session, medication_id: int) -> Dict[str, any]:
    """Check if medication is restricted (controlled)"""
    medication = inventory_crud.get_medication(db, medication_id)
    if not medication:
        return {"restricted": False, "reason": None}
    
    if medication.is_controlled:
        return {
            "restricted": True,
            "reason": "This is a controlled medication and requires a doctor's prescription."
        }
    
    return {"restricted": False, "reason": None}


def check_lab_test_restriction(db: Session, test_name: str, test_code: Optional[str] = None) -> Dict[str, any]:
    """Check if lab test is restricted (specialized)"""
    from app.models.lab_catalog_models import LabTest
    
    lab_test = None
    if test_code:
        lab_test = db.query(LabTest).filter(
            LabTest.test_code == test_code,
            LabTest.is_active == True
        ).first()
    
    if not lab_test and test_name:
        lab_test = db.query(LabTest).filter(
            LabTest.test_name.ilike(f"%{test_name}%"),
            LabTest.is_active == True
        ).first()
    
    if lab_test and lab_test.is_specialized:
        return {
            "restricted": True,
            "reason": "This is a specialized test and requires a doctor's approval."
        }
    
    return {"restricted": False, "reason": None}


def get_service_price(db: Session, service_type: str, service_name: str, service_code: Optional[str] = None) -> Optional[Decimal]:
    """Get price for a service"""
    # Try service pricing first
    if service_code:
        pricing = service_pricing_crud.get_service_pricing_by_code(db, service_code)
        if pricing:
            return pricing.unit_price
    
    pricing = service_pricing_crud.get_service_pricing_by_name(db, service_name)
    if pricing:
        return pricing.unit_price
    
    # For medications, check inventory
    if service_type == "pharmacy":
        medication = inventory_crud.get_medication_by_code(db, service_code) if service_code else None
        if not medication:
            medications = inventory_crud.get_medications(db, search=service_name, limit=1)
            medication = medications[0] if medications else None
        if medication and medication.unit_price:
            return medication.unit_price
    
    # For lab tests, check catalog
    if service_type == "lab_test":
        from app.models.lab_catalog_models import LabTest
        lab_test = None
        if service_code:
            lab_test = db.query(LabTest).filter(
                LabTest.test_code == service_code,
                LabTest.is_active == True
            ).first()
        if not lab_test:
            lab_test = db.query(LabTest).filter(
                LabTest.test_name.ilike(f"%{service_name}%"),
                LabTest.is_active == True
            ).first()
        if lab_test and lab_test.cost:
            return lab_test.cost
    
    return None


# API Endpoints for pricing and restriction checks
@router.get("/api/v1/patients/{patient_id}/direct-requests/check-medication", name="check_medication_restriction_api")
def check_medication_restriction_api(
    patient_id: int,
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if medication is restricted and get pricing"""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    restriction = check_medication_restriction(db, medication_id)
    medication = inventory_crud.get_medication(db, medication_id)
    
    price = None
    if medication:
        price = float(medication.unit_price) if medication.unit_price else None
    
    return JSONResponse(content={
        "restricted": restriction["restricted"],
        "reason": restriction["reason"],
        "price": price,
        "medication_name": medication.name if medication else None
    })


@router.get("/api/v1/patients/{patient_id}/direct-requests/check-lab-test", name="check_lab_test_restriction_api")
def check_lab_test_restriction_api(
    patient_id: int,
    test_name: str,
    test_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if lab test is restricted and get pricing"""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    restriction = check_lab_test_restriction(db, test_name, test_code)
    price = get_service_price(db, "lab_test", test_name, test_code)
    
    return JSONResponse(content={
        "restricted": restriction["restricted"],
        "reason": restriction["reason"],
        "price": float(price) if price else None
    })


@router.get("/api/v1/patients/{patient_id}/direct-requests/check-radiology", name="check_radiology_restriction_api")
def check_radiology_restriction_api(
    patient_id: int,
    study_type: str,
    study_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get radiology pricing (no restrictions currently)"""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    price = get_service_price(db, "radiology", study_type, study_code)
    
    return JSONResponse(content={
        "restricted": False,
        "reason": None,
        "price": float(price) if price else None
    })


@router.get("/api/v1/patients/{patient_id}/direct-requests/check-procedure", name="check_procedure_restriction_api")
def check_procedure_restriction_api(
    patient_id: int,
    procedure_name: str,
    procedure_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get procedure pricing (no restrictions currently)"""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    price = get_service_price(db, "procedure", procedure_name, procedure_code)
    
    return JSONResponse(content={
        "restricted": False,
        "reason": None,
        "price": float(price) if price else None
    })


# Direct Service Request Creation Routes
@router.post("/patients/{patient_id}/direct-requests/pharmacy/create", name="create_direct_pharmacy_request", status_code=status.HTTP_302_FOUND)
def create_direct_pharmacy_request(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Finance", "Pharmacy Staff"])),
    medication_id: int = Form(...),
    dosage: str = Form(...),
    frequency: str = Form(...),
    duration: str = Form(...),
    quantity: int = Form(1),
    instructions: Optional[str] = Form(None),
):
    """Create a direct pharmacy request from patient profile"""
    import traceback
    
    try:
        # Get patient
        patient = patient_crud.get_patient(db, patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Check restriction
        restriction = check_medication_restriction(db, medication_id)
        if restriction["restricted"]:
            return RedirectResponse(
                url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={restriction['reason']}",
                status_code=status.HTTP_302_FOUND
            )
        
        # Get medication
        medication = inventory_crud.get_medication(db, medication_id)
        if not medication:
            raise HTTPException(status_code=404, detail="Medication not found")
        
        # For direct requests, temporarily set payment mechanism to CASH for invoice creation
        original_payment_mechanism = patient.payment_mechanism
        if patient.payment_mechanism != PaymentMechanism.CASH:
            patient.payment_mechanism = PaymentMechanism.CASH
            db.commit()
        
        try:
            # Create minimal encounter for documentation
            encounter_data = EncounterCreate(
                patient_id=patient.id,
                clinician_id=current_user.id,
                chief_complaint=f"Direct pharmacy request: {medication.name}",
                status=EncounterStatus.COMPLETED
            )
            encounter = encounter_crud.create_encounter(db, encounter_data)
            
            # Create prescription
            prescription_data = PrescriptionCreate(
                encounter_id=encounter.id,
                prescribed_by_id=current_user.id,
                medication_name=medication.name,
                medication_code=medication.medication_code,
                dosage=dosage,
                frequency=frequency,
                duration=duration,
                quantity=quantity,
                instructions=instructions if instructions else None,
                is_walk_in=True
            )
            
            new_prescription = encounter_crud.create_prescription(db, prescription_data)
            
            # Create charge (invoice will use CASH payment mechanism)
            try:
                create_charge_for_prescription(db, new_prescription, current_user.id, check_payment_required=False)
            except Exception as billing_error:
                print(f"Warning: Unable to create direct pharmacy charge: {billing_error}")
                traceback.print_exc()
        finally:
            # Restore original payment mechanism
            if original_payment_mechanism != PaymentMechanism.CASH:
                patient.payment_mechanism = original_payment_mechanism
                db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?status=pharmacy_request_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating direct pharmacy request: {error_msg}")
        traceback.print_exc()
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={error_msg[:200]}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/patients/{patient_id}/direct-requests/lab/create", name="create_direct_lab_request", status_code=status.HTTP_302_FOUND)
def create_direct_lab_request(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Finance", "Lab Staff"])),
    test_name: str = Form(...),
    test_code: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a direct lab request from patient profile"""
    import traceback
    
    try:
        # Get patient
        patient = patient_crud.get_patient(db, patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Check restriction
        restriction = check_lab_test_restriction(db, test_name, test_code)
        if restriction["restricted"]:
            return RedirectResponse(
                url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={restriction['reason']}",
                status_code=status.HTTP_302_FOUND
            )
        
        # For direct requests, temporarily set payment mechanism to CASH for invoice creation
        original_payment_mechanism = patient.payment_mechanism
        if patient.payment_mechanism != PaymentMechanism.CASH:
            patient.payment_mechanism = PaymentMechanism.CASH
            db.commit()
        
        try:
            # Create lab order
            lab_order_data = LabOrderCreate(
                encounter_id=None,
                patient_id=patient.id,
                ordered_by_id=current_user.id,
                test_name=test_name,
                test_code=test_code if test_code else None,
                instructions=instructions if instructions else None,
                priority=priority,
                is_walk_in=True
            )
            
            new_order = encounter_crud.create_lab_order(db, lab_order_data)
            
            # Create charge (invoice will use CASH payment mechanism)
            try:
                create_charge_for_lab_order(db, new_order, current_user.id, check_payment_required=False)
            except Exception as billing_error:
                print(f"Warning: Unable to create direct lab charge: {billing_error}")
                traceback.print_exc()
        finally:
            # Restore original payment mechanism
            if original_payment_mechanism != PaymentMechanism.CASH:
                patient.payment_mechanism = original_payment_mechanism
                db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?status=lab_request_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating direct lab request: {error_msg}")
        traceback.print_exc()
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={error_msg[:200]}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/patients/{patient_id}/direct-requests/radiology/create", name="create_direct_radiology_request", status_code=status.HTTP_302_FOUND)
def create_direct_radiology_request(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Finance", "Radiology Staff"])),
    study_type: str = Form(...),
    study_code: Optional[str] = Form(None),
    body_part: Optional[str] = Form(None),
    clinical_indication: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a direct radiology request from patient profile"""
    import traceback
    
    try:
        # Get patient
        patient = patient_crud.get_patient(db, patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # For direct requests, temporarily set payment mechanism to CASH for invoice creation
        original_payment_mechanism = patient.payment_mechanism
        if patient.payment_mechanism != PaymentMechanism.CASH:
            patient.payment_mechanism = PaymentMechanism.CASH
            db.commit()
        
        try:
            # Create radiology order
            radiology_order_data = RadiologyOrderCreate(
                encounter_id=None,
                patient_id=patient.id,
                ordered_by_id=current_user.id,
                study_type=study_type,
                study_code=study_code if study_code else None,
                body_part=body_part if body_part else None,
                clinical_indication=clinical_indication if clinical_indication else None,
                instructions=instructions if instructions else None,
                priority=priority,
                is_walk_in=True
            )
            
            new_order = encounter_crud.create_radiology_order(db, radiology_order_data)
            
            # Create charge (invoice will use CASH payment mechanism)
            try:
                create_charge_for_radiology_order(db, new_order, current_user.id, check_payment_required=False)
            except Exception as billing_error:
                print(f"Warning: Unable to create direct radiology charge: {billing_error}")
                traceback.print_exc()
        finally:
            # Restore original payment mechanism
            if original_payment_mechanism != PaymentMechanism.CASH:
                patient.payment_mechanism = original_payment_mechanism
                db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?status=radiology_request_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating direct radiology request: {error_msg}")
        traceback.print_exc()
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={error_msg[:200]}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/patients/{patient_id}/direct-requests/procedure/create", name="create_direct_procedure_request", status_code=status.HTTP_302_FOUND)
def create_direct_procedure_request(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Finance"])),
    procedure_name: str = Form(...),
    procedure_code: Optional[str] = Form(None),
    procedure_type: str = Form(...),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
):
    """Create a direct procedure request from patient profile"""
    import traceback
    
    try:
        # Get patient
        patient = patient_crud.get_patient(db, patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # For direct requests, temporarily set payment mechanism to CASH for invoice creation
        original_payment_mechanism = patient.payment_mechanism
        if patient.payment_mechanism != PaymentMechanism.CASH:
            patient.payment_mechanism = PaymentMechanism.CASH
            db.commit()
        
        try:
            from app.models.procedure_models import ProcedureType
            
            # Create procedure
            procedure_data = ProcedureCreate(
                patient_id=patient.id,
                encounter_id=None,
                ordered_by_id=current_user.id,
                procedure_name=procedure_name,
                procedure_code=procedure_code if procedure_code else None,
                procedure_type=ProcedureType(procedure_type),
                description=description if description else None,
                indication=indication if indication else None,
                location=location if location else None,
                status=ProcedureStatus.SCHEDULED,
                is_walk_in=True
            )
            
            procedure = procedure_crud.create_procedure(db, procedure_data)
            
            # Create charge (invoice will use CASH payment mechanism)
            try:
                create_charge_for_procedure(db, procedure, current_user.id)
            except Exception as billing_error:
                print(f"Warning: Unable to create direct procedure charge: {billing_error}")
                traceback.print_exc()
        finally:
            # Restore original payment mechanism
            if original_payment_mechanism != PaymentMechanism.CASH:
                patient.payment_mechanism = original_payment_mechanism
                db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?status=procedure_request_created",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Error creating direct procedure request: {error_msg}")
        traceback.print_exc()
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error={error_msg[:200]}",
            status_code=status.HTTP_302_FOUND
        )

