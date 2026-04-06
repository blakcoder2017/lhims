from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, status
from fastapi.responses import HTMLResponse
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import String, func
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.user_models import User
from app.crud import billing_crud
from app.models.billing_models import Invoice, InvoiceStatus
from app.models.patient_models import Patient
from app.core.templates import templates

router = APIRouter(prefix="/billing/consolidated", tags=["Consolidated Receipts"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class InvoiceSearchResult(BaseModel):
    id: int
    invoice_number: str
    invoice_date: datetime
    patient_id: int
    patient_name: str
    total_amount: Decimal
    paid_amount: Decimal
    balance: Decimal
    status: str
    charge_type: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConsolidatedReceiptPreviewItem(BaseModel):
    invoice_id: int
    invoice_number: str
    invoice_date: datetime
    charge_type: Optional[str] = None
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    paid: Decimal
    balance: Decimal
    status: str
    charges: List[dict]


class ConsolidatedReceiptPreview(BaseModel):
    patient_id: int
    patient_name: str
    total_invoices: int
    total_amount: Decimal
    total_discount: Decimal
    total_paid: Decimal
    total_balance: Decimal
    invoices: List[ConsolidatedReceiptPreviewItem]


class ConsolidatedReceiptCreateRequest(BaseModel):
    invoice_ids: List[int]
    payment_method: str
    transaction_reference: Optional[str] = None


class ConsolidatedReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    patient_id: int
    patient_name: str
    total_invoices: int
    total_amount: Decimal
    total_paid: Decimal
    total_discount: Decimal
    total_balance: Decimal
    primary_payment_method: str
    status: str
    generated_at: datetime
    printed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ReprintRequest(BaseModel):
    reason: str
    authorized_by_id: int


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/search", name="search_invoices_for_consolidated_receipt")
def search_invoices(
    request: Request,
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    patient_name: Optional[str] = Query(None, description="Search by patient name (partial match)"),
    phone_number: Optional[str] = Query(None, description="Search by phone number"),
    nhis_number: Optional[str] = Query(None, description="Search by NHIS number"),
    invoice_ids: Optional[str] = Query(None, description="Comma separated invoice IDs"),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    charge_type: Optional[str] = Query(None, description="lab_test, pharmacy, radiology, etc."),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """
    Search and filter invoices for consolidated receipt creation.
    Supports filtering by patient, status, date range, and charge type.
    """
    # Parse invoice IDs if provided
    invoice_id_list = None
    if invoice_ids:
        invoice_id_list = [int(x.strip()) for x in invoice_ids.split(",") if x.strip()]
    
    # Parse dates
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            pass
    
    # Get invoices
    invoices = billing_crud.get_invoices_for_consolidated_receipt(
        db,
        patient_id=patient_id,
        patient_name=patient_name,
        phone_number=phone_number,
        nhis_number=nhis_number,
        invoice_ids=invoice_id_list,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        charge_type=charge_type
    )
    
    # Debug info - include in response
    debug_info = {
        "search_params": {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "status": status,
            "start_date": str(start_dt) if start_dt else None,
            "end_date": str(end_dt) if end_dt else None
        },
        "count": len(invoices)
    }
    
    # Format results
    results = []
    for invoice in invoices:
        # Get primary charge type
        charge_type_str = None
        if invoice.charges:
            first_charge = invoice.charges[0]
            charge_type_str = first_charge.charge_type.value if hasattr(first_charge.charge_type, 'value') else str(first_charge.charge_type)
        
        # Get patient name
        patient_name = ""
        if invoice.patient:
            patient_name = f"{invoice.patient.first_name} {invoice.patient.last_name}"
        
        results.append({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "patient_id": invoice.patient_id,
            "patient_name": patient_name,
            "total_amount": float(invoice.total_amount or 0),
            "paid_amount": float(invoice.paid_amount or 0),
            "balance": float(invoice.balance or 0),
            "status": invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
            "charge_type": charge_type_str
        })
    
    return {
        "invoices": results,
        "total": len(results),
        "debug": debug_info
    }


@router.get("/patients/search", name="search_patients_for_consolidated_receipt")
def search_patients(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (min 2 characters)"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """
    Search patients by name, phone number, NHIS number, or patient ID.
    Returns up to 10 results for autocomplete suggestions.
    """
    # Search by name, phone, nhis, or patient number
    patients = db.query(Patient).filter(
        Patient.is_active == True,
        (
            Patient.first_name.ilike(f"%{q}%") |
            Patient.last_name.ilike(f"%{q}%") |
            func.concat(Patient.first_name, " ", Patient.last_name).ilike(f"%{q}%") |
            Patient.phone_number.ilike(f"%{q}%") |
            Patient.nhis_number.ilike(f"%{q}%") |
            Patient.patient_number.ilike(f"%{q}%") |
            Patient.id.cast(String).like(f"%{q}%")
        )
    ).limit(10).all()
    
    results = []
    for patient in patients:
        results.append({
            "id": patient.id,
            "patient_number": patient.patient_number,
            "name": f"{patient.first_name} {patient.last_name}",
            "phone_number": patient.phone_number,
            "nhis_number": patient.nhis_number,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None
        })
    
    return {"patients": results}


@router.post("/preview", name="preview_consolidated_receipt")
def preview_consolidated_receipt(
    request: Request,
    invoice_ids: List[int] = Body(..., embed=False),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """
    Generate preview data for consolidated receipt.
    Validates invoices belong to same patient and are payable.
    """
    # Get invoices
    invoices = db.query(Invoice).options(
        __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload(Invoice.charges)
    ).filter(
        Invoice.id.in_(invoice_ids),
        Invoice.is_active == True
    ).all()
    
    if not invoices:
        raise HTTPException(status_code=400, detail="No valid invoices found")
    
    # Verify all invoices belong to the same patient
    patient_ids = set(inv.patient_id for inv in invoices)
    if len(patient_ids) > 1:
        raise HTTPException(status_code=400, detail="All invoices must belong to the same patient")
    
    patient_id = patient_ids.pop()
    patient = invoices[0].patient
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    
    # Calculate totals and build preview
    total_amount = Decimal('0.00')
    total_discount = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_balance = Decimal('0.00')
    
    invoice_items = []
    for invoice in invoices:
        # Get primary charge type
        charge_type_str = None
        if invoice.charges:
            first_charge = invoice.charges[0]
            charge_type_str = first_charge.charge_type.value if hasattr(first_charge.charge_type, 'value') else str(first_charge.charge_type)
        
        # Get charges as dict
        charges_list = []
        for charge in invoice.charges:
            charges_list.append({
                "id": charge.id,
                "description": charge.description,
                "charge_type": charge.charge_type.value if hasattr(charge.charge_type, 'value') else str(charge.charge_type),
                "quantity": charge.quantity,
                "unit_price": float(charge.unit_price or 0),
                "discount": float(charge.discount or 0),
                "tax_amount": float(charge.tax_amount or 0),
                "total_amount": float(charge.total_amount or 0)
            })
        
        invoice_items.append({
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "charge_type": charge_type_str,
            "subtotal": float(invoice.subtotal or 0),
            "discount": float(invoice.discount_amount or 0),
            "total": float(invoice.total_amount or 0),
            "paid": float(invoice.paid_amount or 0),
            "balance": float(invoice.balance or 0),
            "status": invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
            "charges": charges_list
        })
        
        total_amount += invoice.total_amount or Decimal('0.00')
        total_discount += invoice.discount_amount or Decimal('0.00')
        total_paid += invoice.paid_amount or Decimal('0.00')
        total_balance += invoice.balance or Decimal('0.00')
    
    return {
        "patient_id": patient_id,
        "patient_name": patient_name,
        "total_invoices": len(invoices),
        "total_amount": float(total_amount),
        "total_discount": float(total_discount),
        "total_paid": float(total_paid),
        "total_balance": float(total_balance),
        "invoices": invoice_items
    }


@router.post("/create", name="create_consolidated_receipt")
def create_consolidated_receipt(
    request: Request,
    invoice_ids: List[int] = Body(..., embed=False),
    payment_method: str = Body(...),
    transaction_reference: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """
    Create consolidated receipt from selected invoices.
    Validates invoices and creates the receipt with all linked data.
    """
    # Get first invoice to verify patient
    first_invoice = db.query(Invoice).filter(Invoice.id == invoice_ids[0]).first()
    if not first_invoice:
        raise HTTPException(status_code=400, detail="First invoice not found")
    
    patient_id = first_invoice.patient_id
    
    try:
        receipt = billing_crud.create_consolidated_receipt(
            db=db,
            patient_id=patient_id,
            invoice_ids=invoice_ids,
            generated_by_id=current_user.id,
            payment_method=payment_method,
            transaction_reference=transaction_reference
        )
        
        # Get patient name
        patient = receipt.patient
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
        
        return {
            "id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "patient_id": receipt.patient_id,
            "patient_name": patient_name,
            "total_invoices": receipt.total_invoices,
            "total_amount": float(receipt.total_amount),
            "total_paid": float(receipt.total_paid),
            "total_discount": float(receipt.total_discount),
            "total_balance": float(receipt.total_balance),
            "primary_payment_method": receipt.primary_payment_method,
            "status": receipt.status,
            "generated_at": receipt.generated_at.isoformat() if receipt.generated_at else None,
            "message": "Consolidated receipt created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating consolidated receipt: {str(e)}")


# UI Routes - These must come BEFORE the /{receipt_id} route
@router.get("/create", name="create_consolidated_receipt_ui")
def create_consolidated_receipt_ui(
    request: Request,
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    patient_name: Optional[str] = Query(None, description="Search by patient name"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number"),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    start_date: Optional[str] = Query(None, description="Start date for filtering"),
    end_date: Optional[str] = Query(None, description="End date for filtering"),
    charge_type: Optional[str] = Query(None, description="Filter by charge type"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """Render the consolidated receipt creation page with optional pre-filled search parameters"""
    from app.crud import hospital_settings_crud
    from app.crud import billing_crud
    from datetime import datetime
    
    # Convert patient_id string to int if valid, otherwise None
    patient_id_int = None
    if patient_id and patient_id.strip():
        try:
            patient_id_int = int(patient_id)
        except ValueError:
            pass  # Keep as None if invalid
    
    # Determine if we should auto-search based on presence of search params
    should_search = any([patient_id_int, patient_name, invoice_number, status, start_date, end_date, charge_type])
    
    # Perform search server-side if parameters provided
    search_results = []
    if should_search:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                pass
        
        # Parse invoice IDs if provided
        invoice_id_list = None
        if invoice_number:
            invoice_id_list = [int(x.strip()) for x in invoice_number.split(",") if x.strip() and x.strip().isdigit()]
        
        # Get invoices
        invoices = billing_crud.get_invoices_for_consolidated_receipt(
            db,
            patient_id=patient_id_int,
            patient_name=patient_name,
            invoice_ids=invoice_id_list,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            charge_type=charge_type
        )
        
        # Format results for template
        for inv in invoices:
            patient_name_str = ""
            if inv.patient:
                patient_name_str = f"{inv.patient.first_name} {inv.patient.last_name}"
            
            charge_type_str = None
            if inv.charges:
                first_charge = inv.charges[0]
                charge_type_str = first_charge.charge_type.value if hasattr(first_charge.charge_type, 'value') else str(first_charge.charge_type)
            
            search_results.append({
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "patient_id": inv.patient_id,
                "patient_name": patient_name_str,
                "total_amount": float(inv.total_amount or 0),
                "paid_amount": float(inv.paid_amount or 0),
                "balance": float(inv.balance or 0),
                "status": inv.status.value if hasattr(inv.status, 'value') else str(inv.status),
                "charge_type": charge_type_str
            })
    
    return templates.TemplateResponse("billing/consolidated_receipt_create.html", {
        "request": request,
        "title": "Create Consolidated Receipt",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "hospital_settings": None,
        # Pre-fill form values
        "initial_patient_id": patient_id_int,
        "initial_patient_name": patient_name,
        "initial_invoice_number": invoice_number,
        "initial_status": status,
        "initial_start_date": start_date,
        "initial_end_date": end_date,
        "initial_charge_type": charge_type,
        # Pre-populated search results
        "search_results": search_results,
        "did_search": should_search,
        "auto_search": should_search  # Fix: template expects 'auto_search'
    })


@router.get("/{receipt_id}", name="get_consolidated_receipt")
def get_consolidated_receipt(
    request: Request,
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """Get consolidated receipt details by ID"""
    receipt = billing_crud.get_consolidated_receipt(db, receipt_id)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Consolidated receipt not found")
    
    # Get patient name
    patient = receipt.patient
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    
    # Build invoices list
    invoices_list = []
    for inv in receipt.invoices:
        charges_list = []
        for charge in inv.charges:
            charges_list.append({
                "id": charge.id,
                "description": charge.description,
                "charge_type": charge.charge_type,
                "quantity": charge.quantity,
                "unit_price": float(charge.unit_price),
                "discount": float(charge.discount),
                "tax_amount": float(charge.tax_amount),
                "total_amount": float(charge.total_amount)
            })
        
        invoices_list.append({
            "invoice_id": inv.invoice_id,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "charge_type": inv.charge_type,
            "subtotal": float(inv.subtotal),
            "discount": float(inv.discount_amount),
            "total": float(inv.total_amount),
            "paid": float(inv.paid_amount),
            "balance": float(inv.balance),
            "status": inv.status,
            "charges": charges_list
        })
    
    # Build payments list
    payments_list = []
    for pay in receipt.payments:
        payments_list.append({
            "payment_id": pay.payment_id,
            "payment_number": pay.payment_number,
            "amount": float(pay.amount),
            "payment_method": pay.payment_method,
            "transaction_reference": pay.transaction_reference,
            "payment_date": pay.payment_date.isoformat() if pay.payment_date else None
        })
    
    return {
        "id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "patient_id": receipt.patient_id,
        "patient_name": patient_name,
        "generated_by": receipt.generated_by.username if receipt.generated_by else "Unknown",
        "total_invoices": receipt.total_invoices,
        "total_amount": float(receipt.total_amount),
        "total_paid": float(receipt.total_paid),
        "total_discount": float(receipt.total_discount),
        "total_balance": float(receipt.total_balance),
        "primary_payment_method": receipt.primary_payment_method,
        "status": receipt.status,
        "generated_at": receipt.generated_at.isoformat() if receipt.generated_at else None,
        "printed_at": receipt.printed_at.isoformat() if receipt.printed_at else None,
        "invoices": invoices_list,
        "payments": payments_list
    }


@router.get("/number/{receipt_number}", name="get_consolidated_receipt_by_number")
def get_consolidated_receipt_by_number(
    request: Request,
    receipt_number: str,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """Get consolidated receipt by receipt number"""
    receipt = billing_crud.get_consolidated_receipt_by_number(db, receipt_number)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Consolidated receipt not found")
    
    # Get patient name
    patient = receipt.patient
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    
    # Build invoices list
    invoices_list = []
    for inv in receipt.invoices:
        charges_list = []
        for charge in inv.charges:
            charges_list.append({
                "id": charge.id,
                "description": charge.description,
                "charge_type": charge.charge_type,
                "quantity": charge.quantity,
                "unit_price": float(charge.unit_price),
                "discount": float(charge.discount),
                "tax_amount": float(charge.tax_amount),
                "total_amount": float(charge.total_amount)
            })
        
        invoices_list.append({
            "invoice_id": inv.invoice_id,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "charge_type": inv.charge_type,
            "subtotal": float(inv.subtotal),
            "discount": float(inv.discount_amount),
            "total": float(inv.total_amount),
            "paid": float(inv.paid_amount),
            "balance": float(inv.balance),
            "status": inv.status,
            "charges": charges_list
        })
    
    return {
        "id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "patient_id": receipt.patient_id,
        "patient_name": patient_name,
        "generated_by": receipt.generated_by.username if receipt.generated_by else "Unknown",
        "total_invoices": receipt.total_invoices,
        "total_amount": float(receipt.total_amount),
        "total_paid": float(receipt.total_paid),
        "total_discount": float(receipt.total_discount),
        "total_balance": float(receipt.total_balance),
        "primary_payment_method": receipt.primary_payment_method,
        "status": receipt.status,
        "generated_at": receipt.generated_at.isoformat() if receipt.generated_at else None,
        "printed_at": receipt.printed_at.isoformat() if receipt.printed_at else None,
        "invoices": invoices_list
    }


@router.get("/", name="list_consolidated_receipts")
def list_consolidated_receipts(
    request: Request,
    patient_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """List consolidated receipts with optional filters"""
    # Parse dates
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            pass
    
    receipts = billing_crud.get_consolidated_receipts(
        db,
        patient_id=patient_id,
        status=status,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )
    
    results = []
    for receipt in receipts:
        patient = receipt.patient
        patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
        
        results.append({
            "id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "patient_id": receipt.patient_id,
            "patient_name": patient_name,
            "total_invoices": receipt.total_invoices,
            "total_amount": float(receipt.total_amount),
            "total_paid": float(receipt.total_paid),
            "total_balance": float(receipt.total_balance),
            "primary_payment_method": receipt.primary_payment_method,
            "status": receipt.status,
            "generated_at": receipt.generated_at.isoformat() if receipt.generated_at else None,
            "printed_at": receipt.printed_at.isoformat() if receipt.printed_at else None
        })
    
    return {
        "receipts": results,
        "total": len(results)
    }


@router.post("/{receipt_id}/print", name="print_consolidated_receipt")
def print_consolidated_receipt(
    request: Request,
    receipt_id: int,
    printer_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """Mark consolidated receipt as printed and create audit log"""
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        receipt = billing_crud.mark_consolidated_receipt_printed(
            db=db,
            receipt_id=receipt_id,
            user_id=current_user.id,
            printer_name=printer_name,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "status": receipt.status,
            "printed_at": receipt.printed_at.isoformat() if receipt.printed_at else None,
            "message": "Consolidated receipt marked as printed"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error printing receipt: {str(e)}")


@router.post("/{receipt_id}/reprint", name="reprint_consolidated_receipt")
def reprint_consolidated_receipt(
    request: Request,
    receipt_id: int,
    reason: str = Body(...),
    authorized_by_id: int = Body(...),
    printer_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier"]))
):
    """
    Reprint a previously generated consolidated receipt.
    Requires authorization reason and authorizing user.
    """
    if len(reason) < 10:
        raise HTTPException(status_code=400, detail="Reason must be at least 10 characters")
    
    # Verify receipt exists
    receipt = billing_crud.get_consolidated_receipt(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Consolidated receipt not found")
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        # Create reprint log
        print_log = billing_crud.create_reprint_log(
            db=db,
            receipt_id=receipt_id,
            user_id=current_user.id,
            authorized_by_id=authorized_by_id,
            reason=reason,
            printer_name=printer_name,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Update printed timestamp
        receipt.printed_at = datetime.now()
        db.commit()
        
        return {
            "id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "status": receipt.status,
            "printed_at": receipt.printed_at.isoformat() if receipt.printed_at else None,
            "message": "Consolidated receipt reprinted successfully",
            "print_log_id": print_log.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reprinting receipt: {str(e)}")


@router.get("/{receipt_id}/logs", name="get_consolidated_receipt_logs")
def get_consolidated_receipt_logs(
    request: Request,
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """Get print audit logs for a consolidated receipt"""
    logs = billing_crud.get_print_logs(db, receipt_id=receipt_id)
    
    results = []
    for log in logs:
        results.append({
            "id": log.id,
            "receipt_id": log.receipt_id,
            "user": log.user.username if log.user else "Unknown",
            "action": log.action,
            "status": log.status,
            "printer_name": log.printer_name,
            "authorized_by": log.authorized_by.username if log.authorized_by else None,
            "reason": log.reason,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })
    
    return {
        "logs": results,
        "total": len(results)
    }


@router.get("/{receipt_id}/print-view", name="print_consolidated_receipt_ui")
def print_consolidated_receipt_ui(
    request: Request,
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance", "Cashier", "Front Office"]))
):
    """Render the consolidated receipt for printing"""
    from app.crud import hospital_settings_crud
    
    receipt = billing_crud.get_consolidated_receipt(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Consolidated receipt not found")
    
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    return templates.TemplateResponse("billing/consolidated_receipt_print.html", {
        "request": request,
        "title": f"Consolidated Receipt - {receipt.receipt_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "hospital_settings": hospital_settings,
        "receipt": receipt,
        "patient": receipt.patient
    })
