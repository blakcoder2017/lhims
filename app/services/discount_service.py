"""
Discount Calculation Service

This module calculates discounts based on configured discount rules.
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import datetime

from app.models.billing_models import DiscountRule, DiscountType, Invoice, Charge
from app.models.patient_models import Patient


def get_applicable_rules(
    db: Session,
    invoice: Invoice,
    charge_type: Optional[str] = None
) -> List[DiscountRule]:
    """
    Get all applicable discount rules for an invoice.
    
    Args:
        db: Database session
        invoice: The invoice to check
        charge_type: Optional specific charge type to filter by
        
    Returns:
        List of applicable discount rules (sorted by priority)
    """
    now = datetime.now()
    
    # Get all active rules
    query = db.query(DiscountRule).filter(
        DiscountRule.is_active == True
    )
    
    # Filter rules that are within validity period
    query = query.filter(
        (DiscountRule.valid_from == None) | (DiscountRule.valid_from <= now),
        (DiscountRule.valid_to == None) | (DiscountRule.valid_to >= now)
    )
    
    rules = query.order_by(DiscountRule.priority.desc()).all()
    
    applicable = []
    for rule in rules:
        # Check minimum invoice amount
        if rule.min_invoice_amount and invoice.subtotal < rule.min_invoice_amount:
            continue
        
        # Check applicable services
        if rule.applicable_services and charge_type:
            if charge_type not in rule.applicable_services:
                continue
        
        # Check patient categories (if any)
        if rule.patient_categories:
            patient = invoice.patient
            if patient:
                # Check if patient matches any category
                patient_category = None
                
                # Determine patient category based on patient attributes
                if patient.date_of_birth:
                    age = (datetime.now().date() - patient.date_of_birth).days / 365
                    if age < 18:
                        patient_category = "children"
                    elif age >= 60:
                        patient_category = "elderly"
                
                if patient.nhis_number:
                    patient_category = "nhis"
                    
                if not patient_category or patient_category not in rule.patient_categories:
                    continue
        
        applicable.append(rule)
    
    return applicable


def calculate_discount(
    invoice: Invoice,
    rules: List[DiscountRule],
    charge_type: Optional[str] = None
) -> Tuple[Decimal, List[str]]:
    """
    Calculate total discount amount based on applicable rules.
    
    Args:
        invoice: The invoice to calculate discount for
        rules: List of applicable discount rules
        charge_type: Optional specific charge type to apply discount to
        
    Returns:
        Tuple of (total_discount_amount, list of applied rule names)
    """
    total_discount = Decimal('0.00')
    applied_rules = []
    
    # Get charges to apply discount to
    charges = invoice.charges or []
    if charge_type:
        charges = [c for c in charges if c.charge_type.value == charge_type]
    
    charge_total = sum(c.total_amount for c in charges)
    
    for rule in rules:
        # Check if rule applies to this charge type
        if rule.applicable_services and charge_type:
            if charge_type not in rule.applicable_services:
                continue
        
        # Calculate discount based on type
        if rule.discount_type == DiscountType.PERCENTAGE:
            discount = charge_total * (rule.discount_value / Decimal('100'))
        else:  # FIXED
            discount = rule.discount_value
        
        # Apply maximum discount limit if set
        if rule.max_discount_amount and discount > rule.max_discount_amount:
            discount = rule.max_discount_amount
        
        total_discount += discount
        applied_rules.append(rule.name)
    
    return total_discount, applied_rules


def calculate_invoice_discount(
    db: Session,
    invoice: Invoice,
    charge_type: Optional[str] = None
) -> Tuple[Decimal, List[str]]:
    """
    Calculate total discount for an invoice based on configured rules.
    
    Args:
        db: Database session
        invoice: The invoice to calculate discount for
        charge_type: Optional specific charge type to apply discount to
        
    Returns:
        Tuple of (total_discount_amount, list of applied rule names)
    """
    rules = get_applicable_rules(db, invoice, charge_type)
    return calculate_discount(invoice, rules, charge_type)


def apply_discount_to_invoice(
    db: Session,
    invoice_id: int,
    charge_type: Optional[str] = None
) -> Tuple[Invoice, Decimal, List[str]]:
    """
    Apply discounts to an invoice and update it.
    
    Args:
        db: Database session
        invoice_id: ID of the invoice to apply discount to
        charge_type: Optional specific charge type to apply discount to
        
    Returns:
        Tuple of (updated_invoice, discount_amount, applied_rule_names)
    """
    from app.crud import billing_crud
    from app.schemas.billing_schemas import InvoiceUpdate
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")
    
    # Load patient relationship
    if not invoice.patient:
        from sqlalchemy.orm import joinedload
        invoice = db.query(Invoice).options(
            joinedload(Invoice.patient),
            joinedload(Invoice.charges)
        ).filter(Invoice.id == invoice_id).first()
    
    discount_amount, applied_rules = calculate_invoice_discount(db, invoice, charge_type)
    
    if discount_amount > 0:
        # Update invoice with discount
        invoice_update = InvoiceUpdate(
            discount_amount=invoice.discount_amount + discount_amount
        )
        billing_crud.update_invoice(db, invoice.id, invoice_update)
        db.refresh(invoice)
    
    return invoice, discount_amount, applied_rules
