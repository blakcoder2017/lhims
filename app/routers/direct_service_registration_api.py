"""
Direct Service Registration API Routes

API endpoints for patients to register directly for services without consultation.
Services: Antenatal, Lab, Pharmacy, Radiology, Procedures
"""
from fastapi import APIRouter, Depends, Request, Query, HTTPException, Form, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List, Any, Dict
from decimal import Decimal
from datetime import datetime, date

from app.core.templates import templates
from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.models.patient_models import Patient, PaymentMechanism
from app.models.direct_service_registration_models import DirectServiceRegistration
from app.crud import patient_crud, direct_service_registration_crud
from app.schemas.direct_service_registration_schemas import (
    DirectServiceRegistrationCreate,
    DirectServiceRegistrationUpdate,
    DirectServiceRegistration,
    DirectServiceRegistrationResponse,
    ServicePricingInfo,
)

router = APIRouter(tags=["Direct Service Registration"])


# Service type labels
SERVICE_TYPE_LABELS = {
    "general": "General Consultation",
    "lab": "Laboratory",
    "pharmacy": "Pharmacy",
    "radiology": "Radiology",
    "procedure": "Procedure",
    "other": "Other"
}


@router.get("/direct-service-registration", name="direct_service_registration_dashboard")
def direct_service_registration_dashboard(
    request: Request,
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    service_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Finance", "Midwife", "Lab Staff", "Pharmacy Staff", "Radiology Staff"])),
):
    """
    Direct Service Registration Dashboard
    Allows staff to register patients directly for services without consultation.
    """
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Get registrations with pagination
    registrations, total_count = direct_service_registration_crud.get_direct_service_registrations(
        db,
        skip=skip,
        limit=per_page,
        service_type=service_type
    )
    
    # Calculate pagination info
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Get statistics
    stats = direct_service_registration_crud.get_direct_service_statistics(db)
    
    context = {
        "request": request,
        "title": "Direct Service Registration",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "registrations": registrations,
        "search_query": query or "",
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "stats": stats,
        "service_type_filter": service_type or "",
    }
    
    return templates.TemplateResponse("direct_service_registration/dashboard.html", context)


@router.get("/api/v1/direct-service-registration/services", name="get_direct_service_types")
def get_direct_service_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of available direct service types with pricing.
    """
    from app.crud import service_pricing_crud
    
    # Define service types and their typical pricing names
    service_types = [
        {"type": "direct_service", "label": "Direct Service", "icon": "fa-user-plus"},
        {"type": "lab", "label": "Laboratory", "icon": "fa-flask"},
        {"type": "pharmacy", "label": "Pharmacy", "icon": "fa-pills"},
        {"type": "radiology", "label": "Radiology", "icon": "fa-x-ray"},
        {"type": "procedure", "label": "Procedure", "icon": "fa-syringe"},
    ]
    
    # Get pricing for each service type
    for service in service_types:
        service_type = service["type"]
        
        # Try to find pricing for this service type
        if service_type == "direct_service":
            # Direct service - no specific pricing needed
            service["unit_price"] = None
            service["currency"] = "GHS"
        elif service_type == "lab":
            # Lab prices are variable, don't show a single price
            service["unit_price"] = None
            service["currency"] = "GHS"
        elif service_type == "pharmacy":
            # Pharmacy prices are variable
            service["unit_price"] = None
            service["currency"] = "GHS"
        elif service_type == "radiology":
            # Radiology prices are variable
            service["unit_price"] = None
            service["currency"] = "GHS"
        elif service_type == "procedure":
            # Procedure prices are variable
            service["unit_price"] = None
            service["currency"] = "GHS"
    
    return JSONResponse(content={"services": service_types})


@router.get("/api/v1/direct-service-registration/patients/search", name="direct_service_patient_search")
def direct_service_patient_search(
    query: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    JSON API endpoint for patient search in direct service registration.
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
            "payment_mechanism": patient.payment_mechanism.value if patient.payment_mechanism else None,
        })
    
    return JSONResponse(content={
        "patients": patients_data,
        "total": total_count
    })


@router.post("/api/v1/direct-service-registration", name="create_direct_service_registration")
def create_direct_service_registration(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(role_required(["Admin", "Front Office", "Finance", "Midwife", "Lab Staff", "Pharmacy Staff", "Radiology Staff"])),
    
    # Patient identification
    search_query: Optional[str] = Form(None),
    patient_id_str: Optional[str] = Form(None),
    
    # New patient details
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    date_of_birth_str: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    national_id: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    
    # Payment
    payment_mechanism: Optional[str] = Form(None),
    nhis_number: Optional[str] = Form(None),
    insurance_provider: Optional[str] = Form(None),
    insurance_policy_number: Optional[str] = Form(None),
    
    # Service details
    service_type: Optional[str] = Form("general"),
    gestational_weeks: Optional[float] = Form(None),
    lmp_str: Optional[str] = Form(None),
    edd_str: Optional[str] = Form(None),
    reason_for_visit: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    registration_notes: Optional[str] = Form(None),
    
    # Service-specific details (JSON string)
    lab_tests: Optional[str] = Form(None),
    medication_name: Optional[str] = Form(None),
    medication_id: Optional[str] = Form(None),
    pharmacy_drug_id: Optional[str] = Form(None),
    study_type: Optional[str] = Form(None),
    procedure_name: Optional[str] = Form(None),
):
    """
    Create a direct service registration.
    Either find existing patient or create new one, then create service order.
    """
    # Convert date strings to date objects (or None if empty)
    date_of_birth = None
    if date_of_birth_str and date_of_birth_str.strip():
        try:
            date_of_birth = datetime.strptime(date_of_birth_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    lmp = None
    if lmp_str and lmp_str.strip():
        try:
            lmp = datetime.strptime(lmp_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    edd = None
    if edd_str and edd_str.strip():
        try:
            edd = datetime.strptime(edd_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Convert patient_id string to int if provided
    patient_id = None
    if patient_id_str and patient_id_str.strip():
        try:
            patient_id = int(patient_id_str.strip())
        except ValueError:
            pass
    
    from app.schemas.patient_schemas import PatientCreate
    from app.core.templates import templates
    
    # Validate service type
    if service_type not in SERVICE_TYPE_LABELS:
        return RedirectResponse(
            url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Invalid+service+type",
            status_code=status.HTTP_302_FOUND
        )
    
    # Step 1: Find or create patient
    patient = None
    
    if patient_id:
        # Use existing patient
        patient = patient_crud.get_patient(db, patient_id)
        if not patient:
            return RedirectResponse(
                url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Patient+not+found",
                status_code=status.HTTP_302_FOUND
            )
    elif search_query and first_name:
        # Search for existing patient first
        patients, _ = patient_crud.search_patients(
            db,
            query=search_query,
            skip=0,
            limit=5
        )
        
        if patients:
            # Found existing patient - use the first match
            patient = patients[0]
    
    # If no patient found, create new one
    if not patient:
        # Validate required fields for new patient
        if not all([first_name, last_name, date_of_birth, gender]):
            return RedirectResponse(
                url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Missing+required+patient+information",
                status_code=status.HTTP_302_FOUND
            )
        
        # Parse payment mechanism
        payment_mech = None
        if payment_mechanism:
            try:
                # Convert to uppercase to match enum values (form may send lowercase)
                payment_mech = PaymentMechanism(payment_mechanism.upper())
            except ValueError:
                payment_mech = PaymentMechanism.CASH
        
        # Create new patient
        try:
            patient_in = PatientCreate(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                national_id=national_id.strip() if national_id and national_id.strip() else None,
                phone_number=phone_number if phone_number else None,
                address=address if address else None,
                payment_mechanism=payment_mech,
                nhis_number=nhis_number if nhis_number else None,
                insurance_provider=insurance_provider if insurance_provider else None,
                insurance_policy_number=insurance_policy_number if insurance_policy_number else None,
            )
            patient = patient_crud.create_patient(db, patient_in)
        except Exception as e:
            print(f"Error creating patient: {e}")
            return RedirectResponse(
                url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Failed+to+create+patient",
                status_code=status.HTTP_302_FOUND
            )
    
    # Step 2: Create direct service registration
    try:
        registration_data = DirectServiceRegistrationCreate(
            patient_id=patient.id,
            service_type=service_type,
            service_type_label=SERVICE_TYPE_LABELS.get(service_type),
            gestational_weeks=gestational_weeks,
            lmp=lmp,
            edd=edd,
            registration_notes=registration_notes,
        )
        
        registration = direct_service_registration_crud.create_direct_service_registration(
            db,
            registration_data,
            current_user.id
        )
    except Exception as e:
        print(f"Error creating registration: {e}")
        return RedirectResponse(
            url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Failed+to+create+registration",
            status_code=status.HTTP_302_FOUND
        )
    
    # Step 3: Create service-specific order and handle payment
    order_id = None
    order_type = None
    redirect_url = None
    
    try:
        if service_type == "direct_service":
            # Direct Service - no specific order needed, just complete registration
            order_id = registration.id
            order_type = "direct_service"
            
            # Mark registration as completed
            direct_service_registration_crud.complete_direct_service_registration(
                db, registration.id, order_id, order_type
            )
            
            redirect_url = f"/direct-service-registration?success=true&patient_id={patient.id}"
            
        elif service_type == "lab":
            # Create lab order (walk-in)
            from app.models.encounter_models import LabOrder, OrderStatus
            from app.services import create_charge_for_lab_order
            
            # Parse lab tests from JSON
            tests = []
            if lab_tests:
                import json
                try:
                    tests = json.loads(lab_tests)
                except:
                    tests = [{"test_name": lab_tests, "test_code": None}]
            
            # Create walk-in lab order
            lab_order = LabOrder(
                patient_id=patient.id,
                encounter_id=None,  # No encounter for direct service
                ordered_by_id=current_user.id,
                test_name=tests[0].get("test_name", "General Lab Tests") if tests else "General Lab Tests",
                test_code=tests[0].get("test_code") if tests else None,
                is_walk_in=True,
                checked_in_at=datetime.now(),
                checked_in_by_id=current_user.id,
                status=OrderStatus.PENDING,
            )
            db.add(lab_order)
            db.commit()
            db.refresh(lab_order)
            
            # Create charge for the lab order
            try:
                create_charge_for_lab_order(db, lab_order.id)
            except Exception as e:
                print(f"Warning: Could not create charge: {e}")
            
            order_id = lab_order.id
            order_type = "lab_order"
            
            # Mark registration as completed
            direct_service_registration_crud.complete_direct_service_registration(
                db, registration.id, order_id, order_type
            )
            
            redirect_url = f"/api/v1/ancillary/lab/orders/{lab_order.id}?from_direct=true"
            
        elif service_type == "pharmacy":
            # Create prescription (walk-in / OTC)
            from app.models.encounter_models import Prescription, OrderStatus
            from app.services import create_charge_for_prescription
            
            # Validate: must select a drug from formulary
            pharmacy_drug_uuid = None
            if pharmacy_drug_id and pharmacy_drug_id.strip():
                try:
                    from uuid import UUID
                    pharmacy_drug_uuid = UUID(pharmacy_drug_id.strip())
                except (ValueError, TypeError):
                    pass
            if not pharmacy_drug_uuid:
                return RedirectResponse(
                    url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Please+select+a+medication+from+the+formulary",
                    status_code=status.HTTP_302_FOUND
                )
            
            prescription = Prescription(
                encounter_id=None,  # No encounter for direct service
                prescribed_by_id=current_user.id,
                pharmacy_drug_id=pharmacy_drug_uuid,
                medication_name=medication_name or "Over-the-counter medication",
                dosage="As directed",
                frequency="As needed",
                duration="As needed",
                is_walk_in=True,
                checked_in_at=datetime.now(),
                checked_in_by_id=current_user.id,
                status=OrderStatus.PENDING,
            )
            db.add(prescription)
            db.commit()
            db.refresh(prescription)
            
            # Create charge for the prescription
            try:
                create_charge_for_prescription(db, prescription.id)
            except Exception as e:
                print(f"Warning: Could not create charge: {e}")
            
            order_id = prescription.id
            order_type = "prescription"
            
            # Mark registration as completed
            direct_service_registration_crud.complete_direct_service_registration(
                db, registration.id, order_id, order_type
            )
            
            redirect_url = f"/pharmacy/prescription/{prescription.id}?from_direct=true"
            
        elif service_type == "radiology":
            # Create radiology order (walk-in)
            from app.models.encounter_models import RadiologyOrder, OrderStatus
            from app.services import create_charge_for_radiology_order
            
            radiology_order = RadiologyOrder(
                patient_id=patient.id,
                encounter_id=None,
                ordered_by_id=current_user.id,
                study_type=study_type or "General Radiology",
                is_walk_in=True,
                checked_in_at=datetime.now(),
                checked_in_by_id=current_user.id,
                status=OrderStatus.PENDING,
            )
            db.add(radiology_order)
            db.commit()
            db.refresh(radiology_order)
            
            # Create charge
            try:
                create_charge_for_radiology_order(db, radiology_order.id)
            except Exception as e:
                print(f"Warning: Could not create charge: {e}")
            
            order_id = radiology_order.id
            order_type = "radiology_order"
            
            # Mark registration as completed
            direct_service_registration_crud.complete_direct_service_registration(
                db, registration.id, order_id, order_type
            )
            
            redirect_url = f"/radiology/orders/{radiology_order.id}?from_direct=true"
            
        elif service_type == "procedure":
            # Create procedure (walk-in)
            from app.models.procedure_models import Procedure, ProcedureStatus
            from app.services import create_charge_for_procedure
            
            procedure = Procedure(
                patient_id=patient.id,
                encounter_id=None,
                procedure_name=procedure_name or "General Procedure",
                ordered_by_id=current_user.id,
                is_walk_in=True,
                status=ProcedureStatus.ORDERED,
            )
            db.add(procedure)
            db.commit()
            db.refresh(procedure)
            
            # Create charge
            try:
                create_charge_for_procedure(db, procedure.id)
            except Exception as e:
                print(f"Warning: Could not create charge: {e}")
            
            order_id = procedure.id
            order_type = "procedure"
            
            # Mark registration as completed
            direct_service_registration_crud.complete_direct_service_registration(
                db, registration.id, order_id, order_type
            )
            
            redirect_url = f"/procedures/{procedure.id}?from_direct=true"
    
    except Exception as e:
        print(f"Error creating service order: {e}")
        import traceback
        traceback.print_exc()
        
        return RedirectResponse(
            url=str(request.url_for("direct_service_registration_dashboard")) + "?error=Failed+to+create+service+order",
            status_code=status.HTTP_302_FOUND
        )
    
    # Success - redirect to the service page
    if redirect_url:
        return RedirectResponse(
            url=redirect_url + "&registration_id=" + str(registration.id),
            status_code=status.HTTP_302_FOUND
        )
    
    # Fallback redirect
    return RedirectResponse(
        url=str(request.url_for("direct_service_registration_dashboard")) + "?success=1",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/api/v1/direct-service-registration/{registration_id}", name="get_direct_service_registration")
def get_direct_service_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get direct service registration details"""
    registration = direct_service_registration_crud.get_direct_service_registration(db, registration_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    return JSONResponse(content={
        "id": registration.id,
        "patient_id": registration.patient_id,
        "service_type": registration.service_type,
        "service_type_label": registration.service_type_label,
        "status": registration.status,
        "order_id": registration.order_id,
        "order_type": registration.order_type,
        "created_at": registration.created_at.isoformat() if registration.created_at else None,
        "completed_at": registration.completed_at.isoformat() if registration.completed_at else None,
    })


@router.get("/api/v1/direct-service-registration", name="list_direct_service_registrations")
def list_direct_service_registrations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List direct service registrations with filtering"""
    registrations, total_count = direct_service_registration_crud.get_direct_service_registrations(
        db,
        skip=skip,
        limit=limit,
        service_type=service_type,
        status=status
    )
    
    registrations_data = []
    for reg in registrations:
        registrations_data.append({
            "id": reg.id,
            "patient_id": reg.patient_id,
            "patient_name": f"{reg.patient.first_name} {reg.patient.last_name}" if reg.patient else None,
            "patient_number": reg.patient.patient_number if reg.patient else None,
            "service_type": reg.service_type,
            "service_type_label": reg.service_type_label,
            "status": reg.status,
            "order_id": reg.order_id,
            "order_type": reg.order_type,
            "created_at": reg.created_at.isoformat() if reg.created_at else None,
        })
    
    return JSONResponse(content={
        "registrations": registrations_data,
        "total": total_count
    })


# Import templates at module level for the dashboard route
from app.core.templates import templates
