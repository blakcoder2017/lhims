from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional, List
from datetime import datetime
import os
import uuid

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
    status_filter: Optional[str] = Query(None, description="Filter by order status"),
    search: Optional[str] = Query(None, description="Search by patient name, patient number, or phone number")
):
    """
    Laboratory dashboard showing pending and completed lab orders.
    """
    from sqlalchemy import or_
    
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
    
    # Search by patient name, patient number, or phone number
    if search:
        search_term = f"%{search.strip()}%"
        # For walk-in orders, patient_id is directly on LabOrder
        # For encounter-based orders, patient is via Encounter
        query = query.outerjoin(Encounter).outerjoin(Patient, 
            or_(LabOrder.patient_id == Patient.id, Encounter.patient_id == Patient.id)
        ).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
            )
        )
    
    lab_orders = query.order_by(LabOrder.ordered_at.desc()).limit(100).all()
    
    # Check payment status for each lab order (for cash patients)
    # OPD: pay before lab results. IPD (on admission): pay at discharge — do not require payment before results.
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid
    from app.models.billing_models import Charge, ChargeType, Invoice
    from app.crud import ipd_crud
    lab_order_payment_status = {}
    
    for order in lab_orders:
        patient_id = None
        if order.encounter and order.encounter.patient:
            patient_id = order.encounter.patient.id
        elif order.patient_id:
            patient_id = order.patient_id
        
        if patient_id and is_cash_patient(db, patient_id):
            # Admitted (IPD) patients pay at discharge — allow lab results without prior payment
            current_admission = ipd_crud.get_current_admission(db, patient_id)
            if current_admission:
                lab_order_payment_status[order.id] = {
                    "payment_required": False,
                    "payment_paid": True,
                    "is_admitted": True
                }
                continue
            # OPD cash: require payment before lab results
            charge = db.query(Charge).filter(
                Charge.lab_order_id == order.id,
                Charge.charge_type == ChargeType.LAB_TEST,
                Charge.invoice.has(Invoice.is_active == True)
            ).first()
            
            if charge:
                invoice = charge.invoice
                payment_required, payment_paid, _, _ = check_payment_required_and_paid(
                    db, patient_id, ChargeType.LAB_TEST,
                    encounter_id=order.encounter_id if order.encounter else None,
                    lab_order_id=order.id
                )
                if payment_required and not payment_paid:
                    lab_order_payment_status[order.id] = {
                        "payment_required": True,
                        "payment_paid": False,
                        "invoice_id": invoice.id,
                        "balance": invoice.balance
                    }
                else:
                    lab_order_payment_status[order.id] = {
                        "payment_required": payment_required,
                        "payment_paid": True
                    }
    
    context = {
        "request": request,
        "title": "Laboratory (LIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "lab_orders": lab_orders,
        "lab_order_payment_status": lab_order_payment_status,
        "status_filter": status_filter,
        "search": search
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
    
    # Check payment status for cash patients.
    # OPD: pay before lab results. IPD (on admission): pay at discharge — allow result entry without prior payment.
    from app.utils.payment_verification import is_cash_patient, has_visit_invoice_been_paid
    from app.models.billing_models import Invoice
    from app.crud import ipd_crud
    
    patient = lab_order.encounter.patient if lab_order.encounter else (db.query(Patient).filter(Patient.id == lab_order.patient_id).first() if lab_order.patient_id else None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found for this lab order")
    payment_required = False
    payment_paid = True
    payment_notice = None
    unpaid_invoice = None
    paid_invoice = None
    is_admitted = False
    
    if is_cash_patient(db, patient.id):
        # Admitted (IPD) patients pay at discharge — allow lab results without prior payment
        current_admission = ipd_crud.get_current_admission(db, patient.id)
        if current_admission:
            is_admitted = True
            payment_required = False
            payment_paid = True
            payment_notice = "Patient is on admission (IPD). Payment will be at discharge. You can enter results."
        else:
            # OPD: visit invoice (consultation + lab) must be paid before result entry
            from app.services import create_charge_for_lab_order
            try:
                create_charge_for_lab_order(db, lab_order, current_user.id, check_payment_required=False)
            except Exception:
                pass
            payment_paid = has_visit_invoice_been_paid(db, encounter_id=lab_order.encounter_id) if lab_order.encounter_id else False
            payment_required = not payment_paid
            invoice = db.query(Invoice).filter(
                Invoice.encounter_id == lab_order.encounter_id,
                Invoice.is_active == True
            ).first() if lab_order.encounter_id else None
            if invoice:
                if payment_paid:
                    paid_invoice = invoice
                    payment_notice = "Payment Status: Visit (consultation + lab) has been paid. You can enter results."
                else:
                    unpaid_invoice = invoice
                    payment_notice = f"Payment Required: Patient must pay visit (consultation + lab) before lab result. Balance: GHS {invoice.balance:.2f}"
    
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
        "patient": patient,
        "samples": samples,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "paid_invoice": paid_invoice,
        "is_admitted": is_admitted,
    }
    return templates.TemplateResponse("ancillary/lab_order_detail.html", context)


@router.post("/lab/orders/{order_id}/enter-result", name="enter_lab_result", status_code=status.HTTP_302_FOUND)
def enter_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    result: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    """
    Enter lab test results.
    OPD cash patients: must pay before lab results. IPD (on admission): pay at discharge — allow result entry.
    """
    from app.utils.payment_verification import (
        is_cash_patient,
        has_visit_invoice_been_paid
    )
    from app.models.billing_models import Invoice
    from app.crud import ipd_crud
    
    lab_order = db.query(LabOrder).options(
        joinedload(LabOrder.encounter)
    ).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    encounter = lab_order.encounter
    patient_id = encounter.patient_id if encounter else lab_order.patient_id
    if not patient_id:
        raise HTTPException(status_code=400, detail="Patient not found for this lab order")
    
    # OPD cash: pay before lab results. IPD (on admission): pay at discharge — allow result entry without prior payment.
    if is_cash_patient(db, patient_id):
        current_admission = ipd_crud.get_current_admission(db, patient_id)
        if not current_admission:
            # OPD: block result entry until visit invoice paid
            if encounter and not has_visit_invoice_been_paid(db, encounter_id=encounter.id):
                pay_url = request.url_for("pay_consultation", patient_id=patient_id)
                return RedirectResponse(
                    url=f"{pay_url}?encounter_id={encounter.id}&return_to=pay_visit&from_lab={order_id}",
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
    
    # Send SMS notification to patient when result is ready (only if valid phone)
    try:
        from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
        patient = encounter.patient if encounter else db.query(Patient).filter(Patient.id == patient_id).first()
        if patient and patient.phone_number and is_valid_phone(patient.phone_number):
            message_template = "Hello {$name}. Your lab test result for {$test_name} is ready. Please visit the hospital or contact your doctor. Thank you!"
            destinations = [{
                "number": patient.phone_number,
                "values": [
                    f"{patient.first_name} {patient.last_name}",
                    lab_order.test_name
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
    except Exception as sms_error:
        print(f"Warning: Unable to send lab result SMS: {sms_error}")
    
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
    
    # Handle file uploads if provided
    if files:
        # patient_id already set above (encounter or lab_order.patient_id)
        
        # Create storage directory
        storage_base = "static/files/lab_results"
        storage_path = os.path.join(storage_base, str(patient_id), str(order_id))
        os.makedirs(storage_path, exist_ok=True)
        
        uploaded_files = []
        for file in files:
            if file.filename:
                # Generate unique filename
                file_ext = os.path.splitext(file.filename)[1] or ""
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(storage_path, unique_filename)
                
                # Save file
                with open(file_path, "wb") as f:
                    content = file.file.read()
                    f.write(content)
                
                uploaded_files.append({
                    "original_name": file.filename,
                    "saved_path": file_path,
                    "file_size": len(content),
                    "file_type": file.content_type or "application/octet-stream"
                })
        
        # Store file info in result text (or could create separate model)
        if uploaded_files:
            file_info = "\n\n[Attached Files: " + ", ".join([f.filename for f in files]) + "]"
            result = result + file_info
            # Update result in update_data
            update_data["result"] = result
    
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
    status_filter: Optional[str] = Query(None, description="Filter by order status"),
    search: Optional[str] = Query(None, description="Search by patient name, patient number, or phone number")
):
    """
    Radiology dashboard showing pending and completed radiology orders.
    """
    from sqlalchemy import or_
    
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
    
    # Search by patient name, patient number, or phone number
    if search:
        search_term = f"%{search.strip()}%"
        # For walk-in orders, patient_id is directly on RadiologyOrder
        # For encounter-based orders, patient is via Encounter
        query = query.outerjoin(Encounter).outerjoin(Patient, 
            or_(RadiologyOrder.patient_id == Patient.id, Encounter.patient_id == Patient.id)
        ).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
            )
        )
    
    radiology_orders = query.order_by(RadiologyOrder.ordered_at.desc()).limit(100).all()
    
    # Check payment status for each radiology order (for cash patients)
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid
    from app.models.billing_models import Charge, ChargeType, Invoice
    radiology_order_payment_status = {}
    
    for order in radiology_orders:
        patient_id = None
        if order.encounter and order.encounter.patient:
            patient_id = order.encounter.patient.id
        elif order.patient_id:
            patient_id = order.patient_id
        
        if patient_id and is_cash_patient(db, patient_id):
            # Check if there's a charge for this radiology order
            charge = db.query(Charge).filter(
                Charge.radiology_order_id == order.id,
                Charge.charge_type == ChargeType.RADIOLOGY,
                Charge.invoice.has(Invoice.is_active == True)
            ).first()
            
            if charge:
                invoice = charge.invoice
                payment_required, payment_paid, _, _ = check_payment_required_and_paid(
                    db, patient_id, ChargeType.RADIOLOGY,
                    encounter_id=order.encounter_id if order.encounter else None,
                    radiology_order_id=order.id
                )
                if payment_required and not payment_paid:
                    radiology_order_payment_status[order.id] = {
                        "payment_required": True,
                        "payment_paid": False,
                        "invoice_id": invoice.id,
                        "balance": invoice.balance
                    }
                else:
                    radiology_order_payment_status[order.id] = {
                        "payment_required": payment_required,
                        "payment_paid": True
                    }
    
    context = {
        "request": request,
        "title": "Radiology (RIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_orders": radiology_orders,
        "radiology_order_payment_status": radiology_order_payment_status,
        "status_filter": status_filter,
        "search": search
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
    
    # Check payment status for cash patients
    from app.utils.payment_verification import (
        is_cash_patient,
        check_payment_required_and_paid,
        requires_payment_before_service
    )
    from app.models.billing_models import ChargeType
    
    patient = radiology_order.encounter.patient
    payment_required = False
    payment_paid = True
    payment_notice = None
    unpaid_invoice = None
    paid_invoice = None
    
    if is_cash_patient(db, patient.id):
        # First, ensure charge exists for this radiology order (if not already created)
        # This allows us to always check payment status
        from app.services import create_charge_for_radiology_order
        try:
            create_charge_for_radiology_order(db, radiology_order, current_user.id, check_payment_required=False)
        except Exception as e:
            # Charge might already exist, continue
            pass
        
        # Check payment requirement and status
        payment_required = requires_payment_before_service(
            db, patient.id, ChargeType.RADIOLOGY
        )
        
        if payment_required:
            payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
                db, patient.id, ChargeType.RADIOLOGY,
                encounter_id=radiology_order.encounter_id,
                radiology_order_id=order_id
            )
            
            if invoice:
                if payment_paid:
                    paid_invoice = invoice
                    payment_notice = f"Payment Status: Patient has paid for this radiology order. Invoice #{invoice.invoice_number} - Amount: GHS {invoice.total_amount:.2f}"
                else:
                    unpaid_invoice = invoice
                    payment_notice = f"Payment Required: Patient has not paid for this radiology order. Outstanding balance: GHS {invoice.balance:.2f}"
            else:
                # Charge might not exist yet or still being created
                payment_notice = "Payment Status: Checking payment status..."
    
    context = {
        "request": request,
        "title": f"Radiology Order #{order_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_order": radiology_order,
        "patient": radiology_order.encounter.patient,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "paid_invoice": paid_invoice
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
    # Payment must be made before saving reports for cash patients
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.RADIOLOGY,
            encounter_id=encounter.id, radiology_order_id=order_id
        )
        
        if payment_required and not payment_paid:
            # Block saving - redirect back with payment required error
            invoice_id = invoice.id if invoice else None
            invoice_balance = invoice.balance if invoice else None
            return RedirectResponse(
                url=f"/radiology/orders/{order_id}?error=payment_required&invoice_id={invoice_id}&balance={invoice_balance}",
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
    
    # Send SMS notification to patient when radiology result is ready (only if valid phone)
    try:
        from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
        patient = encounter.patient
        if patient and patient.phone_number and is_valid_phone(patient.phone_number):
            message_template = "Hello {$name}. Your radiology result for {$study_type} is ready. Please visit the hospital or contact your doctor. Thank you!"
            destinations = [{
                "number": patient.phone_number,
                "values": [
                    f"{patient.first_name} {patient.last_name}",
                    radiology_order.study_type
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
    except Exception as sms_error:
        print(f"Warning: Unable to send radiology result SMS: {sms_error}")
    
    # Automatically create charge when radiology order is completed
    if updated_radiology_order and updated_radiology_order.status == OrderStatus.COMPLETED.value:
        try:
            from app.services import create_charge_for_radiology_order
            create_charge_for_radiology_order(db, updated_radiology_order, current_user.id)
        except Exception as e:
            # Log error but don't fail the request
            # In production, use proper logging
            print(f"Error creating charge for radiology order {order_id}: {e}")
    
    # Redirect with success status
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
    status_filter: Optional[str] = Query(None, description="Filter by prescription status"),
    search: Optional[str] = Query(None, description="Search by patient name, patient number, or phone number")
):
    """
    Pharmacy dashboard showing pending and completed prescriptions.
    """
    from sqlalchemy import or_
    
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
    
    # Search by patient name, patient number, or phone number
    if search:
        search_term = f"%{search.strip()}%"
        # For walk-in orders, patient_id is directly on Prescription (though prescriptions are usually encounter-based)
        # For encounter-based orders, patient is via Encounter
        query = query.outerjoin(Encounter).outerjoin(Patient, 
            or_(Prescription.patient_id == Patient.id, Encounter.patient_id == Patient.id)
        ).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
            )
        )
    
    prescriptions = query.order_by(Prescription.prescribed_at.desc()).limit(100).all()
    
    # Check payment status for each prescription (for cash patients)
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid
    from app.models.billing_models import Charge, ChargeType, Invoice
    prescription_payment_status = {}
    
    for prescription in prescriptions:
        patient_id = None
        if prescription.encounter and prescription.encounter.patient:
            patient_id = prescription.encounter.patient.id
        elif prescription.patient_id:
            patient_id = prescription.patient_id
        
        if patient_id and is_cash_patient(db, patient_id):
            # Check if there's a charge for this prescription
            charge = db.query(Charge).filter(
                Charge.prescription_id == prescription.id,
                Charge.charge_type == ChargeType.PHARMACY,
                Charge.invoice.has(Invoice.is_active == True)
            ).first()
            
            if charge:
                invoice = charge.invoice
                try:
                    payment_required, payment_paid, _charge, _invoice = check_payment_required_and_paid(
                        db, patient_id, ChargeType.PHARMACY,
                        encounter_id=prescription.encounter_id,
                        prescription_id=prescription.id
                    )
                    if payment_required and not payment_paid:
                        prescription_payment_status[prescription.id] = {
                            "payment_required": True,
                            "invoice_id": invoice.id if invoice else None,
                            "balance": invoice.balance if invoice else None
                        }
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    # Don't 500 the dashboard; leave this prescription without payment-required flag
                    prescription_payment_status[prescription.id] = {
                        "payment_required": False,
                        "invoice_id": invoice.id if invoice else None,
                        "balance": invoice.balance if invoice else None
                    }
    
    context = {
        "request": request,
        "title": "Pharmacy (PhIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescriptions": prescriptions,
        "prescription_payment_status": prescription_payment_status,
        "status_filter": status_filter,
        "search": search
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
    
    # Check payment status for cash patients
    from app.utils.payment_verification import (
        is_cash_patient,
        check_payment_required_and_paid,
        requires_payment_before_service
    )
    from app.models.billing_models import ChargeType
    from decimal import Decimal
    
    payment_required = False
    payment_paid = True
    payment_notice = None
    unpaid_invoice = None
    paid_invoice = None
    
    if is_cash_patient(db, patient.id):
        # First, ensure charge exists for this prescription (if not already created)
        # This allows us to always check payment status
        from app.services import create_charge_for_prescription
        try:
            create_charge_for_prescription(db, prescription, current_user.id, check_payment_required=False)
        except Exception as e:
            # Charge might already exist, continue
            pass
        
        # Check payment requirement and status
        payment_required = requires_payment_before_service(
            db, patient.id, ChargeType.PHARMACY
        )
        
        if payment_required:
            payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
                db, patient.id, ChargeType.PHARMACY,
                encounter_id=prescription.encounter_id,
                prescription_id=prescription_id
            )
            
            if invoice:
                if payment_paid:
                    paid_invoice = invoice
                    payment_notice = f"Payment Status: Patient has paid for this prescription. Invoice #{invoice.invoice_number} - Amount: GHS {invoice.total_amount:.2f}"
                else:
                    unpaid_invoice = invoice
                    payment_notice = f"Payment Required: Patient has not paid for this prescription. Outstanding balance: GHS {invoice.balance:.2f}"
            else:
                # Charge might not exist yet or still being created
                payment_notice = "Payment Status: Checking payment status..."
    
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
        "stock_items": stock_items,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "paid_invoice": paid_invoice
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
    
    # Create charge first (if it doesn't exist) for all patients
    # This ensures the charge exists before we check payment
    from app.services import create_charge_for_prescription
    try:
        # Create charge if it doesn't exist (function returns None if charge already exists)
        create_charge_for_prescription(db, prescription, current_user.id, check_payment_required=False)
    except Exception as e:
        # Log error but continue - charge might already exist
        print(f"Note: Charge creation for prescription {prescription_id}: {e}")
    
    # For cash patients: Check payment requirement before dispensing
    # Payment must be made before dispensing for cash patients
    # Note: For IPD patients, pharmacy is still pay-as-you-go
    if is_cash_patient(db, patient_id):
        # Now check if payment has been made
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.PHARMACY,
            encounter_id=encounter.id, prescription_id=prescription_id
        )
        
        if payment_required and not payment_paid:
            # Block dispensing - redirect back with payment required error
            invoice_id = invoice.id if invoice else None
            invoice_balance = invoice.balance if invoice else None
            return RedirectResponse(
                url=f"/pharmacy/prescriptions/{prescription_id}?error=payment_required&invoice_id={invoice_id}&balance={invoice_balance}",
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
    # Payment check already performed above - if we reach here, payment is confirmed
    update_data = {
        "status": OrderStatus.COMPLETED.value,
        "dispensed_by_id": current_user.id,
        "dispensed_at": datetime.now()
    }
    
    prescription_update = PrescriptionUpdate(**update_data)
    updated_prescription = encounter_crud.update_prescription(db, prescription_id, prescription_update)
    
    # Charge is already created before dispensing (for cash patients) or will be created automatically
    # No need to create it again here since we create it earlier for payment verification
    
    # Redirect with success status
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

