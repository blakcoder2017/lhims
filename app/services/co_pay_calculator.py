"""
Co-pay Calculation Service

This module calculates co-pay amounts based on insurance type and service charges.
"""
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.models.patient_models import Patient, PaymentMechanism
from app.models.billing_models import Invoice, Charge, ChargeType
from app.models.encounter_models import Encounter


# Default co-pay rates (can be configured)
DEFAULT_NHIS_COPAY_RATE = Decimal('0.10')  # 10% co-pay for NHIS
DEFAULT_PRIVATE_INSURANCE_COPAY_RATE = Decimal('0.20')  # 20% co-pay for private insurance


def calculate_nhis_co_pay(
    invoice_total: Decimal,
    service_type: Optional[str] = None
) -> Decimal:
    """
    Calculate NHIS co-pay amount.
    
    Args:
        invoice_total: Total invoice amount
        service_type: Type of service (for service-specific rates)
        
    Returns:
        Co-pay amount
    """
    # Service-specific rates (can be expanded)
    service_rates = {
        "consultation": Decimal('0.05'),  # 5% for consultation
        "lab_test": Decimal('0.10'),  # 10% for lab tests
        "radiology": Decimal('0.15'),  # 15% for radiology
        "pharmacy": Decimal('0.20'),  # 20% for pharmacy
    }
    
    rate = service_rates.get(service_type, DEFAULT_NHIS_COPAY_RATE)
    co_pay = invoice_total * rate
    
    # Minimum co-pay (e.g., 5 GHS)
    min_co_pay = Decimal('5.00')
    if co_pay < min_co_pay:
        co_pay = min_co_pay
    
    return co_pay.quantize(Decimal('0.01'))


def calculate_private_insurance_co_pay(
    invoice_total: Decimal,
    insurance_provider: Optional[str] = None
) -> Decimal:
    """
    Calculate private insurance co-pay amount.
    
    Args:
        invoice_total: Total invoice amount
        insurance_provider: Insurance provider name (for provider-specific rates)
        
    Returns:
        Co-pay amount
    """
    # Provider-specific rates (can be expanded)
    provider_rates = {
        "default": DEFAULT_PRIVATE_INSURANCE_COPAY_RATE,
    }
    
    rate = provider_rates.get(insurance_provider, DEFAULT_PRIVATE_INSURANCE_COPAY_RATE)
    co_pay = invoice_total * rate
    
    return co_pay.quantize(Decimal('0.01'))


def calculate_invoice_co_pay(
    db: Session,
    invoice: Invoice
) -> Decimal:
    """
    Calculate total co-pay for an invoice based on patient's payment mechanism.
    
    Args:
        db: Database session
        invoice: The invoice to calculate co-pay for
        
    Returns:
        Total co-pay amount
    """
    if not invoice.payment_mechanism:
        return Decimal('0.00')
    
    # Get patient
    patient = invoice.patient
    
    # Calculate based on payment mechanism
    if invoice.payment_mechanism == PaymentMechanism.NHIS.value:
        # Determine service type from charges
        service_type = None
        if invoice.charges:
            # Get most common charge type
            charge_types = [charge.charge_type.value for charge in invoice.charges]
            if ChargeType.CONSULTATION.value in charge_types:
                service_type = "consultation"
            elif ChargeType.LAB_TEST.value in charge_types:
                service_type = "lab_test"
            elif ChargeType.RADIOLOGY.value in charge_types:
                service_type = "radiology"
            elif ChargeType.PHARMACY.value in charge_types:
                service_type = "pharmacy"
        
        return calculate_nhis_co_pay(invoice.total_amount, service_type)
    
    elif invoice.payment_mechanism == PaymentMechanism.PRIVATE_INSURANCE.value:
        insurance_provider = invoice.insurance_provider or patient.insurance_provider
        return calculate_private_insurance_co_pay(
            invoice.total_amount,
            insurance_provider
        )
    
    # Cash or self-pay: no co-pay
    return Decimal('0.00')


def apply_co_pay_to_invoice(
    db: Session,
    invoice: Invoice
) -> Invoice:
    """
    Apply co-pay calculation to an invoice and update it.
    
    Args:
        db: Database session
        invoice: The invoice to update
        
    Returns:
        Updated invoice
    """
    from app.crud import billing_crud
    from app.schemas.billing_schemas import InvoiceUpdate
    
    co_pay = calculate_invoice_co_pay(db, invoice)
    
    # Update invoice with co-pay as discount
    # Note: In production, you might want a separate co_pay field
    if co_pay > 0:
        invoice_update = InvoiceUpdate(
            discount_amount=invoice.discount_amount + co_pay
        )
        billing_crud.update_invoice(db, invoice.id, invoice_update)
        db.refresh(invoice)
    
    return invoice

