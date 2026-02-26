"""
Billing Notification Service

This module handles notifications for billing events like invoice creation,
payment confirmation, and balance reminders.
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal

from app.models.billing_models import Invoice, Payment
from app.models.patient_models import Patient
from app.models.hospital_settings_models import HospitalSettings


class NotificationChannel:
    """Notification channel types"""
    SMS = "sms"
    EMAIL = "email"
    BOTH = "both"


def get_hospital_settings(db: Session) -> Optional[HospitalSettings]:
    """Get hospital settings for notification configuration"""
    return db.query(HospitalSettings).first()


def send_invoice_notification(
    db: Session,
    invoice: Invoice,
    channel: str = NotificationChannel.BOTH
) -> dict:
    """
    Send notification when an invoice is created.
    
    Args:
        db: Database session
        invoice: The created invoice
        channel: Notification channel (sms, email, or both)
        
    Returns:
        Dict with notification status
    """
    # Load patient
    if not invoice.patient:
        from sqlalchemy.orm import joinedload
        invoice = db.query(Invoice).options(
            joinedload(Invoice.patient)
        ).filter(Invoice.id == invoice.id).first()
    
    patient = invoice.patient
    if not patient:
        return {"success": False, "error": "Patient not found"}
    
    hospital_settings = get_hospital_settings(db)
    
    # Build message
    message = f\"Dear {patient.first_name}, your invoice #{invoice.invoice_number} has been created. \" \
              f\"Total: GHS {invoice.total_amount:.2f}. \" \
              f\"Balance: GHS {invoice.balance:.2f}. \" \
              f\"Thank you for choosing {hospital_settings.name if hospital_settings else 'our facility'}.\"
    
    results = {"success": True, "channels": []}
    
    # Send SMS
    if channel in [NotificationChannel.SMS, NotificationChannel.BOTH]:
        if patient.phone:
            sms_result = _send_sms(patient.phone, message)
            results["channels"].append({"channel": "sms", **sms_result})
        else:
            results["channels"].append({"channel": "sms", "success": False, "error": "No phone number"})
    
    # Send Email
    if channel in [NotificationChannel.EMAIL, NotificationChannel.BOTH]:
        if patient.email:
            email_result = _send_email(patient.email, f\"Invoice {invoice.invoice_number}\", message)
            results["channels"].append({"channel": "email", **email_result})
        else:
            results["channels"].append({"channel": "email", "success": False, "error": "No email"})
    
    return results


def send_payment_notification(
    db: Session,
    payment: Payment,
    channel: str = NotificationChannel.BOTH
) -> dict:
    """
    Send notification when a payment is received.
    
    Args:
        db: Database session
        payment: The payment record
        channel: Notification channel (sms, email, or both)
        
    Returns:
        Dict with notification status
    """
    # Load patient and invoice
    if not payment.patient:
        from sqlalchemy.orm import joinedload
        payment = db.query(Payment).options(
            joinedload(Payment.patient),
            joinedload(Payment.invoice)
        ).filter(Payment.id == payment.id).first()
    
    patient = payment.patient
    invoice = payment.invoice
    
    if not patient:
        return {"success": False, "error": "Patient not found"}
    
    hospital_settings = get_hospital_settings(db)
    
    # Build message
    message = f\"Dear {patient.first_name}, we received your payment of GHS {payment.amount:.2f}. \" \
              f\"Receipt: {payment.receipt_number}. \" \
              f\"Invoice #{invoice.invoice_number} balance: GHS {invoice.balance:.2f}. \" \
              f\"Thank you!\"
    
    results = {"success": True, "channels": []}
    
    # Send SMS
    if channel in [NotificationChannel.SMS, NotificationChannel.BOTH]:
        if patient.phone:
            sms_result = _send_sms(patient.phone, message)
            results["channels"].append({"channel": "sms", **sms_result})
        else:
            results["channels"].append({"channel": "sms", "success": False, "error": "No phone number"})
    
    # Send Email
    if channel in [NotificationChannel.EMAIL, NotificationChannel.BOTH]:
        if patient.email:
            email_result = _send_email(patient.email, f\"Payment Receipt {payment.receipt_number}\", message)
            results["channels"].append({"channel": "email", **email_result})
        else:
            results["channels"].append({"channel": "email", "success": False, "error": "No email"})
    
    return results


def send_balance_reminder(
    db: Session,
    invoice: Invoice,
    channel: str = NotificationChannel.BOTH
) -> dict:
    """
    Send balance reminder for outstanding invoices.
    
    Args:
        db: Database session
        invoice: The invoice with outstanding balance
        channel: Notification channel (sms, email, or both)
        
    Returns:
        Dict with notification status
    """
    # Load patient
    if not invoice.patient:
        from sqlalchemy.orm import joinedload
        invoice = db.query(Invoice).options(
            joinedload(Invoice.patient)
        ).filter(Invoice.id == invoice.id).first()
    
    patient = invoice.patient
    if not patient:
        return {"success": False, "error": "Patient not found"}
    
    hospital_settings = get_hospital_settings(db)
    
    # Build message
    message = f\"Dear {patient.first_name}, this is a reminder that your invoice #{invoice.invoice_number} \" \
              f\"has an outstanding balance of GHS {invoice.balance:.2f}. \" \
              f\"Please settle your bill at your earliest convenience.\"
    
    results = {"success": True, "channels": []}
    
    # Send SMS
    if channel in [NotificationChannel.SMS, NotificationChannel.BOTH]:
        if patient.phone:
            sms_result = _send_sms(patient.phone, message)
            results["channels"].append({"channel": "sms", **sms_result})
        else:
            results["channels"].append({"channel": "sms", "success": False, "error": "No phone number"})
    
    # Send Email
    if channel in [NotificationChannel.EMAIL, NotificationChannel.BOTH]:
        if patient.email:
            email_result = _send_email(patient.email, f\"Balance Reminder - Invoice {invoice.invoice_number}\", message)
            results["channels"].append({"channel": "email", **email_result})
        else:
            results["channels"].append({"channel": "email", "success": False, "error": "No email"})
    
    return results


def send_discharge_notification(
    db: Session,
    invoice: Invoice,
    channel: str = NotificationChannel.BOTH
) -> dict:
    """
    Send notification to front office when IPD patient is ready for discharge billing.
    
    Args:
        db: Database session
        invoice: The invoice for discharge
        channel: Notification channel
        
    Returns:
        Dict with notification status
    """
    hospital_settings = get_hospital_settings(db)
    
    # Build message for front office
    message = f\"IPD Discharge Invoice Ready\\n\" \
              f\"Invoice #: {invoice.invoice_number}\\n\" \
              f\"Patient ID: {invoice.patient_id}\\n\" \
              f\"Total: GHS {invoice.total_amount:.2f}\\n\" \
              f\"Balance: GHS {invoice.balance:.2f}\\n\" \
              f\"Please process discharge billing.\"
    
    results = {"success": True, "channels": []}
    
    # In production, this would notify the front office via internal system
    # For now, we'll log it
    print(f\"[DISCHARGE NOTIFICATION] {message}\")
    results["channels"].append({"channel": "internal", "success": True, "message": "Notification logged"})
    
    return results


# Internal helper functions
def _send_sms(phone: str, message: str) -> dict:
    """
    Send SMS notification.
    
    In production, this would integrate with Ghana's mobile money/SMS providers.
    """
    # TODO: Integrate with SMS provider (e.g., Africa's Talking, Twilio, etc.)
    print(f\"[SMS] To: {phone}, Message: {message}\")
    return {
        "success": True,
        "provider": "placeholder",
        "message_id": f\"SMS_{hash(message)}\"
    }


def _send_email(email: str, subject: str, message: str) -> dict:
    """
    Send email notification.
    
    In production, this would use FastAPI's email integration or SMTP.
    """
    # TODO: Integrate with email provider
    print(f\"[EMAIL] To: {email}, Subject: {subject}, Message: {message}\")
    return {
        "success": True,
        "provider": "placeholder",
        "message_id": f\"EMAIL_{hash(message)}\"
    }


def get_outstanding_invoices_for_reminder(
    db: Session,
    days_threshold: int = 7
) -> List[Invoice]:
    """
    Get invoices that have outstanding balances older than threshold.
    
    Args:
        db: Database session
        days_threshold: Number of days after which to send reminder
        
    Returns:
        List of invoices to send reminders for
    """
    from datetime import timedelta
    from app.models.billing_models import InvoiceStatus
    from sqlalchemy import and_
    
    threshold_date = datetime.now() - timedelta(days=days_threshold)
    
    invoices = db.query(Invoice).options(
        joinedload(Invoice.patient)
    ).filter(
        Invoice.is_active == True,
        Invoice.balance > 0,
        Invoice.status.in_([InvoiceStatus.PENDING.value, InvoiceStatus.PARTIALLY_PAID.value]),
        Invoice.invoice_date <= threshold_date
    ).all()
    
    return invoices
