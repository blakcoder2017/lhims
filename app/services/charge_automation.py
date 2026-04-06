"""
Automated Charge Aggregation Service

This module automatically creates charges when orders are completed:
- Lab orders: Creates charge when lab test is completed
- Radiology orders: Creates charge when radiology study is completed
- Prescriptions: Creates charge when prescription is dispensed
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict
from decimal import Decimal
from datetime import datetime

from app.models.billing_models import Invoice, Charge, InvoiceStatus, ChargeType, PaymentMethod
from app.models.patient_models import PaymentMechanism
from app.models.encounter_models import LabOrder, RadiologyOrder, Prescription, OrderStatus
from app.models.lab_catalog_models import LabTest
from app.models.inventory_models import Medication
from app.models.procedure_models import Procedure
from app.models.procedure_catalog_models import ProcedureCatalog
from app.crud import billing_crud
from app.crud import service_pricing_crud
from app.schemas.billing_schemas import ChargeCreate

# Setup logging
logger = logging.getLogger(__name__)

# Default pricing (fallback if service pricing not configured)
DEFAULT_LAB_TEST_COST = Decimal('50.00')
DEFAULT_RADIOLOGY_COST = Decimal('100.00')
DEFAULT_PHARMACY_COST = Decimal('20.00')  # Per unit
DEFAULT_CONSULTATION_COST = Decimal('100.00')
DEFAULT_PROCEDURE_COST = Decimal('150.00')


def convert_payment_mechanism_to_method(payment_mechanism: PaymentMechanism) -> PaymentMethod:
    """
    Convert Patient PaymentMechanism enum to PaymentMethod enum for billing.
    
    PaymentMechanism (patient model): CASH, NHIS, PRIVATE_INSURANCE, SELF_PAY
    PaymentMethod (billing model): cash, nhis, private_insurance, mobile_money, card, bank_transfer
    
    Args:
        payment_mechanism: The payment mechanism from patient model
        
    Returns:
        Corresponding PaymentMethod enum value
    """
    mapping = {
        PaymentMechanism.CASH: PaymentMethod.CASH,
        PaymentMechanism.NHIS: PaymentMethod.NHIS,
        PaymentMechanism.PRIVATE_INSURANCE: PaymentMethod.PRIVATE_INSURANCE,
        PaymentMechanism.SELF_PAY: PaymentMethod.CASH,  # SELF_PAY defaults to CASH
    }
    return mapping.get(payment_mechanism, PaymentMethod.CASH)


def build_procedure_description(procedure: Procedure, catalog: Optional[ProcedureCatalog] = None) -> str:
    """
    Build a clear description for procedure charges.
    Uses procedure catalog details when available.
    
    Args:
        procedure: The procedure object
        catalog: Optional procedure catalog entry
    
    Returns:
        A clear description string for the bill
    """
    if catalog:
        # Use procedure catalog details for clear billing
        code_info = f" ({catalog.procedure_code})" if catalog.procedure_code else ""
        category_info = f" - {catalog.procedure_category}" if catalog.procedure_category else ""
        return f"{catalog.procedure_name}{code_info}{category_info}"
    else:
        # Fallback to procedure name with ID
        return f"Procedure #{procedure.id}: {procedure.procedure_name}"


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
    # DEBUG: Log encounter_id being queried
    print(f"[DEBUG] get_or_create_invoice_for_encounter - encounter_id: {encounter_id}")
    
    # Check if invoice already exists for this encounter (any non-cancelled status)
    existing_invoice = db.query(Invoice).filter(
        Invoice.encounter_id == encounter_id,
        Invoice.is_active == True,
        Invoice.status.in_([
            InvoiceStatus.DRAFT.value,
            InvoiceStatus.PENDING.value,
            InvoiceStatus.PARTIALLY_PAID.value,
            InvoiceStatus.PAID.value,
        ])
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
    
    # Determine payment method from patient
    payment_method = None
    if patient.payment_mechanism:
        payment_method = convert_payment_mechanism_to_method(patient.payment_mechanism)
    
    # Create new invoice
    from app.schemas.billing_schemas import InvoiceCreate
    invoice_data = InvoiceCreate(
        patient_id=encounter.patient_id,
        encounter_id=encounter_id,
        appointment_id=encounter.appointment_id,
        payment_mechanism=payment_method,
        charges=[]
    )
    
    invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    return invoice


def get_radiology_price(db: Session, radiology_order: "RadiologyOrder") -> Decimal:
    """
    Get the price for a radiology study from service pricing table.
    Falls back to default price if not found.
    """
    # First, try to get price from service pricing table by study_type
    if radiology_order.study_type:
        pricing = service_pricing_crud.get_service_pricing_by_name(db, radiology_order.study_type)
        if pricing and pricing.charge_type == "radiology":
            return pricing.unit_price
    
    # Try to get default radiology price for the charge type
    radiology_pricings = service_pricing_crud.get_service_pricing_by_charge_type(db, "radiology")
    if radiology_pricings:
        # Use first active radiology pricing as default
        return radiology_pricings[0].unit_price
    
    # Fallback to default
    return DEFAULT_RADIOLOGY_COST


def get_lab_test_price(db: Session, lab_order: LabOrder) -> Decimal:
    """
    Get the price for a lab test from Lab Test Catalog.
    Uses lab_test_id if available, otherwise falls back to fuzzy match.
    """
    # First, try to get price using lab_test_id (direct reference)
    if lab_order.lab_test_id:
        lab_test = db.query(LabTest).filter(
            LabTest.id == lab_order.lab_test_id,
            LabTest.is_active == True
        ).first()
        if lab_test and lab_test.cost:
            return Decimal(str(lab_test.cost))
    
    # Try to find lab test by code or name in catalog (fallback)
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
    
    # Fallback to default if no price found in catalog
    return DEFAULT_LAB_TEST_COST


def get_medication_price(db: Session, prescription: Prescription) -> Decimal:
    """
    Get the price for a medication from:
    1. PharmacyDrug (Ghana system) - preferred for Ghana pharmacy
    2. Service pricing table
    3. Inventory medication
    4. Default price fallback
    """
    # First, try to get price from PharmacyBatch (Ghana system) - get FEFO price
    if prescription.pharmacy_drug_id:
        try:
            from uuid import UUID
            from app.models.pharmacy_models import PharmacyBatch
            drug_uuid = UUID(prescription.pharmacy_drug_id) if isinstance(prescription.pharmacy_drug_id, str) else prescription.pharmacy_drug_id
            # Get the FEFO (First Expired First Out) batch with selling_price
            batch = db.query(PharmacyBatch).filter(
                PharmacyBatch.drug_id == drug_uuid,
                PharmacyBatch.status == "ACTIVE",
                PharmacyBatch.selling_price.isnot(None),
                PharmacyBatch.qty_on_hand > 0
            ).order_by(PharmacyBatch.expiry_date.asc()).first()
            if batch and batch.selling_price:
                return Decimal(str(batch.selling_price))
        except (ValueError, TypeError, AttributeError):
            pass  # Invalid UUID or no pharmacy_drug_id
    
    # Second, try to get price from service pricing table
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


def get_consultation_price_for_department(
    db: Session,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    visit_type: Optional[str] = None,
    revisit_follow_up_percentage: Optional[Decimal] = None
) -> Decimal:
    """
    Get consultation price from Departments (admin/departments), NOT ServicePricing.
    Uses Department.consultation_price when department is provided. If department has no
    price set, uses DEFAULT_CONSULTATION_COST. ServicePricing is only used when no
    department context is given (backward compatibility).
    """
    from app.crud import department_crud
    
    base_price = None
    department = None
    if department_id:
        department = department_crud.get_department(db, department_id)
    elif department_name:
        department = department_crud.get_department_by_name(db, department_name)
    
    # When we have department context, use department.consultation_price only (never ServicePricing)
    if department_id or department_name:
        if department is not None and department.consultation_price is not None:
            base_price = department.consultation_price
        else:
            base_price = DEFAULT_CONSULTATION_COST
    else:
        # No department context - fall back to ServicePricing for backward compat
        base_price = get_service_price(db, "Consultation", "consultation", DEFAULT_CONSULTATION_COST)
    
    # Revisit/follow-up discount
    if visit_type and (visit_type.lower() in ("follow_up", "revisit")) and revisit_follow_up_percentage is not None:
        pct = Decimal(str(revisit_follow_up_percentage))
        base_price = (base_price * pct / Decimal("100")).quantize(Decimal("0.01"))
    
    return base_price


def create_charge_for_consultation(
    db: Session,
    patient_id: int,
    created_by_id: Optional[int] = None,
    encounter_id: Optional[int] = None,
    opd_visit_id: Optional[int] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    visit_type: Optional[str] = None
) -> Optional[Charge]:
    """
    Ensure a consultation charge exists for the patient (covers vitals & initial encounter).
    Uses department-based pricing when department_id or department_name is provided.
    Returns created charge or existing charge if already present.
    """
    from app.models.patient_models import Patient
    from app.schemas.billing_schemas import InvoiceCreate
    from app.models.user_models import User
    
    logger.info(f"[CHARGE_AUTO_DBG] create_charge_for_consultation called - patient_id={patient_id}, encounter_id={encounter_id}, opd_visit_id={opd_visit_id}")
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return None
    
    # Check if patient is already admitted to IPD - skip consultation fee for IPD patients
    # IPD patients are billed for consultation as part of their admission/ward charges at discharge
    from app.models.ipd_models import Admission, AdmissionStatus
    from app.utils.payment_verification import is_patient_admitted
    is_admitted = is_patient_admitted(db, patient_id)
    if is_admitted:
        logger.info(f"[CHARGE_AUTO_DBG] Patient {patient_id} is already admitted to IPD - skipping consultation fee creation")
        return None
    
    # Check if patient has active direct service registration today
    # Direct service patients skip consultation fee
    from app.utils.payment_verification import has_active_direct_service_registration
    if has_active_direct_service_registration(db, patient_id):
        logger.info(f"[CHARGE_AUTO_DBG] Patient {patient_id} has active direct service registration - skipping consultation fee creation")
        return None
    
    # Check if patient has a triage (vitals) record today
    # Patients who don't go through triage should not be charged consultation
    from app.utils.payment_verification import has_today_triage_record
    if not has_today_triage_record(db, patient_id):
        logger.info(f"[CHARGE_AUTO_DBG] Patient {patient_id} has no triage record today - skipping consultation fee creation")
        return None
    
    # If created_by_id is None, try to get a system user as fallback
    if not created_by_id:
        # Try to find an admin user as fallback
        from app.models.user_models import Role
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if admin_role:
            admin_user = db.query(User).filter(
                User.role_id == admin_role.id,
                User.is_active == True
            ).first()
            if admin_user:
                created_by_id = admin_user.id
        
        # If no admin found, use first active user
        if not created_by_id:
            first_user = db.query(User).filter(User.is_active == True).first()
            if first_user:
                created_by_id = first_user.id
            else:
                # If no users exist, this is a system error - return None
                print("Warning: No active users found for consultation charge creation")
                return None
    
    # Check if consultation charge already exists for this patient
    # Also check by opd_visit_id or patient+today to catch charges created during triage
    existing_charge = None
    
    # Priority 1: Check by encounter_id if provided
    if encounter_id:
        existing_charge = db.query(Charge).join(Invoice).filter(
            Invoice.patient_id == patient_id,
            Charge.charge_type == ChargeType.CONSULTATION,
            Charge.encounter_id == encounter_id
        ).first()
    
    # Priority 2: Check by opd_visit_id if provided and no existing charge found
    if not existing_charge and opd_visit_id:
        existing_charge = db.query(Charge).join(Invoice).filter(
            Invoice.patient_id == patient_id,
            Charge.charge_type == ChargeType.CONSULTATION,
            (Charge.opd_visit_id == opd_visit_id) | (Invoice.opd_visit_id == opd_visit_id)
        ).first()
    
    # Priority 3: Check for any consultation charge today (PAID or UNPAID) - only when NO opd_visit_id
    # (When opd_visit_id is provided, we must use charge for THIS visit only - never reuse from another)
    if not existing_charge and not opd_visit_id:
        from datetime import date
        # First check for PAID charges (patient already paid at registration)
        existing_charge = db.query(Charge).join(Invoice).filter(
            Invoice.patient_id == patient_id,
            Charge.charge_type == ChargeType.CONSULTATION,
            Charge.encounter_id.is_(None),
            Invoice.is_active == True,
            Invoice.balance <= Decimal('0'),  # PAID
            Invoice.status == InvoiceStatus.PAID,  # PAID
            func.date(Invoice.invoice_date) == date.today()
        ).first()
        # If no paid charge found, check for UNPAID charges
        if not existing_charge:
            existing_charge = db.query(Charge).join(Invoice).filter(
                Invoice.patient_id == patient_id,
                Charge.charge_type == ChargeType.CONSULTATION,
                Charge.encounter_id.is_(None),
                Invoice.is_active == True,
                Invoice.balance > Decimal('0'),
                Invoice.status != InvoiceStatus.PAID,
                func.date(Invoice.invoice_date) == date.today()
            ).first()
    
    if existing_charge:
        # If existing charge doesn't have encounter_id but we have one now, update it
        if encounter_id and not existing_charge.encounter_id:
            existing_charge.encounter_id = encounter_id
            db.commit()
            db.refresh(existing_charge)
            logger.info(f"[CHARGE_AUTO_DBG] Updated existing charge {existing_charge.id} with encounter_id {encounter_id}")
        # When department provided, ensure charge amount matches (revisit discount may not have been applied)
        revisit_pct_existing = None
        try:
            from app.crud import hospital_settings_crud
            settings = hospital_settings_crud.get_hospital_settings(db)
            if settings and getattr(settings, "revisit_follow_up_percentage", None) is not None:
                revisit_pct_existing = settings.revisit_follow_up_percentage
        except Exception:
            pass
        if department_id or department_name:
            from app.models.encounter_models import Encounter, EncounterStatus
            effective_visit_type = visit_type
            if not effective_visit_type and revisit_pct_existing is not None:
                has_prev = db.query(Encounter).filter(
                    Encounter.patient_id == patient_id,
                    Encounter.is_active == True,
                    Encounter.status == EncounterStatus.COMPLETED.value
                ).first() is not None
                if has_prev:
                    effective_visit_type = "revisit"
            correct_price = get_consultation_price_for_department(
                db, department_id=department_id, department_name=department_name,
                visit_type=effective_visit_type, revisit_follow_up_percentage=revisit_pct_existing
            )
            if abs(float(existing_charge.total_amount) - float(correct_price)) > Decimal("0.01"):
                from app.schemas.billing_schemas import ChargeUpdate
                billing_crud.update_charge(db, existing_charge.id, ChargeUpdate(unit_price=correct_price))
                db.refresh(existing_charge)
                db.refresh(existing_charge.invoice)
                logger.info(f"[CHARGE_AUTO_DBG] Corrected existing charge {existing_charge.id} to department price {correct_price}")
        else:
            logger.info(f"[CHARGE_AUTO_DBG] Found existing charge {existing_charge.id} for patient {patient_id}, returning it")
        return existing_charge
    
    logger.info(f"[CHARGE_AUTO_DBG] No existing charge found for patient {patient_id}, creating new one")
    
    # Revisit/follow-up percentage from hospital settings (if present)
    revisit_pct = None
    try:
        from app.crud import hospital_settings_crud
        settings = hospital_settings_crud.get_hospital_settings(db)
        if settings and getattr(settings, "revisit_follow_up_percentage", None) is not None:
            revisit_pct = settings.revisit_follow_up_percentage
    except Exception:
        pass
    
    # Returning patient = has at least one completed encounter from a previous visit
    # Apply revisit discount to returning patients (not first-time visitors)
    from app.models.encounter_models import Encounter, EncounterStatus
    effective_visit_type = visit_type
    if not effective_visit_type and revisit_pct is not None:
        has_previous_encounter = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.is_active == True,
            Encounter.status == EncounterStatus.COMPLETED.value
        ).first() is not None
        if has_previous_encounter:
            effective_visit_type = "revisit"
            logger.info(f"[CHARGE_AUTO_DBG] Patient {patient_id} is returning (has previous encounter), applying revisit discount")
    
    # Determine service price (department-based, with optional revisit discount for returning patients)
    unit_price = get_consultation_price_for_department(
        db,
        department_id=department_id,
        department_name=department_name,
        visit_type=effective_visit_type,
        revisit_follow_up_percentage=revisit_pct
    )
    logger.info(f"[CHARGE_AUTO_DBG] Unit price for consultation: {unit_price}")
    
    # Get or create invoice
    if encounter_id:
        invoice = get_or_create_invoice_for_encounter(db, encounter_id, created_by_id)
    elif opd_visit_id:
        # Create invoice linked to OPD visit
        invoice_data = InvoiceCreate(
            patient_id=patient_id,
            encounter_id=None,
            appointment_id=None,
            opd_visit_id=opd_visit_id,
            payment_mechanism=convert_payment_mechanism_to_method(patient.payment_mechanism),
            charges=[]
        )
        invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
    else:
        # Create standalone invoice
        invoice_data = InvoiceCreate(
            patient_id=patient_id,
            encounter_id=None,
            appointment_id=None,
            payment_mechanism=convert_payment_mechanism_to_method(patient.payment_mechanism),
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
        encounter_id=encounter_id,
        opd_visit_id=opd_visit_id
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    logger.info(f"[CHARGE_AUTO_DBG] Created NEW charge {charge.id} on invoice {invoice.id} for patient {patient_id}")
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
    # Never bill amendment archive records — they are audit copies, not new service orders
    if getattr(lab_order, 'result_status', None) == 'AMENDED_VERSION':
        logger.info(f"[CHARGE_AUTO] Skipping charge for AMENDED_VERSION archive order {lab_order.id}")
        return None

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
    is_admitted = False
    if encounter:
        is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    else:
        # For walk-in orders without encounter, check directly by patient_id
        is_admitted = ipd_crud.get_current_admission(db, patient_id) is not None
    
    # Determine if payment is required immediately
    # OPD cash customers: Pay-as-you-go (payment required)
    # IPD cash customers: Consumables can be charged, but payment at discharge
    # Insurance: Can be billed later
    # Treat NULL payment_mechanism as cash
    is_cash_customer = patient.payment_mechanism is None or patient.payment_mechanism == PaymentMechanism.CASH
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
            payment_mechanism=convert_payment_mechanism_to_method(patient.payment_mechanism),
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
    is_admitted = False
    if encounter:
        is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    else:
        # For walk-in orders without encounter, check directly by patient_id
        is_admitted = ipd_crud.get_current_admission(db, patient_id) is not None
    
    # Determine if payment is required immediately
    # Treat NULL payment_mechanism as cash
    is_cash_customer = patient.payment_mechanism is None or patient.payment_mechanism == PaymentMechanism.CASH
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
            payment_mechanism=convert_payment_mechanism_to_method(patient.payment_mechanism),
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
    
    For walk-in prescriptions (is_walk_in=True): Creates a patient-level invoice
    """
    # Check if charge already exists for this prescription
    existing_charge = db.query(Charge).filter(
        Charge.prescription_id == prescription.id
    ).first()
    
    if existing_charge:
        return None  # Charge already exists, don't create duplicate
    
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient, PaymentMechanism
    from app.crud import ipd_crud
    
    # Handle walk-in prescriptions (no encounter) OR legacy prescriptions with no encounter
    # Check both encounter_id is None AND is_walk_in flag
    if prescription.encounter_id is None or prescription.is_walk_in:
        # This is a walk-in pharmacy sale - create patient-level invoice
        # For legacy data, try to get patient_id from encounter if available
        patient_id = prescription.patient_id
        
        # If no patient_id on prescription but has encounter_id, try to get from encounter
        if patient_id is None and prescription.encounter_id:
            encounter = db.query(Encounter).filter(Encounter.id == prescription.encounter_id).first()
            if encounter:
                patient_id = encounter.patient_id
        
        if patient_id is None:
            # Cannot create charge without patient - skip this prescription
            print(f"Warning: Cannot create charge for prescription {prescription.id} - no patient found")
            return None
        
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient {prescription.patient_id} not found")
        
        # Check for existing active invoice for this patient (walk-in)
        from app.models.billing_models import Invoice, InvoiceStatus
        existing_invoice = db.query(Invoice).filter(
            Invoice.patient_id == patient.id,
            Invoice.encounter_id.is_(None),
            Invoice.is_active == True,
            Invoice.status.in_([InvoiceStatus.DRAFT.value, InvoiceStatus.PENDING.value])
        ).first()
        
        if existing_invoice:
            invoice = existing_invoice
        else:
            # Create new walk-in invoice
            from app.schemas.billing_schemas import InvoiceCreate
            invoice_data = InvoiceCreate(
                patient_id=patient.id,
                encounter_id=None,
                payment_mechanism="cash",  # Walk-in is always cash
                charges=[]
            )
            invoice = billing_crud.create_invoice(db, invoice_data, created_by_id)
        
        # Get price from medication inventory
        unit_price = get_medication_price(db, prescription)
        quantity = prescription.quantity if prescription.quantity else 1
        
        # Create charge
        charge_data = ChargeCreate(
            charge_type=ChargeType.PHARMACY,
            description=f"Medication: {prescription.medication_name} ({prescription.dosage or 'N/A'}, {prescription.frequency or 'N/A'})",
            quantity=quantity,
            unit_price=unit_price,
            discount=Decimal('0.00'),
            tax_rate=Decimal('0.00'),
            encounter_id=None,
            prescription_id=prescription.id
        )
        
        charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
        return charge
    
    # Original logic for encounter-based prescriptions
    encounter = db.query(Encounter).filter(Encounter.id == prescription.encounter_id).first()
    if not encounter:
        raise ValueError(f"Encounter {prescription.encounter_id} not found")
    
    patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
    if not patient:
        raise ValueError(f"Patient {encounter.patient_id} not found")
    
    # Check if patient is admitted (IPD)
    is_admitted = ipd_crud.get_current_admission(db, encounter.patient_id) is not None
    
    # Determine if payment is required immediately
    # Treat NULL payment_mechanism as cash
    is_cash_customer = patient.payment_mechanism is None or patient.payment_mechanism == PaymentMechanism.CASH
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
    # Default to 1 if quantity is not specified - pharmacy will reconcile after dispensing
    quantity = prescription.quantity if prescription.quantity else 1
    
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
    created_by_id: int,
    payment_mechanism: str = None
) -> Optional[Charge]:
    """
    Automatically create a charge when a procedure is ordered or completed.
    Uses ProcedureCatalog prices based on payment mechanism.
    Returns the created charge or None if charge already exists.
    
    Args:
        procedure: The procedure to charge for
        created_by_id: ID of user creating the charge
        payment_mechanism: Payment method - "cash", "nhis", or "private_insurance". 
                         If not provided, will try to get from invoice.
    """
    # Avoid duplicate charges
    existing_charge = db.query(Charge).filter(
        Charge.description.like(f"Procedure #{procedure.id}%"),
        Charge.charge_type == ChargeType.PROCEDURE
    ).join(Invoice).filter(Invoice.patient_id == procedure.patient_id).first()
    
    if existing_charge:
        return None
    
    # Get encounter_id for invoice lookup
    encounter_id = procedure.encounter_id
    
    # Try to get payment_mechanism from invoice if not provided
    if payment_mechanism is None:
        if encounter_id:
            invoice = db.query(Invoice).filter(
                Invoice.encounter_id == encounter_id,
                Invoice.patient_id == procedure.patient_id
            ).order_by(Invoice.id.desc()).first()
            if invoice and invoice.payment_mechanism:
                payment_mechanism = invoice.payment_mechanism.value
        
        if payment_mechanism is None:
            payment_mechanism = "cash"  # Default to cash
    
    # Determine price from ProcedureCatalog - ALWAYS prefer ProcedureCatalog
    # First try direct link, then fallback to matching by name
    unit_price = DEFAULT_PROCEDURE_COST  # Default fallback
    catalog = None
    
    if procedure.procedure_catalog_id:
        # Get procedure catalog entry via direct link
        catalog = db.query(ProcedureCatalog).filter(
            ProcedureCatalog.id == procedure.procedure_catalog_id
        ).first()
    
    # If no direct link, try to find by procedure name
    if not catalog and procedure.procedure_name:
        # Look up ProcedureCatalog by name (case-insensitive)
        catalog = db.query(ProcedureCatalog).filter(
            func.lower(ProcedureCatalog.procedure_name) == func.lower(procedure.procedure_name)
        ).first()
        
        # Auto-link procedure to catalog if found
        if catalog:
            procedure.procedure_catalog_id = catalog.id
            db.commit()
    
    if catalog:
        # Use appropriate price based on payment mechanism
        if payment_mechanism == "nhis" and catalog.nhis_covered:
            unit_price = catalog.nhis_price or catalog.cash_price or DEFAULT_PROCEDURE_COST
        elif payment_mechanism == "private_insurance" and catalog.private_insurance_covered:
            unit_price = catalog.private_insurance_price or catalog.cash_price or DEFAULT_PROCEDURE_COST
        else:
            # Default to cash price
            unit_price = catalog.cash_price or DEFAULT_PROCEDURE_COST
    else:
        # Fallback to service pricing table if no catalog found
        unit_price = get_service_price(
            db,
            procedure.procedure_name,
            "procedure",
            DEFAULT_PROCEDURE_COST,
            service_code=procedure.procedure_code
        )
    
    # Procedures might not always be linked to an encounter (walk-in)
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
        description=build_procedure_description(procedure, catalog),
        quantity=1,
        unit_price=unit_price,
        discount=Decimal('0.00'),
        tax_rate=Decimal('0.00'),
        encounter_id=encounter_id,
        procedure_catalog_id=catalog.id if catalog else None
    )
    
    charge = billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
    return charge


def reconcile_pharmacy_charge_after_dispensing(
    db: Session,
    prescription_id: int,
    qty_dispensed: int,
    unit_price: Decimal
) -> Optional[Dict]:
    """
    Reconciles pharmacy billing after dispensing.
    
    This function adjusts the billing charge to match the actual quantity dispensed
    by the pharmacy. It handles:
    - Overpayment: Creates a credit/refund
    - Underpayment: Creates additional charge
    
    Args:
        db: Database session
        prescription_id: ID of the prescription that was dispensed
        qty_dispensed: Actual quantity dispensed by pharmacy
        unit_price: Unit price from the dispensed batch
    
    Returns:
        Dict with reconciliation details or None if no charge to reconcile
    """
    from app.models.billing_models import Charge, ChargeType, Invoice
    from app.schemas.billing_schemas import ChargeCreate
    from app.crud import billing_crud
    from decimal import Decimal
    
    # Find the existing charge for this prescription
    charge = db.query(Charge).filter(
        Charge.prescription_id == prescription_id,
        Charge.charge_type == ChargeType.PHARMACY
    ).first()
    
    if not charge:
        # No charge exists yet - create one with the dispensed quantity
        # This happens when prescription.quantity was NULL (doctor didn't specify)
        from app.models.encounter_models import Encounter, Prescription
        
        # Get the prescription to find its encounter
        prescription = db.query(Prescription).filter(
            Prescription.id == prescription_id
        ).first()
        
        if prescription and prescription.encounter_id:
            invoice = get_or_create_invoice_for_encounter(
                db, prescription.encounter_id, created_by_id=None, require_payment=False
            )
            
            charge_data = ChargeCreate(
                charge_type=ChargeType.PHARMACY,
                description=f"Medication dispensed: {qty_dispensed} units",
                quantity=qty_dispensed,
                unit_price=unit_price,
                discount=Decimal('0.00'),
                tax_rate=Decimal('0.00'),
                prescription_id=prescription_id,
                encounter_id=prescription.encounter_id
            )
            billing_crud.add_charge_to_invoice(db, invoice.id, charge_data)
            db.commit()
            
            return {
                "action": "created",
                "prescription_id": prescription_id,
                "qty_dispensed": qty_dispensed,
                "total": float(qty_dispensed * unit_price),
                "message": f"Charge created for {qty_dispensed} units at GHS {float(unit_price)} each"
            }
        return None
    
    # Calculate new total based on actual dispensing
    new_total = qty_dispensed * unit_price
    old_subtotal = charge.quantity * charge.unit_price
    old_tax = charge.tax_amount
    old_total = old_subtotal + old_tax
    
    # Get the invoice
    invoice = db.query(Invoice).filter(Invoice.id == charge.invoice_id).first()
    
    if new_total < old_total:
        # Patient overpaid - create credit/refund
        difference = old_total - new_total
        
        # Update the charge to reflect actual amount
        charge.quantity = qty_dispensed
        # Calculate total with tax
        subtotal = qty_dispensed * unit_price
        tax_amount = subtotal * (charge.tax_rate / Decimal('100'))
        charge.tax_amount = tax_amount
        charge.total_amount = subtotal + tax_amount
        
        # Recalculate invoice totals
        if invoice:
            invoice.subtotal = invoice.subtotal - old_subtotal + subtotal
            invoice.tax_amount = invoice.tax_amount - old_tax + tax_amount
            invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.tax_amount
            invoice.balance = invoice.total_amount - invoice.paid_amount
        
        # Create a credit note for the overpayment
        if invoice:
            credit_note_data = billing_crud.ChargeCreate(
                charge_type=ChargeType.OTHER,
                description=f"Pharmacy Dispense Adjustment - Credit for prescription #{prescription_id}",
                quantity=1,
                unit_price=-difference,  # Negative amount for credit
                discount=Decimal('0.00'),
                tax_rate=Decimal('0.00'),
                prescription_id=prescription_id,
                encounter_id=charge.encounter_id
            )
            billing_crud.add_charge_to_invoice(db, invoice.id, credit_note_data)
        
        db.commit()
        
        return {
            "action": "credit",
            "prescription_id": prescription_id,
            "qty_dispensed": qty_dispensed,
            "old_total": float(old_total),
            "new_total": float(new_total),
            "difference": float(difference),
            "message": f"Credit of GHS {float(difference)} will be applied to patient account"
        }
    
    elif new_total > old_total:
        # Patient underpaid - create additional charge
        difference = new_total - old_total
        
        # Update the charge to reflect actual amount
        charge.quantity = qty_dispensed
        # Calculate total with tax
        subtotal = qty_dispensed * unit_price
        tax_amount = subtotal * (charge.tax_rate / Decimal('100'))
        charge.tax_amount = tax_amount
        charge.total_amount = subtotal + tax_amount
        
        # Recalculate invoice totals
        if invoice:
            invoice.subtotal = invoice.subtotal - old_subtotal + subtotal
            invoice.tax_amount = invoice.tax_amount - old_tax + tax_amount
            invoice.total_amount = invoice.subtotal - invoice.discount_amount + invoice.tax_amount
            invoice.balance = invoice.total_amount - invoice.paid_amount
        
        # Create additional charge for the shortfall
        if invoice:
            additional_charge_data = billing_crud.ChargeCreate(
                charge_type=ChargeType.PHARMACY,
                description=f"Pharmacy Dispense Adjustment - Additional charge for prescription #{prescription_id}",
                quantity=1,
                unit_price=difference,
                discount=Decimal('0.00'),
                tax_rate=Decimal('0.00'),
                prescription_id=prescription_id,
                encounter_id=charge.encounter_id
            )
            billing_crud.add_charge_to_invoice(db, invoice.id, additional_charge_data)
        
        db.commit()
        
        return {
            "action": "additional_charge",
            "prescription_id": prescription_id,
            "qty_dispensed": qty_dispensed,
            "old_total": float(old_total),
            "new_total": float(new_total),
            "difference": float(difference),
            "message": f"Additional charge of GHS {float(difference)} required"
        }
    
    else:
        # No difference - just update quantity
        charge.quantity = qty_dispensed
        db.commit()
        
        return {
            "action": "no_change",
            "prescription_id": prescription_id,
            "qty_dispensed": qty_dispensed,
            "total": float(new_total),
            "message": "Charge updated to match dispensed quantity"
        }

