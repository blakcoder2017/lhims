"""
API routes for NHIS Claims management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.claims_models import NHISClaim, ClaimStatus
from app.models.encounter_models import Encounter
from app.crud import claims_crud

router = APIRouter(tags=["NHIS Claims"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/claims", name="claims_dashboard")
def claims_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"])),
    status_filter: Optional[str] = Query(None)
):
    """NHIS Claims dashboard - National Health Insurance Scheme claims"""
    query = db.query(NHISClaim).filter(NHISClaim.is_active == True)
    
    if status_filter:
        try:
            status_enum = ClaimStatus(status_filter)
            query = query.filter(NHISClaim.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show draft and pending claims
        query = query.filter(
            NHISClaim.status.in_([ClaimStatus.DRAFT.value, ClaimStatus.PENDING.value])
        )
    
    from sqlalchemy.orm import joinedload
    claims = query.options(
        joinedload(NHISClaim.patient),
        joinedload(NHISClaim.encounter)
    ).order_by(NHISClaim.claim_date.desc()).limit(100).all()
    
    # Statistics
    total_claims = db.query(NHISClaim).filter(NHISClaim.is_active == True).count()
    pending_claims = db.query(NHISClaim).filter(
        NHISClaim.status == ClaimStatus.PENDING.value,
        NHISClaim.is_active == True
    ).count()
    approved_claims = db.query(NHISClaim).filter(
        NHISClaim.status == ClaimStatus.APPROVED.value,
        NHISClaim.is_active == True
    ).count()
    
    context = {
        "request": request,
        "title": "NHIS Claims",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "claims": claims,
        "status_filter": status_filter,
        "total_claims": total_claims,
        "pending_claims": pending_claims,
        "approved_claims": approved_claims
    }
    return templates.TemplateResponse("claims/dashboard.html", context)


@router.get("/claims/private-insurance", name="private_insurance_claims_dashboard")
def private_insurance_claims_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"])),
    status_filter: Optional[str] = Query(None),
    insurance_provider: Optional[str] = Query(None)
):
    """Private Insurance Claims dashboard - aggregates all bills and claims grouped by insurance company"""
    from app.models.billing_models import Invoice, InvoiceStatus
    from app.models.patient_models import PaymentMechanism
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    from decimal import Decimal
    
    # Base query for private insurance invoices
    base_query = db.query(Invoice).filter(
        Invoice.is_active == True,
        Invoice.payment_mechanism == PaymentMechanism.PRIVATE_INSURANCE.value
    )
    
    if status_filter:
        try:
            status_enum = InvoiceStatus(status_filter)
            base_query = base_query.filter(Invoice.status == status_enum.value)
        except ValueError:
            pass
    
    # Get all invoices
    all_invoices = base_query.options(
        joinedload(Invoice.patient),
        joinedload(Invoice.encounter)
    ).order_by(Invoice.invoice_date.desc()).all()
    
    # Group invoices by insurance provider
    invoices_by_provider = {}
    total_amount_by_provider = {}
    pending_amount_by_provider = {}
    paid_amount_by_provider = {}
    
    for invoice in all_invoices:
        # Get insurance provider from invoice or patient
        provider = invoice.insurance_provider or invoice.patient.insurance_provider or "Unknown Provider"
        
        if provider not in invoices_by_provider:
            invoices_by_provider[provider] = []
            total_amount_by_provider[provider] = Decimal('0.00')
            pending_amount_by_provider[provider] = Decimal('0.00')
            paid_amount_by_provider[provider] = Decimal('0.00')
        
        invoices_by_provider[provider].append(invoice)
        total_amount_by_provider[provider] += invoice.total_amount
        
        if invoice.status == InvoiceStatus.PENDING.value:
            pending_amount_by_provider[provider] += invoice.balance
        elif invoice.status == InvoiceStatus.PAID.value:
            paid_amount_by_provider[provider] += invoice.total_amount
    
    # Filter by insurance provider if specified
    if insurance_provider:
        if insurance_provider in invoices_by_provider:
            filtered_invoices = invoices_by_provider[insurance_provider]
        else:
            filtered_invoices = []
    else:
        filtered_invoices = all_invoices[:100]  # Limit display
    
    # Statistics
    total_invoices = len(all_invoices)
    pending_invoices = sum(1 for inv in all_invoices if inv.status == InvoiceStatus.PENDING.value)
    paid_invoices = sum(1 for inv in all_invoices if inv.status == InvoiceStatus.PAID.value)
    
    total_amount = sum(inv.total_amount for inv in all_invoices)
    total_pending_amount = sum(inv.balance for inv in all_invoices if inv.status == InvoiceStatus.PENDING.value)
    total_paid_amount = sum(inv.total_amount for inv in all_invoices if inv.status == InvoiceStatus.PAID.value)
    
    # Get list of unique insurance providers
    insurance_providers = sorted(invoices_by_provider.keys())
    
    context = {
        "request": request,
        "title": "Private Insurance Claims",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "invoices": filtered_invoices,
        "invoices_by_provider": invoices_by_provider,
        "total_amount_by_provider": total_amount_by_provider,
        "pending_amount_by_provider": pending_amount_by_provider,
        "paid_amount_by_provider": paid_amount_by_provider,
        "insurance_providers": insurance_providers,
        "status_filter": status_filter,
        "insurance_provider_filter": insurance_provider,
        "total_invoices": total_invoices,
        "pending_invoices": pending_invoices,
        "paid_invoices": paid_invoices,
        "total_amount": total_amount,
        "total_pending_amount": total_pending_amount,
        "total_paid_amount": total_paid_amount
    }
    return templates.TemplateResponse("claims/private_insurance_claims.html", context)


@router.post("/claims/create-from-encounter/{encounter_id}", name="create_claim_from_encounter", status_code=302)
def create_claim_from_encounter(
    request: Request,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """Create an NHIS claim from an encounter"""
    try:
        claim = claims_crud.create_claim_from_encounter(db, encounter_id, current_user.id)
        return RedirectResponse(
            url=f"/claims/{claim.id}?status=created",
            status_code=302
        )
    except ValueError as e:
        return RedirectResponse(
            url=f"/encounters/{encounter_id}?error={str(e)}",
            status_code=302
        )


@router.get("/claims/{claim_id}", name="view_claim")
def view_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """View a specific NHIS claim"""
    claim = claims_crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    context = {
        "request": request,
        "title": f"NHIS Claim {claim.claim_number}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "claim": claim,
        "encounter": claim.encounter,
        "patient": claim.patient,
        "invoice": claim.invoice
    }
    return templates.TemplateResponse("claims/claim_detail.html", context)


@router.post("/claims/{claim_id}/submit", name="submit_claim", status_code=302)
def submit_claim(
    request: Request,
    claim_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Finance"]))
):
    """
    Submit claim to NHIA.
    Note: Actual API submission is pending NHIA API integration.
    This currently marks the claim as submitted.
    """
    claim = claims_crud.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # TODO: When NHIA API is available, implement actual submission
    # For now, just update status
    updated_claim = claims_crud.update_claim_status(
        db, claim_id, ClaimStatus.SUBMITTED
    )
    
    if updated_claim:
        # Set submission reference
        updated_claim.submission_reference = f"SUBM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        db.commit()
    else:
        raise HTTPException(status_code=400, detail="Failed to submit claim")
    
    return RedirectResponse(
        url=f"/claims/{claim_id}?status=submitted"
    )

