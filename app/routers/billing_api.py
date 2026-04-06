from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func
from typing import Optional, List
from decimal import Decimal
from collections import OrderedDict
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.billing_models import Invoice, Payment, InvoiceStatus, PaymentMethod, ChargeType, RefundStatus
from app.models.patient_models import Patient
from app.crud import billing_crud
from app.schemas.billing_schemas import InvoiceCreate, PaymentCreate, RefundCreate, RefundUpdate, RefundApprove, RefundReject, RefundProcess, RefundCancel, RefundPolicyCreate, RefundPolicyUpdate

router = APIRouter(tags=["Billing"])
# Register the age filter
from datetime import date
def calculate_age(dob):
    if not dob:
        return None
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age
templates.env.filters["age"] = calculate_age


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
    patient_query: Optional[str] = Query(None, description="Search by patient name, number, or phone"),
    sort_by: Optional[str] = Query("balance", description="Sort by: balance, date, name, oldest"),
    page: Optional[int] = Query(1, ge=1, description="Page number"),
    page_size: Optional[int] = Query(20, ge=1, le=100, description="Items per page"),
    payment_type: Optional[str] = Query(None, description="Filter by payment type: cash, insurance, nhis, private_insurance"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)")
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
        # Normalize to lowercase to match database enum values
        status_filter = status_filter.lower()
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
    
    # Filter by date range if provided
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Invoice.invoice_date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            # Add one day to include the end date
            from datetime import timedelta
            to_date = to_date + timedelta(days=1)
            query = query.filter(Invoice.invoice_date < to_date)
        except ValueError:
            pass
    
    # Filter by payment type if provided
    if payment_type:
        # Use lowercase string values to match database enum values
        payment_types_map = {
            "cash": ["cash", "mobile_money", "card", "bank_transfer"],
            "insurance": ["nhis", "private_insurance"],
            "nhis": ["nhis"],
            "private_insurance": ["private_insurance"]
        }
        if payment_type in payment_types_map:
            payment_method_values = payment_types_map[payment_type]
            # Filter invoices by payment mechanism using string values
            # Cast to string for comparison to avoid enum issues
            from sqlalchemy import cast, String
            query = query.join(Invoice.patient).filter(
                or_(
                    cast(Invoice.payment_mechanism, String).in_(payment_method_values),
                    cast(Patient.payment_mechanism, String).in_(payment_method_values)
                )
            )
    
    # Get total count for pagination before applying limit/offset
    total_count = query.filter(Invoice.is_active == True).count()
    
    # Calculate offset for pagination
    offset = (page - 1) * page_size
    
    # Apply sorting based on sort_by parameter
    if sort_by == "date":
        query = query.order_by(Invoice.invoice_date.desc())
    elif sort_by == "oldest":
        query = query.order_by(Invoice.invoice_date.asc())
    elif sort_by == "name":
        query = query.join(Invoice.patient).order_by(Patient.last_name.asc(), Patient.first_name.asc())
    else:  # balance (default)
        # For balance sorting, we'll sort after aggregation
        query = query.order_by(Invoice.invoice_date.desc())
    
    invoices = query.filter(Invoice.is_active == True).offset(offset).limit(page_size).all()
    
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
    
    # Sort based on sort_by parameter
    if sort_by == "name":
        patient_summary_list.sort(key=lambda s: s["patient_name"].lower())
    elif sort_by == "oldest":
        # For oldest, we keep the original invoice order which is by date asc
        patient_summary_list.sort(key=lambda s: s["total_balance"], reverse=False)
    else:  # balance (default) or date
        patient_summary_list.sort(key=lambda s: s["total_balance"], reverse=True)
    
    # Calculate pagination info
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    has_prev = page > 1
    has_next = page < total_pages
    
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
        "patient_query": patient_query or "",
        # New pagination and filter params
        "sort_by": sort_by,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "payment_type": payment_type,
        "date_from": date_from,
        "date_to": date_to
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
    from app.utils.charge_types_utils import get_charge_types
    from app.models.service_pricing_models import ServicePricing
    
    # Group service pricing by charge type
    service_pricing_by_charge_type = {}
    all_service_pricing = db.query(ServicePricing).filter(
        ServicePricing.is_active == True
    ).order_by(ServicePricing.charge_type, ServicePricing.service_name).all()
    
    for service in all_service_pricing:
        ct = service.charge_type
        if ct not in service_pricing_by_charge_type:
            service_pricing_by_charge_type[ct] = []
        service_pricing_by_charge_type[ct].append({
            "id": service.id,
            "service_name": service.service_name,
            "service_code": service.service_code,
            "unit_price": float(service.unit_price) if service.unit_price else 0,
            "description": service.description or service.service_name
        })
    
    context = {
        "request": request,
        "title": "Create Invoice",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "patient": patient,
        "encounter": encounter,
        "charge_types": [ct for ct in get_charge_types(db) if ct not in ['lab_test', 'pharmacy', 'other']],
        "payment_methods": [pm.value for pm in PaymentMethod],
        "services": all_services,  # All services for dropdown
        "service_pricing_by_charge_type": service_pricing_by_charge_type
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
    
    if has_charge_type and has_description and has_unit_price:
        try:
            charge_type_enum = ChargeType(charge_type.strip())
            quantity_int = int(quantity.strip()) if quantity and quantity.strip() else 1
            unit_price_dec = Decimal(unit_price.strip())
            discount_dec = Decimal(discount.strip()) if discount and discount.strip() else Decimal('0.00')
            tax_rate_dec = Decimal(tax_rate.strip()) if tax_rate and tax_rate.strip() else Decimal('0.00')
            
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
            else:
                # Skip zero or negative prices silently
                pass
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
    
    invoice = billing_crud.create_invoice(db, invoice_data, current_user.id)
    return RedirectResponse(
        url=f"/billing/invoices/{invoice.id}",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/billing/invoices/{invoice_id}", name="view_invoice")
def view_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Front Office", "Nurse"]))
):
    """
    View a specific invoice.
    """
    from app.models.billing_models import ChargePayment, Charge
    from app.crud import hospital_settings_crud, service_pricing_crud
    from app.models.procedure_catalog_models import ProcedureCatalog
    from app.models.service_pricing_models import ServicePricing
    from app.utils.charge_types_utils import get_charge_types
    
    invoice = db.query(Invoice).options(
        joinedload(Invoice.charges).joinedload(Charge.charge_payments),
        joinedload(Invoice.patient),
        joinedload(Invoice.payments)
    ).filter(Invoice.id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get hospital settings for branding
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Get active procedure catalogs for the Add Charge modal
    procedure_catalogs = db.query(ProcedureCatalog).filter(
        ProcedureCatalog.is_active == True
    ).order_by(ProcedureCatalog.procedure_name).all()
    procedure_catalog_list = [
        {
            "id": p.id, 
            "name": p.procedure_name, 
            "procedure_code": p.procedure_code,
            "procedure_category": p.procedure_category,
            "cash_price": float(p.cash_price) if p.cash_price else 0,
            "nhis_price": float(p.nhis_price) if p.nhis_price else 0,
            "nhis_covered": p.nhis_covered
        }
        for p in procedure_catalogs
    ]
    
    # Get charge types for the Add Charge modal dropdown
    # Filter out lab_test, pharmacy, and other as they are handled by specific services
    all_charge_types = get_charge_types(db)
    charge_types = [ct for ct in all_charge_types if ct not in ['lab_test', 'pharmacy', 'other']]
    
    # Get active service pricing grouped by charge type for the Add Charge modal
    all_service_pricing = db.query(ServicePricing).filter(
        ServicePricing.is_active == True
    ).order_by(ServicePricing.charge_type, ServicePricing.service_name).all()
    
    service_pricing_by_charge_type = {}
    for service in all_service_pricing:
        ct = service.charge_type
        if ct not in service_pricing_by_charge_type:
            service_pricing_by_charge_type[ct] = []
        service_pricing_by_charge_type[ct].append({
            "id": service.id,
            "service_name": service.service_name,
            "service_code": service.service_code,
            "unit_price": float(service.unit_price) if service.unit_price else 0,
            "description": service.description or service.service_name
        })
    
    context = {
        "request": request,
        "title": f"Invoice {invoice.invoice_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "invoice": invoice,
        "patient": invoice.patient,
        "hospital_settings": hospital_settings,
        "now": datetime.now(),
        "procedure_catalogs": procedure_catalog_list,
        "service_pricing_by_charge_type": service_pricing_by_charge_type,
        "charge_types": charge_types
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
    prescription_id: Optional[int] = Form(None),
    procedure_catalog_id: Optional[str] = Form(None)
):
    """
    Add a charge to an invoice.
    For procedure charges, if procedure_catalog_id is provided, the price is fetched
    from the procedure catalog and cannot be overridden.
    """
    from app.schemas.billing_schemas import ChargeCreate
    from app.models.procedure_catalog_models import ProcedureCatalog
    
    # Get payment mechanism from invoice to determine correct price
    invoice = billing_crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment_mechanism = invoice.payment_mechanism.value if invoice.payment_mechanism else "cash"
    
    # For procedure charges, enforce procedure catalog pricing
    final_unit_price = Decimal(unit_price)
    final_description = description
    
    # Convert procedure_catalog_id from string to int if not empty
    final_procedure_catalog_id = None
    if procedure_catalog_id and procedure_catalog_id.strip():
        try:
            final_procedure_catalog_id = int(procedure_catalog_id.strip())
        except ValueError:
            final_procedure_catalog_id = None
    
    if charge_type == "procedure" and final_procedure_catalog_id:
        # Fetch price from procedure catalog
        catalog = db.query(ProcedureCatalog).filter(
            ProcedureCatalog.id == final_procedure_catalog_id
        ).first()
        
        if catalog:
            # Use the appropriate price based on payment mechanism
            if payment_mechanism == "nhis" and catalog.nhis_covered:
                final_unit_price = catalog.nhis_price or catalog.cash_price
            elif payment_mechanism == "private_insurance" and catalog.private_insurance_covered:
                final_unit_price = catalog.private_insurance_price or catalog.cash_price
            else:
                final_unit_price = catalog.cash_price
            
            # Enhance description with procedure catalog details
            code_info = f" ({catalog.procedure_code})" if catalog.procedure_code else ""
            category_info = f" - {catalog.procedure_category}" if catalog.procedure_category else ""
            final_description = f"{catalog.procedure_name}{code_info}{category_info}"
        else:
            # Procedure catalog not found, use the provided price but log warning
            pass
    
    # Get charge type enum, handling custom charge types
    try:
        charge_type_enum = ChargeType(charge_type)
    except ValueError:
        # For custom charge types not in enum, use OTHER
        charge_type_enum = ChargeType.OTHER
    
    charge_data = ChargeCreate(
        charge_type=charge_type_enum,
        description=final_description,
        quantity=quantity,
        unit_price=final_unit_price,
        discount=Decimal(discount),
        tax_rate=Decimal(tax_rate),
        encounter_id=encounter_id,
        lab_order_id=lab_order_id,
        radiology_order_id=radiology_order_id,
        prescription_id=prescription_id,
        procedure_catalog_id=final_procedure_catalog_id
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
    current_user = Depends(role_required(["Admin", "Finance", "Front Office", "Nurse"])),
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
    invoice_id: Optional[int] = Query(None),
    from_registration: Optional[str] = Query(None),
    return_to: Optional[str] = Query(None),
    patient_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
):
    """Print receipt for a payment. Patient added to triage only after receipt printed (via button)."""
    from app.crud import hospital_settings_crud

    payment = billing_crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if not invoice_id:
        invoice_id = payment.invoice_id

    invoice = billing_crud.get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pid = patient_id or invoice.patient_id
    dept = (department or "").strip() or "General Medicine"

    hospital_settings = hospital_settings_crud.get_hospital_settings(db)

    from app.models.billing_models import Receipt
    receipt = db.query(Receipt).filter(
        Receipt.payment_id == payment_id,
        Receipt.is_active == True
    ).first()

    # Post-payment nav buttons (patient is auto-added to vitals queue after payment)
    show_post_payment_buttons = pid and (
        from_registration and str(from_registration) in ("1", "true", "yes") or return_to == "triage"
    )
    patients_list_url = request.url_for("patients_list") if show_post_payment_buttons else None
    dashboard_url = request.url_for("dashboard") if show_post_payment_buttons else None

    context = {
        "request": request,
        "title": f"Receipt - {payment.payment_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "payment": payment,
        "receipt": receipt,
        "invoice": invoice,
        "patient": invoice.patient,
        "hospital_settings": hospital_settings,
        "from_registration": from_registration and str(from_registration) in ("1", "true", "yes"),
        "return_to_triage": return_to == "triage" and pid,
        "triage_patient_id": pid,
        "show_post_payment_buttons": show_post_payment_buttons,
        "patients_list_url": patients_list_url,
        "dashboard_url": dashboard_url,
    }
    return templates.TemplateResponse("billing/receipt.html", context)


@router.post("/billing/invoices/{invoice_id}/discount", name="apply_invoice_discount", status_code=status.HTTP_302_FOUND)
def apply_invoice_discount(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Accountant", "Billing Staff"])),
    discount_amount: float = Form(...),
    discount_reason: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """
    Apply a discount to an invoice.
    """
    from app.models.billing_models import Invoice, InvoiceStatus
    from decimal import Decimal
    
    # Get invoice
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Validate discount amount
    if discount_amount <= 0:
        raise HTTPException(status_code=400, detail="Discount amount must be greater than 0")
    
    if discount_amount > float(invoice.balance):
        raise HTTPException(status_code=400, detail=f"Discount cannot exceed invoice balance of GHS {invoice.balance}")
    
    # Apply discount
    current_discount = float(invoice.discount_amount) if invoice.discount_amount else 0
    invoice.discount_amount = Decimal(str(current_discount + discount_amount))
    invoice.balance = invoice.total_amount - invoice.paid_amount - invoice.discount_amount
    
    # Update status
    if invoice.balance <= 0:
        invoice.status = InvoiceStatus.PAID
    
    db.commit()
    db.refresh(invoice)
    
    # Redirect back to invoice
    return RedirectResponse(
        url=str(request.url_for('view_invoice', invoice_id=invoice_id)) + "?status=discount_applied",
        status_code=status.HTTP_302_FOUND
    )


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
    from app.utils.charge_types_utils import get_charge_types
    
    context = {
        "request": request,
        "title": f"Invoice - Encounter #{encounter_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "encounter": encounter,
        "patient": encounter.patient,
        "invoices": invoices,
        "charge_types": [ct for ct in get_charge_types(db) if ct not in ['lab_test', 'pharmacy', 'other']],
        "payment_methods": [pm.value for pm in PaymentMethod]
    }
    return templates.TemplateResponse("billing/encounter_invoice.html", context)


# ==================== Refund UI Routes ====================

@router.get("/billing/refunds", tags=["UI"], name="refunds_list")
def refunds_list(
    request: Request,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Render refunds list page"""
    refund_status = RefundStatus[status.upper()] if status else None
    refunds = billing_crud.get_refunds(db, status=refund_status) if refund_status else billing_crud.get_refunds(db)
    
    context = {
        "request": request,
        "title": "Refund Requests",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "refunds": refunds
    }
    return templates.TemplateResponse("billing/refunds_list.html", context)


@router.get("/billing/refund-policies", tags=["UI"], name="refund_policies")
def refund_policies(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Render refund policies page"""
    policies = billing_crud.get_refund_policies(db)
    
    context = {
        "request": request,
        "title": "Refund Policies",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "policies": policies
    }
    return templates.TemplateResponse("billing/refund_policies.html", context)


# ==================== Refund Policy API Endpoints ====================

@router.post("/refund-policies", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_refund_policy(
    policy_data: RefundPolicyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new refund policy"""
    policy = billing_crud.create_refund_policy(db, policy_data, current_user.id)
    return {"id": policy.id, "name": policy.name, "message": "Refund policy created successfully"}


@router.get("/refund-policies", response_model=List[dict])
def get_refund_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all refund policies"""
    policies = billing_crud.get_refund_policies(db, skip, limit)
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "is_active": p.is_active,
            "max_refund_amount": float(p.max_refund_amount) if p.max_refund_amount else None,
            "refund_window_days": p.refund_window_days,
            "auto_approve_threshold": float(p.auto_approve_threshold) if p.auto_approve_threshold else None,
            "requires_approval": p.requires_approval,
            "approval_level": p.approval_level
        }
        for p in policies
    ]


@router.get("/refund-policies/{policy_id}", response_model=dict)
def get_refund_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific refund policy"""
    policy = billing_crud.get_refund_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Refund policy not found")
    return {
        "id": policy.id,
        "name": policy.name,
        "description": policy.description,
        "is_active": policy.is_active,
        "max_refund_amount": float(policy.max_refund_amount) if policy.max_refund_amount else None,
        "refund_window_days": policy.refund_window_days,
        "auto_approve_threshold": float(policy.auto_approve_threshold) if policy.auto_approve_threshold else None,
        "requires_approval": policy.requires_approval,
        "approval_level": policy.approval_level
    }


@router.patch("/refund-policies/{policy_id}", response_model=dict)
def update_refund_policy(
    policy_id: int,
    policy_data: RefundPolicyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a refund policy"""
    policy = billing_crud.update_refund_policy(db, policy_id, policy_data)
    if not policy:
        raise HTTPException(status_code=404, detail="Refund policy not found")
    return {"id": policy.id, "name": policy.name, "message": "Refund policy updated successfully"}


# ==================== Refund API Endpoints ====================

@router.post("/billing/refunds", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_refund(
    refund_data: RefundCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new refund request"""
    try:
        refund = billing_crud.create_refund(db, refund_data, current_user.id)
        if not refund:
            raise HTTPException(status_code=404, detail="Payment or invoice not found")
        return {
            "id": refund.id,
            "refund_number": refund.refund_number,
            "status": refund.status.value,
            "message": "Refund request created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/billing/refunds", response_model=List[dict])
def get_refunds(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[RefundStatus] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all refunds with optional status filter"""
    refunds = billing_crud.get_refunds(db, skip, limit, status)
    return [
        {
            "id": r.id,
            "refund_number": r.refund_number,
            "invoice_id": r.invoice_id,
            "payment_id": r.payment_id,
            "patient_id": r.patient_id,
            "amount": float(r.amount),
            "reason": r.reason,
            "status": r.status.value,
            "request_date": r.request_date.isoformat() if r.request_date else None,
            "approval_date": r.approval_date.isoformat() if r.approval_date else None,
            "processed_date": r.processed_date.isoformat() if r.processed_date else None
        }
        for r in refunds
    ]


# Refund Statistics Endpoint - MUST be BEFORE /{refund_id} route
@router.get("/billing/refunds/statistics", response_model=dict)
def get_refund_statistics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get refund statistics for dashboard"""
    from sqlalchemy import func
    from app.models.billing_models import Refund, RefundStatus
    
    # Total counts by status - use Refund.status column, not the enum directly
    stats = db.query(
        Refund.status,
        func.count(Refund.id).label('count'),
        func.coalesce(func.sum(Refund.amount), 0).label('total_amount')
    ).group_by(Refund.status).all()
    
    status_breakdown = {}
    for status, count, total in stats:
        status_breakdown[status.value if hasattr(status, 'value') else str(status)] = {
            "count": count,
            "total_amount": float(total)
        }
    
    # Overall totals
    total_refunds = db.query(func.count(Refund.id)).scalar() or 0
    total_amount = db.query(func.coalesce(func.sum(Refund.amount), 0)).scalar() or 0
    
    # Pending count for urgent attention
    pending_count = db.query(func.count(Refund.id)).filter(
        Refund.status == RefundStatus.PENDING
    ).scalar() or 0
    
    return {
        "total_refunds": total_refunds,
        "total_amount": float(total_amount),
        "pending_count": pending_count,
        "status_breakdown": status_breakdown
    }


@router.get("/billing/refunds/{refund_id}", response_model=dict)
def get_refund(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific refund"""
    refund = billing_crud.get_refund(db, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    return {
        "id": refund.id,
        "refund_number": refund.refund_number,
        "invoice_id": refund.invoice_id,
        "payment_id": refund.payment_id,
        "patient_id": refund.patient_id,
        "amount": float(refund.amount),
        "reason": refund.reason,
        "status": refund.status.value,
        "refund_method": refund.refund_method.value if refund.refund_method else None,
        "transaction_reference": refund.transaction_reference,
        "rejection_reason": refund.rejection_reason,
        "notes": refund.notes,
        "request_date": refund.request_date.isoformat() if refund.request_date else None,
        "approval_date": refund.approval_date.isoformat() if refund.approval_date else None,
        "processed_date": refund.processed_date.isoformat() if refund.processed_date else None,
        "requested_by_id": refund.requested_by_id,
        "approved_by_id": refund.approved_by_id,
        "processed_by_id": refund.processed_by_id,
        "policy_id": refund.policy_id
    }


@router.get("/patients/{patient_id}/refunds", response_model=List[dict])
def get_patient_refunds(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all refunds for a patient"""
    refunds = billing_crud.get_patient_refunds(db, patient_id, skip, limit)
    return [
        {
            "id": r.id,
            "refund_number": r.refund_number,
            "invoice_id": r.invoice_id,
            "payment_id": r.payment_id,
            "amount": float(r.amount),
            "reason": r.reason,
            "status": r.status.value,
            "request_date": r.request_date.isoformat() if r.request_date else None
        }
        for r in refunds
    ]


@router.get("/invoices/{invoice_id}/refunds", response_model=List[dict])
def get_invoice_refunds(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all refunds for an invoice"""
    refunds = billing_crud.get_invoice_refunds(db, invoice_id)
    return [
        {
            "id": r.id,
            "refund_number": r.refund_number,
            "payment_id": r.payment_id,
            "patient_id": r.patient_id,
            "amount": float(r.amount),
            "reason": r.reason,
            "status": r.status.value,
            "request_date": r.request_date.isoformat() if r.request_date else None
        }
        for r in refunds
    ]


@router.delete("/billing/invoices/by-number/{invoice_number}", response_model=dict)
def delete_invoice_by_number(
    invoice_number: str,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """
    Delete (void) an invoice by invoice number (e.g., INV-20260304-0007).
    Only allows deletion of invoices that are not fully paid.
    """
    # Find the invoice by invoice number
    db_invoice = db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_number} not found")
    
    # Check if invoice has payments - if so, cannot delete
    if db_invoice.payments and len(db_invoice.payments) > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete invoice with payments. Please process a refund first."
        )
    
    # Check if invoice is PAID - if so, cannot delete
    if db_invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete a paid invoice. Please process a refund first."
        )
    
    # Use the CRUD function to soft delete
    success = billing_crud.delete_invoice(db, db_invoice.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete invoice")
    
    return {
        "message": f"Invoice {invoice_number} deleted successfully",
        "invoice_id": db_invoice.id,
        "invoice_number": invoice_number
    }


@router.delete("/billing/invoices/{invoice_id}", response_model=dict)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """
    Delete (void) an invoice by ID.
    Only allows deletion of invoices that are not fully paid.
    """
    # First, find the invoice by ID
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Check if invoice has payments - if so, cannot delete
    if db_invoice.payments and len(db_invoice.payments) > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete invoice with payments. Please process a refund first."
        )
    
    # Check if invoice is PAID - if so, cannot delete
    if db_invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete a paid invoice. Please process a refund first."
        )
    
    # Use the CRUD function to soft delete
    success = billing_crud.delete_invoice(db, invoice_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete invoice")
    
    return {
        "message": f"Invoice {db_invoice.invoice_number} deleted successfully",
        "invoice_id": invoice_id,
        "invoice_number": db_invoice.invoice_number
    }


@router.patch("/billing/refunds/{refund_id}/approve", response_model=dict)
def approve_refund(
    refund_id: int,
    data: RefundApprove,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Approve a refund request"""
    try:
        refund = billing_crud.approve_refund(db, refund_id, current_user.id, data.notes)
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found")
        return {
            "id": refund.id,
            "refund_number": refund.refund_number,
            "status": refund.status.value,
            "message": "Refund approved successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/billing/refunds/{refund_id}/reject", response_model=dict)
def reject_refund(
    refund_id: int,
    data: RefundReject,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Reject a refund request"""
    try:
        refund = billing_crud.reject_refund(db, refund_id, current_user.id, data.rejection_reason, data.notes)
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found")
        return {
            "id": refund.id,
            "refund_number": refund.refund_number,
            "status": refund.status.value,
            "message": "Refund rejected successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/billing/refunds/{refund_id}/process", response_model=dict)
def process_refund(
    refund_id: int,
    data: RefundProcess,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Process a refund - mark as processed and update invoice/payment status"""
    try:
        refund = billing_crud.process_refund(
            db, refund_id, current_user.id, 
            data.refund_method, data.transaction_reference, data.notes
        )
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found")
        return {
            "id": refund.id,
            "refund_number": refund.refund_number,
            "status": refund.status.value,
            "message": "Refund processed successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

