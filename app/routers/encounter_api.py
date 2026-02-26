from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

from app.db.database import get_db
from app.core.deps import role_required, get_current_user, permission_required
from app.crud import encounter_crud, billing_crud, service_pricing_crud, appointment_crud
from app.schemas.encounter_schemas import (
    EncounterCreate, EncounterUpdate, Encounter, EncounterAutoSave,
    LabOrderCreate, LabOrderUpdate, LabOrder,
    RadiologyOrderCreate, RadiologyOrderUpdate, RadiologyOrder,
    PrescriptionCreate, PrescriptionUpdate, Prescription,
    DifferentialInput, DifferentialResponse, DifferentialSaveRequest,
    AddendumCreate, Addendum
)
from app.schemas.appointment_schemas import AppointmentCreate, AppointmentUpdate
from app.models.encounter_models import EncounterStatus, OrderStatus, LabOrder as LabOrderModel, RadiologyOrder as RadiologyOrderModel, EncounterAddendum
from app.models.procedure_models import ProcedureStatus
from app.models.billing_models import InvoiceStatus, ChargeType
from app.models.scheduled_appointment_models import AppointmentType, AppointmentStatus
from app.models.appointment_models import QueueStatus
from app.schemas.billing_schemas import ChargeCreate

from app.services import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_procedure,
    create_charge_for_consultation,
    auto_create_lab_sample,
    create_sample_if_not_exists
)
from app.services.gstg_differential import generate_differential_suggestions
from app.utils.payment_verification import link_existing_charge_to_encounter

router = APIRouter(
    prefix="/api/v1/encounters",
    tags=["Encounters"]
)


def _calculate_age_years(dob: Optional[date]) -> Optional[int]:
    if not dob:
        return None
    today = datetime.utcnow().date()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(years, 0)


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
    queue_entry_id: Optional[int] = Form(None),  # Link to OPD queue entry
    appointment_id: Optional[int] = Form(None),
    opd_visit_id: Optional[int] = Form(None),  # OPD visit link
    admission_id: Optional[int] = Form(None),  # IPD admission link
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
    diagnoses: Optional[List[int]] = Form(None),  # Disease IDs from multi-select
):
    """
    Handles HTML form submission for creating a new clinical encounter.
    Workflow Steps 5-7: Clinical Encounter Documentation
    
    Only doctors/clinicians (or admins) can start encounters. Front desk and nurses must check in patients instead.
    
    For cash patients: Checks if consultation fee has been paid before allowing encounter creation.
    """
    from app.utils.payment_verification import (
        verify_encounter_workflow,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    
    # Verify complete workflow: vitals + check-in + payment (for ALL users including admins)
    workflow_complete, missing_step, vitals_record, appointment_record, payment_info = verify_encounter_workflow(
        db, patient_id, check_vitals=True, check_checkin=True, check_payment=True
    )
    
    if not workflow_complete:
        triage_url = request.url_for("patient_triage", patient_id=patient_id)
        status_param = "checkin_required"
        if missing_step == "vitals":
            status_param = "vitals_required"
        elif missing_step == "payment":
            status_param = "payment_required"
        return RedirectResponse(
            url=f"{triage_url}?status={status_param}",
            status_code=status.HTTP_302_FOUND
        )
    
    # Use the verified appointment record
    if appointment_record:
        appointment_id = appointment_record.id
    else:
        # Validate that appointment_id exists if provided
        if appointment_id:
            from app.models.scheduled_appointment_models import ScheduledAppointment
            existing = db.query(ScheduledAppointment).filter(ScheduledAppointment.id == appointment_id).first()
            if not existing:
                # Invalid appointment_id, set to None
                appointment_id = None
    
    try:
        # Create encounter data
        encounter_data = EncounterCreate(
            patient_id=patient_id,
            queue_entry_id=queue_entry_id if queue_entry_id else None,
            appointment_id=appointment_id,
            opd_visit_id=opd_visit_id if opd_visit_id else None,
            admission_id=admission_id if admission_id else None,
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
        
        # Create encounter (with validation)
        try:
            new_encounter = encounter_crud.create_encounter(db, encounter_data)
        except ValueError as e:
            # Handle validation errors
            error_msg = str(e)
            triage_url = request.url_for("patient_triage", patient_id=patient_id)
            return RedirectResponse(
                url=f"{triage_url}?error={error_msg}",
                status_code=status.HTTP_302_FOUND
            )
        
        # Link existing paid consultation charge to this encounter (don't create new charge)
        # This prevents duplicate charges when patient has already paid at registration
        try:
            link_existing_charge_to_encounter(
                db, new_encounter.patient_id, new_encounter.id
            )
        except Exception as _:
            print(f"Warning: Could not link existing charge to encounter {new_encounter.id}")
        
        # Link diseases to encounter
        from app.crud import disease_crud
        import json
        
        # Debug: Log received diagnoses
        print(f"DEBUG: Received diagnoses parameter: {diagnoses}, type: {type(diagnoses)}")
        
        # Process diagnoses from multi-select field (new method)
        if diagnoses and len(diagnoses) > 0:
            # First diagnosis is primary, rest are secondary
            for idx, disease_id in enumerate(diagnoses):
                try:
                    # Ensure disease_id is an integer
                    if isinstance(disease_id, str):
                        disease_id = int(disease_id)
                    elif not isinstance(disease_id, int):
                        disease_id = int(disease_id)
                    
                    is_primary = (idx == 0)  # First one is primary
                    disease_crud.add_disease_to_encounter(
                        db, new_encounter.id, disease_id=disease_id, is_primary=is_primary
                    )
                except (ValueError, TypeError) as e:
                    print(f"Error adding disease {disease_id} to encounter: {e}")
                    continue
        else:
            # Fallback to old method for backward compatibility
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


@router.post("/create", response_model=Encounter, status_code=status.HTTP_201_CREATED)
def create_encounter_json(
    encounter: EncounterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """
    Create a new clinical encounter via JSON API.
    """
    # Override clinician_id with current user
    if not encounter.clinician_id:
        encounter.clinician_id = current_user.id
    
    # Create encounter
    new_encounter = encounter_crud.create_encounter(db, encounter)
    
    # Link diseases to encounter if diagnoses provided
    if encounter.diagnoses and len(encounter.diagnoses) > 0:
        from app.crud import disease_crud
        for idx, disease_id in enumerate(encounter.diagnoses):
            is_primary = (idx == 0)  # First one is primary
            try:
                disease_crud.add_disease_to_encounter(
                    db, new_encounter.id, disease_id=disease_id, is_primary=is_primary
                )
            except Exception:
                continue
    
    return new_encounter


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


@router.get("/{encounter_id}/compare", name="encounter_compare")
def compare_encounters(
    encounter_id: int,
    compare_with: int = Query(..., description="ID of the encounter to compare with"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Compare two encounters side-by-side.
    Returns clinical data from both encounters for comparison.
    """
    # Get current encounter
    current_encounter = encounter_crud.get_encounter_with_orders(db, encounter_id)
    if not current_encounter:
        raise HTTPException(status_code=404, detail="Current encounter not found")
    
    # Get comparison encounter
    compare_encounter = encounter_crud.get_encounter_with_orders(db, compare_with)
    if not compare_encounter:
        raise HTTPException(status_code=404, detail="Comparison encounter not found")
    
    # Verify they're for the same patient
    if current_encounter.patient_id != compare_encounter.patient_id:
        raise HTTPException(status_code=400, detail="Cannot compare encounters from different patients")
    
    def format_encounter(enc):
        return {
            "id": enc.id,
            "encounter_date": enc.encounter_date.isoformat() if enc.encounter_date else None,
            "status": enc.status.value if enc.status else None,
            "clinician": enc.clinician.full_name if enc.clinician else None,
            "chief_complaint": enc.chief_complaint,
            "history_of_present_illness": enc.history_of_present_illness,
            "past_medical_history": enc.past_medical_history,
            "allergies": enc.allergies,
            "medications": enc.medications,
            "physical_examination": enc.physical_examination,
            "assessment": enc.assessment,
            "plan": enc.plan,
            "primary_diagnosis_code": enc.primary_diagnosis_code,
            "primary_diagnosis_description": enc.primary_diagnosis_description,
            "lab_orders": [
                {
                    "id": o.id,
                    "test_name": o.test_name,
                    "status": o.status.value,
                    "result": o.result
                }
                for o in (enc.lab_orders or [])
            ],
            "radiology_orders": [
                {
                    "id": o.id,
                    "procedure_name": o.procedure_name,
                    "status": o.status.value,
                    "result": o.result
                }
                for o in (enc.radiology_orders or [])
            ],
            "prescriptions": [
                {
                    "id": p.id,
                    "medication_name": p.medication_name,
                    "dosage": p.dosage,
                    "frequency": p.frequency,
                    "duration": p.duration
                }
                for p in (enc.prescriptions or [])
            ],
            "procedures": [
                {
                    "id": p.id,
                    "procedure_name": p.procedure_name,
                    "status": p.status.value if p.status else None
                }
                for p in (enc.procedures or [])
            ]
        }
    
    return {
        "current": format_encounter(current_encounter),
        "comparison": format_encounter(compare_encounter),
        "timestamp": datetime.now().isoformat()
    }


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
    
    # Skip validation if status is not being changed (None)
    if status_to_check is not None:
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
    
    # If addendum is being updated, set the author and timestamp
    if encounter_update.addendum is not None:
        # Get the existing encounter to check if addendum changed
        existing_encounter = encounter_crud.get_encounter(db, encounter_id)
        if existing_encounter and existing_encounter.addendum != encounter_update.addendum:
            # Addendum changed - update the tracking fields
            from datetime import datetime
            existing_encounter.addendum_by_id = current_user.id
            existing_encounter.addendum_at = datetime.now()
            db.commit()
            # Refresh the encounter to get updated values
            db.refresh(existing_encounter)
            encounter = existing_encounter
    
    # If encounter is completed, update appointment and queue entry
    if status_to_check is not None and status_to_check == EncounterStatus.COMPLETED:
        # Update scheduled appointment if exists
        if encounter.appointment_id:
            appointment_update = AppointmentUpdate(
                status=AppointmentStatus.COMPLETED,
                completed_at=datetime.now()
            )
            appointment_crud.update_appointment(db, encounter.appointment_id, appointment_update)
        
        # Update queue entry if exists (remove patient from queue)
        if encounter.queue_entry_id:
            from app.models.appointment_models import OPDQueue
            queue_entry = db.query(OPDQueue).filter(
                OPDQueue.id == encounter.queue_entry_id,
                OPDQueue.is_active == True
            ).first()
            if queue_entry:
                queue_entry.status = QueueStatus.COMPLETED
                queue_entry.completed_at = datetime.now()
                db.commit()
    
    return encounter


@router.post("/{encounter_id}/autosave", name="encounter_autosave")
def auto_save_encounter(
    encounter_id: int,
    auto_save: EncounterAutoSave,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Auto-save clinical notes without full validation.
    Used for real-time saving of clinical documentation.
    """
    # Get existing encounter
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Create update data - only update non-None fields
    update_data = auto_save.model_dump(exclude_unset=True)
    
    if update_data:
        # Use the existing update_encounter function with minimal validation
        from app.schemas.encounter_schemas import EncounterUpdate
        encounter_update = EncounterUpdate(**update_data)
        updated_encounter = encounter_crud.update_encounter(db, encounter_id, encounter_update)
        
        if not updated_encounter:
            raise HTTPException(status_code=500, detail="Failed to save encounter")
        
        return {
            "status": "success",
            "message": "Clinical notes saved",
            "encounter_id": encounter_id,
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "status": "no_changes",
        "message": "No changes to save",
        "encounter_id": encounter_id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/{encounter_id}/order-status", name="encounter_order_status")
def get_encounter_order_status(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Get real-time status of lab and radiology orders for an encounter.
    Used for polling/refresh without full page reload.
    """
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get lab orders
    lab_orders = db.query(LabOrderModel).filter(
        LabOrderModel.encounter_id == encounter_id
    ).order_by(LabOrderModel.created_at.desc()).all()
    
    # Get radiology orders
    radiology_orders = db.query(RadiologyOrderModel).filter(
        RadiologyOrderModel.encounter_id == encounter_id
    ).order_by(RadiologyOrderModel.created_at.desc()).all()
    
    return {
        "encounter_id": encounter_id,
        "lab_orders": [
            {
                "id": order.id,
                "test_name": order.test_name,
                "status": order.status.value,
                "priority": order.priority,
                "result": order.result,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None
            }
            for order in lab_orders
        ],
        "radiology_orders": [
            {
                "id": order.id,
                "procedure_name": order.procedure_name,
                "status": order.status.value,
                "priority": order.priority,
                "result": order.result,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None
            }
            for order in radiology_orders
        ],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/{encounter_id}/check-drug-interaction", name="check_drug_interaction")
def check_drug_interaction(
    encounter_id: int,
    medication_name: str,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """
    Check for potential drug-allergy interactions before prescribing.
    Returns warnings if potential interactions are detected.
    """
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    warnings = []
    medication_name_lower = medication_name.lower()
    
    # Check patient allergies
    patient_allergies = (encounter.allergies or "").lower()
    
    drug_class_keywords = {
        'penicillin': ['penicillin', 'amoxicillin', 'ampicillin', 'amoxil', 'cloxacillin'],
        'sulfa': ['sulfonamide', 'sulfamethoxazole', 'co-trimoxazole', 'bactrim', 'septrin'],
        'nsaid': ['ibuprofen', 'diclofenac', 'naproxen', 'aspirin', 'paracetamol', 'acetaminophen'],
        'cephalosporin': ['cephalexin', 'ceftriaxone', 'cefuroxime', 'cefixime'],
        'macrolide': ['erythromycin', 'azithromycin', 'clarithromycin'],
        'fluoroquinolone': ['ciprofloxacin', 'levofloxacin', 'ofloxacin'],
        'ACE inhibitor': ['lisinopril', 'enalapril', 'captopril', 'ramipril'],
    }
    
    for allergy_class, class_drugs in drug_class_keywords.items():
        for drug in class_drugs:
            if drug in medication_name_lower and allergy_class in patient_allergies:
                warnings.append({
                    "type": "allergy",
                    "severity": "high",
                    "message": f"Patient has {allergy_class} allergy - {medication_name} belongs to this class"
                })
    
    # Check current medications
    current_meds = (encounter.medications or "").lower()
    
    interaction_checks = [
        ('warfarin', ['aspirin', 'ibuprofen', 'nsaid', 'naproxen'], 'Increased bleeding risk'),
        ('metformin', ['contrast', 'alcohol'], 'Risk of lactic acidosis'),
        ('lisinopril', ['potassium', 'spironolactone'], 'Risk of hyperkalemia'),
        ('sildenafil', ['nitrate', 'nitroglycerin'], 'Dangerous blood pressure drop'),
        ('ciprofloxacin', ['tizanidine'], 'Dangerous blood pressure drop'),
        ('simvastatin', ['erythromycin', 'clarithromycin'], 'Risk of muscle toxicity'),
    ]
    
    for med, interactants, warning in interaction_checks:
        if med in medication_name_lower:
            for interactant in interactants:
                if interactant in current_meds:
                    warnings.append({
                        "type": "interaction",
                        "severity": "medium",
                        "message": f"Interaction: {medication_name} + {interactant} - {warning}"
                    })
    
    return {
        "encounter_id": encounter_id,
        "medication_name": medication_name,
        "has_warnings": len(warnings) > 0,
        "warnings": warnings,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/{encounter_id}/create-appointment", name="create_appointment_from_encounter")
def create_appointment_from_encounter(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"])),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    department: str = Form(...),
    appointment_type: str = Form("follow_up"),
    notes: Optional[str] = Form(None),
):
    """
    Create a follow-up appointment from an encounter (for doctors).
    This allows doctors to schedule return visits for patients.
    Returns JSON with appointment details on success.
    """
    from fastapi.responses import JSONResponse
    from app.models.scheduled_appointment_models import AppointmentType
    from app.services.sms_onlinegh_service import send_personalized_sms_notification
    
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Parse scheduled datetime
    scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
    scheduled_datetime = datetime.strptime(scheduled_datetime_str, "%Y-%m-%d %H:%M")
    
    # Create appointment
    appointment_data = AppointmentCreate(
        patient_id=encounter.patient_id,
        department=department,
        department_type="opd",
        appointment_type=AppointmentType(appointment_type),
        scheduled_date=scheduled_datetime,
        chief_complaint=f"Follow-up appointment",
        notes=notes or f"Follow-up appointment created by doctor from encounter {encounter_id}",
        priority=5,
        assigned_clinician_id=current_user.id,
        created_by_id=current_user.id
    )
    
    new_appointment = appointment_crud.create_appointment(db, appointment_data)
    
    # Send SMS notification to patient
    sms_sent = False
    try:
        patient = encounter.patient
        if patient and patient.phone_number:
            scheduled_date_str = scheduled_datetime.strftime("%Y-%m-%d at %H:%M")
            message_template = "Hello {$name}. Your follow-up appointment is scheduled for {$date} at {$department}. Please arrive on time. Thank you!"
            destinations = [{
                "number": patient.phone_number,
                "values": [
                    f"{patient.first_name} {patient.last_name}",
                    scheduled_date_str,
                    department
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
            sms_sent = True
    except Exception as sms_error:
        print(f"Warning: Unable to send appointment SMS: {sms_error}")
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "message": "Appointment created successfully",
            "appointment_id": new_appointment.id,
            "appointment_type": new_appointment.appointment_type.value if hasattr(new_appointment.appointment_type, 'value') else str(new_appointment.appointment_type),
            "scheduled_date": new_appointment.scheduled_date.isoformat() if new_appointment.scheduled_date else None,
            "department": new_appointment.department,
            "sms_sent": sms_sent
        }
    )


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


@router.get("/{encounter_id}/differentials", response_model=DifferentialResponse)
def get_saved_differentials(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Return saved Ghana STG differential data for an encounter."""
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    saved_payload = encounter_crud.load_differential_data(encounter)
    default_summary = (
        encounter.assessment
        or encounter.history_of_present_illness
        or encounter.chief_complaint
        or ""
    )
    if not saved_payload:
        return DifferentialResponse(
            clinical_summary=default_summary,
            generated_at=datetime.utcnow(),
            suggestions=[],
            notes=None
        )
    
    generated_at = saved_payload.get("generated_at")
    if isinstance(generated_at, str):
        try:
            generated_dt = datetime.fromisoformat(generated_at)
        except ValueError:
            generated_dt = datetime.utcnow()
    elif isinstance(generated_at, datetime):
        generated_dt = generated_at
    else:
        generated_dt = datetime.utcnow()
    
    suggestions = saved_payload.get("suggestions", [])
    return DifferentialResponse(
        clinical_summary=saved_payload.get("clinical_summary") or default_summary,
        generated_at=generated_dt,
        suggestions=suggestions,
        notes=saved_payload.get("notes")
    )


@router.post("/{encounter_id}/differentials/generate", response_model=DifferentialResponse)
def generate_differentials(
    encounter_id: int,
    payload: DifferentialInput,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Generate differential diagnoses mapped to the Ghana STG."""
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    summary = payload.clinical_summary.strip() if payload.clinical_summary else None
    if not summary:
        summary = (
            encounter.assessment
            or encounter.history_of_present_illness
            or encounter.chief_complaint
        )
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinical summary is required to generate differentials."
        )
    
    patient = encounter.patient
    resolved_age = payload.age if payload.age is not None else _calculate_age_years(getattr(patient, "date_of_birth", None))
    resolved_sex = payload.sex or (getattr(patient, "gender", None))
    
    suggestions = generate_differential_suggestions(
        clinical_summary=summary,
        age=resolved_age,
        sex=resolved_sex,
        key_vitals=payload.key_vitals,
        key_labs=payload.key_labs
    )
    
    saved_payload = encounter_crud.load_differential_data(encounter)
    if saved_payload:
        status_map = {
            (item.get("diagnosis") or "").lower(): item.get("status", "suggested")
            for item in saved_payload.get("suggestions", [])
        }
        for suggestion in suggestions:
            key = suggestion["diagnosis"].lower()
            if key in status_map:
                suggestion["status"] = status_map[key]
    
    generated_at = datetime.utcnow()
    return DifferentialResponse(
        clinical_summary=summary,
        generated_at=generated_at,
        suggestions=suggestions,
        notes=saved_payload.get("notes") if saved_payload else None
    )


@router.post("/{encounter_id}/differentials/save", response_model=DifferentialResponse)
def save_differentials(
    encounter_id: int,
    payload: DifferentialSaveRequest,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Persist clinician selections for differential diagnoses."""
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if not payload.suggestions:
        raise HTTPException(status_code=400, detail="At least one suggestion is required.")
    
    summary = payload.clinical_summary.strip() if payload.clinical_summary else (
        encounter.assessment
        or encounter.history_of_present_illness
        or encounter.chief_complaint
        or ""
    )
    timestamp = datetime.utcnow().isoformat()
    stored_payload = {
        "clinical_summary": summary,
        "generated_at": timestamp,
        "suggestions": [suggestion.model_dump() for suggestion in payload.suggestions],
        "notes": payload.notes
    }
    encounter_crud.save_differential_data(db, encounter_id, stored_payload)
    
    return DifferentialResponse(
        clinical_summary=summary,
        generated_at=datetime.fromisoformat(timestamp),
        suggestions=stored_payload["suggestions"],
        notes=payload.notes
    )


# Lab Order Endpoints
@router.post("/{encounter_id}/lab-orders", response_model=LabOrder, status_code=status.HTTP_201_CREATED, dependencies=[Depends(permission_required("lab_create"))])
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
    
    # lab_test_id is required - validate and get test details from Lab Test Catalog
    if not lab_order.lab_test_id:
        raise HTTPException(status_code=400, detail="lab_test_id is required. Select a test from the Lab Test Catalog.")
    
    from app.models.lab_catalog_models import LabTest
    lab_test = db.query(LabTest).filter(LabTest.id == lab_order.lab_test_id, LabTest.is_active == True).first()
    if not lab_test:
        raise HTTPException(status_code=400, detail="Selected lab test not found in catalog.")
    
    # Override with catalog details
    lab_order.test_name = lab_test.test_name
    lab_order.test_code = lab_order.test_code or lab_test.test_code
    
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
    
    # Auto-create sample for the lab order
    try:
        sample = create_sample_if_not_exists(db, new_order.id, current_user.id)
        if sample:
            print(f"Auto-created sample {sample.barcode} for lab order {new_order.id}")
    except Exception as sample_error:
        print(f"Warning: Unable to auto-create sample for order {new_order.id}: {sample_error}")
    
    return new_order


@router.post("/{encounter_id}/lab-orders/create", name="create_lab_order_form", status_code=status.HTTP_302_FOUND, dependencies=[Depends(permission_required("lab_create"))])
async def create_lab_order_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
):
    """Handle HTML form submission or JSON for creating a lab order."""
    # Support both form data and JSON body
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # Parse JSON body
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        
        # Support both lab_test_id (single) and test_ids (comma-separated)
        lab_test_ids = body.get("lab_test_id")
        if not lab_test_ids:
            test_ids_str = body.get("test_ids")
            if test_ids_str:
                lab_test_ids = [tid.strip() for tid in test_ids_str.split(",") if tid.strip()]
            else:
                lab_test_ids = []
        else:
            lab_test_ids = [str(lab_test_ids)]
        test_name = body.get("test_name")
        test_code = body.get("test_code")
        instructions = body.get("instructions")
        priority = body.get("priority", "routine")
    else:
        # Parse form data
        form_data = await request.form()
        # Support both lab_test_id (single) and test_ids (comma-separated)
        lab_test_ids = form_data.get("lab_test_id")
        if not lab_test_ids:
            test_ids_str = form_data.get("test_ids")
            if test_ids_str:
                lab_test_ids = [tid.strip() for tid in test_ids_str.split(",") if tid.strip()]
            else:
                lab_test_ids = []
        else:
            lab_test_ids = [str(lab_test_ids)]
        test_name = form_data.get("test_name")
        test_code = form_data.get("test_code")
        instructions = form_data.get("instructions")
        priority = form_data.get("priority", "routine")
    
    # Validate at least one test is selected
    if not lab_test_ids:
        raise HTTPException(status_code=422, detail="lab_test_id is required")
    
    # Convert to integers and validate
    try:
        lab_test_ids = [int(tid) for tid in lab_test_ids]
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid lab_test_id: must be an integer")
    try:
        # Verify encounter exists
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        # Get test details from Lab Test Catalog (required)
        from app.models.lab_catalog_models import LabTest
        
        # Create orders for all selected tests
        created_orders = []
        errors = []
        
        for lab_test_id in lab_test_ids:
            lab_test = db.query(LabTest).filter(LabTest.id == lab_test_id, LabTest.is_active == True).first()
            if not lab_test:
                errors.append(f"Invalid lab test ID: {lab_test_id}")
                continue
            
            resolved_test_name = lab_test.test_name
            resolved_test_code = lab_test.test_code

            if not resolved_test_name:
                errors.append(f"Lab test name is required for ID: {lab_test_id}")
                continue

            # Create lab order data
            lab_order_data = LabOrderCreate(
                encounter_id=encounter_id,
                patient_id=encounter.patient_id,  # Set patient_id from encounter
                ordered_by_id=current_user.id,
                test_name=resolved_test_name,
                test_code=resolved_test_code if resolved_test_code else None,
                lab_test_id=lab_test.id,
                instructions=instructions if instructions else None,
                priority=priority,
                is_walk_in=False
            )
            
            # Create lab order
            new_order = encounter_crud.create_lab_order(db, lab_order_data)
            created_orders.append(new_order.id)
            
            try:
                create_charge_for_lab_order(db, new_order, current_user.id)
            except Exception as billing_error:
                print(f"Warning: Unable to create lab charge for order {new_order.id}: {billing_error}")
            
            # Auto-create sample for the lab order
            try:
                sample = create_sample_if_not_exists(db, new_order.id, current_user.id)
                if sample:
                    print(f"Auto-created sample {sample.barcode} for lab order {new_order.id}")
            except Exception as sample_error:
                print(f"Warning: Unable to auto-create sample for order {new_order.id}: {sample_error}")
        
        # Check if any orders were created
        if not created_orders:
            error_msg = errors[0] if errors else "No valid lab tests selected"
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Build response message
        if len(created_orders) == 1:
            message = "Lab order added."
        else:
            message = f"{len(created_orders)} lab orders added."
        
        # AJAX (e.g. from IPD admission modal): return JSON so page can reload instead of redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse(
                status_code=201,
                content={"success": True, "message": message, "order_ids": created_orders}
            )
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=lab_order_added",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": str(e)}
            )
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
@router.post("/{encounter_id}/radiology-orders", response_model=RadiologyOrder, status_code=status.HTTP_201_CREATED, dependencies=[Depends(permission_required("radiology_create"))])
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


@router.post("/{encounter_id}/radiology-orders/create", name="create_radiology_order_form", status_code=status.HTTP_302_FOUND, dependencies=[Depends(permission_required("radiology_create"))])
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
        
        # AJAX (e.g. from IPD admission modal): return JSON so page can reload instead of redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse(
                status_code=201,
                content={"success": True, "message": "Radiology order added.", "order_id": new_order.id}
            )
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?status=radiology_order_added",
            status_code=status.HTTP_302_FOUND
        )
    except HTTPException:
        raise
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": str(e)}
            )
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
@router.post("/{encounter_id}/prescriptions", response_model=Prescription, status_code=status.HTTP_201_CREATED, dependencies=[Depends(permission_required("pharmacy_dispense"))])
def create_prescription_endpoint(
    encounter_id: int,
    prescription: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Create a new prescription for an encounter (JSON API)."""
    from uuid import UUID
    from datetime import date
    from fastapi.responses import JSONResponse
    
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # STOCK CHECK: Verify medication is available in pharmacy inventory
    stock_warning = None
    pharmacy_drug_uuid = None
    
    # Ghana: Require pharmacy_drug_id - must select a specific formulation
    if prescription.pharmacy_drug_id:
        try:
            pharmacy_drug_uuid = UUID(prescription.pharmacy_drug_id)
            
            # Fetch pharmacy drug for snapshot fields
            from app.models.pharmacy_models import PharmacyDrug, PharmacyBatch, PharmacyStore
            from sqlalchemy.orm import joinedload
            drug = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
                PharmacyDrug.id == pharmacy_drug_uuid, PharmacyDrug.is_active == True
            ).first()
            if drug:
                # Build medication name from drug components if not provided
                if not prescription.medication_name:
                    # Handle Decimal types from database properly
                    strength_val = float(drug.strength_value) if drug.strength_value else None
                    conc_val = float(drug.concentration_value) if drug.concentration_value else None
                    
                    strength = f"{strength_val} {drug.strength_unit or ''}" if strength_val else ""
                    if conc_val:
                        strength = f"{conc_val} {drug.concentration_unit or ''}"
                    prescription.medication_name = f"{drug.generic_name} {strength} {drug.dosage_form.name if drug.dosage_form else ''}".strip()
                
                # Capture snapshot fields for when drug is deleted
                prescription.dosage_form_name = drug.dosage_form.name if drug.dosage_form else None
                try:
                    prescription.strength_value = float(drug.strength_value) if drug.strength_value else None
                except (TypeError, ValueError):
                    prescription.strength_value = None
                prescription.strength_unit = drug.strength_unit
                prescription.route = drug.route
                try:
                    prescription.concentration_value = float(drug.concentration_value) if drug.concentration_value else None
                except (TypeError, ValueError):
                    prescription.concentration_value = None
                prescription.concentration_unit = drug.concentration_unit
                
                # Check stock availability
                store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
                if store:
                    batches = db.query(PharmacyBatch).filter(
                        PharmacyBatch.store_id == store.id,
                        PharmacyBatch.drug_id == pharmacy_drug_uuid,
                        PharmacyBatch.status == "ACTIVE",
                        PharmacyBatch.expiry_date >= date.today(),
                    ).all()
                    
                    required_qty = prescription.quantity if prescription.quantity else 1
                    total_available = sum(b.qty_on_hand - b.qty_reserved for b in batches if (b.qty_on_hand - b.qty_reserved) > 0)
                    
                    if total_available == 0:
                        stock_warning = {
                            "message": f"WARNING: {prescription.medication_name} is currently OUT OF STOCK.",
                            "available_quantity": 0,
                            "requested_quantity": required_qty,
                            "is_out_of_stock": True
                        }
                    elif total_available < required_qty:
                        stock_warning = {
                            "message": f"WARNING: Insufficient stock. Requested: {required_qty}, Available: {total_available}",
                            "available_quantity": total_available,
                            "requested_quantity": required_qty,
                            "is_out_of_stock": False,
                            "is_partial": True
                        }
        except (ValueError, TypeError):
            pass  # Invalid UUID, ignore
    
    # Override encounter_id and prescribed_by_id
    prescription.encounter_id = encounter_id
    prescription.prescribed_by_id = current_user.id
    
    # Create prescription
    created_prescription = encounter_crud.create_prescription(db, prescription)
    
    # Automatically create charge for the prescription (so patient can see bill immediately)
    # SKIP billing if medication is out of stock or has insufficient stock
    try:
        from app.services import create_charge_for_prescription
        skip_billing = False
        if stock_warning:
            if stock_warning.get("is_out_of_stock") or stock_warning.get("is_partial"):
                skip_billing = True
        
        if not skip_billing:
            create_charge_for_prescription(db, created_prescription, current_user.id, check_payment_required=True)
        else:
            print(f"Note: Skipping charge for prescription {created_prescription.id} - out of stock/insufficient stock")
    except Exception as e:
        print(f"Note: Could not create charge for prescription {created_prescription.id}: {e}")
    
    # Build response
    response_data = {
        "id": created_prescription.id,
        "medication_name": created_prescription.medication_name,
        "dosage": created_prescription.dosage,
        "frequency": created_prescription.frequency,
        "duration": created_prescription.duration,
        "quantity": created_prescription.quantity,
        "instructions": created_prescription.instructions,
        "status": created_prescription.status.value,
        "prescribed_at": created_prescription.prescribed_at.isoformat() if created_prescription.prescribed_at else None
    }
    
    # Include stock warning in response (but still return success)
    if stock_warning:
        response_data["stock_warning"] = stock_warning
    
    return JSONResponse(content=response_data, status_code=201)


@router.post("/{encounter_id}/prescriptions/create", name="create_prescription_form", status_code=status.HTTP_201_CREATED, dependencies=[Depends(permission_required("pharmacy_dispense"))])
def create_prescription_form(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"])),
    medication_id: Optional[str] = Form(None),
    pharmacy_drug_id: Optional[str] = Form(None),
    medication_name: str = Form(...),
    medication_code: Optional[str] = Form(None),
    dosage: str = Form(...),
    frequency: str = Form(...),
    duration: str = Form(...),
    quantity: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
):
    """Handle HTML form submission for creating a prescription. Ghana: requires pharmacy_drug_id (formulation selection)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Creating prescription for encounter {encounter_id}, user {current_user.id}")
        logger.info(f"Form data: medication_name={medication_name}, pharmacy_drug_id={pharmacy_drug_id}, dosage={dosage}, frequency={frequency}, duration={duration}")
        
        # Verify encounter exists
        encounter = encounter_crud.get_encounter(db, encounter_id)
        logger.info(f"Encounter found: {encounter is not None}")
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        # Ghana: Require pharmacy_drug_id - doctor MUST select a specific formulation
        pharmacy_drug_uuid = None
        if pharmacy_drug_id and pharmacy_drug_id.strip():
            try:
                from uuid import UUID
                pharmacy_drug_uuid = UUID(pharmacy_drug_id.strip())
            except (ValueError, TypeError):
                pass
        if not pharmacy_drug_uuid:
            raise HTTPException(status_code=422, detail="Please select a medication from the formulary (specific formulation with strength and dosage form). Free text is not allowed.")
        
        # Convert medication_id from string to int, handling empty strings (legacy)
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
        
        # Fetch pharmacy drug for name/code and snapshot fields (Ghana formulation)
        medication_name_final = medication_name.strip()
        medication_code_final = medication_code.strip() if medication_code else None
        
        # Initialize stock warnings
        stock_warnings = []
        
        # Snapshot fields from pharmacy_drug
        dosage_form_name_final = None
        strength_value_final = None
        strength_unit_final = None
        route_final = None
        concentration_value_final = None
        concentration_unit_final = None
        
        if pharmacy_drug_uuid:
            from app.models.pharmacy_models import PharmacyDrug, PharmacyBatch
            from sqlalchemy.orm import joinedload
            drug = db.query(PharmacyDrug).options(joinedload(PharmacyDrug.dosage_form)).filter(
                PharmacyDrug.id == pharmacy_drug_uuid, PharmacyDrug.is_active == True
            ).first()
            if drug:
                # Build medication name from drug components
                # Handle Decimal types from database properly
                strength_val = float(drug.strength_value) if drug.strength_value else None
                conc_val = float(drug.concentration_value) if drug.concentration_value else None
                
                strength = f"{strength_val} {drug.strength_unit or ''}" if strength_val else ""
                if conc_val:
                    strength = f"{conc_val} {drug.concentration_unit or ''}"
                medication_name_final = f"{drug.generic_name} {strength} {drug.dosage_form.name if drug.dosage_form else ''}".strip()
                medication_code_final = drug.item_code or medication_code_final
                
                # Capture snapshot fields for when drug is deleted
                dosage_form_name_final = drug.dosage_form.name if drug.dosage_form else None
                try:
                    strength_value_final = float(drug.strength_value) if drug.strength_value else None
                except (TypeError, ValueError):
                    strength_value_final = None
                strength_unit_final = drug.strength_unit
                route_final = drug.route
                try:
                    concentration_value_final = float(drug.concentration_value) if drug.concentration_value else None
                except (TypeError, ValueError):
                    concentration_value_final = None
                concentration_unit_final = drug.concentration_unit
                
                # STOCK CHECK: Verify medication is available in pharmacy inventory
                required_qty = quantity_int if quantity_int else 1
                
                # Get active pharmacy store
                from app.models.pharmacy_models import PharmacyStore
                store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
                
                if store:
                    # Check available batches for this drug using FEFO logic
                    from datetime import date
                    batches = db.query(PharmacyBatch).filter(
                        PharmacyBatch.store_id == store.id,
                        PharmacyBatch.drug_id == pharmacy_drug_uuid,
                        PharmacyBatch.status == "ACTIVE",
                        PharmacyBatch.expiry_date >= date.today(),
                    ).all()
                    
                    total_available = sum(b.qty_on_hand - b.qty_reserved for b in batches if (b.qty_on_hand - b.qty_reserved) > 0)
                    
                    if total_available == 0:
                        stock_warnings.append({
                            "message": f"{medication_name_final} is currently OUT OF STOCK. Patient will need to obtain from another pharmacy.",
                            "is_out_of_stock": True,
                            "available_quantity": 0,
                            "requested_quantity": required_qty
                        })
                    elif total_available < required_qty:
                        stock_warnings.append({
                            "message": f"{medication_name_final} has insufficient stock. Requested: {required_qty}, Available: {total_available}. Partial fill only.",
                            "is_out_of_stock": False,
                            "is_partial": True,
                            "available_quantity": total_available,
                            "requested_quantity": required_qty
                        })
        elif medication_id_int:
            from app.crud import inventory_crud
            medication = inventory_crud.get_medication(db, medication_id_int)
            if medication:
                medication_name_final = medication.name
                medication_code_final = medication.medication_code or medication_code_final
        
        # Drug-Allergy Interaction Check
        allergy_warnings = []
        
        # Get patient allergies from encounter
        patient_allergies = encounter.allergies or ""
        patient_allergies_lower = patient_allergies.lower()
        
        # Check against known drug classes (simplified - in production, use a drug interaction database)
        # Common drug class prefixes to check
        drug_class_keywords = {
            'penicillin': ['penicillin', 'amoxicillin', 'ampicillin', 'amoxil', 'cloxacillin'],
            'sulfa': ['sulfonamide', 'sulfamethoxazole', 'co-trimoxazole', 'bactrim', 'septrin'],
            'nsaid': ['ibuprofen', 'diclofenac', 'naproxen', 'aspirin', 'paracetamol', 'acetaminophen'],
            'cephalosporin': ['cephalexin', 'ceftriaxone', 'cefuroxime', 'cefixime'],
            'macrolide': ['erythromycin', 'azithromycin', 'clarithromycin'],
            'fluoroquinolone': ['ciprofloxacin', 'levofloxacin', 'ofloxacin'],
            'ACE inhibitor': ['lisinopril', 'enalapril', 'captopril', 'ramipril'],
        }
        
        medication_name_lower = medication_name_final.lower()
        
        # Check if medication matches any known drug class
        for allergy_class, class_drugs in drug_class_keywords.items():
            for drug in class_drugs:
                if drug in medication_name_lower:
                    # Check if patient has this allergy recorded
                    if allergy_class in patient_allergies_lower:
                        allergy_warnings.append(f"Warning: Patient is allergic to {allergy_class} drugs (e.g., {drug})")
        
        # Check current medications for potential interactions
        current_meds = encounter.medications or ""
        current_meds_lower = current_meds.lower()
        
        # Simple drug interaction checks
        interaction_checks = [
            ('warfarin', ['aspirin', 'ibuprofen', 'nsaid'], 'Increased bleeding risk'),
            ('metformin', ['contrast'], 'Risk of lactic acidosis with contrast'),
            ('lisinopril', ['potassium'], 'Risk of hyperkalemia'),
            ('sildenafil', ['nitrate'], 'Dangerous blood pressure drop'),
        ]
        
        for med, interactants, warning in interaction_checks:
            if med in medication_name_lower:
                for interactant in interactants:
                    if interactant in current_meds_lower:
                        allergy_warnings.append(f"Potential interaction: {medication_name_final} + {interactant} - {warning}")
        
        # If there are allergy warnings, return them for clinician review
        if allergy_warnings:
            # Return warnings but still allow prescription (clinician override)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "warning": True,
                        "messages": allergy_warnings,
                        "prescription": None
                    }
                )
            else:
                # For form submission, add warning to session and continue
                from fastapi import Request
                # Warnings will be shown after creation
        
        # Create prescription data
        prescription_data = PrescriptionCreate(
            encounter_id=encounter_id,
            prescribed_by_id=current_user.id,
            medication_id=medication_id_int,
            pharmacy_drug_id=str(pharmacy_drug_uuid),
            medication_name=medication_name_final,
            medication_code=medication_code_final if medication_code_final else None,
            dosage_form_name=dosage_form_name_final,
            strength_value=strength_value_final,
            strength_unit=strength_unit_final,
            route=route_final,
            concentration_value=concentration_value_final,
            concentration_unit=concentration_unit_final,
            dosage=dosage.strip(),
            frequency=frequency.strip(),
            duration=duration.strip(),
            quantity=quantity_int,
            instructions=instructions.strip() if instructions else None,
        )
        
        # Create prescription
        logger.info("Creating prescription in database...")
        prescription = encounter_crud.create_prescription(db, prescription_data)
        logger.info(f"Prescription created with ID: {prescription.id}")
        
        # Automatically create charge for the prescription (so patient can see bill immediately)
        # SKIP billing if medication is out of stock or has insufficient stock
        try:
            from app.services import create_charge_for_prescription
            # Check if there's a stock warning before creating charge
            skip_billing = False
            if stock_warnings:
                for sw in stock_warnings:
                    if sw.get("is_out_of_stock"):
                        skip_billing = True
                        break
                    if sw.get("is_partial"):
                        # Also skip billing for insufficient stock (can't fulfill full quantity)
                        skip_billing = True
                        break
            
            if not skip_billing:
                # Create charge with check_payment_required=True to properly handle OPD vs IPD
                # For OPD cash: requires payment before dispense
                # For IPD cash: payment deferred to discharge
                # For NHIS: accumulate for claims
                create_charge_for_prescription(db, prescription, current_user.id, check_payment_required=True)
            else:
                print(f"Note: Skipping charge creation for prescription {prescription.id} due to stock issues")
        except Exception as e:
            # Log error but don't fail prescription creation if charge creation fails
            # This could happen if medication pricing is not set up
            print(f"Note: Could not create charge for prescription {prescription.id}: {e}")
        
        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            from fastapi.responses import JSONResponse
            
            # Get stock info for response - ALWAYS show available quantity
            stock_info = {"available_quantity": 0, "is_out_of_stock": False}
            if pharmacy_drug_uuid:
                from app.models.pharmacy_models import PharmacyBatch, PharmacyStore
                from datetime import date
                store = db.query(PharmacyStore).filter(PharmacyStore.is_active == True).first()
                if store:
                    batches = db.query(PharmacyBatch).filter(
                        PharmacyBatch.store_id == store.id,
                        PharmacyBatch.drug_id == pharmacy_drug_uuid,
                        PharmacyBatch.status == "ACTIVE",
                        PharmacyBatch.expiry_date >= date.today(),
                    ).all()
                    total_available = sum(float(b.qty_on_hand or 0) - float(b.qty_reserved or 0) for b in batches if (float(b.qty_on_hand or 0) - float(b.qty_reserved or 0)) > 0)
                    stock_info = {
                        "available_quantity": total_available, 
                        "is_out_of_stock": total_available == 0,
                        "has_stock": total_available > 0
                    }
            
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
                    },
                    "stock_info": stock_info,
                    "stock_warnings": stock_warnings if stock_warnings else None
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
        logger.error(f"Error creating prescription: {str(e)}", exc_info=True)
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
    procedure_catalog_id: Optional[int] = Form(None),
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
            procedure_catalog_id=procedure_catalog_id,  # Link to procedure catalog
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
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    from app.models.encounter_models import Prescription as PrescriptionModel
    
    # Get prescription to access encounter and patient
    prescription = db.query(PrescriptionModel).filter(PrescriptionModel.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # If marking as dispensed (COMPLETED), verify payment for cash patients
    if prescription_update.status == OrderStatus.COMPLETED:
        # Get patient from encounter
        encounter = prescription.encounter
        patient_id = encounter.patient_id
        
        # Create charge first (if it doesn't exist) for all patients
        # This ensures the charge exists before we check payment
        from app.services import create_charge_for_prescription
        try:
            # Create charge if it doesn't exist (function returns None if charge already exists)
            create_charge_for_prescription(db, prescription, current_user.id, check_payment_required=False)
        except Exception as e:
            # Log error but continue - charge might already exist
            print(f"Note: Charge creation for prescription {prescription_id}: {e}")
        
        # Check payment requirement for cash patients (pharmacy fee)
        # Payment must be made before dispensing for cash patients
        if is_cash_patient(db, patient_id):
            payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
                db, patient_id, ChargeType.PHARMACY,
                encounter_id=encounter.id, prescription_id=prescription_id
            )
            
            if payment_required and not payment_paid:
                # Block dispensing - payment required
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payment required before dispensing. Please process payment for this prescription first. Invoice ID: {invoice.id if invoice else 'N/A'}, Balance: {invoice.balance if invoice else 'N/A'}"
                )
        
        # If marking as dispensed, set dispensed_by_id
        if not prescription_update.dispensed_by_id:
            prescription_update.dispensed_by_id = current_user.id
            prescription_update.dispensed_at = datetime.now()
    
    updated_prescription = encounter_crud.update_prescription(db, prescription_id, prescription_update)
    if not updated_prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return updated_prescription


# Delete Routes for Services
@router.delete("/lab-orders/{lab_order_id}", status_code=status.HTTP_200_OK)
def delete_lab_order(
    lab_order_id: int,
    encounter_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Delete a lab order. Only pending/in_progress orders can be deleted."""
    lab_order = encounter_crud.get_lab_order(db, lab_order_id)
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Verify it belongs to the encounter
    if lab_order.encounter_id != encounter_id:
        raise HTTPException(status_code=400, detail="Lab order does not belong to this encounter")
    
    # Only allow deletion of pending or in_progress orders
    if lab_order.status.value in [OrderStatus.COMPLETED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete completed lab orders. Only pending or in-progress orders can be removed."
        )
    
    # Check for associated charges and handle them
    from app.models.billing_models import Charge, Invoice, InvoiceStatus
    associated_charges = db.query(Charge).filter(Charge.lab_order_id == lab_order_id).all()
    
    if associated_charges:
        # Check if any invoice is paid - if so, prevent deletion
        for charge in associated_charges:
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice and invoice.status == InvoiceStatus.PAID:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete lab order. Associated charges have been paid. Please contact Finance department."
                )
        
        # Delete all associated charges (this will update invoice totals)
        from app.crud import billing_crud
        for charge in associated_charges:
            billing_crud.delete_charge(db, charge.id)
    
    # Delete associated lab samples first (required because of NOT NULL constraint on lab_order_id)
    from app.models.lab_models import LabSample
    associated_samples = db.query(LabSample).filter(LabSample.lab_order_id == lab_order_id).all()
    for sample in associated_samples:
        db.delete(sample)
    
    # Delete the lab order
    db.delete(lab_order)
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Lab order deleted successfully", "lab_order_id": lab_order_id}
    )


@router.delete("/radiology-orders/{radiology_order_id}", status_code=status.HTTP_200_OK)
def delete_radiology_order(
    radiology_order_id: int,
    encounter_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Delete a radiology order. Only pending/in_progress orders can be deleted."""
    radiology_order = db.query(RadiologyOrderModel).filter(RadiologyOrderModel.id == radiology_order_id).first()
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    # Verify it belongs to the encounter
    if radiology_order.encounter_id != encounter_id:
        raise HTTPException(status_code=400, detail="Radiology order does not belong to this encounter")
    
    # Only allow deletion of pending or in_progress orders
    if radiology_order.status.value in [OrderStatus.COMPLETED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete completed radiology orders. Only pending or in-progress orders can be removed."
        )
    
    # Check for associated charges and handle them
    from app.models.billing_models import Charge, Invoice, InvoiceStatus
    associated_charges = db.query(Charge).filter(Charge.radiology_order_id == radiology_order_id).all()
    
    if associated_charges:
        # Check if any invoice is paid - if so, prevent deletion
        for charge in associated_charges:
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice and invoice.status == InvoiceStatus.PAID:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete radiology order. Associated charges have been paid. Please contact Finance department."
                )
        
        # Delete all associated charges (this will update invoice totals)
        from app.crud import billing_crud
        for charge in associated_charges:
            billing_crud.delete_charge(db, charge.id)
    
    # Delete the radiology order
    db.delete(radiology_order)
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Radiology order deleted successfully", "radiology_order_id": radiology_order_id}
    )


@router.delete("/prescriptions/{prescription_id}", status_code=status.HTTP_200_OK)
def delete_prescription(
    prescription_id: int,
    encounter_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Delete a prescription. Only pending/in_progress prescriptions can be deleted."""
    from app.models.encounter_models import Prescription as PrescriptionModel
    
    prescription = db.query(PrescriptionModel).filter(PrescriptionModel.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Verify it belongs to the encounter
    if prescription.encounter_id != encounter_id:
        raise HTTPException(status_code=400, detail="Prescription does not belong to this encounter")
    
    # Only allow deletion of pending or in_progress prescriptions
    if prescription.status.value in [OrderStatus.COMPLETED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete completed prescriptions. Only pending or in-progress prescriptions can be removed."
        )
    
    # Check for associated charges and handle them
    from app.models.billing_models import Charge, Invoice, InvoiceStatus
    associated_charges = db.query(Charge).filter(Charge.prescription_id == prescription_id).all()
    
    if associated_charges:
        # Check if any invoice is paid - if so, prevent deletion
        for charge in associated_charges:
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice and invoice.status == InvoiceStatus.PAID:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete prescription. Associated charges have been paid. Please contact Finance department."
                )
        
        # Delete all associated charges (this will update invoice totals)
        from app.crud import billing_crud
        for charge in associated_charges:
            billing_crud.delete_charge(db, charge.id)
    
    # Delete the prescription
    db.delete(prescription)
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Prescription deleted successfully", "prescription_id": prescription_id}
    )


@router.delete("/procedures/{procedure_id}", status_code=status.HTTP_200_OK)
def delete_procedure(
    procedure_id: int,
    encounter_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Delete a procedure. Only pending/in_progress procedures can be deleted."""
    from app.models.procedure_models import Procedure as ProcedureModel
    
    procedure = db.query(ProcedureModel).filter(ProcedureModel.id == procedure_id).first()
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")
    
    # Verify it belongs to the encounter
    if procedure.encounter_id != encounter_id:
        raise HTTPException(status_code=400, detail="Procedure does not belong to this encounter")
    
    # Only allow deletion of pending or in_progress procedures
    if procedure.status.value in [ProcedureStatus.COMPLETED.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete completed procedures. Only pending or in-progress procedures can be removed."
        )
    
    # Check for associated charges and handle them
    # Procedures might have charges linked by description pattern
    from app.models.billing_models import Charge, Invoice, InvoiceStatus, ChargeType
    from sqlalchemy import or_
    
    # Look for charges that match this procedure (by description pattern or encounter)
    associated_charges = db.query(Charge).filter(
        Charge.charge_type == ChargeType.PROCEDURE,
        Charge.encounter_id == encounter_id,
        or_(
            Charge.description.like(f"Procedure #{procedure_id}%"),
            Charge.description.like(f"%{procedure.procedure_name}%")
        )
    ).all()
    
    if associated_charges:
        # Check if any invoice is paid - if so, prevent deletion
        for charge in associated_charges:
            invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
            if invoice and invoice.status == InvoiceStatus.PAID:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete procedure. Associated charges have been paid. Please contact Finance department."
                )
        
        # Delete all associated charges (this will update invoice totals)
        from app.crud import billing_crud
        for charge in associated_charges:
            billing_crud.delete_charge(db, charge.id)
    
    # Delete the procedure
    db.delete(procedure)
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Procedure deleted successfully", "procedure_id": procedure_id}
    )


@router.delete("/antenatal-charges/{charge_id}", status_code=status.HTTP_200_OK)
def delete_antenatal_charge(
    charge_id: int,
    encounter_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Clinician", "Admin"]))
):
    """Delete an antenatal charge."""
    from app.models.billing_models import Charge
    
    charge = db.query(Charge).filter(Charge.id == charge_id).first()
    if not charge:
        raise HTTPException(status_code=404, detail="Antenatal charge not found")
    
    # Verify it's an antenatal charge and belongs to the encounter
    if charge.charge_type != ChargeType.ANTENATAL:
        raise HTTPException(status_code=400, detail="This is not an antenatal charge")
    
    # Check if charge is linked to encounter via invoice
    if charge.invoice and charge.invoice.encounter_id != encounter_id:
        raise HTTPException(status_code=400, detail="Charge does not belong to this encounter")
    
    # Check if invoice is paid - don't allow deletion of paid charges
    if charge.invoice and charge.invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete charges from paid invoices. Please contact Finance department."
        )
    
    # Delete the charge and update invoice totals
    invoice = charge.invoice
    if invoice:
        # Update invoice totals
        invoice.subtotal -= (charge.unit_price * charge.quantity - charge.discount)
        invoice.tax_amount -= charge.tax_amount
        invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.tax_amount
        invoice.balance = invoice.total_amount - invoice.paid_amount
    
    db.delete(charge)
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={"message": "Antenatal charge deleted successfully", "charge_id": charge_id}
    )


# Addendum Endpoints
@router.post("/{encounter_id}/addendums", response_model=Addendum, status_code=status.HTTP_201_CREATED)
def create_addendum_endpoint(
    encounter_id: int,
    addendum: AddendumCreate,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Doctor", "Nurse", "Clinician", "Admin"]))
):
    """Create a new addendum for an encounter."""
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Create the addendum
    created_addendum = encounter_crud.create_addendum(db, addendum, encounter_id, current_user.id)
    return created_addendum


@router.get("/{encounter_id}/addendums", response_model=List[Addendum])
def get_encounter_addendums(
    encounter_id: int,
    db: Session = Depends(get_db)
):
    """Get all addendums for an encounter."""
    # Verify encounter exists
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    return encounter_crud.get_addendums_by_encounter(db, encounter_id)


# Auto-Close Endpoints
@router.post("/auto-close", name="auto_close_encounters")
def auto_close_encounters(
    db: Session = Depends(get_db),
    current_user = Depends(permission_required("encounter_edit"))
):
    """
    Manually trigger the auto-close of stale encounters.
    
    This endpoint will close all OPD encounters that have been in progress
    for more than 24 hours and have no pending lab or radiology orders.
    
    Requires encounter_edit permission.
    """
    from app.services.encounter_auto_close_service import auto_close_stale_encounters
    
    result = auto_close_stale_encounters(db)
    return result


@router.get("/auto-close/preview", name="preview_stale_encounters")
def preview_stale_encounters(
    db: Session = Depends(get_db),
    current_user = Depends(permission_required("encounter_view"))
):
    """
    Preview which encounters would be closed without actually closing them.
    
    This is useful for admins to review before running the auto-close.
    
    Requires encounter_view permission.
    """
    from app.services.encounter_auto_close_service import get_stale_encounters_preview
    
    result = get_stale_encounters_preview(db)
    return result
