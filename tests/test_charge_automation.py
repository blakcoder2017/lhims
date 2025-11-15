"""
Tests for automated charge aggregation service.
"""
import pytest
from decimal import Decimal
from datetime import datetime

from app.models.encounter_models import LabOrder, RadiologyOrder, Prescription, OrderStatus
from app.models.billing_models import Invoice, Charge, ChargeType
from app.services.charge_automation import (
    create_charge_for_lab_order,
    create_charge_for_radiology_order,
    create_charge_for_prescription,
    get_lab_test_price,
    get_medication_price
)


@pytest.mark.unit
def test_get_lab_test_price_with_catalog(db_session):
    """Test getting lab test price from catalog."""
    from app.models.lab_catalog_models import LabTest
    
    # Create a lab test with price
    lab_test = LabTest(
        test_name="Complete Blood Count",
        test_code="CBC",
        cost=Decimal("75.00"),
        is_active=True
    )
    db_session.add(lab_test)
    db_session.commit()
    
    # Create a lab order
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient
    
    patient = Patient(
        first_name="Test",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        gender="Male",
        national_id="TEST-123"
    )
    db_session.add(patient)
    db_session.flush()
    
    encounter = Encounter(
        patient_id=patient.id,
        clinician_id=1,
        status="in_progress"
    )
    db_session.add(encounter)
    db_session.flush()
    
    lab_order = LabOrder(
        encounter_id=encounter.id,
        ordered_by_id=1,
        test_name="Complete Blood Count",
        test_code="CBC",
        status=OrderStatus.COMPLETED.value
    )
    db_session.add(lab_order)
    db_session.commit()
    
    # Test price retrieval
    price = get_lab_test_price(db_session, lab_order)
    assert price == Decimal("75.00")


@pytest.mark.unit
def test_get_lab_test_price_without_catalog(db_session):
    """Test getting default lab test price when not in catalog."""
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient
    
    patient = Patient(
        first_name="Test",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        gender="Male",
        national_id="TEST-456"
    )
    db_session.add(patient)
    db_session.flush()
    
    encounter = Encounter(
        patient_id=patient.id,
        clinician_id=1,
        status="in_progress"
    )
    db_session.add(encounter)
    db_session.flush()
    
    lab_order = LabOrder(
        encounter_id=encounter.id,
        ordered_by_id=1,
        test_name="Unknown Test",
        status=OrderStatus.COMPLETED.value
    )
    db_session.add(lab_order)
    db_session.commit()
    
    # Test default price
    price = get_lab_test_price(db_session, lab_order)
    assert price == Decimal("50.00")  # DEFAULT_LAB_TEST_COST


@pytest.mark.integration
def test_create_charge_for_lab_order(db_session):
    """Test automatic charge creation for completed lab order."""
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient
    
    # Setup patient and encounter
    patient = Patient(
        first_name="Test",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        gender="Male",
        national_id="TEST-789"
    )
    db_session.add(patient)
    db_session.flush()
    
    encounter = Encounter(
        patient_id=patient.id,
        clinician_id=1,
        status="in_progress"
    )
    db_session.add(encounter)
    db_session.flush()
    
    # Create completed lab order
    lab_order = LabOrder(
        encounter_id=encounter.id,
        ordered_by_id=1,
        test_name="Blood Test",
        status=OrderStatus.COMPLETED.value,
        completed_at=datetime.now()
    )
    db_session.add(lab_order)
    db_session.commit()
    
    # Create charge
    charge = create_charge_for_lab_order(db_session, lab_order, created_by_id=1)
    
    assert charge is not None
    assert charge.charge_type == ChargeType.LAB_TEST
    assert charge.lab_order_id == lab_order.id
    assert charge.encounter_id == encounter.id
    
    # Verify invoice was created
    invoice = db_session.query(Invoice).filter(Invoice.encounter_id == encounter.id).first()
    assert invoice is not None
    assert invoice.total_amount > 0


@pytest.mark.integration
def test_create_charge_prevents_duplicates(db_session):
    """Test that duplicate charges are not created."""
    from app.models.encounter_models import Encounter
    from app.models.patient_models import Patient
    
    # Setup
    patient = Patient(
        first_name="Test",
        last_name="Patient",
        date_of_birth=datetime(1990, 1, 1).date(),
        gender="Male",
        national_id="TEST-DUP"
    )
    db_session.add(patient)
    db_session.flush()
    
    encounter = Encounter(
        patient_id=patient.id,
        clinician_id=1,
        status="in_progress"
    )
    db_session.add(encounter)
    db_session.flush()
    
    lab_order = LabOrder(
        encounter_id=encounter.id,
        ordered_by_id=1,
        test_name="Test",
        status=OrderStatus.COMPLETED.value
    )
    db_session.add(lab_order)
    db_session.commit()
    
    # Create charge first time
    charge1 = create_charge_for_lab_order(db_session, lab_order, created_by_id=1)
    assert charge1 is not None
    
    # Try to create again
    charge2 = create_charge_for_lab_order(db_session, lab_order, created_by_id=1)
    assert charge2 is None  # Should return None for duplicate
    
    # Verify only one charge exists
    charges = db_session.query(Charge).filter(Charge.lab_order_id == lab_order.id).all()
    assert len(charges) == 1

