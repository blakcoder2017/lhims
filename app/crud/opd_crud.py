from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.patient_models import Patient
from app.models.appointment_models import Appointment
from app.schemas.opd_schemas import (
    OPDVisitCreate, OPDVisitUpdate
)


def generate_opd_number(db: Session) -> str:
    """
    Generate unique OPD visit number.
    Format: OPD-YYYY-NNNN (e.g., OPD-2024-0001)
    """
    current_year = datetime.now().year
    
    # Get last OPD number for this year
    last_visit = db.query(OPDVisit).filter(
        OPDVisit.opd_number.like(f"OPD-{current_year}-%")
    ).order_by(OPDVisit.opd_number.desc()).first()
    
    if last_visit:
        # Extract sequence number
        try:
            last_seq = int(last_visit.opd_number.split('-')[-1])
            next_seq = last_seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1
    
    return f"OPD-{current_year}-{next_seq:04d}"


def create_opd_visit(db: Session, opd_visit: OPDVisitCreate, patient_id: int) -> OPDVisit:
    """
    Create a new OPD visit with auto-generated OPD number.
    """
    # Generate OPD number
    opd_number = generate_opd_number(db)
    
    # Create OPD visit object
    db_opd_visit = OPDVisit(
        opd_number=opd_number,
        patient_id=patient_id,
        appointment_id=opd_visit.appointment_id,
        visit_date=opd_visit.visit_date or datetime.now(),
        status=opd_visit.status or OPDVisitStatus.ACTIVE,
        payment_status=opd_visit.payment_status or "pending",
        visit_type=opd_visit.visit_type,
        chief_complaint=opd_visit.chief_complaint,
        notes=opd_visit.notes,
        consultation_charge_created=False,
        total_charges=Decimal('0.00')
    )
    
    db.add(db_opd_visit)
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def get_opd_visit(db: Session, opd_visit_id: int) -> Optional[OPDVisit]:
    """Get an OPD visit by ID with relationships"""
    return db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.appointment)
    ).filter(OPDVisit.id == opd_visit_id, OPDVisit.is_active == True).first()


def get_opd_visit_by_number(db: Session, opd_number: str) -> Optional[OPDVisit]:
    """Get an OPD visit by OPD number"""
    return db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.appointment)
    ).filter(OPDVisit.opd_number == opd_number, OPDVisit.is_active == True).first()


def get_opd_visits_by_patient(
    db: Session, 
    patient_id: int, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[OPDVisitStatus] = None
) -> List[OPDVisit]:
    """Get all OPD visits for a patient"""
    query = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.appointment)
    ).filter(
        OPDVisit.patient_id == patient_id,
        OPDVisit.is_active == True
    )
    
    if status:
        query = query.filter(OPDVisit.status == status)
    
    return query.order_by(OPDVisit.visit_date.desc()).offset(skip).limit(limit).all()


def get_opd_visits(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[OPDVisitStatus] = None,
    payment_status: Optional[str] = None,
    patient_id: Optional[int] = None
) -> List[OPDVisit]:
    """Get all OPD visits with optional filters"""
    query = db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.appointment)
    ).filter(OPDVisit.is_active == True)
    
    if status:
        query = query.filter(OPDVisit.status == status)
    
    if payment_status:
        query = query.filter(OPDVisit.payment_status == payment_status)
    
    if patient_id:
        query = query.filter(OPDVisit.patient_id == patient_id)
    
    return query.order_by(OPDVisit.visit_date.desc()).offset(skip).limit(limit).all()


def get_active_opd_visit_by_patient(db: Session, patient_id: int) -> Optional[OPDVisit]:
    """Get the active OPD visit for a patient (if any)"""
    return db.query(OPDVisit).options(
        joinedload(OPDVisit.patient),
        joinedload(OPDVisit.appointment)
    ).filter(
        OPDVisit.patient_id == patient_id,
        OPDVisit.status == OPDVisitStatus.ACTIVE,
        OPDVisit.is_active == True
    ).order_by(OPDVisit.visit_date.desc()).first()


def update_opd_visit(db: Session, opd_visit_id: int, opd_visit_update: OPDVisitUpdate) -> Optional[OPDVisit]:
    """Update an OPD visit"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    update_data = opd_visit_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_opd_visit, field, value)
    
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def complete_opd_visit(db: Session, opd_visit_id: int) -> Optional[OPDVisit]:
    """Mark an OPD visit as completed"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    db_opd_visit.status = OPDVisitStatus.COMPLETED
    db_opd_visit.completed_at = datetime.now()
    
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def cancel_opd_visit(db: Session, opd_visit_id: int) -> Optional[OPDVisit]:
    """Cancel an OPD visit"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    db_opd_visit.status = OPDVisitStatus.CANCELLED
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def update_opd_visit_payment_status(
    db: Session, 
    opd_visit_id: int, 
    payment_status: str
) -> Optional[OPDVisit]:
    """Update payment status of an OPD visit"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    db_opd_visit.payment_status = payment_status
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def sync_opd_visit_payment_status(
    db: Session,
    opd_visit_id: int
) -> Optional[OPDVisit]:
    """
    Sync OPD visit payment status based on linked invoice payment status.
    This is useful for fixing existing OPD visits where payment was made
    but the status wasn't updated.
    """
    from app.models.billing_models import Invoice, InvoiceStatus, Charge
    from decimal import Decimal
    from sqlalchemy import or_
    
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    # Find invoices linked to this OPD visit (directly or through charges)
    # Method 1: Direct link via invoice.opd_visit_id
    invoices_direct = db.query(Invoice).filter(
        Invoice.opd_visit_id == opd_visit_id,
        Invoice.is_active == True
    ).all()
    
    # Method 2: Link via charges (for invoices created before opd_visit_id was added to invoices)
    invoices_via_charges = db.query(Invoice).join(Charge).filter(
        Charge.opd_visit_id == opd_visit_id,
        Invoice.is_active == True
    ).distinct().all()
    
    # Combine both lists (remove duplicates by ID)
    all_invoice_ids = set()
    all_invoices = []
    for inv in invoices_direct + invoices_via_charges:
        if inv.id not in all_invoice_ids:
            all_invoice_ids.add(inv.id)
            all_invoices.append(inv)
    
    if not all_invoices:
        # No invoices found, keep current status
        return db_opd_visit
    
    # Check if any invoice is fully paid
    for invoice in all_invoices:
        # Method 1: Check invoice status (most reliable)
        if invoice.status == InvoiceStatus.PAID:
            # Invoice is marked as paid, update OPD visit status
            if db_opd_visit.payment_status != "paid":
                db_opd_visit.payment_status = "paid"
                db.commit()
                db.refresh(db_opd_visit)
            return db_opd_visit
        
        # Method 2: Recalculate balance to be sure (in case it wasn't updated)
        if invoice.total_amount and invoice.paid_amount is not None:
            calculated_balance = invoice.total_amount - invoice.paid_amount
            if calculated_balance <= Decimal('0.00') or (invoice.balance is not None and invoice.balance <= Decimal('0.00')):
                # Invoice is fully paid, update OPD visit status
                if db_opd_visit.payment_status != "paid":
                    db_opd_visit.payment_status = "paid"
                    db.commit()
                    db.refresh(db_opd_visit)
                return db_opd_visit
        
        # Method 3: Check balance directly
        elif invoice.balance is not None and invoice.balance <= Decimal('0.00'):
            # Invoice is fully paid, update OPD visit status
            if db_opd_visit.payment_status != "paid":
                db_opd_visit.payment_status = "paid"
                db.commit()
                db.refresh(db_opd_visit)
            return db_opd_visit
        
        # Method 4: Check payments directly (most comprehensive check)
        from app.models.billing_models import Payment, PaymentStatus
        completed_payments = db.query(Payment).filter(
            Payment.invoice_id == invoice.id,
            Payment.status == PaymentStatus.COMPLETED,
            Payment.is_active == True
        ).all()
        
        if completed_payments:
            total_paid = sum(p.amount for p in completed_payments)
            if invoice.total_amount and total_paid >= invoice.total_amount:
                # Payments cover the full invoice amount, update OPD visit status
                if db_opd_visit.payment_status != "paid":
                    db_opd_visit.payment_status = "paid"
                    db.commit()
                    db.refresh(db_opd_visit)
                return db_opd_visit
    
    return db_opd_visit


def mark_consultation_charge_created(db: Session, opd_visit_id: int) -> Optional[OPDVisit]:
    """Mark that consultation charge has been created for this OPD visit"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    db_opd_visit.consultation_charge_created = True
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def update_opd_visit_total_charges(
    db: Session, 
    opd_visit_id: int, 
    total_charges: Decimal
) -> Optional[OPDVisit]:
    """Update total charges for an OPD visit"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return None
    
    db_opd_visit.total_charges = total_charges
    db.commit()
    db.refresh(db_opd_visit)
    return db_opd_visit


def delete_opd_visit(db: Session, opd_visit_id: int) -> bool:
    """Soft delete an OPD visit"""
    db_opd_visit = get_opd_visit(db, opd_visit_id)
    if not db_opd_visit:
        return False
    
    db_opd_visit.is_active = False
    db.commit()
    return True

