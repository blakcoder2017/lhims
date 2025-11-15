from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import encounter_crud, billing_crud, service_pricing_crud
from app.schemas.encounter_schemas import (
    EncounterCreate, EncounterUpdate, Encounter,
    LabOrderCreate, LabOrderUpdate, LabOrder,
    RadiologyOrderCreate, RadiologyOrderUpdate, RadiologyOrder,
    PrescriptionCreate, PrescriptionUpdate, Prescription
)
from app.schemas.appointment_schemas import AppointmentCreate, AppointmentUpdate
from app.models.encounter_models import EncounterStatus, OrderStatus, LabOrder as LabOrderModel, RadiologyOrder as RadiologyOrderModel
from app.models.billing_models import InvoiceStatus, ChargeType
from app.models.appointment_models import AppointmentType, AppointmentStatus
from app.schemas.billing_schemas import ChargeCreate

from app.services import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_procedure
)

router = APIRouter(
    prefix="/api/v1/encounters",
    tags=["Encounters"]
)


# Encounter Endpoints
@router.post("/", response_model=Encounter, status_code=status.HTTP_201_CREATED)
def create_encounter_endpoint(
    encounter: EncounterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Create a new clinical encounter (JSON API). Restricted to doctors/clinicians (and admins)."""
    # Override clinician_id with current user (or use provided clinician_id for assigned doctor)
    # Front office creates the encounter, but clinician_id can be set to assigned doctor
    if not encounter.clinician_id:
        encounter.clinician_id = current_user.id
    return encounter_crud.create_encounter(db, encounter)


@router.post("/create", name="create_encounter_form", status_code=status.HTTP_302_FOUND)
def create_encounter_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    
    # Form fields
    patient_id: int = Form(...),
    appointment_id: Optional[int] = Form(None),
    chief_complaint: Optional[str] = Form(None),
    history_of_present_illness: Optional[str] = Form(None),
    past_medical_history: Optional[str] = Form(None),
    allergies: Optional[str] = Form(None),
    medications: Optional[str] = Form(None),
    physical_examination: Optional[str] = Form(None),
    assessment: Optional[str] = Form(None),
    plan: Optional[str] = Form(None),
    primary_diagnosis_code: Optional[str] = Form(None),
    primary_diagnosis_description: Optional[str] = Form(None),
    secondary_diagnosis_codes: Optional[str] = Form(None),
    primary_disease_id: Optional[str] = Form(None),
    secondary_disease_ids: Optional[str] = Form(None),
    custom_diseases: Optional[str] = Form(None),
):
    """
    Handles HTML form submission for creating a new clinical encounter.
    Workflow Steps 5-7: Clinical Encounter Documentation
    
    Only doctors/clinicians (or admins) can start encounters. Front desk and nurses must check in patients instead.
    
    For cash patients: Checks if consultation fee has been paid before allowing encounter creation.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    
    # Check payment requirement for cash patients (consultation fee)
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.CONSULTATION
        )
        
        if payment_required and not payment_paid:
            # Redirect to payment page
            return RedirectResponse(
                url=f"/patients/{patient_id}/pay/consultation?return_to=encounters/new",
                status_code=status.HTTP_302_FOUND
            )
    
    try:
        # Create encounter data
        encounter_data = EncounterCreate(
            patient_id=patient_id,
            appointment_id=appointment_id,
            clinician_id=current_user.id,
            status=EncounterStatus.IN_PROGRESS,
            chief_complaint=chief_complaint if chief_complaint else None,
            history_of_present_illness=history_of_present_illness if history_of_present_illness else None,
            past_medical_history=past_medical_history if past_medical_history else None,
            allergies=allergies if allergies else None,
            medications=medications if medications else None,
            physical_examination=physical_examination if physical_examination else None,
            assessment=assessment if assessment else None,
            plan=plan if plan else None,
            primary_diagnosis_code=primary_diagnosis_code if primary_diagnosis_code else None,
            primary_diagnosis_description=primary_diagnosis_description if primary_diagnosis_description else None,
            secondary_diagnosis_codes=secondary_diagnosis_codes if secondary_diagnosis_codes else None,
        )
        
        # Create encounter
        new_encounter = encounter_crud.create_encounter(db, encounter_data)
        
        # Link diseases to encounter
        from app.crud import disease_crud
        import json
        
        # Process primary disease
        if primary_disease_id and primary_disease_id.strip():
            try:
                disease_id = int(primary_disease_id)
                disease_crud.add_disease_to_encounter(
                    db, new_encounter.id, disease_id=disease_id, is_primary=True
                )
            except (ValueError, TypeError):
                pass  # Invalid ID, skip
        
        # Process secondary diseases
        if secondary_disease_ids and secondary_disease_ids.strip():
            try:
                secondary_ids = json.loads(secondary_disease_ids)
                for disease_id in secondary_ids:
                    try:
                        disease_crud.add_disease_to_encounter(
                            db, new_encounter.id, disease_id=int(disease_id), is_primary=False
                        )
                    except (ValueError, TypeError):
                        continue
            except (json.JSONDecodeError, TypeError):
                pass  # Invalid JSON, skip
        
        # Process custom diseases
        if custom_diseases and custom_diseases.strip():
            try:
                custom_names = json.loads(custom_diseases)
                for custom_name in custom_names:
                    if custom_name and custom_name.strip():
                        disease_crud.add_disease_to_encounter(
                            db, new_encounter.id, custom_name=custom_name.strip(), is_primary=False
                        )
            except (json.JSONDecodeError, TypeError):
                pass  # Invalid JSON, skip
        
        # NEW WORKFLOW: If encounter created by nurse, automatically create appointment and add to doctor queue
        if not appointment_id and current_user.role.name in ["Nurse", "Admin"]:
            from app.crud import appointment_crud
            
            # Determine department from chief complaint or use default
            department = "General Medicine"  # Default department
            if chief_complaint:
                # Try to infer department from chief complaint (basic logic)
                complaint_lower = chief_complaint.lower()
                if any(word in complaint_lower for word in ["pediatric", "child", "baby", "infant"]):
                    department = "Pediatrics"
                elif any(word in complaint_lower for word in ["pregnant", "pregnancy", "obstetric", "gynec"]):
                    department = "Obstetrics & Gynecology"
                elif any(word in complaint_lower for word in ["emergency", "urgent", "trauma", "accident"]):
                    department = "Emergency"
            
            # Create appointment automatically to add patient to doctor queue
            appointment_data = AppointmentCreate(
                patient_id=patient_id,
                department=department,
                department_type="opd",
                appointment_type=AppointmentType.WALK_IN,
                scheduled_date=datetime.now(),
                chief_complaint=chief_complaint,
                notes="Auto-created from encounter by nurse",
                priority=5,
                assigned_clinician_id=None,  # Will be auto-assigned
                created_by_id=current_user.id
            )
            
            new_appointment = appointment_crud.create_appointment(db, appointment_data)
            
            # Check in the patient automatically so they appear in doctor queue
            appointment_crud.update_appointment(
                db, 
                new_appointment.id, 
                AppointmentUpdate(status=AppointmentStatus.CHECKED_IN, checked_in_at=datetime.now())
            )
            
            # Link encounter to appointment
            new_encounter.appointment_id = new_appointment.id
            db.commit()
            db.refresh(new_encounter)
        
        # Redirect to view encounter page
        return RedirectResponse(
            url=f"/encounters/{new_encounter.id}?status=encounter_created",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating encounter: {str(e)}"
        )


@router.get("/{encounter_id}", response_model=Encounter)
def get_encounter_endpoint(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific encounter by ID."""
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


@router.get("/patient/{patient_id}", response_model=List[Encounter])
def get_patient_encounters(
    patient_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all encounters for a specific patient."""
    return encounter_crud.get_encounters_by_patient(db, patient_id, skip, limit)


@router.post("/{encounter_id}/detain", response_model=Encounter, status_code=status.HTTP_200_OK)
def detain_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Admin"]))
):
    """Detain a patient for observation. Only doctors can detain patients."""
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update encounter status to DETAINED
    encounter_update = EncounterUpdate(status=EncounterStatus.DETAINED)
    updated_encounter = encounter_crud.update_encounter(db, encounter_id, encounter_update)
    
    if not updated_encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    return updated_encounter


@router.put("/{encounter_id}", response_model=Encounter)
def update_encounter_endpoint(
    encounter_id: int,
    encounter_update: EncounterUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin", "Front Office"])),
    force_close: Optional[bool] = Query(False, description="Force close encounter even with pending orders (Admin only)")
):
    """Update an existing encounter. Doctors can update, but closing requires validation."""
    # Check if trying to close the encounter
    # Handle both Enum and string values
    status_to_check = encounter_update.status
    if isinstance(status_to_check, str):
        status_to_check = EncounterStatus(status_to_check)
    
    if status_to_check == EncounterStatus.COMPLETED:
        # Get the encounter with orders
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        # Check for pending lab orders
        pending_lab_orders = db.query(LabOrderModel).filter(
            LabOrderModel.encounter_id == encounter_id,
            LabOrderModel.status.in_([OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS])
        ).count()
        
        # Check for pending radiology orders
        pending_radiology_orders = db.query(RadiologyOrderModel).filter(
            RadiologyOrderModel.encounter_id == encounter_id,
            RadiologyOrderModel.status.in_([OrderStatus.PENDING, OrderStatus.ORDERED, OrderStatus.IN_PROGRESS])
        ).count()
        
        # Validate force_close permission
        if force_close and current_user.role.name != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Administrators can force close encounters with pending orders."
            )
        
        # Check for pending orders (unless force_close is enabled for Admin)
        if (pending_lab_orders > 0 or pending_radiology_orders > 0) and not (force_close and current_user.role.name == "Admin"):
            error_details = []
            if pending_lab_orders > 0:
                error_details.append(f"{pending_lab_orders} pending lab order(s)")
            if pending_radiology_orders > 0:
                error_details.append(f"{pending_radiology_orders} pending radiology order(s)")
            
            error_message = f"Cannot close encounter. There are {', '.join(error_details)}. Please complete all orders before closing the encounter."
            
            # If user is Admin, suggest force close option
            if current_user.role.name == "Admin":
                error_message += " As an Administrator, you can use the 'Force Close' option if necessary."
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Check for unpaid bills if patient is admitted
        from app.crud import ipd_crud
        from app.models.ipd_models import AdmissionStatus
        
        # Check if patient is currently admitted
        current_admission = ipd_crud.get_current_admission(db, encounter.patient_id)
        
        if current_admission:
            # Patient is admitted - check for unpaid bills
            encounter_invoices = billing_crud.get_invoices_by_encounter(db, encounter_id)
            unpaid_invoices = [inv for inv in encounter_invoices if inv.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIALLY_PAID] and inv.balance > 0]
            
            # Also check for any invoices related to the admission (ward/bed charges)
            from app.models.billing_models import Invoice
            patient_invoices = billing_crud.get_invoices_by_patient(db, encounter.patient_id)
            admission_unpaid = [inv for inv in patient_invoices 
                              if inv.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIALLY_PAID] 
                              and inv.balance > 0 
                              and inv.invoice_date >= current_admission.admission_date]
            
            if unpaid_invoices or admission_unpaid:
                total_unpaid = sum([inv.balance for inv in unpaid_invoices + admission_unpaid])
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot close encounter. Patient is admitted and has outstanding bills of {total_unpaid:.2f}. Please settle all bills before closing the encounter or discharging the patient."
                )
        
    encounter = encounter_crud.update_encounter(db, encounter_id, encounter_update)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # If encounter is completed, remove patient from queue (update appointment status)
    if status_to_check == EncounterStatus.COMPLETED:
        if encounter.appointment_id:
            from app.crud import appointment_crud
            appointment_update = AppointmentUpdate(
                status=AppointmentStatus.COMPLETED,
                completed_at=datetime.now()
            )
            appointment_crud.update_appointment(db, encounter.appointment_id, appointment_update)
    
    return encounter


@router.delete("/{encounter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_encounter_endpoint(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Delete an encounter (soft delete)."""
    encounter = encounter_crud.delete_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return None


# Lab Order Endpoints
@router.post("/{encounter_id}/lab-orders", response_model=LabOrder, status_code=status.HTTP_201_CREATED)
def create_lab_order_endpoint(
    encounter_id: int,
    lab_order: LabOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Create a new lab order for an encounter (JSON API)."""
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Override encounter_id, patient_id, and ordered_by_id
    lab_order.encounter_id = encounter_id
    lab_order.patient_id = encounter.patient_id  # Set patient_id from encounter
    lab_order.ordered_by_id = current_user.id
    lab_order.is_walk_in = False
    new_order = encounter_crud.create_lab_order(db, lab_order)
    
    try:
        create_charge_for_lab_order(db, new_order, current_user.id)
    except Exception as billing_error:
        print(f"Warning: Unable to create lab charge for order {new_order.id}: {billing_error}")
    
    return new_order


@router.post("/{encounter_id}/lab-orders/create", name="create_lab_order_form", status_code=status.HTTP_302_FOUND)
def create_lab_order_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
    service_pricing_id: Optional[int] = Form(None),
    test_name: Optional[str] = Form(None),
    test_code: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Handle HTML form submission for creating a lab order."""
    try:
        # Verify encounter exists
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        resolved_test_name = test_name
        resolved_test_code = test_code

        if service_pricing_id:
            service = service_pricing_crud.get_service_pricing(db, service_pricing_id)
            if not service or service.charge_type != ChargeType.LAB_TEST.value:
                raise HTTPException(status_code=400, detail="Invalid lab service selected.")
            resolved_test_name = service.service_name
            resolved_test_code = service.service_code or test_code

        if not resolved_test_name:
            raise HTTPException(status_code=400, detail="Lab test name is required.")

        # Create lab order data
        lab_order_data = LabOrderCreate(
            encounter_id=encounter_id,
            patient_id=encounter.patient_id,  # Set patient_id from encounter
            ordered_by_id=current_user.id,
            test_name=resolved_test_name,
            test_code=resolved_test_code if resolved_test_code else None,
            instructions=instructions if instructions else None,
            priority=priority,
            is_walk_in=False
        )
        
        # Create lab order
        new_order = encounter_crud.create_lab_order(db, lab_order_data)
        
        try:
            create_charge_for_lab_order(db, new_order, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create lab charge for order {new_order.id}: {billing_error}")
        
        # Redirect back to encounter page
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=lab_order_added",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating lab order: {str(e)}"
        )


@router.get("/{encounter_id}/lab-orders", response_model=List[LabOrder])
def get_encounter_lab_orders(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all lab orders for an encounter."""
    return encounter_crud.get_lab_orders_by_encounter(db, encounter_id)


@router.put("/lab-orders/{lab_order_id}", response_model=LabOrder)
def update_lab_order_endpoint(
    lab_order_id: int,
    lab_order_update: LabOrderUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Clinician", "Lab Staff", "Admin"]))
):
    """Update a lab order (e.g., enter results)."""
    # If updating result, set result_entered_by_id
    if lab_order_update.result and not lab_order_update.result_entered_by_id:
        lab_order_update.result_entered_by_id = current_user.id
        lab_order_update.result_entered_at = datetime.now()
    
    lab_order = encounter_crud.update_lab_order(db, lab_order_id, lab_order_update)
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    return lab_order


# Radiology Order Endpoints
@router.post("/{encounter_id}/radiology-orders", response_model=RadiologyOrder, status_code=status.HTTP_201_CREATED)
def create_radiology_order_endpoint(
    encounter_id: int,
    radiology_order: RadiologyOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Create a new radiology order for an encounter (JSON API)."""
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Override encounter_id, patient_id, and ordered_by_id
    radiology_order.encounter_id = encounter_id
    radiology_order.patient_id = encounter.patient_id  # Set patient_id from encounter
    radiology_order.ordered_by_id = current_user.id
    radiology_order.is_walk_in = False
    new_order = encounter_crud.create_radiology_order(db, radiology_order)
    
    try:
        create_charge_for_radiology_order(db, new_order, current_user.id)
    except Exception as billing_error:
        print(f"Warning: Unable to create radiology charge for order {new_order.id}: {billing_error}")
    
    return new_order


@router.post("/{encounter_id}/radiology-orders/create", name="create_radiology_order_form", status_code=status.HTTP_302_FOUND)
def create_radiology_order_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
    service_pricing_id: Optional[int] = Form(None),
    study_type: Optional[str] = Form(None),
    study_code: Optional[str] = Form(None),
    body_part: Optional[str] = Form(None),
    clinical_indication: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    priority: str = Form("routine"),
):
    """Handle HTML form submission for creating a radiology order."""
    try:
        # Verify encounter exists
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        resolved_study_type = study_type
        resolved_study_code = study_code

        if service_pricing_id:
            service = service_pricing_crud.get_service_pricing(db, service_pricing_id)
            if not service or service.charge_type != ChargeType.RADIOLOGY.value:
                raise HTTPException(status_code=400, detail="Invalid radiology service selected.")
            resolved_study_type = service.service_name
            resolved_study_code = service.service_code or study_code

        if not resolved_study_type:
            raise HTTPException(status_code=400, detail="Radiology study is required.")

        # Create radiology order data
        radiology_order_data = RadiologyOrderCreate(
            encounter_id=encounter_id,
            patient_id=encounter.patient_id,  # Set patient_id from encounter
            ordered_by_id=current_user.id,
            study_type=resolved_study_type,
            study_code=resolved_study_code if resolved_study_code else None,
            body_part=body_part if body_part else None,
            clinical_indication=clinical_indication if clinical_indication else None,
            instructions=instructions if instructions else None,
            priority=priority,
            is_walk_in=False
        )
        
        # Create radiology order
        new_order = encounter_crud.create_radiology_order(db, radiology_order_data)
        
        try:
            create_charge_for_radiology_order(db, new_order, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create radiology charge for order {new_order.id}: {billing_error}")
        
        # Redirect back to encounter page
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=radiology_order_added",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating radiology order: {str(e)}"
        )


@router.get("/{encounter_id}/radiology-orders", response_model=List[RadiologyOrder])
def get_encounter_radiology_orders(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all radiology orders for an encounter."""
    return encounter_crud.get_radiology_orders_by_encounter(db, encounter_id)


@router.put("/radiology-orders/{radiology_order_id}", response_model=RadiologyOrder)
def update_radiology_order_endpoint(
    radiology_order_id: int,
    radiology_order_update: RadiologyOrderUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Update a radiology order (e.g., enter report)."""
    # If updating report, set report_entered_by_id
    if radiology_order_update.report and not radiology_order_update.report_entered_by_id:
        radiology_order_update.report_entered_by_id = current_user.id
        radiology_order_update.report_entered_at = datetime.now()
    
    radiology_order = encounter_crud.update_radiology_order(db, radiology_order_id, radiology_order_update)
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    return radiology_order


# Prescription Endpoints
@router.post("/{encounter_id}/prescriptions", response_model=Prescription, status_code=status.HTTP_201_CREATED)
def create_prescription_endpoint(
    encounter_id: int,
    prescription: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Create a new prescription for an encounter (JSON API)."""
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Override encounter_id and prescribed_by_id
    prescription.encounter_id = encounter_id
    prescription.prescribed_by_id = current_user.id
    return encounter_crud.create_prescription(db, prescription)


@router.post("/{encounter_id}/prescriptions/create", name="create_prescription_form", status_code=status.HTTP_302_FOUND)
def create_prescription_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
    medication_id: Optional[str] = Form(None),
    medication_name: str = Form(...),
    medication_code: Optional[str] = Form(None),
    dosage: str = Form(...),
    frequency: str = Form(...),
    duration: str = Form(...),
    quantity: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
):
    """Handle HTML form submission for creating a prescription."""
    try:
        # Verify encounter exists
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        # Convert medication_id from string to int, handling empty strings
        medication_id_int = None
        if medication_id and medication_id.strip():
            try:
                medication_id_int = int(medication_id)
            except (ValueError, TypeError):
                medication_id_int = None
        
        # Convert quantity from string to int, handling empty strings
        quantity_int = None
        if quantity and quantity.strip():
            try:
                quantity_int = int(quantity)
            except (ValueError, TypeError):
                quantity_int = None
        
        # Validate required fields
        if not medication_name or not medication_name.strip():
            raise HTTPException(status_code=422, detail="Medication name is required")
        if not dosage or not dosage.strip():
            raise HTTPException(status_code=422, detail="Dosage is required")
        if not frequency or not frequency.strip():
            raise HTTPException(status_code=422, detail="Frequency is required")
        if not duration or not duration.strip():
            raise HTTPException(status_code=422, detail="Duration is required")
        
        # If medication_id is provided, fetch medication details to populate name/code
        medication_name_final = medication_name.strip()
        medication_code_final = medication_code.strip() if medication_code else None
        if medication_id_int:
            from app.crud import inventory_crud
            medication = inventory_crud.get_medication(db, medication_id_int)
            if medication:
                medication_name_final = medication.name
                medication_code_final = medication.medication_code or medication_code_final
        
        # Create prescription data
        prescription_data = PrescriptionCreate(
            encounter_id=encounter_id,
            prescribed_by_id=current_user.id,
            medication_id=medication_id_int,
            medication_name=medication_name_final,
            medication_code=medication_code_final if medication_code_final else None,
            dosage=dosage.strip(),
            frequency=frequency.strip(),
            duration=duration.strip(),
            quantity=quantity_int,
            instructions=instructions.strip() if instructions else None,
        )
        
        # Create prescription
        prescription = encounter_crud.create_prescription(db, prescription_data)
        
        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=201,
                content={
                    "success": True,
                    "message": "Prescription added successfully",
                    "prescription": {
                        "id": prescription.id,
                        "medication_name": prescription.medication_name,
                        "dosage": prescription.dosage,
                        "frequency": prescription.frequency,
                        "duration": prescription.duration,
                        "quantity": prescription.quantity,
                        "instructions": prescription.instructions,
                        "status": prescription.status.value
                    }
                }
            )
        
        # Redirect back to encounter page for regular form submission
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=prescription_added",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=422,
                content={"success": False, "error": f"Validation error: {str(e)}"}
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            from fastapi.responses import JSONResponse
            import traceback
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Error creating prescription: {str(e)}", "traceback": traceback.format_exc()}
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating prescription: {str(e)}"
        )


@router.get("/{encounter_id}/prescriptions", response_model=List[Prescription])
def get_encounter_prescriptions(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all prescriptions for an encounter."""
    return encounter_crud.get_prescriptions_by_encounter(db, encounter_id)


@router.post("/{encounter_id}/procedures/create", name="create_procedure_form", status_code=status.HTTP_302_FOUND)
def create_procedure_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    procedure_name: str = Form(...),
    procedure_code: Optional[str] = Form(None),
    procedure_type: str = Form(...),
    description: Optional[str] = Form(None),
    indication: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
):
    """Create a new procedure for an encounter."""
    try:
        from app.crud import procedure_crud
        from app.models.procedure_models import ProcedureType, ProcedureStatus
        from app.schemas.procedure_schemas import ProcedureCreate
        
        # Get encounter to get patient_id
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        # Parse procedure type
        try:
            proc_type = ProcedureType(procedure_type)
        except ValueError:
            raise ValueError(f"Invalid procedure type: {procedure_type}")
        
        # Create procedure data
        procedure_data = ProcedureCreate(
            patient_id=encounter.patient_id,
            encounter_id=encounter_id,
            ordered_by_id=current_user.id,
            procedure_name=procedure_name.strip(),
            procedure_code=procedure_code.strip() if procedure_code else None,
            procedure_type=proc_type,
            description=description.strip() if description else None,
            indication=indication.strip() if indication else None,
            location=location.strip() if location else None,
            status=ProcedureStatus.SCHEDULED,
            is_walk_in=False
        )
        
        # Create procedure
        procedure = procedure_crud.create_procedure(db, procedure_data)
        
        try:
            create_charge_for_procedure(db, procedure, current_user.id)
        except Exception as billing_error:
            print(f"Warning: Unable to create procedure charge for procedure {procedure.id}: {billing_error}")
        
        # Redirect back to encounter page
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=procedure_added",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/{encounter_id}/antenatal-orders/create", name="create_antenatal_order_form", status_code=status.HTTP_302_FOUND)
def create_antenatal_order_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    service_pricing_id: int = Form(...),
    quantity: int = Form(1),
    notes: Optional[str] = Form(None)
):
    """Add an antenatal service charge directly from the encounter."""
    try:
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")

        service = service_pricing_crud.get_service_pricing(db, service_pricing_id)
        if not service or service.charge_type != ChargeType.ANTENATAL.value:
            raise HTTPException(status_code=400, detail="Invalid antenatal service selected.")

        from app.services.charge_automation import get_or_create_invoice_for_encounter

        quantity = max(1, quantity or 1)
        unit_price = Decimal(str(service.unit_price or Decimal("0.00")))
        invoice = get_or_create_invoice_for_encounter(db, encounter_id, current_user.id, require_payment=False)

        description = f"Antenatal Service - {service.service_name}"
        if notes:
            description = f"{description} ({notes})"

        charge_data = ChargeCreate(
            charge_type=ChargeType.ANTENATAL,
            description=description[:500],
            quantity=quantity,
            unit_price=unit_price,
            discount=Decimal("0.00"),
            tax_rate=Decimal("0.00"),
            encounter_id=encounter_id
        )

        billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)

        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=antenatal_added",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error adding antenatal service: {str(e)}"
        )


@router.put("/prescriptions/{prescription_id}", response_model=Prescription)
def update_prescription_endpoint(
    prescription_id: int,
    prescription_update: PrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"]))
):
    """Update a prescription (e.g., mark as dispensed)."""
    # If marking as dispensed, set dispensed_by_id
    if prescription_update.status == OrderStatus.COMPLETED and not prescription_update.dispensed_by_id:
        prescription_update.dispensed_by_id = current_user.id
        prescription_update.dispensed_at = datetime.now()
    
    prescription = encounter_crud.update_prescription(db, prescription_id, prescription_update)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription

