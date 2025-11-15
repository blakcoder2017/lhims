from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.encounter_models import LabOrder, RadiologyOrder, Prescription, OrderStatus, Encounter
from app.models.patient_models import Patient
from app.crud import encounter_crud
from app.schemas.encounter_schemas import LabOrderUpdate, RadiologyOrderUpdate, PrescriptionUpdate

router = APIRouter(tags=["Ancillary Services"])
templates = Jinja2Templates(directory="app/templates")


# Laboratory Information System (LIS) Routes
@router.get("/lab", name="lab_dashboard")
def lab_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor", "Nurse", "Clinician"])),
    status_filter: Optional[str] = Query(None, description="Filter by order status")
):
    """
    Laboratory dashboard showing pending and completed lab orders.
    """
    # Query for lab orders
    query = db.query(LabOrder).options(
        joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabOrder.ordered_by),
        joinedload(LabOrder.result_entered_by)
    )
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(LabOrder.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show pending and in_progress orders
        query = query.filter(
            LabOrder.status.in_([OrderStatus.PENDING.value, OrderStatus.IN_PROGRESS.value])
        )
    
    lab_orders = query.order_by(LabOrder.ordered_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Laboratory (LIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "lab_orders": lab_orders,
        "status_filter": status_filter
    }
    return templates.TemplateResponse("ancillary/lab_dashboard.html", context)


@router.get("/lab/orders/{order_id}", name="view_lab_order")
def view_lab_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor", "Nurse", "Clinician"]))
):
    """
    View a specific lab order and enter results.
    """
    from app.models.lab_models import LabSample
    
    lab_order = db.query(LabOrder).options(
        joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabOrder.ordered_by),
        joinedload(LabOrder.result_entered_by),
        joinedload(LabOrder.samples)
    ).filter(LabOrder.id == order_id).first()
    
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Get samples for this order
    samples = db.query(LabSample).filter(
        LabSample.lab_order_id == order_id,
        LabSample.is_active == True
    ).all()
    
    context = {
        "request": request,
        "title": f"Lab Order #{order_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "lab_order": lab_order,
        "patient": lab_order.encounter.patient,
        "samples": samples
    }
    return templates.TemplateResponse("ancillary/lab_order_detail.html", context)


@router.post("/lab/orders/{order_id}/enter-result", name="enter_lab_result", status_code=status.HTTP_302_FOUND)
def enter_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    result: str = Form(...)
):
    """
    Enter lab test results.
    For cash patients: Checks if payment has been made before allowing result entry.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Get patient from encounter
    encounter = lab_order.encounter
    patient_id = encounter.patient_id
    
    # Check payment requirement for cash patients (lab test fee)
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.LAB_TEST, 
            encounter_id=encounter.id, lab_order_id=order_id
        )
        
        if payment_required and not payment_paid:
            # Redirect to payment page
            return RedirectResponse(
                url=f"/patients/{patient_id}/pay/lab?order_id={order_id}&return_to=lab/orders/{order_id}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Update lab order with result
    update_data = {
        "result": result,
        "result_entered_by_id": current_user.id,
        "result_entered_at": datetime.now(),
        "status": OrderStatus.COMPLETED.value,
        "completed_at": datetime.now()
    }
    
    # Validate result before saving
    validation_status = None
    try:
        from app.services import validate_lab_result
        validation = validate_lab_result(db, lab_order, result)
        validation_status = validation.status
        
        # Add validation warnings to result if any
        if validation.warnings:
            result = f"{result}\n\n[Validation Notes: {', '.join(validation.warnings)}]"
    except Exception as e:
        # Log validation error but continue
        print(f"Error validating lab result {order_id}: {e}")
    
    lab_order_update = LabOrderUpdate(**update_data)
    updated_lab_order = encounter_crud.update_lab_order(db, order_id, lab_order_update)
    
    # Automatically create charge when lab order is completed
    if updated_lab_order and updated_lab_order.status == OrderStatus.COMPLETED.value:
        try:
            from app.services import create_charge_for_lab_order
            create_charge_for_lab_order(db, updated_lab_order, current_user.id)
        except Exception as e:
            # Log error but don't fail the request
            # In production, use proper logging
            print(f"Error creating charge for lab order {order_id}: {e}")
    
    # Redirect with validation status
    redirect_url = f"/lab/orders/{order_id}?status=result_entered"
    if validation_status and validation_status in ["critical", "abnormal"]:
        redirect_url += f"&validation={validation_status}"
    
    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_302_FOUND
    )


# Radiology Information System (RIS) Routes
@router.get("/radiology", name="radiology_dashboard")
def radiology_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"])),  # Radiology accessible to Admin, Clinicians, and Radiology Staff
    status_filter: Optional[str] = Query(None, description="Filter by order status")
):
    """
    Radiology dashboard showing pending and completed radiology orders.
    """
    # Query for radiology orders
    query = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient),
        joinedload(RadiologyOrder.ordered_by),
        joinedload(RadiologyOrder.report_entered_by)
    )
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(RadiologyOrder.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show pending and in_progress orders
        query = query.filter(
            RadiologyOrder.status.in_([OrderStatus.PENDING.value, OrderStatus.IN_PROGRESS.value])
        )
    
    radiology_orders = query.order_by(RadiologyOrder.ordered_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Radiology (RIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_orders": radiology_orders,
        "status_filter": status_filter
    }
    return templates.TemplateResponse("ancillary/radiology_dashboard.html", context)


@router.get("/radiology/orders/{order_id}", name="view_radiology_order")
def view_radiology_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"]))
):
    """
    View a specific radiology order and enter report.
    """
    radiology_order = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient),
        joinedload(RadiologyOrder.ordered_by),
        joinedload(RadiologyOrder.report_entered_by),
        joinedload(RadiologyOrder.images)
    ).filter(RadiologyOrder.id == order_id).first()
    
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    context = {
        "request": request,
        "title": f"Radiology Order #{order_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_order": radiology_order,
        "patient": radiology_order.encounter.patient
    }
    return templates.TemplateResponse("ancillary/radiology_order_detail.html", context)


@router.post("/radiology/orders/{order_id}/enter-report", name="enter_radiology_report", status_code=status.HTTP_302_FOUND)
def enter_radiology_report(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"])),
    report: str = Form(...)
):
    """
    Enter radiology report.
    For cash patients: Checks if payment has been made before allowing report entry.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    
    radiology_order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    # Get patient from encounter
    encounter = radiology_order.encounter
    patient_id = encounter.patient_id
    
    # Check payment requirement for cash patients (radiology fee)
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.RADIOLOGY,
            encounter_id=encounter.id, radiology_order_id=order_id
        )
        
        if payment_required and not payment_paid:
            # Redirect to payment page
            return RedirectResponse(
                url=f"/patients/{patient_id}/pay/radiology?order_id={order_id}&return_to=radiology/orders/{order_id}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Update radiology order with report
    update_data = {
        "report": report,
        "report_entered_by_id": current_user.id,
        "report_entered_at": datetime.now(),
        "status": OrderStatus.COMPLETED.value,
        "completed_at": datetime.now()
    }
    
    # Validate report before saving
    try:
        from app.services import validate_radiology_report
        validation = validate_radiology_report(db, radiology_order, report)
        if not validation.is_valid:
            # If validation fails, redirect back with error
            return RedirectResponse(
                url=f"/radiology/orders/{order_id}?error={validation.message}",
                status_code=status.HTTP_302_FOUND
            )
    except Exception as e:
        # Log validation error but continue
        print(f"Error validating radiology report {order_id}: {e}")
    
    radiology_order_update = RadiologyOrderUpdate(**update_data)
    updated_radiology_order = encounter_crud.update_radiology_order(db, order_id, radiology_order_update)
    
    # Automatically create charge when radiology order is completed
    if updated_radiology_order and updated_radiology_order.status == OrderStatus.COMPLETED.value:
        try:
            from app.services import create_charge_for_radiology_order
            create_charge_for_radiology_order(db, updated_radiology_order, current_user.id)
        except Exception as e:
            # Log error but don't fail the request
            # In production, use proper logging
            print(f"Error creating charge for radiology order {order_id}: {e}")
    
    return RedirectResponse(
        url=f"/radiology/orders/{order_id}?status=report_entered",
        status_code=status.HTTP_302_FOUND
    )


# Pharmacy Information System (PhIS) Routes
@router.get("/pharmacy", name="pharmacy_dashboard")
def pharmacy_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin", "Doctor", "Nurse", "Clinician"])),
    status_filter: Optional[str] = Query(None, description="Filter by prescription status")
):
    """
    Pharmacy dashboard showing pending and completed prescriptions.
    """
    # Query for prescriptions
    query = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.dispensed_by)
    )
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(Prescription.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show pending prescriptions
        query = query.filter(Prescription.status == OrderStatus.PENDING.value)
    
    prescriptions = query.order_by(Prescription.prescribed_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Pharmacy (PhIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescriptions": prescriptions,
        "status_filter": status_filter
    }
    return templates.TemplateResponse("ancillary/pharmacy_dashboard.html", context)


@router.get("/pharmacy/prescriptions/{prescription_id}", name="view_prescription")
def view_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"]))
):
    """
    View a specific prescription and dispense medication.
    """
    from app.crud import inventory_crud
    from app.crud import encounter_crud
    
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.dispensed_by),
        joinedload(Prescription.medication)  # Eager load medication if linked
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient
    
    # Check inventory availability
    medication = None
    stock_check = None
    formulary_check = None
    stock_items = []
    
    # First, try to use medication_id if linked
    if prescription.medication_id and prescription.medication:
        medication = prescription.medication
    # Fallback to code lookup
    elif prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    # Fallback to name search
    if not medication:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    if medication:
        # Stock check
        required_quantity = prescription.quantity or 1
        stock_check = inventory_crud.check_stock_availability(db, medication.id, required_quantity)
        stock_items = inventory_crud.get_stock_items_by_medication(db, medication.id)
        
        # Formulary check
        formulary_check = inventory_crud.check_formulary_compliance(
            db, medication.id, patient.nhis_number
        )
        
        # Drug interaction check - get other active prescriptions for this patient
        other_prescriptions = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == patient.id,
            Prescription.id != prescription_id,
            Prescription.status.in_([OrderStatus.PENDING.value, OrderStatus.ORDERED.value, OrderStatus.IN_PROGRESS.value])
        ).all()
        
        other_medication_ids = []
        for other_prescription in other_prescriptions:
            if other_prescription.medication_code:
                other_med = inventory_crud.get_medication_by_code(db, other_prescription.medication_code)
                if other_med:
                    other_medication_ids.append(other_med.id)
            else:
                other_meds = inventory_crud.get_medications(db, search=other_prescription.medication_name, limit=1)
                if other_meds:
                    other_medication_ids.append(other_meds[0].id)
        
        interaction_check = None
        if other_medication_ids:
            interaction_check = inventory_crud.check_drug_interactions(
                db, [medication.id] + other_medication_ids
            )
    else:
        interaction_check = None
    
    context = {
        "request": request,
        "title": f"Prescription #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "medication": medication,
        "stock_check": stock_check,
        "formulary_check": formulary_check,
        "interaction_check": interaction_check,
        "stock_items": stock_items
    }
    return templates.TemplateResponse("ancillary/prescription_detail.html", context)


@router.post("/pharmacy/prescriptions/{prescription_id}/dispense", name="dispense_prescription", status_code=status.HTTP_302_FOUND)
def dispense_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"])),
    stock_item_id: Optional[int] = Form(None)
):
    """
    Mark prescription as dispensed and update inventory.
    For cash patients: Checks if payment has been made before allowing dispensing.
    For IPD patients: Pharmacy charges are pay-as-you-go even if admitted.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    from app.crud import inventory_crud
    from app.schemas.inventory_schemas import InventoryTransactionCreate
    from app.models.inventory_models import TransactionType
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get patient from encounter
    encounter = prescription.encounter
    patient_id = encounter.patient_id
    
    # Check payment requirement for cash patients (pharmacy fee)
    # Note: For IPD patients, pharmacy is still pay-as-you-go
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.PHARMACY,
            encounter_id=encounter.id, prescription_id=prescription_id
        )
        
        if payment_required and not payment_paid:
            # Redirect to payment page
            return RedirectResponse(
                url=f"/patients/{patient_id}/pay/pharmacy?prescription_id={prescription_id}&return_to=pharmacy/prescriptions/{prescription_id}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Try to find medication - use medication_id first if linked
    medication = None
    if prescription.medication_id:
        medication = inventory_crud.get_medication(db, prescription.medication_id)
    elif prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    if not medication:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    # Update inventory if medication found
    if medication and stock_item_id:
        quantity = prescription.quantity or 1
        
        # Create sale transaction
        transaction_data = InventoryTransactionCreate(
            medication_id=medication.id,
            stock_item_id=stock_item_id,
            prescription_id=prescription_id,
            transaction_type=TransactionType.SALE,
            quantity=-quantity,  # Negative for sale
            notes=f"Dispensed for prescription #{prescription_id}"
        )
        inventory_crud.create_inventory_transaction(db, transaction_data, current_user.id)
    
    # Update prescription as dispensed
    update_data = {
        "status": OrderStatus.COMPLETED.value,
        "dispensed_by_id": current_user.id,
        "dispensed_at": datetime.now()
    }
    
    prescription_update = PrescriptionUpdate(**update_data)
    updated_prescription = encounter_crud.update_prescription(db, prescription_id, prescription_update)
    
    # Automatically create charge when prescription is dispensed
    if updated_prescription and updated_prescription.status == OrderStatus.COMPLETED.value:
        try:
            from app.services import create_charge_for_prescription
            create_charge_for_prescription(db, updated_prescription, current_user.id)
        except Exception as e:
            # Log error but don't fail the request
            # In production, use proper logging
            print(f"Error creating charge for prescription {prescription_id}: {e}")
    
    return RedirectResponse(
        url=f"/pharmacy/prescriptions/{prescription_id}?status=dispensed",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/pharmacy/prescriptions/{prescription_id}/print", name="print_prescription")
def print_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin", "Doctor", "Nurse", "Clinician"]))
):
    """Print prescription on receipt printer (especially when out of stock)"""
    from app.crud import hospital_settings_crud
    from app.crud import inventory_crud
    
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by)
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient
    
    # Get hospital settings for receipt header
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Check stock availability
    medication = None
    stock_check = None
    if prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    if not medication and prescription.medication_name:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    if medication:
        stock_check = inventory_crud.check_stock_availability(db, medication.id, prescription.quantity or 1)
    
    context = {
        "request": request,
        "title": f"Prescription #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "medication": medication,
        "stock_check": stock_check,
        "hospital_settings": hospital_settings
    }
    return templates.TemplateResponse("pharmacy/prescription_receipt.html", context)


@router.post("/pharmacy/prescriptions/{prescription_id}/cancel", name="cancel_prescription", status_code=status.HTTP_302_FOUND)
def cancel_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"])),
    reason: Optional[str] = Form(None)
):
    """
    Cancel a prescription when medication is not in stock.
    The prescription will still appear in patient records for audit purposes.
    """
    from app.models.encounter_models import OrderStatus
    from datetime import datetime
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Only allow cancellation if prescription is not already completed or cancelled
    if prescription.status == OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a prescription that has already been dispensed"
        )
    
    if prescription.status == OrderStatus.CANCELLED:
        # Already cancelled, just redirect back
        return RedirectResponse(
            url=f"/pharmacy/prescriptions/{prescription_id}?status=already_cancelled",
            status_code=status.HTTP_302_FOUND
        )
    
    # Update prescription status to cancelled
    prescription.status = OrderStatus.CANCELLED
    prescription.updated_at = datetime.now()
    
    # Store cancellation reason in instructions if provided
    if reason:
        current_instructions = prescription.instructions or ""
        cancellation_note = f"\n\n[CANCELLED by {current_user.full_name or current_user.username} on {datetime.now().strftime('%Y-%m-%d %H:%M')}: {reason}]"
        prescription.instructions = current_instructions + cancellation_note
    else:
        current_instructions = prescription.instructions or ""
        cancellation_note = f"\n\n[CANCELLED by {current_user.full_name or current_user.username} on {datetime.now().strftime('%Y-%m-%d %H:%M')}: Medication not in stock]"
        prescription.instructions = current_instructions + cancellation_note
    
    db.commit()
    db.refresh(prescription)
    
    return RedirectResponse(
        url=f"/pharmacy/prescriptions/{prescription_id}?status=cancelled",
        status_code=status.HTTP_302_FOUND
    )

