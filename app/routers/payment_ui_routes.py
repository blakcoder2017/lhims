"""
Payment UI Routes

Routes for handling pay-as-you-go payments for cash patients.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from app.core.templates import templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime
from urllib.parse import quote

from app.db.database import get_db
from app.core.deps import role_required, get_current_user
from app.crud import patient_crud, billing_crud, service_pricing_crud, department_crud
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


# Default prices if service pricing not configured
DEFAULT_VITALS_FEE = Decimal('20.00')
DEFAULT_CONSULTATION_FEE = Decimal('100.00')
DEFAULT_PHARMACY_FEE = Decimal('20.00')  # Per unit/medication
DEFAULT_LAB_TEST_FEE = Decimal('50.00')


def _patient_return_path(patient_id: int, return_to: Optional[str]) -> Optional[str]:
    """Resolve return path; 'dashboard' means app home (no /patients/{id}/dashboard route)."""
    if not return_to:
        return None
    if return_to == "dashboard":
        return "/"
    return f"/patients/{patient_id}/{return_to}"


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


def _get_revisit_info(db, patient_id: int):
    """Determine if patient is returning and revisit discount config."""
    from app.models.encounter_models import Encounter, EncounterStatus
    from app.crud import hospital_settings_crud
    has_previous = db.query(Encounter).filter(
        Encounter.patient_id == patient_id,
        Encounter.is_active == True,
        Encounter.status == EncounterStatus.COMPLETED.value,
    ).first() is not None
    revisit_pct = None
    try:
        settings = hospital_settings_crud.get_hospital_settings(db)
        if settings and getattr(settings, "revisit_follow_up_percentage", None) is not None:
            revisit_pct = float(settings.revisit_follow_up_percentage)
    except Exception:
        pass
    return has_previous, revisit_pct


@router.get("/patients/{patient_id}/collect-payment", name="collect_payment")
def collect_payment_page(
    request: Request,
    patient_id: int,
    opd_visit_id: Optional[int] = Query(None),
    new_visit: Optional[str] = Query(None),
    return_to: Optional[str] = Query("triage"),
    visit_type: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin"])),
):
    """Payment page: select department (for department-based consultation fee) then proceed to pay."""
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not is_cash_patient(db, patient_id):
        return RedirectResponse(url=f"/patients/{patient_id}/triage", status_code=302)
    departments, _ = department_crud.get_departments(db, limit=100, active_only=True)
    has_previous, revisit_pct = _get_revisit_info(db, patient_id)
    is_revisit_eligible = has_previous and revisit_pct is not None
    # visit_type override: "revisit" or "new" from query; otherwise auto from history
    effective_visit_type = None
    if visit_type and str(visit_type).strip().lower() in ("revisit", "follow_up"):
        effective_visit_type = "revisit"
    elif visit_type and str(visit_type).strip().lower() == "new":
        effective_visit_type = "new"
    elif is_revisit_eligible:
        effective_visit_type = "revisit"
    from app.services.charge_automation import get_consultation_price_for_department
    from decimal import Decimal
    departments_with_prices = []
    for dept in departments:
        full_price = get_consultation_price_for_department(db, department_name=dept.name, visit_type=None)
        revisit_price = (
            get_consultation_price_for_department(
                db, department_name=dept.name, visit_type="revisit",
                revisit_follow_up_percentage=Decimal(str(revisit_pct)) if revisit_pct else None
            )
            if is_revisit_eligible else None
        )
        departments_with_prices.append({
            "id": dept.id,
            "name": dept.name,
            "full_price": float(full_price) if full_price else None,
            "revisit_price": float(revisit_price) if revisit_price else None,
        })
    preselect_department = (department or "").strip() or None
    context = {
        "request": request,
        "title": "Collect payment – Select department and pay",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "departments": departments_with_prices,
        "opd_visit_id": opd_visit_id,
        "new_visit": new_visit or "",
        "return_to": return_to or "triage",
        "is_revisit_eligible": is_revisit_eligible,
        "revisit_discount_pct": revisit_pct,
        "effective_visit_type": effective_visit_type,
        "preselect_department": preselect_department,
    }
    return templates.TemplateResponse("billing/collect_payment.html", context)


@router.get("/patients/{patient_id}/add-to-triage", name="add_to_triage_and_redirect")
def add_to_triage_and_redirect(
    patient_id: int,
    department: str = Query("General Medicine"),
    return_to: str = Query("dashboard"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin"])),
):
    """Add patient to vitals queue (triage) then redirect. Called after receipt is printed."""
    from app.crud import appointment_crud
    from app.schemas.appointment_schemas import QueueCreate
    from app.models.appointment_models import VisitType, OPDQueue, QueueStatus
    from sqlalchemy import func
    from datetime import date

    department_name = (department or "").strip() or "General Medicine"
    today = date.today()
    existing = (
        db.query(OPDQueue)
        .filter(
            OPDQueue.patient_id == patient_id,
            OPDQueue.is_active == True,
            OPDQueue.status.in_([QueueStatus.WAITING.value, QueueStatus.IN_PROGRESS.value]),
        )
        .filter(func.date(OPDQueue.created_at) == today)
        .first()
    )
    if not existing:
        queue_data = QueueCreate(
            patient_id=patient_id,
            department=department_name,
            department_type="opd",
            visit_type=VisitType.WALK_IN,
            priority=5,
            chief_complaint=None,
            notes="Added to vitals queue after payment receipt printed",
            assigned_clinician_id=None,
            created_by_id=current_user.id,
        )
        appointment_crud.create_queue_entry(db, queue_data)

    if return_to == "triage":
        return RedirectResponse(url=f"/patients/{patient_id}/triage", status_code=302)
    return RedirectResponse(url="/", status_code=302)


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
        redirect_url = _patient_return_path(patient_id, return_to) or f"/patients/{patient_id}/triage"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if already paid
    payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
        db, patient_id, ChargeType.OTHER
    )
    
    if payment_paid:
        # Already paid, redirect back
        redirect_url = _patient_return_path(patient_id, return_to) or f"/patients/{patient_id}/triage"
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
    
    redirect_url = (_patient_return_path(patient_id, return_to) or f"/patients/{patient_id}/triage") + "?status=payment_success"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/patients/{patient_id}/pay/consultation", name="pay_consultation")
def pay_consultation_page(
    request: Request,
    patient_id: int,
    encounter_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Front Office", "Finance", "Admin"])),
    return_to: Optional[str] = Query(None),
    new_visit: Optional[str] = Query(None),
    from_lab: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    from_registration: Optional[str] = Query(None),
    opd_visit_id: Optional[int] = Query(None),
    visit_type: Optional[str] = Query(None),
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
        redirect_url = _patient_return_path(patient_id, return_to) or f"/patients/{patient_id}/encounters/new"
        if new_visit:
            redirect_url += f"?new_visit={new_visit}" if "?" not in redirect_url else f"&new_visit={new_visit}"
        return RedirectResponse(url=redirect_url, status_code=302)

    # When encounter_id is set (e.g. from lab: pay visit = consultation + lab), use that invoice
    if encounter_id is not None:
        invoice = db.query(Invoice).filter(
            Invoice.patient_id == patient_id,
            Invoice.encounter_id == encounter_id,
            Invoice.is_active == True,
        ).first()
        if invoice:
            if invoice.balance and invoice.balance <= Decimal("0"):
                # Already paid, redirect back
                if from_lab is not None:
                    return RedirectResponse(url=f"/api/v1/ancillary/lab/orders/{from_lab}?status=payment_success", status_code=302)
                return RedirectResponse(url=f"/patients/{patient_id}/encounters/new?status=payment_success", status_code=302)
            # Use first charge for template (consultation or any); amount_due = full invoice balance
            charge = db.query(Charge).filter(Charge.invoice_id == invoice.id).first()
            if charge:
                amount_due = float(invoice.balance)
                context = {
                    "request": request,
                    "title": "Pay Visit (Consultation + Lab)",
                    "current_user": current_user,
                    "user_role": current_user.role.name,
                    "patient": patient,
                    "charge": charge,
                    "invoice": invoice,
                    "service_type": "consultation",
                    "encounter_id": encounter_id,
                    "return_to": return_to or "encounters/new",
                    "new_visit": new_visit,
                    "amount_due": amount_due,
                    "from_lab": from_lab,
                }
                return templates.TemplateResponse("billing/pay_service.html", context)

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
    
    # For new visits, department is required for correct consultation fee (from Departments, not ServicePricing)
    if is_new_visit_flag and not department:
        params = [f"new_visit=true", f"return_to={return_to or 'triage'}"]
        if opd_visit_id:
            params.append(f"opd_visit_id={opd_visit_id}")
        if visit_type:
            params.append(f"visit_type={visit_type}")
        return RedirectResponse(
            url=str(request.url_for("collect_payment", patient_id=patient_id)) + "?" + "&".join(params),
            status_code=302
        )
    
    # For new visits, we need to find or create a NEW charge (not use old paid charges)
    if is_new_visit_flag:
        # Check for existing UNPAID charges for this new visit
        # Don't reuse old paid charges - each visit needs its own charge
        today = date.today()
        existing_query = db.query(Charge).join(Invoice).filter(
            Invoice.patient_id == patient_id,
            Charge.charge_type == ChargeType.CONSULTATION,
            Charge.encounter_id.is_(None),
            Invoice.is_active == True,
            Invoice.balance > Decimal('0'),
            Invoice.status != InvoiceStatus.PAID,
            func.date(Charge.created_at) == today
        )
        if opd_visit_id:
            existing_query = existing_query.filter(
                (Invoice.opd_visit_id == opd_visit_id) | (Charge.opd_visit_id == opd_visit_id)
            )
        existing_charge = existing_query.order_by(Charge.created_at.desc()).first()
        
        if existing_charge:
            # Department is required (enforced above); ensure charge amount matches department price (with revisit discount)
            from app.services.charge_automation import get_consultation_price_for_department
            has_prev, revisit_pct = _get_revisit_info(db, patient_id)
            visit_type_for_price = None
            if visit_type and str(visit_type).strip().lower() in ("revisit", "follow_up"):
                visit_type_for_price = "revisit"
            elif visit_type and str(visit_type).strip().lower() == "new":
                visit_type_for_price = None
            elif has_prev and revisit_pct is not None:
                visit_type_for_price = "revisit"
            correct_price = get_consultation_price_for_department(
                db, department_name=department,
                visit_type=visit_type_for_price, revisit_follow_up_percentage=revisit_pct
            )
            if abs(float(existing_charge.total_amount) - float(correct_price)) > 0.01:
                from app.crud import billing_crud
                from app.schemas.billing_schemas import ChargeUpdate
                updated = billing_crud.update_charge(db, existing_charge.id, ChargeUpdate(unit_price=correct_price))
                if updated:
                    existing_charge = updated
                    db.refresh(existing_charge.invoice)
            
            charge = existing_charge
            invoice = existing_charge.invoice
            payment_paid = False  # Unpaid charge requires payment
        else:
            # Create a new charge via create_charge_for_consultation (may return existing charge from triage etc.)
            from app.services.charge_automation import create_charge_for_consultation
            from app.crud import opd_crud
            vt_param = None
            if visit_type and str(visit_type).strip().lower() in ("revisit", "follow_up"):
                vt_param = "revisit"
            elif visit_type and str(visit_type).strip().lower() == "new":
                vt_param = "new"
            new_charge = create_charge_for_consultation(
                db, patient_id, current_user.id,
                encounter_id=encounter_id,
                opd_visit_id=opd_visit_id,
                department_name=department,
                visit_type=vt_param
            )
            if new_charge:
                charge = new_charge
                invoice = new_charge.invoice
                # Verify amount: create_charge_for_consultation may return existing charge with wrong price
                if department:
                    from app.services.charge_automation import get_consultation_price_for_department
                    has_prev, revisit_pct = _get_revisit_info(db, patient_id)
                    visit_type_for_price = vt_param if vt_param else ("revisit" if has_prev and revisit_pct else None)
                    correct_price = get_consultation_price_for_department(
                        db, department_name=department,
                        visit_type=visit_type_for_price, revisit_follow_up_percentage=revisit_pct
                    )
                    if abs(float(charge.total_amount) - float(correct_price)) > 0.01:
                        from app.crud import billing_crud
                        from app.schemas.billing_schemas import ChargeUpdate
                        updated = billing_crud.update_charge(db, charge.id, ChargeUpdate(unit_price=correct_price))
                        if updated:
                            charge = updated
                            db.refresh(charge.invoice)
                if opd_visit_id:
                    opd_crud.mark_consultation_charge_created(db, opd_visit_id)
            else:
                # Fallback to get_or_create_service_charge (uses department price with revisit discount when applicable)
                from app.services.charge_automation import get_consultation_price_for_department
                has_prev, revisit_pct = _get_revisit_info(db, patient_id)
                visit_type_for_price = vt_param if vt_param else ("revisit" if has_prev and revisit_pct else None)
                if department:
                    service_price = get_consultation_price_for_department(
                        db, department_name=department,
                        visit_type=visit_type_for_price, revisit_follow_up_percentage=revisit_pct
                    )
                else:
                    service_price = get_service_price(db, "Consultation", "consultation", DEFAULT_CONSULTATION_FEE)
                charge, invoice = get_or_create_service_charge(
                    db, patient_id, ChargeType.CONSULTATION,
                    "Consultation Fee (Covers Vitals & Initial Encounter)",
                    service_price,
                    encounter_id=encounter_id,
                    opd_visit_id=opd_visit_id,
                    created_by_id=current_user.id
                )
                if opd_visit_id:
                    opd_crud.mark_consultation_charge_created(db, opd_visit_id)
            payment_paid = False  # New charge requires payment
    else:
        # Not a new visit - check if already paid
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.CONSULTATION, encounter_id=encounter_id
        )
        
        if payment_paid:
            # Already paid, redirect back
            redirect_url = _patient_return_path(patient_id, return_to) or f"/patients/{patient_id}/encounters/new"
            if new_visit:
                redirect_url += f"?new_visit={new_visit}" if "?" not in redirect_url else f"&new_visit={new_visit}"
            return RedirectResponse(url=redirect_url, status_code=302)
        
        # Get or create charge (use department-based price with revisit discount when department provided)
        if not charge:
            from app.services.charge_automation import get_consultation_price_for_department
            has_prev, revisit_pct = _get_revisit_info(db, patient_id)
            visit_type_for_price = None
            if visit_type and str(visit_type).strip().lower() in ("revisit", "follow_up"):
                visit_type_for_price = "revisit"
            elif visit_type and str(visit_type).strip().lower() != "new" and has_prev and revisit_pct:
                visit_type_for_price = "revisit"
                service_price = get_consultation_price_for_department(
                    db, department_name=department,
                    visit_type=visit_type_for_price, revisit_follow_up_percentage=revisit_pct
                )
            else:
                service_price = get_service_price(db, "Consultation", "consultation", DEFAULT_CONSULTATION_FEE)
            charge, invoice = get_or_create_service_charge(
                db, patient_id, ChargeType.CONSULTATION,
                "Consultation Fee (Covers Vitals & Initial Encounter)",
                service_price,
                encounter_id=encounter_id,
                opd_visit_id=opd_visit_id,
                created_by_id=current_user.id
            )
    
    # When encounter_id is set, pay full visit invoice (consultation + lab)
    amount_due = None
    if encounter_id and invoice and invoice.balance and invoice.balance > Decimal("0"):
        amount_due = float(invoice.balance)

    context = {
        "request": request,
        "title": "Pay Consultation Fee" if not encounter_id else "Pay Visit (Consultation + Lab)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "charge": charge,
        "invoice": invoice,
        "service_type": "consultation",
        "encounter_id": encounter_id,
        "return_to": return_to or "encounters/new",
        "new_visit": new_visit,
        "amount_due": amount_due,
        "from_lab": from_lab,
        "from_registration": from_registration,
        "department": department,
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
    new_visit: Optional[str] = Form(None),
    from_lab: Optional[int] = Form(None),
    from_registration: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
):
    """Process payment for consultation fee (or full visit = consultation + lab)."""
    from app.models.billing_models import Invoice, Charge
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
            invoice.opd_visit_id = active_opd_visit.id
            db.commit()
            db.refresh(invoice)

    # Create payment (records in paid bills at invoice level)
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        patient_id=patient_id,
        amount=amount_decimal,
        payment_method="cash",
        status=PaymentStatus.COMPLETED,
        notes="Consultation fee payment"
    )
    payment = billing_crud.create_payment(db, payment_data, current_user.id)

    # Allocate payment to consultation charge so it appears in paid bills / charge-level tracking
    consultation_charge = db.query(Charge).filter(
        Charge.invoice_id == invoice_id,
        Charge.charge_type == ChargeType.CONSULTATION,
    ).first()
    if consultation_charge:
        billing_crud.allocate_payment_to_charge(db, payment.id, consultation_charge.id, amount_decimal)

    # Ensure OPD visit payment status is synced immediately after payment
    if invoice.opd_visit_id:
        opd_crud.sync_opd_visit_payment_status(db, invoice.opd_visit_id)
    elif active_opd_visit:
        opd_crud.sync_opd_visit_payment_status(db, active_opd_visit.id)

    # Create receipt so it appears in receipts and can be printed
    try:
        receipt = billing_crud.create_receipt(db, payment.id, current_user.id)
        receipt_number = receipt.receipt_number
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error creating receipt for payment %s: %s", payment.id, e)
        receipt_number = payment.receipt_number or "N/A"

    # Send SMS notification to patient for consultation payment
    try:
        from app.services.sms_onlinegh_service import send_personalized_sms_notification
        patient = invoice.patient
        if patient and patient.phone_number:
            message_template = "Hello {$name}. Payment of GHS {$amount} received. Receipt: {$receipt_number}. Invoice Balance: GHS {$balance}. Thank you!"
            destinations = [{
                "number": patient.phone_number,
                "values": [
                    f"{patient.first_name} {patient.last_name}",
                    float(payment.amount),
                    receipt_number,
                    float(invoice.balance) if invoice.balance else 0.00
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
    except Exception as sms_error:
        print(f"Warning: Unable to send consultation payment SMS: {sms_error}")

    # Add patient to vitals queue immediately after payment when going to triage
    is_from_registration = from_registration and str(from_registration).strip() in ("1", "true", "yes")
    if is_from_registration or return_to == "triage":
        department_name = (department or "").strip() or "General Medicine"
        try:
            from app.crud import appointment_crud
            from app.schemas.appointment_schemas import QueueCreate
            from app.models.appointment_models import VisitType, OPDQueue, QueueStatus
            from sqlalchemy import func
            from datetime import date
            today = date.today()
            existing = (
                db.query(OPDQueue)
                .filter(
                    OPDQueue.patient_id == patient_id,
                    OPDQueue.is_active == True,
                    OPDQueue.status.in_([QueueStatus.WAITING.value, QueueStatus.IN_PROGRESS.value]),
                )
                .filter(func.date(OPDQueue.created_at) == today)
                .first()
            )
            if not existing:
                queue_data = QueueCreate(
                    patient_id=patient_id,
                    department=department_name,
                    department_type="opd",
                    visit_type=VisitType.WALK_IN,
                    priority=5,
                    chief_complaint=None,
                    notes="Added to vitals queue after payment",
                    assigned_clinician_id=None,
                    created_by_id=current_user.id,
                )
                appointment_crud.create_queue_entry(db, queue_data)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Failed to add patient %s to vitals queue after payment: %s", patient_id, e)
    
    # From registration: redirect to receipt
    if is_from_registration:
        department_name = (department or "").strip() or "General Medicine"
        redirect_url = f"/billing/receipt/{payment.id}?from_registration=1&patient_id={patient_id}&department={quote(department_name)}"
        return RedirectResponse(url=redirect_url, status_code=302)

    # Returning cash patient (revisit): redirect to receipt; patient already added to vitals queue
    if return_to == "triage":
        department_name = (department or "").strip() or "General Medicine"
        opd_id = invoice.opd_visit_id or (active_opd_visit.id if active_opd_visit else None)
        extra = f"&opd_visit_id={opd_id}" if opd_id else ""
        redirect_url = f"/billing/receipt/{payment.id}?return_to=triage&patient_id={patient_id}&department={quote(department_name)}{extra}"
        return RedirectResponse(url=redirect_url, status_code=302)

    # Redirect: from_lab = back to lab order; else return_to / encounter_id / default
    new_visit_param = f"&new_visit={new_visit}" if new_visit else ""
    if from_lab is not None:
        redirect_url = f"/api/v1/ancillary/lab/orders/{from_lab}?status=payment_success&receipt={receipt_number}"
    elif return_to:
        base = _patient_return_path(patient_id, return_to) or f"/patients/{patient_id}/encounters/new"
        redirect_url = f"{base}?status=payment_success&receipt={receipt_number}{new_visit_param}".rstrip("&")
    elif encounter_id:
        redirect_url = f"/encounters/{encounter_id}?status=payment_success&receipt={receipt_number}{new_visit_param}"
    else:
        redirect_url = f"/patients/{patient_id}/encounters/new?status=payment_success&receipt={receipt_number}{new_visit_param}"
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
        redirect_url = f"/api/v1/ancillary/radiology/orders/{order_id}"
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
        redirect_url = f"/api/v1/ancillary/radiology/orders/{order_id}"
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
        "return_to": return_to or f"api/v1/ancillary/radiology/orders/{order_id}"
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
    
    redirect_url = f"/api/v1/ancillary/radiology/orders/{order_id}?status=payment_success" if order_id else f"/patients/{patient_id}?status=payment_success"
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
        "return_to": return_to or f"api/v1/ancillary/pharmacy/prescriptions/{prescription_id}"
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
        redirect_url = f"/api/v1/ancillary/lab/orders/{order_id}"
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
        redirect_url = f"/api/v1/ancillary/lab/orders/{order_id}"
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
        "return_to": return_to or f"api/v1/ancillary/lab/orders/{order_id}"
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
    
    redirect_url = f"/api/v1/ancillary/lab/orders/{order_id}?status=payment_success" if order_id else f"/patients/{patient_id}?status=payment_success"
    if return_to:
        redirect_url = f"/{return_to}?status=payment_success"
    
    return RedirectResponse(url=redirect_url, status_code=302)

