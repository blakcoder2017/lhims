"""
Direct Service Request API Routes

Routes for patients to request services directly from their profile without consultation.
Supports Pharmacy, Lab, Radiology, and Procedures with restrictions and pricing display.
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from app.core.templates import templates
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
    PrescriptionCreate,
)
from app.schemas.procedure_schemas import ProcedureCreate
from app.services import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_procedure,
    create_charge_for_prescription,
    create_sample_if_not_exists
)

router = APIRouter(tags=["Direct Service Requests"])


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
    medication_id: Optional[int] = Query(None),  # Legacy inventory medication ID
    pharmacy_drug_id: Optional[str] = Query(None),  # Ghana pharmacy drug UUID
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if medication is restricted and get pricing and stock"""
    from uuid import UUID
    from datetime import datetime
    
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    price = None
    available_stock = 0
    medication_name = None
    
    # Check pharmacy_drug_id first (UUID from Ghana pharmacy system)
    if pharmacy_drug_id:
        try:
            drug_uuid = UUID(pharmacy_drug_id)
            from app.models.pharmacy_models import PharmacyDrug, PharmacyBatch, PharmacyStore
            
            drug = db.query(PharmacyDrug).filter(PharmacyDrug.id == drug_uuid).first()
            if drug:
                medication_name = drug.generic_name
                
                # Get price and stock from pharmacy batches
                store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
                if store:
                    # Get FEFO batch
                    batch = db.query(PharmacyBatch).filter(
                        PharmacyBatch.store_id == store.id,
                        PharmacyBatch.drug_id == drug.id,
                        PharmacyBatch.status == "ACTIVE",
                        PharmacyBatch.expiry_date >= datetime.now().date(),
                        PharmacyBatch.qty_on_hand > 0,
                    ).order_by(PharmacyBatch.expiry_date.asc()).first()
                    
                    if batch and batch.selling_price:
                        price = float(batch.selling_price)
                    
                    # Calculate total available stock
                    batches = db.query(PharmacyBatch).filter(
                        PharmacyBatch.store_id == store.id,
                        PharmacyBatch.drug_id == drug.id,
                        PharmacyBatch.status == "ACTIVE",
                        PharmacyBatch.expiry_date >= datetime.now().date(),
                    ).all()
                    available_stock = float(sum(b.qty_on_hand for b in batches if b.qty_on_hand > 0))
                
                # Fallback to inventory if no pharmacy price/stock
                if price is None or available_stock == 0:
                    from app.models.inventory_models import Medication, StockItem
                    inv_query = db.query(Medication).filter(Medication.is_active == True)
                    
                    medication = None
                    if drug.item_code:
                        medication = inv_query.filter(
                            (Medication.medication_code == drug.item_code) |
                            (Medication.generic_name.ilike(f"%{drug.generic_name}%"))
                        ).first()
                    else:
                        medication = inv_query.filter(
                            Medication.generic_name.ilike(f"%{drug.generic_name}%")
                        ).first()
                    
                    if medication:
                        if price is None and medication.unit_price:
                            price = float(medication.unit_price)
                        
                        if available_stock == 0:
                            now = datetime.now()
                            stock_items = db.query(StockItem).filter(
                                StockItem.medication_id == medication.id,
                                StockItem.is_active == True,
                                (StockItem.expiry_date >= now) | (StockItem.expiry_date.is_(None))
                            ).all()
                            available_stock = float(sum(item.available_quantity for item in stock_items if item.available_quantity))
        except ValueError:
            pass  # Invalid UUID, fall through to check medication_id
    
    # Fallback to inventory medication_id
    if (price is None or available_stock == 0) and medication_id:
        medication = inventory_crud.get_medication(db, medication_id)
        if medication:
            medication_name = medication.name
            if price is None:
                price = float(medication.unit_price) if medication.unit_price else None
            
            if available_stock == 0:
                # Get stock from inventory
                from app.models.inventory_models import StockItem
                from datetime import datetime
                now = datetime.now()
                stock_items = db.query(StockItem).filter(
                    StockItem.medication_id == medication.id,
                    StockItem.is_active == True,
                    (StockItem.expiry_date >= now) | (StockItem.expiry_date.is_(None))
                ).all()
                available_stock = float(sum(item.available_quantity for item in stock_items if item.available_quantity))
    
    return JSONResponse(content={
        "restricted": False,  # Could add restriction logic here
        "reason": None,
        "price": price,
        "available_stock": available_stock,
        "medication_name": medication_name
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
async def create_direct_pharmacy_request(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Finance", "Management", "Pharmacy Staff"])),
    prescriptions_json: Optional[str] = Form(None),
):
    """Create a direct pharmacy request from patient profile with multiple prescriptions"""
    import traceback
    import json
    from uuid import UUID
    
    prescriptions_data = None
    
    # Check if we have JSON data (new format with multiple prescriptions)
    if prescriptions_json:
        try:
            prescriptions_data = json.loads(prescriptions_json)
            if not isinstance(prescriptions_data, list):
                prescriptions_data = [prescriptions_data]
        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse prescriptions_json: {e}")
            prescriptions_data = None
    
    # If no JSON, try to get individual fields (legacy single prescription format)
    if not prescriptions_data:
        # Get form fields for single prescription (legacy support)
        form_data = await request.form()
        medication_id = form_data.get('medication_id')
        pharmacy_drug_id = form_data.get('pharmacy_drug_id')
        medication_name = form_data.get('medication_name')
        dosage = form_data.get('dosage')
        frequency = form_data.get('frequency')
        frequency_custom = form_data.get('frequency_custom')
        duration = form_data.get('duration')
        quantity = form_data.get('quantity', '1')
        instructions = form_data.get('instructions')
        
        if not medication_name:
            return RedirectResponse(
                url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Medication+is+required",
                status_code=status.HTTP_302_FOUND
            )
        
        # Build frequency from custom if needed
        if frequency == 'Other' and frequency_custom:
            frequency = frequency_custom
        
        # Single prescription - create list with one item
        prescriptions_data = [{
            'medication_id': medication_id,
            'pharmacy_drug_id': pharmacy_drug_id,
            'medication_name': medication_name,
            'dosage': dosage or '',
            'frequency': frequency or '',
            'duration': duration,
            'quantity': int(quantity) if quantity else 1,
            'instructions': instructions
        }]
    
    if not prescriptions_data or not isinstance(prescriptions_data, list):
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Invalid+prescription+data",
            status_code=status.HTTP_302_FOUND
        )
    
    if len(prescriptions_data) > 20:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Maximum+20+prescriptions+allowed",
            status_code=status.HTTP_302_FOUND
        )
    
    print(f"[DEBUG] create_direct_pharmacy_request called with {len(prescriptions_data)} prescriptions")
    
    # Track created prescriptions and any warnings
    created_count = 0
    failed_count = 0
    stock_warning = None
    
    for idx, prescr_data in enumerate(prescriptions_data):
        try:
            # Get required fields
            pharmacy_drug_id = prescr_data.get('pharmacy_drug_id')
            medication_name = prescr_data.get('medication_name', '')
            
            if not pharmacy_drug_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Prescription #{idx + 1}: pharmacy_drug_id is required. Please select a medication from the pharmacy formulary."
                )
                failed_count += 1
                continue
            
            if not medication_name:
                print(f"[WARN] Skipping prescription {idx}: medication name is required")
                failed_count += 1
                continue
                
            if not prescr_data.get('frequency'):
                print(f"[WARN] Skipping prescription {idx}: frequency is required")
                failed_count += 1
                continue
            
            # Track which system we're using
            use_ghana_system = bool(pharmacy_drug_id and str(pharmacy_drug_id).strip())
            
            # Ghana: Get drug details from PharmacyDrug if pharmacy_drug_id provided
            pharmacy_drug = None
            if use_ghana_system:
                try:
                    pharmacy_drug_uuid = UUID(str(pharmacy_drug_id).strip())
                    from app.models.pharmacy_models import PharmacyDrug
                    pharmacy_drug = db.query(PharmacyDrug).options(
                        joinedload(PharmacyDrug.dosage_form)
                    ).filter(
                        PharmacyDrug.id == pharmacy_drug_uuid,
                        PharmacyDrug.is_active == True
                    ).first()
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid pharmacy_drug_id format: {e}")
            
            # Build medication name from pharmacy drug if available
            medication_name_final = medication_name
            medication_code_final = None
            dosage_form_name = None
            strength_value = None
            strength_unit = None
            route = None
            concentration_value = None
            concentration_unit = None
            
            if pharmacy_drug:
                strength = f"{pharmacy_drug.strength_value} {pharmacy_drug.strength_unit or ''}" if pharmacy_drug.strength_value else ""
                if pharmacy_drug.concentration_value:
                    strength = f"{pharmacy_drug.concentration_value} {pharmacy_drug.concentration_unit or ''}"
                medication_name_final = f"{pharmacy_drug.generic_name} {strength} {pharmacy_drug.dosage_form.name if pharmacy_drug.dosage_form else ''}".strip()
                medication_code_final = pharmacy_drug.item_code
                dosage_form_name = pharmacy_drug.dosage_form.name if pharmacy_drug.dosage_form else None
                strength_value = float(pharmacy_drug.strength_value) if pharmacy_drug.strength_value else None
                strength_unit = pharmacy_drug.strength_unit
                route = pharmacy_drug.route
                concentration_value = float(pharmacy_drug.concentration_value) if pharmacy_drug.concentration_value else None
                concentration_unit = pharmacy_drug.concentration_unit
                
                # STOCK CHECK: Verify medication is available in pharmacy inventory
                from datetime import date
                from app.models.pharmacy_models import PharmacyBatch, PharmacyStore
                store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
                
                if store:
                    try:
                        pharmacy_drug_uuid = UUID(str(pharmacy_drug_id).strip())
                        batch = db.query(PharmacyBatch).filter(
                            PharmacyBatch.drug_id == pharmacy_drug_uuid,
                            PharmacyBatch.store_id == store.id,
                            PharmacyBatch.expiry_date > date.today(),
                            PharmacyBatch.qty_on_hand > 0
                        ).order_by(PharmacyBatch.expiry_date.asc()).first()
                        
                        if not batch:
                            stock_warning = f"{medication_name_final} may be out of stock"
                    except Exception as stock_error:
                        print(f"Warning: Stock check failed: {stock_error}")
            
            # Get quantity
            try:
                quantity = int(prescr_data.get('quantity', 1))
                if quantity < 1:
                    quantity = 1
            except (ValueError, TypeError):
                quantity = 1
            
            # Create prescription data
            from app.schemas.encounter_schemas import PrescriptionCreate
            prescription_data = PrescriptionCreate(
                pharmacy_drug_id=str(pharmacy_drug_id).strip(),
                encounter_id=None,
                patient_id=patient_id,
                prescribed_by_id=current_user.id,
                medication_name=medication_name_final,
                medication_code=medication_code_final,
                dosage_form_name=dosage_form_name,
                strength_value=strength_value,
                strength_unit=strength_unit,
                route=route,
                concentration_value=concentration_value,
                concentration_unit=concentration_unit,
                dosage=prescr_data.get('dosage', ''),
                frequency=prescr_data.get('frequency', ''),
                duration=prescr_data.get('duration') if prescr_data.get('duration') else None,
                quantity=quantity,
                instructions=prescr_data.get('instructions') if prescr_data.get('instructions') else None,
                is_walk_in=False
            )
            
            # Create the prescription
            new_prescription = encounter_crud.create_prescription(db, prescription_data)
            
            # Create charge for the prescription
            try:
                from app.services import create_charge_for_prescription
                create_charge_for_prescription(db, new_prescription, current_user.id, check_payment_required=False)
            except Exception as billing_error:
                print(f"Warning: Unable to create direct pharmacy charge: {billing_error}")
                traceback.print_exc()
            
            created_count += 1
            
        except Exception as prescr_error:
            print(f"[ERROR] Error creating prescription {idx}: {prescr_error}")
            traceback.print_exc()
            failed_count += 1
            continue
    
    if created_count == 0:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Failed+to+create+any+prescriptions",
            status_code=status.HTTP_302_FOUND
        )
    
    # Build redirect URL with stock warning if applicable
    redirect_url = str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?status=pharmacy_request_created&count={created_count}"
    if stock_warning:
        redirect_url += f"&warning={stock_warning}"
    if failed_count > 0:
        redirect_url += f"&failed={failed_count}"
    
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

@router.post("/patients/{patient_id}/direct-requests/lab/create", name="create_direct_lab_request", status_code=status.HTTP_302_FOUND)
def create_direct_lab_request(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Front Office", "Admin", "Finance", "Lab Staff"])),
    test_ids: str = Form(...),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Create a direct lab request from patient profile"""
    import traceback
    
    # Parse test_ids (comma-separated)
    try:
        test_id_list = [int(tid.strip()) for tid in test_ids.split(',') if tid.strip()]
    except ValueError:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Invalid test IDs",
            status_code=status.HTTP_302_FOUND
        )
    
    if not test_id_list:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Please select at least one test",
            status_code=status.HTTP_302_FOUND
        )
    
    # Get selected tests from database
    selected_tests = db.query(LabTest).filter(LabTest.id.in_(test_id_list)).all()
    
    if not selected_tests:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=Selected tests not found",
            status_code=status.HTTP_302_FOUND
        )
    
    # Create a mapping for quick lookup
    test_map = {t.id: t for t in selected_tests}
    
    # Check if all requested tests were found
    found_ids = set(test_map.keys())
    missing_ids = set(test_id_list) - found_ids
    if missing_ids:
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?error=Some tests not found (IDs: {missing_ids})",
            status_code=status.HTTP_302_FOUND
        )
    
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
            created_orders = []
            # Create lab order for each selected test
            for test in selected_tests:
                # Check restriction for each test
                restriction = check_lab_test_restriction(db, test.test_name, test.test_code)
                if restriction["restricted"]:
                    continue  # Skip restricted tests
                
                # Create lab order
                lab_order_data = LabOrderCreate(
                    encounter_id=None,
                    patient_id=patient.id,
                    ordered_by_id=current_user.id,
                    test_name=test.test_name,
                    test_code=test.test_code if test.test_code else None,
                    lab_test_id=test.id,
                    instructions=instructions if instructions else None,
                    priority=priority,
                    is_walk_in=True
                )
                
                new_order = encounter_crud.create_lab_order(db, lab_order_data)
                created_orders.append(new_order)
                
                # Create charge (invoice will use CASH payment mechanism)
                try:
                    create_charge_for_lab_order(db, new_order, current_user.id, check_payment_required=False)
                except Exception as billing_error:
                    print(f"Warning: Unable to create direct lab charge: {billing_error}")
                    traceback.print_exc()
                
                # Auto-create sample for the lab order
                try:
                    sample = create_sample_if_not_exists(db, new_order.id, current_user.id)
                    if sample:
                        print(f"Auto-created sample {sample.barcode} for direct lab order {new_order.id}")
                except Exception as sample_error:
                    print(f"Warning: Unable to auto-create sample for order {new_order.id}: {sample_error}")
        finally:
            # Restore original payment mechanism
            if original_payment_mechanism != PaymentMechanism.CASH:
                patient.payment_mechanism = original_payment_mechanism
                db.commit()
        
        if not created_orders:
            return RedirectResponse(
                url=str(request.url_for("view_patient_records", patient_id=patient_id)) + "?error=No orders could be created (all tests may be restricted)",
                status_code=status.HTTP_302_FOUND
            )
        
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
    procedure_catalog_ids: Optional[str] = Form(None),  # Comma-separated IDs from catalog selection
    procedure_names: Optional[str] = Form(None),  # Semicolon-separated names from catalog
    procedure_name: Optional[str] = Form(None),  # Manual single procedure entry
    procedure_code: Optional[str] = Form(None),
    procedure_type: str = Form(...),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
):
    """Create a direct procedure request from patient profile - supports multiple procedures from catalog"""
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
            from app.models.procedure_catalog_models import ProcedureCatalog
            
            # Determine which procedures to create
            procedures_to_create = []
            
            # Option 1: Multiple procedures from catalog selection
            if procedure_catalog_ids:
                catalog_ids = [x.strip() for x in procedure_catalog_ids.split(',') if x.strip()]
                for cat_id in catalog_ids:
                    try:
                        catalog_id = int(cat_id)
                        catalog = db.query(ProcedureCatalog).filter(ProcedureCatalog.id == catalog_id).first()
                        if catalog:
                            procedures_to_create.append({
                                'procedure_catalog_id': catalog.id,
                                'procedure_name': catalog.procedure_name,
                                'procedure_code': catalog.procedure_code,
                                'procedure_type': procedure_type,
                                'description': description,
                                'indication': indication,
                                'location': location
                            })
                    except ValueError:
                        continue
            
            # Option 2: Single manual procedure entry
            elif procedure_name:
                procedures_to_create.append({
                    'procedure_catalog_id': None,
                    'procedure_name': procedure_name,
                    'procedure_code': procedure_code,
                    'procedure_type': procedure_type,
                    'description': description,
                    'indication': indication,
                    'location': location
                })
            
            # Create procedures and charges
            created_count = 0
            failed_procedures = []
            
            for proc_data in procedures_to_create:
                try:
                    procedure_data = ProcedureCreate(
                        patient_id=patient.id,
                        encounter_id=None,
                        ordered_by_id=current_user.id,
                        procedure_catalog_id=proc_data.get('procedure_catalog_id'),
                        procedure_name=proc_data['procedure_name'],
                        procedure_code=proc_data.get('procedure_code'),
                        procedure_type=ProcedureType(proc_data['procedure_type']),
                        description=proc_data.get('description'),
                        indication=proc_data.get('indication'),
                        location=proc_data.get('location'),
                        status=ProcedureStatus.SCHEDULED,
                        is_walk_in=True
                    )
                    
                    procedure = procedure_crud.create_procedure(db, procedure_data)
                    created_count += 1
                    
                    # Create charge with proper procedure catalog pricing
                    try:
                        create_charge_for_procedure(db, procedure, current_user.id)
                    except Exception as billing_error:
                        print(f"Warning: Unable to create direct procedure charge: {billing_error}")
                        traceback.print_exc()
                except Exception as proc_error:
                    # Log the failed procedure but continue with others
                    failed_procedures.append({
                        'name': proc_data.get('procedure_name'),
                        'error': str(proc_error)
                    })
                    print(f"Warning: Failed to create procedure {proc_data.get('procedure_name')}: {proc_error}")
                    traceback.print_exc()
            
            # Build status message
            status_msg = f"procedure_request_created"
            if created_count > 0:
                status_msg = f"procedure_request_created&created={created_count}"
            if failed_procedures:
                failed_names = ', '.join([p['name'] for p in failed_procedures])
                status_msg = f"{status_msg}&failed={len(failed_procedures)}"
                print(f"[WARNING] {len(failed_procedures)} procedures failed to create: {failed_names}")
        finally:
            # Restore original payment mechanism
            if original_payment_mechanism != PaymentMechanism.CASH:
                patient.payment_mechanism = original_payment_mechanism
                db.commit()
        
        return RedirectResponse(
            url=str(request.url_for("view_patient_records", patient_id=patient_id)) + f"?status={status_msg}",
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

