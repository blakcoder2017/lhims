"""
Pharmacy Ghana-Ready Models
- dosage_form, pharmacy_drug (formulation), pharmacy_supplier, pharmacy_store
- pharmacy_batch, pharmacy_stock_ledger (FEFO, immutable)
- pharmacy_dispense, pharmacy_dispense_item, pharmacy_dispense_allocation
- pharmacy_drug_interaction, pharmacy_role_policy, patient_active_medication
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Date, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class PharmacyDosageForm(Base):
    __tablename__ = "pharmacy_dosage_form"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class PharmacySupplier(Base):
    __tablename__ = "pharmacy_supplier"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text(), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class PharmacyStore(Base):
    __tablename__ = "pharmacy_store"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    facility_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class PharmacyDrug(Base):
    """Formulation = generic + strength + dosage form + route. NOT generic-only."""
    __tablename__ = "pharmacy_drug"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_code = Column(String(50), unique=True, nullable=False, index=True)
    generic_name = Column(String(255), nullable=False, index=True)
    brand_name = Column(String(255), nullable=True, index=True)
    dosage_form_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_dosage_form.id"), nullable=False)
    strength_value = Column(Numeric(20, 6), nullable=True)
    strength_unit = Column(String(50), nullable=True)
    route = Column(String(50), nullable=True, index=True)
    concentration_value = Column(Numeric(20, 6), nullable=True)
    concentration_unit = Column(String(100), nullable=True)
    pack_size = Column(Integer, nullable=True)
    reorder_level = Column(Numeric(20, 6), nullable=True)
    reorder_qty = Column(Numeric(20, 6), nullable=True)
    is_controlled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text(), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    dosage_form = relationship("PharmacyDosageForm", back_populates="drugs")
    batches = relationship("PharmacyBatch", back_populates="drug")


class PharmacyBatch(Base):
    __tablename__ = "pharmacy_batch"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=False)
    store_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_store.id"), nullable=False)
    batch_no = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False)
    received_date = Column(Date, nullable=True)
    unit_cost = Column(Numeric(20, 6), nullable=True)
    selling_price = Column(Numeric(20, 6), nullable=True)
    qty_on_hand = Column(Numeric(20, 6), nullable=False, default=0)
    qty_reserved = Column(Numeric(20, 6), nullable=False, default=0)
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, QUARANTINED, EXPIRED, DEPLETED
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_supplier.id"), nullable=True)
    invoice_ref = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    drug = relationship("PharmacyDrug", back_populates="batches")
    store = relationship("PharmacyStore", back_populates="batches")
    supplier = relationship("PharmacySupplier", back_populates="batches")


class PharmacyStockLedger(Base):
    """Immutable stock movement ledger."""
    __tablename__ = "pharmacy_stock_ledger"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_store.id"), nullable=False)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_batch.id"), nullable=True)
    movement_type = Column(String(50), nullable=False)  # STOCK_IN, DISPENSE, SALE, RETURN, etc.
    qty_in = Column(Numeric(20, 6), nullable=False, default=0)
    qty_out = Column(Numeric(20, 6), nullable=False, default=0)
    unit_cost_snapshot = Column(Numeric(20, 6), nullable=True)
    selling_price_snapshot = Column(Numeric(20, 6), nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    note = Column(Text(), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    store = relationship("PharmacyStore")
    drug = relationship("PharmacyDrug")
    batch = relationship("PharmacyBatch")


class PharmacyDispense(Base):
    __tablename__ = "pharmacy_dispense"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)  # Link to prescription
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)  # Link to invoice
    prescriber_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(50), nullable=False, default="DRAFT")  # DRAFT, DISPENSED, CANCELLED, RETURNED
    dispensed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dispensed_at = Column(DateTime, nullable=True)
    payment_type = Column(String(50), nullable=True)  # CASH, INSURANCE, WARD_CHARGE, FREE
    notes = Column(Text(), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    patient = relationship("Patient", foreign_keys=[patient_id])
    encounter = relationship("Encounter", foreign_keys=[encounter_id])
    prescription = relationship("Prescription", foreign_keys=[prescription_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    items = relationship("PharmacyDispenseItem", back_populates="dispense")


class PharmacyDispenseItem(Base):
    __tablename__ = "pharmacy_dispense_item"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispense_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_dispense.id"), nullable=False)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=False)
    dosage_instructions = Column(Text(), nullable=True)
    qty_prescribed = Column(Numeric(20, 6), nullable=True)
    qty_dispensed = Column(Numeric(20, 6), nullable=False)
    unit_selling_price = Column(Numeric(20, 6), nullable=True)
    unit_cost_snapshot = Column(Numeric(20, 6), nullable=True)  # Actual cost from batch
    total_amount = Column(Numeric(20, 6), nullable=True)
    total_cost = Column(Numeric(20, 6), nullable=True)  # Cost for profit calculation
    margin = Column(Numeric(20, 6), nullable=True)  # Profit margin
    created_at = Column(DateTime, server_default=func.now())

    dispense = relationship("PharmacyDispense", back_populates="items")
    drug = relationship("PharmacyDrug")
    allocations = relationship("PharmacyDispenseAllocation", back_populates="dispense_item")


class PharmacyDispenseAllocation(Base):
    """FEFO batch allocation per dispense item."""
    __tablename__ = "pharmacy_dispense_allocation"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispense_item_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_dispense_item.id"), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_batch.id"), nullable=False)
    qty_allocated = Column(Numeric(20, 6), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    dispense_item = relationship("PharmacyDispenseItem", back_populates="allocations")
    batch = relationship("PharmacyBatch")


class PharmacyDrugInteraction(Base):
    __tablename__ = "pharmacy_drug_interaction"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_a_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=False)
    drug_b_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=False)
    severity = Column(String(50), nullable=False)  # MINOR, MODERATE, MAJOR, CONTRAINDICATED
    description = Column(Text(), nullable=True)
    recommendation = Column(Text(), nullable=True)
    reference = Column(Text(), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    drug_a = relationship("PharmacyDrug", foreign_keys=[drug_a_id])
    drug_b = relationship("PharmacyDrug", foreign_keys=[drug_b_id])


class PharmacyRolePolicy(Base):
    __tablename__ = "pharmacy_role_policy"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(100), unique=True, nullable=False, index=True)
    can_view_unit_cost = Column(Boolean, default=False)
    can_view_margin = Column(Boolean, default=False)
    can_edit_selling_price = Column(Boolean, default=False)
    can_adjust_stock = Column(Boolean, default=False)
    can_approve_adjustment = Column(Boolean, default=False)
    can_dispense_controlled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class PatientActiveMedication(Base):
    __tablename__ = "patient_active_medication"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, STOPPED
    source = Column(String(50), nullable=True)  # PRESCRIPTION, DISPENSE, MANUAL
    created_at = Column(DateTime, server_default=func.now())

    patient = relationship("Patient", foreign_keys=[patient_id])
    drug = relationship("PharmacyDrug")


# Add back_populates
PharmacyDosageForm.drugs = relationship("PharmacyDrug", back_populates="dosage_form")
PharmacyStore.batches = relationship("PharmacyBatch", back_populates="store")
PharmacySupplier.batches = relationship("PharmacyBatch", back_populates="supplier")
