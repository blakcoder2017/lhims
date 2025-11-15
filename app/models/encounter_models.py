from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
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


class Encounter(Base):

    __tablename__ = "encounters"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)  # Optional link to appointment
    clinician_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Doctor/nurse who documented
    
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
    
    # Diagnosis (ICD-10)
    primary_diagnosis_code = Column(String(20), nullable=True)  # ICD-10 code for primary diagnosis
    primary_diagnosis_description = Column(String(500), nullable=True)  # Description of primary diagnosis
    secondary_diagnosis_codes = Column(Text, nullable=True)  # JSON array of secondary diagnosis codes and descriptions
    
    # Timestamps
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="encounters")
    appointment = relationship("Appointment", back_populates="encounters")
    clinician = relationship("User", foreign_keys=[clinician_id])
    lab_orders = relationship("LabOrder", back_populates="encounter", cascade="all, delete-orphan")
    radiology_orders = relationship("RadiologyOrder", back_populates="encounter", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="encounter", cascade="all, delete-orphan")
    admission = relationship("Admission", back_populates="encounter", uselist=False)
    procedures = relationship("Procedure", back_populates="encounter", cascade="all, delete-orphan")
    diseases = relationship("EncounterDisease", back_populates="encounter", cascade="all, delete-orphan")
    
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
    
    # Walk-in Support
    is_walk_in = Column(Boolean, default=False, server_default='false')  # True if this is a walk-in order
    checked_in_at = Column(DateTime, nullable=True)  # When front desk checked in the walk-in order
    checked_in_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Front desk staff who checked in
    
    # Order Details
    test_name = Column(String(200), nullable=False)  # Name of the lab test
    test_code = Column(String(50), nullable=True)  # Test code (e.g., CBC, LFT)
    instructions = Column(Text, nullable=True)  # Special instructions
    priority = Column(String(20), default="routine")  # routine, urgent, stat
    
    # Status Tracking
    status = Column(postgresql.ENUM(OrderStatus, values_callable=lambda x: [e.value for e in x], name='orderstatus', create_type=False), nullable=False, default=OrderStatus.PENDING)
    ordered_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Result (to be filled by lab staff)
    result = Column(Text, nullable=True)  # Lab result
    result_entered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Lab staff who entered result
    result_entered_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    encounter = relationship("Encounter", back_populates="lab_orders")
    patient = relationship("Patient", foreign_keys=[patient_id])
    ordered_by = relationship("User", foreign_keys=[ordered_by_id])
    result_entered_by = relationship("User", foreign_keys=[result_entered_by_id])
    checked_in_by = relationship("User", foreign_keys=[checked_in_by_id])
    samples = relationship("LabSample", back_populates="lab_order")
    qc_records = relationship("QCRecord", back_populates="lab_order")
    
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
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=True)  # Link to inventory medication (optional)
    
    # Prescription Details
    medication_name = Column(String(200), nullable=False)  # Name of medication
    medication_code = Column(String(50), nullable=True)  # Medication code (e.g., NDC code)
    dosage = Column(String(100), nullable=False)  # e.g., "500mg", "10ml"
    frequency = Column(String(100), nullable=False)  # e.g., "twice daily", "every 8 hours"
    duration = Column(String(100), nullable=False)  # e.g., "7 days", "2 weeks"
    quantity = Column(Integer, nullable=True)  # Number of units to dispense
    instructions = Column(Text, nullable=True)  # Patient instructions
    
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
    medication = relationship("Medication", foreign_keys=[medication_id])  # Link to inventory medication
    inventory_transactions = relationship("InventoryTransaction", back_populates="prescription")
    
    def __repr__(self):
        return f"<Prescription(id={self.id}, medication_name='{self.medication_name}', status={self.status.value})>"

