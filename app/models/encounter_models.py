from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum


class EncounterStatus(str, enum.Enum):
    """Encounter status enumeration"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DETAINED = "detained"  # Patient held for observation
    AUTO_CLOSED = "auto_closed"  # Automatically closed after 24 hours of inactivity


class Encounter(Base):

    __tablename__ = "encounters"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    queue_entry_id = Column(Integer, ForeignKey("opd_queue.id"), nullable=True)  # Optional link to queue entry
    appointment_id = Column(Integer, ForeignKey("scheduled_appointments.id"), nullable=True)  # Link to scheduled appointment
    clinician_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Doctor/nurse who documented
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)  # Link to OPD visit (for OPD encounters)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Link to IPD admission (for IPD encounters)
    
    # Encounter Details
    status = Column(postgresql.ENUM(EncounterStatus, values_callable=lambda x: [e.value for e in x], name='encounterstatus', create_type=False), nullable=False, default=EncounterStatus.IN_PROGRESS)
    encounter_date = Column(DateTime, nullable=False, server_default=func.now())
    
    # Clinical Documentation
    chief_complaint = Column(Text, nullable=True)  # Patient's main complaint
    history_of_present_illness = Column(Text, nullable=True)  # HPI - detailed history
    past_medical_history = Column(Text, nullable=True)  # PMH - past medical conditions
    allergies = Column(Text, nullable=True)  # Known allergies
    medications = Column(Text, nullable=True)  # Current medications
    physical_examination = Column(Text, nullable=True)  # Physical exam findings
    assessment = Column(Text, nullable=True)  # Clinical assessment
    plan = Column(Text, nullable=True)  # Treatment plan
    
    # Follow-up addendum - for adding comments after encounter is closed
    addendum = Column(Text, nullable=True)  # Addendum/follow-up notes added after encounter completion
    addendum_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who added the addendum
    addendum_at = Column(DateTime, nullable=True)  # When the addendum was added
    
    # Diagnosis (ICD-10)
    primary_diagnosis_code = Column(String(20), nullable=True)  # ICD-10 code for primary diagnosis
    primary_diagnosis_description = Column(String(500), nullable=True)  # Description of primary diagnosis
    secondary_diagnosis_codes = Column(Text, nullable=True)  # JSON array of secondary diagnosis codes and descriptions
    differential_diagnosis_data = Column(Text, nullable=True)  # JSON blob storing G-STG differential suggestions/status
    
    # Timestamps
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    queue_entry = relationship("OPDQueue", back_populates="encounters")
    appointment = relationship("ScheduledAppointment", back_populates="encounters")
    clinician = relationship("User", foreign_keys=[clinician_id])
    addendum_by = relationship("User", foreign_keys=[addendum_by_id])  # User who added addendum
    opd_visit = relationship("OPDVisit", back_populates="encounters")
    admission = relationship("Admission", back_populates="encounters", foreign_keys=[admission_id])
    lab_orders = relationship("LabOrder", back_populates="encounter", cascade="all, delete-orphan")
    radiology_orders = relationship("RadiologyOrder", back_populates="encounter", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="encounter", cascade="all, delete-orphan")
    addendums = relationship("EncounterAddendum", back_populates="encounter", cascade="all, delete-orphan")
    procedures = relationship("Procedure", back_populates="encounter", cascade="all, delete-orphan")
    diseases = relationship("EncounterDisease", back_populates="encounter", cascade="all, delete-orphan")
    antenatal_visits = relationship("AntenatalVisit", back_populates="encounter", foreign_keys="AntenatalVisit.encounter_id")
    birth_records = relationship("BirthRecord", back_populates="encounter", foreign_keys="BirthRecord.encounter_id")

    def __repr__(self):
        return f"<Encounter(id={self.id}, patient_id={self.patient_id}, status={self.status.value})>"


class OrderStatus(str, enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    ORDERED = "ordered"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LabOrder(Base):
    """
    SQLAlchemy Model for laboratory test orders.
    Part of CPOE (Computerized Provider Order Entry) system.
    """
    __tablename__ = "lab_orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)  # Optional for walk-in orders
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # Direct patient link for walk-in orders
    ordered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Clinician who ordered
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)  # Link to OPD visit (denormalized for reporting)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Link to IPD admission (denormalized for reporting)
    
    # Walk-in Support
    is_walk_in = Column(Boolean, default=False, server_default='false')  # True if this is a walk-in order
    checked_in_at = Column(DateTime, nullable=True)  # When front desk checked in the walk-in order
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Front desk staff who checked in
    
    # Order Details
    test_name = Column(String(200), nullable=False)  # Name of the lab test
    test_code = Column(String(50), nullable=True)  # Test code (e.g., CBC, LFT)
    
    # Lab Test Catalog Reference (links to Lab Test Catalog)
    lab_test_id = Column(Integer, ForeignKey("lab_tests.id", ondelete="SET NULL"), nullable=True)  # Link to LabTest catalog
    
    instructions = Column(Text, nullable=True)  # Special instructions
    priority = Column(String(20), default="routine")  # routine, urgent, stat
    
    # Status Tracking
    status = Column(postgresql.ENUM(OrderStatus, values_callable=lambda x: [e.value for e in x], name='orderstatus', create_type=False), nullable=False, default=OrderStatus.PENDING)
    ordered_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Result (to be filled by lab staff)
    result = Column(Text, nullable=True)  # Lab result (free-text; used when no template)
    result_entered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Lab staff who entered result
    result_entered_at = Column(DateTime, nullable=True)

    # Template-driven structured results
    template_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("lab_templates.id", ondelete="SET NULL"), nullable=True)
    template_version_used = Column(Integer, nullable=True)
    result_json = Column(postgresql.JSONB, nullable=True)  # Structured result keyed by field code
    result_status = Column(String(50), nullable=True)  # DRAFT, SUBMITTED, VERIFIED, AUTHORIZED, RELEASED, AMENDED
    flags_json = Column(postgresql.JSONB, nullable=True)  # Abnormal/critical flags per field
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    authorized_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    authorized_at = Column(DateTime, nullable=True)
    previous_version_id = Column(Integer, ForeignKey("lab_orders.id", ondelete="SET NULL"), nullable=True)
    amend_reason = Column(Text, nullable=True)
    critical_called = Column(Boolean, nullable=True)
    critical_called_at = Column(DateTime, nullable=True)
    critical_called_to = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="lab_orders")
    patient = relationship("Patient", foreign_keys=[patient_id])
    ordered_by = relationship("User", foreign_keys=[ordered_by_id])
    result_entered_by = relationship("User", foreign_keys=[result_entered_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    authorized_by = relationship("User", foreign_keys=[authorized_by_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    opd_visit = relationship("OPDVisit", foreign_keys=[opd_visit_id])
    admission = relationship("Admission", foreign_keys=[admission_id])
    samples = relationship("LabSample", back_populates="lab_order")
    qc_records = relationship("QCRecord", back_populates="lab_order")
    lab_test = relationship("LabTest")  # Link to Lab Test Catalog
    
    def __repr__(self):
        return f"<LabOrder(id={self.id}, test_name='{self.test_name}', status={self.status.value})>"


class RadiologyOrder(Base):
    """
    SQLAlchemy Model for radiology/imaging orders.
    Part of CPOE (Computerized Provider Order Entry) system.
    """
    __tablename__ = "radiology_orders"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)  # Optional for walk-in orders
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)  # Direct patient link for walk-in orders
    ordered_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Clinician who ordered
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)  # Link to OPD visit (denormalized for reporting)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Link to IPD admission (denormalized for reporting)
    
    # Walk-in Support
    is_walk_in = Column(Boolean, default=False, server_default='false')  # True if this is a walk-in order
    checked_in_at = Column(DateTime, nullable=True)  # When front desk checked in the walk-in order
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Front desk staff who checked in
    
    # Order Details
    study_type = Column(String(200), nullable=False)  # e.g., "Chest X-Ray", "CT Head", "Ultrasound Abdomen"
    study_code = Column(String(50), nullable=True)  # Study code
    body_part = Column(String(100), nullable=True)  # Body part to be imaged
    clinical_indication = Column(Text, nullable=True)  # Reason for the study
    instructions = Column(Text, nullable=True)  # Special instructions
    priority = Column(String(20), default="routine")  # routine, urgent, stat
    
    # Status Tracking
    status = Column(postgresql.ENUM(OrderStatus, values_callable=lambda x: [e.value for e in x], name='orderstatus', create_type=False), nullable=False, default=OrderStatus.PENDING)
    ordered_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Result (to be filled by radiology staff)
    report = Column(Text, nullable=True)  # Radiology report
    report_entered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Radiologist who entered report
    report_entered_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="radiology_orders")
    patient = relationship("Patient", foreign_keys=[patient_id])
    ordered_by = relationship("User", foreign_keys=[ordered_by_id])
    report_entered_by = relationship("User", foreign_keys=[report_entered_by_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    opd_visit = relationship("OPDVisit", foreign_keys=[opd_visit_id])
    admission = relationship("Admission", foreign_keys=[admission_id])
    images = relationship("RadiologyImage", back_populates="radiology_order")
    
    def __repr__(self):
        return f"<RadiologyOrder(id={self.id}, study_type='{self.study_type}', status={self.status.value})>"


class Prescription(Base):
    """
    SQLAlchemy Model for medication prescriptions.
    Part of CPOE (Computerized Provider Order Entry) system.
    """
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    prescribed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Clinician who prescribed
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=True)  # Legacy: inventory medication
    pharmacy_drug_id = Column(postgresql.UUID(as_uuid=True), ForeignKey("pharmacy_drug.id"), nullable=True)  # Ghana: exact formulation (REQUIRED for new presc)
    opd_visit_id = Column(Integer, ForeignKey("opd_visits.id"), nullable=True)  # Link to OPD visit (denormalized for reporting)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # Link to IPD admission (denormalized for reporting)
    
    # Prescription Details
    medication_name = Column(String(200), nullable=False)  # Name of medication
    medication_code = Column(String(50), nullable=True)  # Medication code (e.g., NDC code)
    
    # Snapshot fields from pharmacy_drug (optional - for display when drug deleted)
    dosage_form_name = Column(String(100), nullable=True)
    strength_value = Column(Numeric(20, 6), nullable=True)
    strength_unit = Column(String(50), nullable=True)
    route = Column(String(50), nullable=True)
    concentration_value = Column(Numeric(20, 6), nullable=True)
    concentration_unit = Column(String(100), nullable=True)
    
    # Dose input
    dosage = Column(String(100), nullable=False)  # e.g., "500mg", "10ml"
    frequency = Column(String(100), nullable=False)  # e.g., "twice daily", "every 8 hours"
    duration = Column(String(100), nullable=False)  # e.g., "7 days", "2 weeks"
    quantity = Column(Integer, nullable=True)  # Number of units to dispense - pharmacy decides actual quantity
    instructions = Column(Text, nullable=True)  # Patient instructions
    
    # Walk-in Support
    is_walk_in = Column(Boolean, default=False, server_default='false')  # True if this is a walk-in pharmacy sale
    checked_in_at = Column(DateTime, nullable=True)  # When front desk confirmed payment
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Front desk staff who confirmed payment
    
    # Status Tracking
    status = Column(postgresql.ENUM(OrderStatus, values_callable=lambda x: [e.value for e in x], name='orderstatus', create_type=False), nullable=False, default=OrderStatus.PENDING)
    prescribed_at = Column(DateTime, server_default=func.now())
    dispensed_at = Column(DateTime, nullable=True)
    dispensed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Pharmacy staff who dispensed
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="prescriptions")
    prescribed_by = relationship("User", foreign_keys=[prescribed_by_id])
    dispensed_by = relationship("User", foreign_keys=[dispensed_by_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    opd_visit = relationship("OPDVisit", foreign_keys=[opd_visit_id])
    admission = relationship("Admission", foreign_keys=[admission_id])
    medication = relationship("Medication", foreign_keys=[medication_id])  # Legacy
    pharmacy_drug = relationship("PharmacyDrug", foreign_keys=[pharmacy_drug_id])  # Ghana: formulation
    inventory_transactions = relationship("InventoryTransaction", back_populates="prescription")
    charges = relationship("Charge", back_populates="prescription")
    
    def __repr__(self):
        return f"<Prescription(id={self.id}, medication_name='{self.medication_name}', status={self.status.value})>"


class EncounterAddendum(Base):
    """
    SQLAlchemy Model for encounter addendums/follow-up notes.
    Each addendum is a separate entry, allowing for history tracking.
    """
    __tablename__ = "encounter_addendums"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=False)
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who added the addendum
    
    # Addendum Content
    content = Column(Text, nullable=False)  # The addendum text
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Soft delete
    is_active = Column(Boolean, default=True)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="addendums")
    added_by = relationship("User", foreign_keys=[added_by_id])
    
    def __repr__(self):
        return f"<EncounterAddendum(id={self.id}, encounter_id={self.encounter_id})>"
