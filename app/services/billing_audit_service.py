"""
Billing Audit Service

This module provides audit logging for billing operations to ensure
compliance and traceability.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Any, Dict
from datetime import datetime, date
import json

from app.models.audit_models import AuditLog, AuditAction
from app.models.billing_models import Invoice, Payment, Refund
from app.models.user_models import User


def log_billing_action(
    db: Session,
    user_id: int,
    action: AuditAction,
    resource_type: str,
    resource_id: int,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "success"
) -> AuditLog:
    """
    Log a billing action to the audit trail.
    
    Args:
        db: Database session
        user_id: ID of user performing action
        action: Type of action (CREATE, UPDATE, VOID, etc.)
        resource_type: Type of resource (Invoice, Payment, etc.)
        resource_id: ID of the resource
        old_values: Previous values (for updates/voids)
        new_values: New values (for creates/updates)
        description: Human-readable description
        ip_address: Client IP address
        status: Action status (success, failed, error)
        
    Returns:
        Created AuditLog entry
    """
    # Get username for historical reference
    user = db.query(User).filter(User.id == user_id).first()
    username = user.username if user else None
    
    audit_log = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        description=description,
        ip_address=ip_address,
        status=status
    )
    
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    
    return audit_log


def log_invoice_created(
    db: Session,
    user_id: int,
    invoice: Invoice,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log invoice creation"""
    new_values = {
        "invoice_number": invoice.invoice_number,
        "patient_id": invoice.patient_id,
        "total_amount": str(invoice.total_amount),
        "payment_mechanism": invoice.payment_mechanism.value if invoice.payment_mechanism else None
    }
    
    return log_billing_action(
        db=db,
        user_id=user_id,
        action=AuditAction.CREATE,
        resource_type="Invoice",
        resource_id=invoice.id,
        new_values=new_values,
        description=f\"Created invoice {invoice.invoice_number}\",
        ip_address=ip_address
    )


def log_invoice_updated(
    db: Session,
    user_id: int,
    invoice: Invoice,
    old_values: Dict[str, Any],
    new_values: Dict[str, Any],
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log invoice update"""
    return log_billing_action(
        db=db,
        user_id=user_id,
        action=AuditAction.UPDATE,
        resource_type="Invoice",
        resource_id=invoice.id,
        old_values=old_values,
        new_values=new_values,
        description=f\"Updated invoice {invoice.invoice_number}\",
        ip_address=ip_address
    )


def log_invoice_voided(
    db: Session,
    user_id: int,
    invoice: Invoice,
    reason: str,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log invoice voiding"""
    old_values = {
        "invoice_number": invoice.invoice_number,
        "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        "total_amount": str(invoice.total_amount),
        "paid_amount": str(invoice.paid_amount)
    }
    
    new_values = {
        "status": "voided",
        "void_reason": reason,
        "voided_by": user_id,
        "voided_at": datetime.now().isoformat()
    }
    
    return log_billing_action(
        db=db,
        user_id=user_id,
        action=AuditAction.VOID,
        resource_type="Invoice",
        resource_id=invoice.id,
        old_values=old_values,
        new_values=new_values,
        description=f\"Voided invoice {invoice.invoice_number}: {reason}\",
        ip_address=ip_address
    )


def log_payment_received(
    db: Session,
    user_id: int,
    payment: Payment,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log payment received"""
    new_values = {
        "payment_number": payment.payment_number,
        "receipt_number": payment.receipt_number,
        "invoice_id": payment.invoice_id,
        "amount": str(payment.amount),
        "payment_method": payment.payment_method.value if payment.payment_method else None
    }
    
    return log_billing_action(
        db=db,
        user_id=user_id,
        action=AuditAction.CREATE,
        resource_type="Payment",
        resource_id=payment.id,
        new_values=new_values,
        description=f\"Payment received: {payment.payment_number}\",
        ip_address=ip_address
    )


def log_payment_voided(
    db: Session,
    user_id: int,
    payment: Payment,
    reason: str,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log payment voiding"""
    old_values = {
        "payment_number": payment.payment_number,
        "amount": str(payment.amount),
        "status": payment.status.value if hasattr(payment.status, 'value') else payment.status
    }
    
    new_values = {
        "status": "voided",
        "void_reason": reason,
        "voided_by": user_id,
        "voided_at": datetime.now().isoformat()
    }
    
    return log_billing_action(
        db=db,
        user_id=user_id,
        action=AuditAction.VOID,
        resource_type="Payment",
        resource_id=payment.id,
        old_values=old_values,
        new_values=new_values,
        description=f\"Voided payment {payment.payment_number}: {reason}\",
        ip_address=ip_address
    )


def log_refund_processed(
    db: Session,
    user_id: int,
    refund: Refund,
    old_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log refund processing"""
    action = AuditAction.CREATE if not old_values else AuditAction.UPDATE
    
    new_values = {
        "refund_number": refund.refund_number,
        "amount": str(refund.amount),
        "status": refund.status.value if hasattr(refund.status, 'value') else refund.status,
        "reason": refund.reason
    }
    
    return log_billing_action(
        db=db,
        user_id=user_id,
        action=action,
        resource_type="Refund",
        resource_id=refund.id,
        old_values=old_values,
        new_values=new_values,
        description=f\"Refund processed: {refund.refund_number}\",
        ip_address=ip_address
    )


# Cash Reconciliation Functions

def get_cash_reconciliation_data(
    db: Session,
    date: datetime
) -> Dict[str, any]:
    """
    Get cash reconciliation data for a specific date.
    
    Args:
        db: Database session
        date: Date to reconcile
        
    Returns:
        Dict with reconciliation data
    """
    from app.models.billing_models import Payment, PaymentStatus
    from app.models.billing_models import PaymentMethod
    from app.models.expense_models import Expense, ExpenseStatus
    from decimal import Decimal
    
    # Get all payments for the day
    payments = db.query(Payment).filter(
        Payment.is_active == True,
        Payment.status == PaymentStatus.COMPLETED.value,
        func.date(Payment.payment_date) == date.date()
    ).all()
    
    # Group by payment method
    collections_by_method = {}
    for payment in payments:
        method = payment.payment_method.value if payment.payment_method else "unknown"
        if method not in collections_by_method:
            collections_by_method[method] = Decimal('0.00')
        collections_by_method[method] += payment.amount
    
    total_collections = sum(p.amount for p in payments)
    
    # Get expenses for the day
    expenses = db.query(Expense).filter(
        Expense.is_active == True,
        Expense.status == ExpenseStatus.APPROVED.value,
        func.date(Expense.expense_date) == date.date()
    ).all()
    
    total_expenses = sum(e.amount for e in expenses)
    
    # Calculate expected vs actual
    reconciliation = {
        "date": date.date(),
        "total_collections": total_collections,
        "total_expenses": total_expenses,
        "net_position": total_collections - total_expenses,
        "collections_by_method": collections_by_method,
        "payment_count": len(payments),
        "expense_count": len(expenses),
        "payments": payments,
        "expenses": expenses
    }
    
    return reconciliation
