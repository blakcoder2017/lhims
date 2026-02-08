from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func
from typing import Optional, List
from decimal import Decimal
from collections import OrderedDict

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.billing_models import Invoice, Payment, InvoiceStatus, PaymentMethod, ChargeType
from app.models.patient_models import Patient
from app.crud import billing_crud
from app.schemas.billing_schemas import InvoiceCreate, PaymentCreate

router = APIRouter(tags=["Billing"])
templates = Jinja2Templates(directory="app/templates")


def _parse_invoice_ids(invoice_ids_param: str) -> List[int]:
    if not invoice_ids_param:
        return []
    ids = []
    for value in invoice_ids_param.split(","):
        value = value.strip()
        if not value:
            continue
        try:
            ids.append(int(value))
        except ValueError:
            continue
    return list(dict.fromkeys(ids))  # preserve order, remove duplicates


def _fetch_invoices_for_payment(db: Session, invoice_ids: List[int]) -> List[Invoice]:
    if not invoice_ids:
        return []
    invoices = db.query(Invoice).options(joinedload(Invoice.patient)).filter(
        Invoice.id.in_(invoice_ids),
        Invoice.is_active == True
    ).order_by(Invoice.invoice_date.asc()).all()
    return invoices


# Invoice Routes
@router.get("/billing/invoices", name="billing_dashboard")
def billing_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"])),
    status_filter: Optional[str] = Query(None, description="Filter by invoice status"),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    patient_query: Optional[str] = Query(None, description="Search by patient name, number, or phone")
):
    """
    Billing dashboard showing invoices.
    """
    query = db.query(Invoice).options(
        joinedload(Invoice.patient),
        joinedload(Invoice.created_by)
    )
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = InvoiceStatus(status_filter)
            query = query.filter(Invoice.status == status_enum.value)
        except ValueError:
            pass
    
    # Filter by patient if provided
    if patient_id:
        query = query.filter(Invoice.patient_id == patient_id)
    
    if patient_query:
        search_term = f"%{patient_query.strip()}%"
        query = query.join(Invoice.patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                func.concat(Patient.first_name, " ", Patient.last_name).ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term)
            )
        )
    
    invoices = query.filter(Invoice.is_active == True).order_by(Invoice.invoice_date.desc()).limit(100).all()
    
    # Aggregate invoices per patient to present consolidated billing view
    patient_summaries = OrderedDict()
    status_priority = {
        InvoiceStatus.PAID.value: 0,
        InvoiceStatus.PARTIALLY_PAID.value: 1,
        InvoiceStatus.PENDING.value: 2,
        InvoiceStatus.DRAFT.value: 3
    }
    overall_totals = {
        "invoice_count": 0,
        "open_invoices": 0,
        "total_billed": Decimal("0.00"),
        "total_paid": Decimal("0.00"),
        "total_balance": Decimal("0.00")
    }
    
    for invoice in invoices:
        patient = invoice.patient
        if not patient:
            continue
        
        patient_id_key = patient.id
        if patient_id_key not in patient_summaries:
            # Get patient payment mechanism
            patient_payment_mechanism = None
            if patient.payment_mechanism:
                patient_payment_mechanism = getattr(patient.payment_mechanism, "value", patient.payment_mechanism)
            
            patient_summaries[patient_id_key] = {
                "patient_id": patient.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "patient_number": patient.patient_number or "N/A",
                "patient_payment_mechanism": patient_payment_mechanism,
                "is_insurance_patient": patient_payment_mechanism in ["nhis", "private_insurance"],
                "invoice_count": 0,
                "open_invoices": 0,
                "total_billed": Decimal("0.00"),
                "total_paid": Decimal("0.00"),
                "total_balance": Decimal("0.00"),
                "payment_methods": set(),
                "status_counts": {},
                "all_invoice_ids": [],
                "payable_invoice_ids": [],
            }
        
        entry = patient_summaries[patient_id_key]
        billed = invoice.total_amount or Decimal("0.00")
        paid = invoice.paid_amount or Decimal("0.00")
        balance = invoice.balance if invoice.balance is not None else (billed - paid)
        
        entry["invoice_count"] += 1
        entry["total_billed"] += billed
        entry["total_paid"] += paid
        entry["total_balance"] += balance
        if balance > 0:
            entry["open_invoices"] += 1
        
        payment_label = None
        if invoice.payment_mechanism:
            payment_label = getattr(invoice.payment_mechanism, "value", invoice.payment_mechanism)
        elif patient.payment_mechanism:
            payment_label = getattr(patient.payment_mechanism, "value", patient.payment_mechanism)
        entry["payment_methods"].add(payment_label or "Unspecified")
        
        status_value = getattr(invoice.status, "value", invoice.status)
        entry["status_counts"][status_value] = entry["status_counts"].get(status_value, 0) + 1
        entry["all_invoice_ids"].append(invoice.id)
        if balance > 0:
            entry["payable_invoice_ids"].append(invoice.id)
        
        overall_totals["invoice_count"] += 1
        overall_totals["total_billed"] += billed
        overall_totals["total_paid"] += paid
        overall_totals["total_balance"] += balance
        if balance > 0:
            overall_totals["open_invoices"] += 1
    
    patient_summary_list = []
    for summary in patient_summaries.values():
        summary["payment_label"] = ", ".join(sorted(summary["payment_methods"])) if summary["payment_methods"] else "Unspecified"
        status_list = [
            {
                "key": status_key,
                "label": status_key.replace("_", " ").title(),
                "count": count,
                "priority": status_priority.get(status_key, 99)
            }
            for status_key, count in summary["status_counts"].items()
        ]
        summary["status_list"] = sorted(status_list, key=lambda s: s["priority"])
        patient_summary_list.append(summary)
    
    # Sort by outstanding balance descending
    patient_summary_list.sort(key=lambda s: s["total_balance"], reverse=True)
    
    patient_filter = None
    if patient_id:
        patient_filter = db.query(Patient).filter(Patient.id == patient_id).first()
    
    context = {
        "request": request,
        "title": "Billing & Invoices",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "invoices": invoices,
        "patient_summaries": patient_summary_list,
        "billing_totals": overall_totals,
        "status_filter": status_filter,
        "patient_id": patient_id,
        "patient_filter": patient_filter,
        "patient_query": patient_query or ""
    }
    return templates.TemplateResponse("billing/invoices_dashboard.html", context)


@router.get("/billing/pay-selected", name="pay_selected_invoices_page")
def pay_selected_invoices_page(
    request: Request,
    invoice_ids: str = Query(..., description="Comma separated invoice IDs"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"]))
):
    ids = _parse_invoice_ids(invoice_ids)
    invoices = _fetch_invoices_for_payment(db, ids)
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for payment.")
    
    patient_ids = {inv.patient_id for inv in invoices if inv.patient_id}
    if len(patient_ids) != 1:
        raise HTTPException(status_code=400, detail="Invoices must belong to the same patient.")
    
    outstanding_invoices = []
    total_balance = Decimal("0.00")
    for inv in invoices:
        balance = inv.balance
        if balance is None:
            balance = (inv.total_amount or Decimal("0.00")) - (inv.paid_amount or Decimal("0.00"))
        balance = max(balance, Decimal("0.00"))
        if balance > 0:
            outstanding_invoices.append({"invoice": inv, "balance": balance})
            total_balance += balance
    
    if total_balance <= 0:
        raise HTTPException(status_code=400, detail="Selected invoices are already settled.")
    
    patient = invoices[0].patient
    payment_methods = [pm.value for pm in PaymentMethod]
    
    context = {
        "request": request,
        "title": "Pay Selected Invoices",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "outstanding_invoices": outstanding_invoices,
        "total_balance": total_balance,
        "invoice_ids_param": ",".join(str(inv["invoice"].id) for inv in outstanding_invoices),
        "payment_methods": payment_methods
    }
    return templates.TemplateResponse("billing/pay_selected_invoices.html", context)


@router.post("/billing/pay-selected", name="process_selected_invoices_payment", status_code=status.HTTP_302_FOUND)
def process_selected_invoices_payment(
    request: Request,
    invoice_ids: str = Form(...),
    amount: str = Form(...),
    payment_method: str = Form(...),
    transaction_reference: Optional[str] = Form(None),
    receipt_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"]))
):
    ids = _parse_invoice_ids(invoice_ids)
    invoices = _fetch_invoices_for_payment(db, ids)
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for payment.")
    
    patient_ids = {inv.patient_id for inv in invoices if inv.patient_id}
    if len(patient_ids) != 1:
        raise HTTPException(status_code=400, detail="Invoices must belong to the same patient.")
    
    outstanding = []
    total_balance = Decimal("0.00")
    for inv in invoices:
        balance = inv.balance
        if balance is None:
            balance = (inv.total_amount or Decimal("0.00")) - (inv.paid_amount or Decimal("0.00"))
        balance = max(balance, Decimal("0.00"))
        if balance > 0:
            outstanding.append((inv, balance))
            total_balance += balance
    
    if total_balance <= 0:
        raise HTTPException(status_code=400, detail="Selected invoices are already settled.")
    
    try:
        pay_amount = Decimal(amount)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment amount.")
    
    if pay_amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero.")
    
    pay_amount = min(pay_amount, total_balance)
    remaining = pay_amount
    try:
        payment_method_enum = PaymentMethod(payment_method)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment method.")
    
    for invoice, balance in outstanding:
        if remaining <= 0:
            break
        portion = balance if balance <= remaining else remaining
        if portion <= 0:
            continue
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=portion,
            payment_method=payment_method_enum,
            transaction_reference=transaction_reference,
            receipt_number=receipt_number or None,
            notes=notes
        )
        billing_crud.create_payment(db, payment_data, current_user.id)
        remaining -= portion
    
    status_message = "payment_success"
    return RedirectResponse(
        url=f"/billing/invoices?status={status_message}&paid_amount={float(pay_amount):.2f}",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/billing/invoices/create", name="create_invoice_page")
def create_invoice_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"])),
    patient_id: Optional[int] = Query(None),
    encounter_id: Optional[int] = Query(None)
):
    """
    Page for creating a new invoice.
    """
    from app.crud import patient_crud, encounter_crud, service_pricing_crud
    
    patient = None
    encounter = None
    
    if patient_id:
        patient = patient_crud.get_patient(db, patient_id)
    if encounter_id:
        encounter = encounter_crud.get_encounter(db, encounter_id)
        if encounter and not patient:
            patient = encounter.patient
    
    # Load all active service pricing for service selection
    all_services = service_pricing_crud.get_all_service_pricing(db, skip=0, limit=1000, include_inactive=False)
    
    context = {
        "request": request,
        "title": "Create Invoice",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "encounter": encounter,
        "charge_types": [ct.value for ct in ChargeType],
        "payment_methods": [pm.value for pm in PaymentMethod],
        "services": all_services  # All services for dropdown
    }
    return templates.TemplateResponse("billing/create_invoice.html", context)


@router.post("/billing/invoices/create", name="create_invoice", status_code=status.HTTP_302_FOUND)
def create_invoice(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"])),
    patient_id: int = Form(...),
    encounter_id: Optional[str] = Form(None),
    appointment_id: Optional[str] = Form(None),
    payment_mechanism: Optional[str] = Form(None),
    nhis_number: Optional[str] = Form(None),
    insurance_provider: Optional[str] = Form(None),
    insurance_policy_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    # Charge fields (optional - if provided, a charge will be created)
    charge_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    quantity: Optional[str] = Form("1"),
    unit_price: Optional[str] = Form(None),
    discount: Optional[str] = Form("0.00"),
    tax_rate: Optional[str] = Form("0.00")
):
    """
    Create a new invoice with optional initial charge.
    """
    from app.schemas.billing_schemas import InvoiceCreate, ChargeCreate
    
    # Convert empty strings to None for optional integer fields
    encounter_id_int = None
    if encounter_id and encounter_id.strip():
        try:
            encounter_id_int = int(encounter_id)
        except (ValueError, TypeError):
            encounter_id_int = None
    
    appointment_id_int = None
    if appointment_id and appointment_id.strip():
        try:
            appointment_id_int = int(appointment_id)
        except (ValueError, TypeError):
            appointment_id_int = None
    
    # Prepare charges list
    charges = []
    
    # If charge fields are provided, create a charge
    # Check if charge fields are provided (not None and not empty strings)
    has_charge_type = charge_type and charge_type.strip()
    has_description = description and description.strip()
    has_unit_price = unit_price and unit_price.strip()
    
    # Debug logging (can be removed later)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Charge fields received - charge_type: {charge_type}, description: {description}, unit_price: {unit_price}")
    logger.info(f"Has charge fields - charge_type: {has_charge_type}, description: {has_description}, unit_price: {has_unit_price}")
    
    if has_charge_type and has_description and has_unit_price:
        try:
            charge_type_enum = ChargeType(charge_type.strip())
            quantity_int = int(quantity.strip()) if quantity and quantity.strip() else 1
            unit_price_dec = Decimal(unit_price.strip())
            discount_dec = Decimal(discount.strip()) if discount and discount.strip() else Decimal('0.00')
            tax_rate_dec = Decimal(tax_rate.strip()) if tax_rate and tax_rate.strip() else Decimal('0.00')
            
            logger.info(f"Creating charge - type: {charge_type_enum}, description: {description.strip()}, unit_price: {unit_price_dec}, quantity: {quantity_int}")
            
            if unit_price_dec > 0:
                charge_data = ChargeCreate(
                    charge_type=charge_type_enum,
                    description=description.strip(),
                    quantity=quantity_int,
                    unit_price=unit_price_dec,
                    discount=discount_dec,
                    tax_rate=tax_rate_dec,
                    encounter_id=encounter_id_int
                )
                charges.append(charge_data)
                logger.info(f"Charge added to charges list. Total charges: {len(charges)}")
            else:
                logger.warning(f"Unit price is 0 or negative: {unit_price_dec}")
        except (ValueError, TypeError) as e:
            # If charge creation fails, log error but continue without charge
            logger.error(f"Error creating charge: {e}", exc_info=True)
            pass
    else:
        logger.info("Charge fields not provided or incomplete - creating invoice without charge")
    
    invoice_data = InvoiceCreate(
        patient_id=patient_id,
        encounter_id=encounter_id_int,
        appointment_id=appointment_id_int,
        payment_mechanism=PaymentMethod(payment_mechanism) if payment_mechanism else None,
        nhis_number=nhis_number,
        insurance_provider=insurance_provider,
        insurance_policy_number=insurance_policy_number,
        notes=notes,
        charges=charges
    )
    
    logger.info(f"Creating invoice with {len(charges)} charge(s)")
    invoice = billing_crud.create_invoice(db, invoice_data, current_user.id)
    logger.info(f"Invoice created: {invoice.invoice_number}, Total: {invoice.total_amount}, Charges: {len(invoice.charges) if hasattr(invoice, 'charges') else 'N/A'}")
    
    return RedirectResponse(
        url=f"/billing/invoices/{invoice.id}",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/billing/invoices/{invoice_id}", name="view_invoice")
def view_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"]))
):
    """
    View a specific invoice.
    """
    from app.models.billing_models import ChargePayment, Charge
    invoice = db.query(Invoice).options(
        joinedload(Invoice.charges).joinedload(Charge.charge_payments),
        joinedload(Invoice.patient),
        joinedload(Invoice.payments)
    ).filter(Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    context = {
        "request": request,
        "title": f"Invoice {invoice.invoice_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "invoice": invoice,
        "patient": invoice.patient
    }
    return templates.TemplateResponse("billing/invoice_detail.html", context)


@router.post("/billing/invoices/{invoice_id}/add-charge", name="add_charge", status_code=status.HTTP_302_FOUND)
def add_charge(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"])),
    charge_type: str = Form(...),
    description: str = Form(...),
    quantity: int = Form(1),
    unit_price: str = Form(...),
    discount: str = Form("0.00"),
    tax_rate: str = Form("0.00"),
    encounter_id: Optional[int] = Form(None),
    lab_order_id: Optional[int] = Form(None),
    radiology_order_id: Optional[int] = Form(None),
    prescription_id: Optional[int] = Form(None)
):
    """
    Add a charge to an invoice.
    """
    from app.schemas.billing_schemas import ChargeCreate
    
    charge_data = ChargeCreate(
        charge_type=ChargeType(charge_type),
        description=description,
        quantity=quantity,
        unit_price=Decimal(unit_price),
        discount=Decimal(discount),
        tax_rate=Decimal(tax_rate),
        encounter_id=encounter_id,
        lab_order_id=lab_order_id,
        radiology_order_id=radiology_order_id,
        prescription_id=prescription_id
    )
    
    billing_crud.add_charge_to_invoice(db, invoice_id, charge_data)
    
    return RedirectResponse(
        url=f"/billing/invoices/{invoice_id}?status=charge_added",
        status_code=status.HTTP_302_FOUND
    )


# Payment Routes
@router.post("/billing/invoices/{invoice_id}/payment", name="process_payment", status_code=status.HTTP_302_FOUND)
async def process_payment(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"])),
    amount: str = Form(...),
    payment_method: str = Form(...),
    transaction_reference: Optional[str] = Form(None),
    receipt_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """
    Process a payment for an invoice.
    Supports paying individual charges or full invoice balance.
    """
    from app.models.billing_models import Charge, ChargePayment
    
    invoice = billing_crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment_amount = Decimal(amount)
    
    # Get form data to check for charge selections
    form_data = await request.form()
    charge_ids = form_data.getlist("charge_ids")  # Get list of selected charge IDs
    
    # Receipt number will be auto-generated if not provided
    payment_data = PaymentCreate(
        invoice_id=invoice_id,
        amount=payment_amount,
        payment_method=PaymentMethod(payment_method),
        transaction_reference=transaction_reference,
        receipt_number=receipt_number if receipt_number else None,  # Auto-generated if None
        notes=notes
    )
    
    payment = billing_crud.create_payment(db, payment_data, current_user.id)
    
    # Send SMS notification to patient
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
                    payment.receipt_number or "N/A",
                    float(invoice.balance) if invoice.balance else 0.00
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
    except Exception as sms_error:
        print(f"Warning: Unable to send payment SMS: {sms_error}")
    
    # If specific charges were selected, allocate payment to those charges
    if charge_ids:
        remaining_amount = payment_amount
        
        for charge_id_str in charge_ids:
            try:
                charge_id = int(charge_id_str)
            except (ValueError, TypeError):
                continue
                
            charge_amount_key = f"charge_amount_{charge_id}"
            if charge_amount_key in form_data:
                try:
                    charge_amount = Decimal(str(form_data[charge_amount_key]))
                except (ValueError, TypeError):
                    continue
                
                # Verify charge exists and belongs to invoice
                charge = db.query(Charge).filter(
                    Charge.id == charge_id,
                    Charge.invoice_id == invoice_id
                ).first()
                
                if charge and charge_amount > 0 and remaining_amount >= charge_amount:
                    # Calculate how much has already been paid for this charge
                    existing_payments = db.query(ChargePayment).filter(
                        ChargePayment.charge_id == charge_id,
                        ChargePayment.is_active == True
                    ).all()
                    already_paid = sum(cp.amount for cp in existing_payments)
                    charge_balance = charge.total_amount - already_paid
                    
                    # Only allocate up to the charge balance
                    allocation_amount = min(charge_amount, charge_balance, remaining_amount)
                    
                    if allocation_amount > 0:
                        charge_payment = ChargePayment(
                            payment_id=payment.id,
                            charge_id=charge_id,
                            amount=allocation_amount
                        )
                        db.add(charge_payment)
                        remaining_amount -= allocation_amount
        
        db.commit()
    
    # Redirect to receipt page after payment
    return RedirectResponse(
        url=f"/billing/receipt/{payment.id}?invoice_id={invoice_id}",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/billing/receipt/{payment_id}", name="print_receipt")
def print_receipt(
    request: Request,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office"])),
    invoice_id: Optional[int] = Query(None)
):
    """Print receipt for a payment"""
    from app.crud import hospital_settings_crud
    
    payment = billing_crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Get invoice if not provided
    if not invoice_id:
        invoice_id = payment.invoice_id
    
    invoice = billing_crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get hospital settings for receipt header
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Get receipt if exists
    from app.models.billing_models import Receipt
    receipt = db.query(Receipt).filter(
        Receipt.payment_id == payment_id,
        Receipt.is_active == True
    ).first()
    
    context = {
        "request": request,
        "title": f"Receipt - {payment.payment_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "payment": payment,
        "receipt": receipt,
        "invoice": invoice,
        "patient": invoice.patient,
        "hospital_settings": hospital_settings
    }
    return templates.TemplateResponse("billing/receipt.html", context)


@router.get("/billing/receipts/{receipt_number}", name="view_receipt")
def view_receipt(
    request: Request,
    receipt_number: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """View receipt by receipt number"""
    from app.crud import hospital_settings_crud
    from app.models.billing_models import Receipt
    
    receipt = db.query(Receipt).options(
        joinedload(Receipt.payment).joinedload(Payment.invoice).joinedload(Invoice.patient),
        joinedload(Receipt.patient),
        joinedload(Receipt.generated_by)
    ).filter(
        Receipt.receipt_number == receipt_number,
        Receipt.is_active == True
    ).first()
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    payment = receipt.payment
    invoice = receipt.invoice
    patient = receipt.patient
    
    # Get hospital settings for receipt header
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    context = {
        "request": request,
        "title": f"Receipt - {receipt_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "payment": payment,
        "receipt": receipt,
        "invoice": invoice,
        "patient": patient,
        "hospital_settings": hospital_settings
    }
    return templates.TemplateResponse("billing/receipt.html", context)


@router.get("/patients/{patient_id}/invoices", name="patient_invoices")
def patient_invoices(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    View all invoices for a patient.
    """
    from app.crud import patient_crud
    
    patient = patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    invoices = billing_crud.get_invoices_by_patient(db, patient_id)
    
    context = {
        "request": request,
        "title": f"Invoices - {patient.first_name} {patient.last_name}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "invoices": invoices
    }
    return templates.TemplateResponse("billing/patient_invoices.html", context)


@router.get("/encounters/{encounter_id}/invoice", name="encounter_invoice")
def encounter_invoice(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    View or create invoice for an encounter.
    """
    from app.crud import encounter_crud
    
    encounter = encounter_crud.get_encounter(db, encounter_id)
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Check if invoice already exists
    invoices = billing_crud.get_invoices_by_encounter(db, encounter_id)
    
    context = {
        "request": request,
        "title": f"Invoice - Encounter #{encounter_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounter": encounter,
        "patient": encounter.patient,
        "invoices": invoices,
        "charge_types": [ct.value for ct in ChargeType],
        "payment_methods": [pm.value for pm in PaymentMethod]
    }
    return templates.TemplateResponse("billing/encounter_invoice.html", context)

