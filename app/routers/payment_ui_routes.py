"""
Payment UI Routes

Routes for handling pay-as-you-go payments for cash patients.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import patient_crud, billing_crud, service_pricing_crud
from app.models.billing_models import ChargeType, InvoiceStatus, PaymentStatus
from app.utils.payment_verification import (
    requires_payment_before_service,
    has_paid_for_service,
    get_or_create_service_charge,
    check_payment_required_and_paid,
    is_cash_patient
)
from app.schemas.billing_schemas import PaymentCreate

router = APIRouter(
    prefix="",
    tags=["Payment UI"]
)

templates = Jinja2Templates(directory="app/templates")

# Default prices if service pricing not configured
DEFAULT_VITALS_FEE = Decimal('20.00')
DEFAULT_CONSULTATION_FEE = Decimal('100.00')
DEFAULT_PHARMACY_FEE = Decimal('20.00')  # Per unit/medication
DEFAULT_LAB_TEST_FEE = Decimal('50.00')


def get_service_price(db: Session, service_name: str, charge_type: str, default_price: Decimal) -> Decimal:
    """Get service price from pricing table or use default."""
    pricing = service_pricing_crud.get_service_pricing_by_name(db, service_name)
    if pricing and pricing.is_active:
        return Decimal(str(pricing.unit_price))
    
    # Try to get by charge type
    pricing_list = service_pricing_crud.get_service_pricing_by_charge_type(db, charge_type)
    if pricing_list:
        return Decimal(str(pricing_list[0].unit_price))
    
    return default_price


@router.get("/patients/{patient_id}/pay/vitals", name="pay_vitals")
def pay_vitals_page(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Nurse"])),
    return_to: Optional[str] = Query(None)
):
    """Payment page for vitals fee."""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if payment is required
    if not is_cash_patient(db, patient_id):
        # Not a cash patient, redirect back
        redirect_url = f"/patients/{patient_id}/triage"
        if return_to:
            redirect_url = f"/patients/{patient_id}/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if already paid
    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
        db, patient_id, ChargeType.OTHER
    )
    
    if payment_paid:
        # Already paid, redirect back
        redirect_url = f"/patients/{patient_id}/triage"
        if return_to:
            redirect_url = f"/patients/{patient_id}/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Get or create charge
    if not charge:
        service_price = get_service_price(db, "Vitals", "other", DEFAULT_VITALS_FEE)
        charge, invoice = get_or_create_service_charge(
            db, patient_id, ChargeType.OTHER,
            "Vitals Recording Fee",
            service_price,
            created_by_id=current_user.id
        )
    
    context = {
        "request": request,
        "title": "Pay Vitals Fee",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "charge": charge,
        "invoice": invoice,
        "service_type": "vitals",
        "return_to": return_to or "triage"
    }
    
    return templates.TemplateResponse("billing/pay_service.html", context)


@router.post("/patients/{patient_id}/pay/vitals", name="process_vitals_payment")
def process_vitals_payment(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin"])),
    return_to: Optional[str] = Form(None),
    invoice_id: int = Form(...),
    amount: str = Form(...)
):
    """Process payment for vitals fee."""
    amount_decimal = Decimal(amount)
    
    # Create payment
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=amount_decimal,
        payment_method="cash",
        status=PaymentStatus.COMPLETED,
        notes="Vitals fee payment"
    )
    
    payment = billing_crud.create_payment(db, payment_data, current_user.id)
    
    redirect_url = f"/patients/{patient_id}/triage?status=payment_success"
    if return_to:
        redirect_url = f"/patients/{patient_id}/{return_to}?status=payment_success"
    
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/patients/{patient_id}/pay/consultation", name="pay_consultation")
def pay_consultation_page(
    request: Request,
    patient_id: int,
    encounter_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin"])),
    return_to: Optional[str] = Query(None),
    new_visit: Optional[str] = Query(None)
):
    """Payment page for consultation fee."""
    from datetime import datetime
    from app.models.encounter_models import Encounter, EncounterStatus
    from app.models.billing_models import Charge, Invoice
    from sqlalchemy import func
    from datetime import date
    
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if payment is required
    if not is_cash_patient(db, patient_id):
        # Not a cash patient, redirect back
        redirect_url = f"/patients/{patient_id}/encounters/new"
        if return_to:
            redirect_url = f"/patients/{patient_id}/{return_to}"
        if new_visit:
            redirect_url += f"?new_visit={new_visit}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if this is a new visit (explicit or detected)
    is_new_visit_flag = new_visit and new_visit.lower() == 'true'
    
    # If not explicitly a new visit, check if there's a completed encounter today
    if not is_new_visit_flag:
        today = date.today()
        completed_encounters_today = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.status == EncounterStatus.COMPLETED.value,
            Encounter.is_active == True,
            func.date(Encounter.encounter_date) == today
        ).count()
        
        if completed_encounters_today > 0:
            is_new_visit_flag = True
    
    # For new visits, we need to find or create a NEW charge (not use old paid charges)
    if is_new_visit_flag:
        # Check for existing UNPAID charges for this new visit
        # Don't reuse old paid charges - each visit needs its own charge
        today = date.today()
        existing_charge = db.query(Charge).join(Invoice).filter(
            Invoice.patient_id == patient_id,
            Charge.charge_type == ChargeType.CONSULTATION,
            Charge.encounter_id.is_(None),
            Invoice.is_active == True,
            Invoice.balance > Decimal('0'),
            Invoice.status != InvoiceStatus.PAID,
            func.date(Charge.created_at) == today
        ).order_by(Charge.created_at.desc()).first()
        
        if existing_charge:
            # Use existing unpaid charge for this visit
            charge = existing_charge
            invoice = existing_charge.invoice
            payment_paid = False  # Unpaid charge requires payment
        else:
            # Create a new charge for this new visit
            service_price = get_service_price(db, "Consultation", "consultation", DEFAULT_CONSULTATION_FEE)
            charge, invoice = get_or_create_service_charge(
                db, patient_id, ChargeType.CONSULTATION,
                "Consultation Fee (Covers Vitals & Initial Encounter)",
                service_price,
                encounter_id=encounter_id,
                opd_visit_id=opd_visit_id,
                created_by_id=current_user.id
            )
            payment_paid = False  # New charge requires payment
    else:
        # Not a new visit - check if already paid
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.CONSULTATION, encounter_id=encounter_id
        )
        
        if payment_paid:
            # Already paid, redirect back
            redirect_url = f"/patients/{patient_id}/encounters/new"
            if return_to:
                redirect_url = f"/patients/{patient_id}/{return_to}"
            if new_visit:
                redirect_url += f"?new_visit={new_visit}"
            return RedirectResponse(url=redirect_url, status_code=302)
        
        # Get or create charge
        if not charge:
            service_price = get_service_price(db, "Consultation", "consultation", DEFAULT_CONSULTATION_FEE)
            charge, invoice = get_or_create_service_charge(
                db, patient_id, ChargeType.CONSULTATION,
                "Consultation Fee (Covers Vitals & Initial Encounter)",
                service_price,
                encounter_id=encounter_id,
                opd_visit_id=opd_visit_id,
                created_by_id=current_user.id
            )
    
    context = {
        "request": request,
        "title": "Pay Consultation Fee",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "charge": charge,
        "invoice": invoice,
        "service_type": "consultation",
        "encounter_id": encounter_id,
        "return_to": return_to or "encounters/new",
        "new_visit": new_visit  # Preserve new_visit parameter
    }
    
    return templates.TemplateResponse("billing/pay_service.html", context)


@router.post("/patients/{patient_id}/pay/consultation", name="process_consultation_payment")
def process_consultation_payment(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin"])),
    return_to: Optional[str] = Form(None),
    invoice_id: int = Form(...),
    amount: str = Form(...),
    encounter_id: Optional[int] = Form(None),
    new_visit: Optional[str] = Form(None)
):
    """Process payment for consultation fee."""
    from app.models.billing_models import Invoice
    from app.crud import opd_crud
    
    amount_decimal = Decimal(amount)
    
    # Validate invoice belongs to patient
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="Invoice does not belong to this patient")
    
    # If patient has an active OPD visit, ensure invoice is linked to it
    active_opd_visit = opd_crud.get_active_opd_visit_by_patient(db, patient_id)
    if active_opd_visit:
        if invoice.opd_visit_id != active_opd_visit.id:
            # Invoice is not linked to the active OPD visit - link it now
            invoice.opd_visit_id = active_opd_visit.id
            db.commit()
            db.refresh(invoice)
    
    # Create payment
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=amount_decimal,
        payment_method="cash",
        status=PaymentStatus.COMPLETED,
        notes="Consultation fee payment"
    )
    
    payment = billing_crud.create_payment(db, payment_data, current_user.id)
    
    # Ensure OPD visit payment status is synced immediately after payment
    # This is critical for encounter creation validation
    if invoice.opd_visit_id:
        from app.crud import opd_crud
        opd_crud.sync_opd_visit_payment_status(db, invoice.opd_visit_id)
    elif active_opd_visit:
        # If we just linked the invoice, sync now
        opd_crud.sync_opd_visit_payment_status(db, active_opd_visit.id)
    
    # Create receipt for the payment
    try:
        receipt = billing_crud.create_receipt(db, payment.id, current_user.id)
        receipt_number = receipt.receipt_number
    except Exception as e:
        # Log error but don't fail the payment
        print(f"Error creating receipt for payment {payment.id}: {e}")
        receipt_number = payment.receipt_number or "N/A"
    
    # Determine redirect based on return_to parameter
    # If coming from registration, go to triage; otherwise go to encounter creation
    # Preserve new_visit parameter if it exists
    new_visit_param = ""
    if new_visit:
        new_visit_param = f"&new_visit={new_visit}"
    
    redirect_url = f"/patients/{patient_id}/encounters/new?status=payment_success&receipt={receipt_number}{new_visit_param}"
    if return_to:
        redirect_url = f"/patients/{patient_id}/{return_to}?status=payment_success&receipt={receipt_number}{new_visit_param}"
    if encounter_id:
        redirect_url = f"/encounters/{encounter_id}?status=payment_success&receipt={receipt_number}{new_visit_param}"
    
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/patients/{patient_id}/pay/radiology", name="pay_radiology")
def pay_radiology_page(
    request: Request,
    patient_id: int,
    order_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Radiology Staff"])),
    return_to: Optional[str] = Query(None)
):
    """Payment page for radiology fee."""
    from app.models.encounter_models import RadiologyOrder, Encounter
    from app.services.charge_automation import get_radiology_price
    
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get radiology order
    radiology_order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    # Verify patient matches and get encounter
    encounter = None
    encounter_id = None
    
    # For walk-in orders, check patient_id directly
    if radiology_order.patient_id:
        if radiology_order.patient_id != patient_id:
            raise HTTPException(status_code=400, detail="Radiology order does not belong to this patient")
    
    # For encounter-based orders, verify through encounter
    if radiology_order.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == radiology_order.encounter_id).first()
        if encounter:
            encounter_id = encounter.id
            if encounter.patient_id != patient_id:
                raise HTTPException(status_code=400, detail="Radiology order encounter does not belong to this patient")
    
    # Check if payment is required
    if not is_cash_patient(db, patient_id):
        # Not a cash patient, redirect back
        redirect_url = f"/radiology/orders/{order_id}"
        if return_to:
            redirect_url = f"/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if already paid
    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
        db, patient_id, ChargeType.RADIOLOGY,
        encounter_id=encounter_id,
        radiology_order_id=order_id
    )
    
    if payment_paid:
        # Already paid, redirect back
        redirect_url = f"/radiology/orders/{order_id}"
        if return_to:
            redirect_url = f"/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Get or create charge
    if not charge:
        # Calculate radiology price
        radiology_price = get_radiology_price(db, radiology_order)
        
        charge, invoice = get_or_create_service_charge(
            db, patient_id, ChargeType.RADIOLOGY,
            f"Radiology: {radiology_order.study_type}",
            radiology_price,
            encounter_id=encounter_id,
            radiology_order_id=order_id,
            created_by_id=current_user.id
        )
    
    context = {
        "request": request,
        "title": "Pay Radiology Fee",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "radiology_order": radiology_order,
        "charge": charge,
        "invoice": invoice,
        "service_type": "radiology",
        "return_to": return_to or f"radiology/orders/{order_id}"
    }
    
    return templates.TemplateResponse("billing/pay_service.html", context)


@router.post("/patients/{patient_id}/pay/radiology", name="process_radiology_payment")
def process_radiology_payment(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Radiology Staff"])),
    return_to: Optional[str] = Form(None),
    order_id: Optional[int] = Form(None),
    invoice_id: int = Form(...),
    amount: str = Form(...)
):
    """Process payment for radiology fee."""
    amount_decimal = Decimal(amount)
    
    # Create payment
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=amount_decimal,
        payment_method="cash",
        status=PaymentStatus.COMPLETED,
        notes="Radiology fee payment"
    )
    
    payment = billing_crud.create_payment(db, payment_data, current_user.id)
    
    redirect_url = f"/radiology/orders/{order_id}?status=payment_success" if order_id else f"/patients/{patient_id}?status=payment_success"
    if return_to:
        redirect_url = f"/{return_to}?status=payment_success"
    
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/patients/{patient_id}/pay/pharmacy", name="pay_pharmacy")
def pay_pharmacy_page(
    request: Request,
    patient_id: int,
    prescription_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Pharmacy Staff"])),
    return_to: Optional[str] = Query(None)
):
    """Payment page for pharmacy/prescription fee."""
    from app.models.encounter_models import Prescription, Encounter
    from app.services.charge_automation import get_medication_price
    
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get prescription
    prescription = db.query(Prescription).join(Encounter).filter(
        Prescription.id == prescription_id,
        Encounter.patient_id == patient_id
    ).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    encounter = prescription.encounter
    
    # Check if payment is required
    if not is_cash_patient(db, patient_id):
        # Not a cash patient, redirect back
        redirect_url = f"/pharmacy/prescriptions/{prescription_id}"
        if return_to:
            redirect_url = f"/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if already paid
    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
        db, patient_id, ChargeType.PHARMACY,
        encounter_id=encounter.id,
        prescription_id=prescription_id
    )
    
    if payment_paid:
        # Already paid, redirect back
        redirect_url = f"/pharmacy/prescriptions/{prescription_id}"
        if return_to:
            redirect_url = f"/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Get or create charge
    if not charge:
        # Calculate medication price
        medication_price = get_medication_price(db, prescription)
        
        # Calculate total based on quantity
        quantity = prescription.quantity or 1
        total_price = medication_price * Decimal(str(quantity))
        
        charge, invoice = get_or_create_service_charge(
            db, patient_id, ChargeType.PHARMACY,
            f"Pharmacy: {prescription.medication_name} ({prescription.dosage})",
            total_price,
            encounter_id=encounter.id,
            prescription_id=prescription_id,
            created_by_id=current_user.id
        )
    
    context = {
        "request": request,
        "title": "Pay Pharmacy Fee",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "prescription": prescription,
        "charge": charge,
        "invoice": invoice,
        "service_type": "pharmacy",
        "return_to": return_to or f"pharmacy/prescriptions/{prescription_id}"
    }
    
    return templates.TemplateResponse("billing/pay_service.html", context)


@router.post("/patients/{patient_id}/pay/pharmacy", name="process_pharmacy_payment")
def process_pharmacy_payment(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Pharmacy Staff"])),
    return_to: Optional[str] = Form(None),
    prescription_id: Optional[int] = Form(None),
    invoice_id: int = Form(...),
    amount: str = Form(...)
):
    """Process payment for pharmacy/prescription fee."""
    amount_decimal = Decimal(amount)
    
    # Create payment
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=amount_decimal,
        payment_method="cash",
        status=PaymentStatus.COMPLETED,
        notes="Pharmacy fee payment"
    )
    
    payment = billing_crud.create_payment(db, payment_data, current_user.id)
    
    redirect_url = f"/pharmacy/prescriptions/{prescription_id}?status=payment_success" if prescription_id else f"/patients/{patient_id}?status=payment_success"
    if return_to:
        redirect_url = f"/{return_to}?status=payment_success"
    
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/patients/{patient_id}/pay/lab", name="pay_lab")
def pay_lab_page(
    request: Request,
    patient_id: int,
    order_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Lab Staff"])),
    return_to: Optional[str] = Query(None)
):
    """Payment page for lab test fee."""
    from app.models.encounter_models import LabOrder, Encounter
    from app.services.charge_automation import get_lab_test_price
    
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get lab order
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Verify patient matches and get encounter
    encounter = None
    encounter_id = None
    
    # For walk-in orders, check patient_id directly
    if lab_order.patient_id:
        if lab_order.patient_id != patient_id:
            raise HTTPException(status_code=400, detail="Lab order does not belong to this patient")
    
    # For encounter-based orders, verify through encounter
    if lab_order.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == lab_order.encounter_id).first()
        if encounter:
            encounter_id = encounter.id
            if encounter.patient_id != patient_id:
                raise HTTPException(status_code=400, detail="Lab order encounter does not belong to this patient")
    
    # Check if payment is required
    if not is_cash_patient(db, patient_id):
        # Not a cash patient, redirect back
        redirect_url = f"/lab/orders/{order_id}"
        if return_to:
            redirect_url = f"/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if already paid
    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
        db, patient_id, ChargeType.LAB_TEST,
        encounter_id=encounter_id,
        lab_order_id=order_id
    )
    
    if payment_paid:
        # Already paid, redirect back
        redirect_url = f"/lab/orders/{order_id}"
        if return_to:
            redirect_url = f"/{return_to}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Get or create charge
    if not charge:
        # Calculate lab test price
        lab_test_price = get_lab_test_price(db, lab_order)
        
        charge, invoice = get_or_create_service_charge(
            db, patient_id, ChargeType.LAB_TEST,
            f"Lab Test: {lab_order.test_name}",
            lab_test_price,
            encounter_id=encounter_id,
            lab_order_id=order_id,
            created_by_id=current_user.id
        )
    
    context = {
        "request": request,
        "title": "Pay Lab Test Fee",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "lab_order": lab_order,
        "charge": charge,
        "invoice": invoice,
        "service_type": "lab",
        "return_to": return_to or f"lab/orders/{order_id}"
    }
    
    return templates.TemplateResponse("billing/pay_service.html", context)


@router.post("/patients/{patient_id}/pay/lab", name="process_lab_payment")
def process_lab_payment(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin", "Lab Staff"])),
    return_to: Optional[str] = Form(None),
    order_id: Optional[int] = Form(None),
    invoice_id: int = Form(...),
    amount: str = Form(...)
):
    """Process payment for lab test fee."""
    amount_decimal = Decimal(amount)
    
    # Create payment
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=amount_decimal,
        payment_method="cash",
        status=PaymentStatus.COMPLETED,
        notes="Lab test fee payment"
    )
    
    payment = billing_crud.create_payment(db, payment_data, current_user.id)
    
    redirect_url = f"/lab/orders/{order_id}?status=payment_success" if order_id else f"/patients/{patient_id}?status=payment_success"
    if return_to:
        redirect_url = f"/{return_to}?status=payment_success"
    
    return RedirectResponse(url=redirect_url, status_code=302)

