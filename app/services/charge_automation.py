"""
Automated Charge Aggregation Service

This module automatically creates charges when orders are completed:
- Lab orders: Creates charge when lab test is completed
- Radiology orders: Creates charge when radiology study is completed
- Prescriptions: Creates charge when prescription is dispensed
"""
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.models.billing_models import Invoice, Charge, InvoiceStatus, ChargeType
from app.models.encounter_models import LabOrder, RadiologyOrder, Prescription, OrderStatus
from app.models.lab_catalog_models import LabTest
from app.models.inventory_models import Medication
from app.models.procedure_models import Procedure
from app.crud import billing_crud
from app.crud import service_pricing_crud
from app.schemas.billing_schemas import ChargeCreate


# Default pricing (fallback if service pricing not configured)
DEFAULT_LAB_TEST_COST = Decimal('50.00')
DEFAULT_RADIOLOGY_COST = Decimal('100.00')
DEFAULT_PHARMACY_COST = Decimal('20.00')  # Per unit
DEFAULT_CONSULTATION_COST = Decimal('100.00')
DEFAULT_PROCEDURE_COST = Decimal('150.00')


def get_or_create_invoice_for_encounter(
    db: Session,
    encounter_id: int,
    created_by_id: int,
    require_payment: bool = False
) -> Invoice:
    """
    Get existing invoice for encounter or create a new one.
    Returns the invoice (existing or newly created).
    
    Args:
        require_payment: If True, for OPD cash customers, payment is required before service delivery
    """
    # Check if invoice already exists for this encounter
    existing_invoice = db.query(Invoice).filter(
        Invoice.encounter_id == encounter_id,
        Invoice.is_active == True,
        Invoice.status.in_([InvoiceStatus.DRAFT.value, InvoiceStatus.PENDING.value, InvoiceStatus.PARTIALLY_PAID.value])
    ).first()
    
    if existing_invoice:
        return existing_invoice
    
    # Get encounter to get patient_id and check if patient is admitted
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient, PaymentMechanism
    from app.crud import ipd_crud
    
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise ValueError(f"Encounter {encounter_id} not found")
    
    # Get patient to check payment mechanism
    patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
    if not patient:
        raise ValueError(f"Patient {encounter.patient_id} not found")
    
    # Check if patient is admitted (IPD)
    is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    
    # Determine payment mechanism from patient
    payment_mechanism = None
    if patient.payment_mechanism:
        payment_mechanism = patient.payment_mechanism
    
    # Create new invoice
    from app.schemas.billing_schemas import InvoiceCreate
    invoice_data = InvoiceCreate(
        patient_id=encounter.patient_id,
        encounter_id=encounter_id,
        appointment_id=encounter.appointment_id,
        payment_mechanism=payment_mechanism,
        charges=[]
    )
    
    invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    return invoice


def get_lab_test_price(db: Session, lab_order: LabOrder) -> Decimal:
    """
    Get the price for a lab test from service pricing table.
    Falls back to lab catalog, then default price if not found.
    """
    # First, try to get price from service pricing table
    if lab_order.test_name:
        pricing = service_pricing_crud.get_service_pricing_by_name(db, lab_order.test_name)
        if pricing:
            return pricing.unit_price
    
    if lab_order.test_code:
        pricing = service_pricing_crud.get_service_pricing_by_code(db, lab_order.test_code)
        if pricing and pricing.charge_type == "lab_test":
            return pricing.unit_price
    
    # Try to find lab test by code or name in catalog
    lab_test = None
    if lab_order.test_code:
        lab_test = db.query(LabTest).filter(
            LabTest.test_code == lab_order.test_code,
            LabTest.is_active == True
        ).first()
    
    if not lab_test and lab_order.test_name:
        lab_test = db.query(LabTest).filter(
            LabTest.test_name.ilike(f"%{lab_order.test_name}%"),
            LabTest.is_active == True
        ).first()
    
    if lab_test and lab_test.cost:
        return Decimal(str(lab_test.cost))
    
    # Fallback to default
    return DEFAULT_LAB_TEST_COST


def get_medication_price(db: Session, prescription: Prescription) -> Decimal:
    """
    Get the price for a medication from service pricing table.
    Falls back to inventory, then default price if not found.
    """
    # First, try to get price from service pricing table
    if prescription.medication_name:
        pricing = service_pricing_crud.get_service_pricing_by_name(db, prescription.medication_name)
        if pricing and pricing.charge_type == "pharmacy":
            return pricing.unit_price
    
    if prescription.medication_code:
        pricing = service_pricing_crud.get_service_pricing_by_code(db, prescription.medication_code)
        if pricing and pricing.charge_type == "pharmacy":
            return pricing.unit_price
    
    # Try to find medication by code or name in inventory
    from app.crud import inventory_crud
    from app.models.inventory_models import StockItem
    
    medication = None
    if prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    if not medication and prescription.medication_name:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    # If medication found, try to get price from medication's unit_price
    if medication:
        if medication.unit_price:
            return Decimal(str(medication.unit_price))
        # If no unit_price, try unit_cost as fallback
        if medication.unit_cost:
            return Decimal(str(medication.unit_cost))
    
    # Fallback to default
    return DEFAULT_PHARMACY_COST


def get_service_price(
    db: Session,
    service_name: Optional[str],
    charge_type: str,
    default_price: Decimal,
    service_code: Optional[str] = None
) -> Decimal:
    """
    Helper to fetch service pricing by name or code with fallback.
    """
    if service_name:
        pricing = service_pricing_crud.get_service_pricing_by_name(db, service_name)
        if pricing and (not charge_type or pricing.charge_type == charge_type):
            return pricing.unit_price
    
    if service_code:
        pricing = service_pricing_crud.get_service_pricing_by_code(db, service_code)
        if pricing and (not charge_type or pricing.charge_type == charge_type):
            return pricing.unit_price
    
    return default_price


def create_charge_for_consultation(
    db: Session,
    patient_id: int,
    created_by_id: int,
    encounter_id: Optional[int] = None
) -> Optional[Charge]:
    """
    Ensure a consultation charge exists for the patient (covers vitals & initial encounter).
    Returns created charge or existing charge if already present.
    """
    from app.models.patient_models import Patient
    from app.schemas.billing_schemas import InvoiceCreate
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return None
    
    # Check if consultation charge already exists for this patient/encounter
    existing_charge = db.query(Charge).join(Invoice).filter(
        Invoice.patient_id == patient_id,
        Charge.charge_type == ChargeType.CONSULTATION,
        Charge.encounter_id == encounter_id
    ).first()
    
    if existing_charge:
        return existing_charge
    
    # Determine service price
    unit_price = get_service_price(db, "Consultation", "consultation", DEFAULT_CONSULTATION_COST)
    
    # Get or create invoice
    if encounter_id:
        invoice = get_or_create_invoice_for_encounter(db, encounter_id, created_by_id)
    else:
        # Create standalone invoice
        invoice_data = InvoiceCreate(
            patient_id=patient_id,
            encounter_id=None,
            appointment_id=None,
            payment_mechanism=patient.payment_mechanism,
            charges=[]
        )
        invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    charge_data = ChargeCreate(
        charge_type=ChargeType.CONSULTATION,
        description="Consultation Fee (Covers Vitals & Initial Encounter)",
        quantity=1,
        unit_price=unit_price,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=encounter_id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    return charge


def create_charge_for_lab_order(
    db: Session,
    lab_order: LabOrder,
    created_by_id: int,
    check_payment_required: bool = True
) -> Optional[Charge]:
    """
    Automatically create a charge when a lab order is completed.
    Returns the created charge or None if charge already exists.
    
    For OPD cash customers: Pay-as-you-go (payment required before service)
    For IPD cash customers: Consumables are pay-as-you-go, but charges can be deferred to discharge
    For insurance customers: Charges are created but can be billed later
    """
    # Check if charge already exists for this lab order
    existing_charge = db.query(Charge).filter(
        Charge.lab_order_id == lab_order.id
    ).first()
    
    if existing_charge:
        return None  # Charge already exists, don't create duplicate
    
    # Get encounter and patient to check payment mechanism and admission status
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient, PaymentMechanism
    from app.crud import ipd_crud
    
    encounter = None
    patient_id = lab_order.patient_id
    if lab_order.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == lab_order.encounter_id).first()
        if not encounter:
            raise ValueError(f"Encounter {lab_order.encounter_id} not found")
        patient_id = encounter.patient_id
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")
    
    # Check if patient is admitted (IPD)
    is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    
    # Determine if payment is required immediately
    # OPD cash customers: Pay-as-you-go (payment required)
    # IPD cash customers: Consumables can be charged, but payment at discharge
    # Insurance: Can be billed later
    is_cash_customer = patient.payment_mechanism == PaymentMechanism.CASH
    require_immediate_payment = False
    
    if check_payment_required and is_cash_customer:
        if not is_admitted:
            # OPD cash customer - pay-as-you-go
            require_immediate_payment = True
        else:
            # IPD cash customer - consumables are pay-as-you-go, but can defer to discharge
            # For now, we'll create the charge but allow deferral
            require_immediate_payment = False
    
    # Get or create invoice for encounter
    if lab_order.encounter_id:
        invoice = get_or_create_invoice_for_encounter(
            db, lab_order.encounter_id, created_by_id, require_payment=require_immediate_payment
        )
    else:
        from app.schemas.billing_schemas import InvoiceCreate
        invoice_data = InvoiceCreate(
            patient_id=patient.id,
            encounter_id=None,
            appointment_id=None,
            payment_mechanism=patient.payment_mechanism,
            charges=[]
        )
        invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    # Get price from lab test catalog
    unit_price = get_lab_test_price(db, lab_order)
    
    # Create charge
    charge_data = ChargeCreate(
        charge_type=ChargeType.LAB_TEST,
        description=f"Lab Test: {lab_order.test_name}",
        quantity=1,
        unit_price=unit_price,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=lab_order.encounter_id,
        lab_order_id=lab_order.id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    
    # For OPD cash customers with pay-as-you-go, check if payment is required
    # This will be enforced at the service delivery level (e.g., when lab result is entered)
    # For now, we just create the charge
    
    return charge


def create_charge_for_radiology_order(
    db: Session,
    radiology_order: RadiologyOrder,
    created_by_id: int,
    check_payment_required: bool = True
) -> Optional[Charge]:
    """
    Automatically create a charge when a radiology order is completed.
    Returns the created charge or None if charge already exists.
    
    For OPD cash customers: Pay-as-you-go (payment required before service)
    For IPD cash customers: Consumables are pay-as-you-go, but charges can be deferred to discharge
    """
    # Check if charge already exists for this radiology order
    existing_charge = db.query(Charge).filter(
        Charge.radiology_order_id == radiology_order.id
    ).first()
    
    if existing_charge:
        return None  # Charge already exists, don't create duplicate
    
    # Get encounter and patient to check payment mechanism and admission status
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient, PaymentMechanism
    from app.crud import ipd_crud
    
    encounter = None
    patient_id = radiology_order.patient_id
    if radiology_order.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == radiology_order.encounter_id).first()
        if not encounter:
            raise ValueError(f"Encounter {radiology_order.encounter_id} not found")
        patient_id = encounter.patient_id
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise ValueError(f"Patient {patient_id} not found")
    
    # Check if patient is admitted (IPD)
    is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    
    # Determine if payment is required immediately
    is_cash_customer = patient.payment_mechanism == PaymentMechanism.CASH
    require_immediate_payment = False
    
    if check_payment_required and is_cash_customer:
        if not is_admitted:
            # OPD cash customer - pay-as-you-go
            require_immediate_payment = True
        else:
            # IPD cash customer - consumables are pay-as-you-go, but can defer to discharge
            require_immediate_payment = False
    
    # Get or create invoice for encounter
    if radiology_order.encounter_id:
        invoice = get_or_create_invoice_for_encounter(
            db, radiology_order.encounter_id, created_by_id, require_payment=require_immediate_payment
        )
    else:
        from app.schemas.billing_schemas import InvoiceCreate
        invoice_data = InvoiceCreate(
            patient_id=patient.id,
            encounter_id=None,
            appointment_id=None,
            payment_mechanism=patient.payment_mechanism,
            charges=[]
        )
        invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    # Get price from service pricing table
    unit_price = None
    if radiology_order.study_type:
        pricing = service_pricing_crud.get_service_pricing_by_name(db, radiology_order.study_type)
        if pricing and pricing.charge_type == "radiology":
            unit_price = pricing.unit_price
    
    # If not found, try to get default radiology price for the charge type
    if unit_price is None:
        radiology_pricings = service_pricing_crud.get_service_pricing_by_charge_type(db, "radiology")
        if radiology_pricings:
            # Use first active radiology pricing as default
            unit_price = radiology_pricings[0].unit_price
    
    # Fallback to default
    if unit_price is None:
        unit_price = DEFAULT_RADIOLOGY_COST
    
    # Create charge
    charge_data = ChargeCreate(
        charge_type=ChargeType.RADIOLOGY,
        description=f"Radiology Study: {radiology_order.study_type}",
        quantity=1,
        unit_price=unit_price,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=radiology_order.encounter_id,
        radiology_order_id=radiology_order.id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    return charge


def create_charge_for_prescription(
    db: Session,
    prescription: Prescription,
    created_by_id: int,
    check_payment_required: bool = True
) -> Optional[Charge]:
    """
    Automatically create a charge when a prescription is dispensed.
    Returns the created charge or None if charge already exists.
    
    For OPD cash customers: Pay-as-you-go (payment required before dispensing)
    For IPD cash customers: Consumables are pay-as-you-go, but charges can be deferred to discharge
    """
    # Check if charge already exists for this prescription
    existing_charge = db.query(Charge).filter(
        Charge.prescription_id == prescription.id
    ).first()
    
    if existing_charge:
        return None  # Charge already exists, don't create duplicate
    
    # Get encounter and patient to check payment mechanism and admission status
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient, PaymentMechanism
    from app.crud import ipd_crud
    
    encounter = db.query(Encounter).filter(Encounter.id == prescription.encounter_id).first()
    if not encounter:
        raise ValueError(f"Encounter {prescription.encounter_id} not found")
    
    patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
    if not patient:
        raise ValueError(f"Patient {encounter.patient_id} not found")
    
    # Check if patient is admitted (IPD)
    is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    
    # Determine if payment is required immediately
    is_cash_customer = patient.payment_mechanism == PaymentMechanism.CASH
    require_immediate_payment = False
    
    if check_payment_required and is_cash_customer:
        if not is_admitted:
            # OPD cash customer - pay-as-you-go (payment required before dispensing)
            require_immediate_payment = True
        else:
            # IPD cash customer - consumables are pay-as-you-go, but can defer to discharge
            require_immediate_payment = False
    
    # Get or create invoice for encounter
    invoice = get_or_create_invoice_for_encounter(
        db, prescription.encounter_id, created_by_id, require_payment=require_immediate_payment
    )
    
    # Get price from medication inventory
    unit_price = get_medication_price(db, prescription)
    quantity = prescription.quantity or 1
    
    # Create charge
    charge_data = ChargeCreate(
        charge_type=ChargeType.PHARMACY,
        description=f"Medication: {prescription.medication_name} ({prescription.dosage}, {prescription.frequency})",
        quantity=quantity,
        unit_price=unit_price,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=prescription.encounter_id,
        prescription_id=prescription.id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    return charge


def create_charge_for_procedure(
    db: Session,
    procedure: Procedure,
    created_by_id: int
) -> Optional[Charge]:
    """
    Automatically create a charge when a procedure is ordered or completed.
    Returns the created charge or None if charge already exists.
    """
    # Avoid duplicate charges
    existing_charge = db.query(Charge).filter(
        Charge.description.like(f"Procedure #{procedure.id}%"),
        Charge.charge_type == ChargeType.PROCEDURE
    ).join(Invoice).filter(Invoice.patient_id == procedure.patient_id).first()
    
    if existing_charge:
        return None
    
    # Determine price from service pricing table
    unit_price = get_service_price(
        db,
        procedure.procedure_name,
        "procedure",
        DEFAULT_PROCEDURE_COST,
        service_code=procedure.procedure_code
    )
    
    # Procedures might not always be linked to an encounter (walk-in)
    encounter_id = procedure.encounter_id
    
    if encounter_id:
        invoice = get_or_create_invoice_for_encounter(db, encounter_id, created_by_id, require_payment=False)
    else:
        # Create standalone invoice for walk-in procedure
        from app.schemas.billing_schemas import InvoiceCreate
        invoice_data = InvoiceCreate(
            patient_id=procedure.patient_id,
            encounter_id=None,
            appointment_id=None,
            payment_mechanism=None,
            charges=[]
        )
        invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    
    charge_data = ChargeCreate(
        charge_type=ChargeType.PROCEDURE,
        description=f"Procedure #{procedure.id}: {procedure.procedure_name}",
        quantity=1,
        unit_price=unit_price,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=encounter_id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    return charge

