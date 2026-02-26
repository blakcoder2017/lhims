from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects import postgresql
from app.db.database import Base
import enum
from datetime import datetime


class WardStatus(str, enum.Enum):
    """Ward status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class BedStatus(str, enum.Enum):
    """Bed status enumeration"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class AdmissionStatus(str, enum.Enum):
    """Admission status enumeration"""
    ADMITTED = "admitted"
    DISCHARGED = "discharged"
    TRANSFERRED = "transferred"
    ABSCONDED = "absconded"


class DischargeStatus(str, enum.Enum):
    """Discharge status enumeration"""
    NORMAL = "normal"  # Normal discharge
    DEATH = "death"  # Patient died
    REFERRAL = "referral"  # Referred to another facility


class DepartmentType(str, enum.Enum):
    """Department type enumeration"""
    OPD = "opd"  # Outpatient Department
    IPD = "ipd"  # Inpatient Department
    BOTH = "both"  # Both OPD and IPD


class Ward(Base):
    """
    SQLAlchemy Model for hospital wards.
    Tracks ward information and capacity.
    """
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    
    # Ward Details
    name = Column(String(100), nullable=False, unique=True, index=True)  # Ward name (e.g., "Ward A", "ICU")
    ward_number = Column(String(50), nullable=True, unique=True, index=True)  # Ward number/code
    ward_type = Column(String(50), nullable=True)  # e.g., "General", "ICU", "Pediatric", "Maternity"
    capacity = Column(Integer, nullable=False, default=0)  # Total bed capacity
    current_occupancy = Column(Integer, nullable=False, default=0)  # Current number of occupied beds
    status = Column(postgresql.ENUM(WardStatus, values_callable=lambda x: [e.value for e in x], name='wardstatus', create_type=False), nullable=False, default=WardStatus.ACTIVE)
    
    # Location
    floor = Column(String(50), nullable=True)  # Floor number
    building = Column(String(100), nullable=True)  # Building name
    
    # Additional Information
    description = Column(Text, nullable=True)  # Ward description
    charge_per_day = Column(Numeric(10, 2), nullable=False, server_default='0.00')  # Daily charge for ward (required)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    beds = relationship("Bed", back_populates="ward", cascade="all, delete-orphan")
    # Specify primaryjoin to resolve ambiguity (Admission has multiple FKs to Ward: ward_id, transferred_from_ward_id, transferred_to_ward_id)
    # We want admissions where this ward is the current ward (ward_id), not transferred_from or transferred_to
    admissions = relationship(
        "Admission",
        primaryjoin="Ward.id == Admission.ward_id",
        back_populates="ward"
    )
    
    def __repr__(self):
        return f"<Ward(id={self.id}, name='{self.name}', capacity={self.capacity}, occupancy={self.current_occupancy})>"


class Bed(Base):
    """
    SQLAlchemy Model for hospital beds.
    Tracks individual beds within wards.
    """
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    
    # Bed Details
    bed_number = Column(String(50), nullable=False, index=True)  # Bed number (e.g., "A1", "B5")
    bed_name = Column(String(100), nullable=True)  # Optional bed name/description
    status = Column(postgresql.ENUM(BedStatus, values_callable=lambda x: [e.value for e in x], name='bedstatus', create_type=False), nullable=False, default=BedStatus.AVAILABLE)
    
    # Bed Information
    bed_type = Column(String(50), nullable=True)  # e.g., "Standard", "ICU", "Private"
    charge_per_day = Column(Numeric(10, 2), nullable=False, server_default='0.00')  # Daily charge for bed (required)
    
    # Additional Information
    notes = Column(Text, nullable=True)  # Additional notes about the bed
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    ward = relationship("Ward", back_populates="beds")
    admissions = relationship("Admission", back_populates="bed")
    
    def __repr__(self):
        return f"<Bed(id={self.id}, bed_number='{self.bed_number}', ward_id={self.ward_id}, status={self.status.value})>"


class Admission(Base):
    """
    SQLAlchemy Model for patient admissions.
    Tracks patient admissions to wards and beds.
    """
    __tablename__ = "admissions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)  # Optional link to encounter
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)  # Optional link to billing invoice
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=False)
    admitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who admitted the patient
    discharged_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # User who discharged the patient
    
    # Admission Details
    admission_number = Column(String(50), unique=True, nullable=False, index=True)  # Unique admission number
    status = Column(postgresql.ENUM(AdmissionStatus, values_callable=lambda x: [e.value for e in x], name='admissionstatus', create_type=False), nullable=False, default=AdmissionStatus.ADMITTED)
    
    # Dates
    admission_date = Column(DateTime, nullable=False, server_default=func.now())
    discharge_date = Column(DateTime, nullable=True)
    expected_discharge_date = Column(DateTime, nullable=True)  # Expected discharge date
    ready_for_discharge_at = Column(DateTime, nullable=True)  # Timestamp when discharge prep completed
    
    # Admission Information
    admission_reason = Column(Text, nullable=True)  # Reason for admission
    diagnosis = Column(Text, nullable=True)  # Diagnosis at admission
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Allergies - Critical for patient safety during medication administration
    allergies = Column(Text, nullable=True)  # Known allergies (e.g., "Penicillin, Peanut")
    
    # Guardian/Attendant Information
    guardian_name = Column(String(200), nullable=True)  # Name of guardian/attendant
    guardian_phone = Column(String(20), nullable=True)  # Phone number of guardian/attendant
    guardian_relationship = Column(String(50), nullable=True)  # Relationship to patient (e.g., "Father", "Spouse")
    guardian_address = Column(Text, nullable=True)  # Address of guardian/attendant
    
    # Discharge Information
    discharge_status = Column(postgresql.ENUM(DischargeStatus, values_callable=lambda x: [e.value for e in x], name='dischargestatus', create_type=False), nullable=True)  # Discharge status: normal, death, referral
    discharge_diagnosis = Column(Text, nullable=True)  # Final diagnosis at discharge
    discharge_notes = Column(Text, nullable=True)  # Discharge notes and instructions
    
    # Transfer Information
    transferred_from_ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)  # Previous ward if transferred
    transferred_to_ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)  # New ward if transferred
    transfer_reason = Column(Text, nullable=True)  # Reason for transfer
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="admissions")
    # Initial encounter that led to admission (many-to-one, using encounter_id)
    initial_encounter = relationship("Encounter", foreign_keys=[encounter_id], post_update=True)
    # All encounters linked to this admission (one-to-many, using Encounter.admission_id)
    # Use primaryjoin string to explicitly specify which foreign key to use (Encounter.admission_id, not Admission.encounter_id)
    encounters = relationship(
        "Encounter", 
        back_populates="admission",
        primaryjoin="Admission.id == Encounter.admission_id"
    )
    # Invoice relationship: Admission can have one invoice via invoice_id (one-to-one)
    # Note: Invoice also has admission_id, but this relationship uses Admission.invoice_id
    invoice = relationship("Invoice", foreign_keys=[invoice_id], uselist=False)
    ward = relationship("Ward", foreign_keys=[ward_id], back_populates="admissions")
    bed = relationship("Bed", back_populates="admissions")
    admitted_by = relationship("User", foreign_keys=[admitted_by_id])
    discharged_by = relationship("User", foreign_keys=[discharged_by_id])
    transferred_from_ward = relationship("Ward", foreign_keys=[transferred_from_ward_id])
    transferred_to_ward = relationship("Ward", foreign_keys=[transferred_to_ward_id])
    admission_notes = relationship("AdmissionNote", back_populates="admission", cascade="all, delete-orphan")
    diagnoses = relationship("AdmissionDiagnosis", back_populates="admission", cascade="all, delete-orphan")
    wound_care_records = relationship("WoundCare", back_populates="admission", cascade="all, delete-orphan")
    procedure_records = relationship("Procedure", back_populates="admission", cascade="all, delete-orphan")
    drug_administrations = relationship("DrugAdministration", back_populates="admission")
    fluid_balance_entries = relationship("FluidBalance", back_populates="admission", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Admission(id={self.id}, patient_id={self.patient_id}, ward_id={self.ward_id}, bed_id={self.bed_id}, status={self.status.value})>"


class DoctorDuty(Base):
    """
    SQLAlchemy Model for doctor duty schedules.
    Tracks which doctors are on duty and their schedules.
    """
    __tablename__ = "doctor_duties"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Doctor/user ID
    department = Column(String(100), nullable=False)  # Department (e.g., "General Medicine", "Emergency")
    
    # Duty Schedule
    duty_date = Column(DateTime, nullable=False, index=True)  # Date of duty
    shift_start = Column(DateTime, nullable=False)  # Shift start time
    shift_end = Column(DateTime, nullable=False)  # Shift end time
    shift_type = Column(String(50), nullable=True)  # e.g., "Morning", "Evening", "Night", "Full Day"
    
    # Duty Status
    is_on_duty = Column(Boolean, default=True)  # Whether doctor is currently on duty
    status = Column(String(50), nullable=True, default="scheduled")  # e.g., "scheduled", "completed", "cancelled"
    
    # Additional Information
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])
    
    def __repr__(self):
        return f"<DoctorDuty(id={self.id}, doctor_id={self.doctor_id}, department='{self.department}', duty_date={self.duty_date})>"


class AdmissionNote(Base):
    """
    SQLAlchemy Model for admission notes.
    Allows nurses and doctors to add multiple notes to an admission with timestamps.
    Supports threaded replies for interactive communication.
    """
    __tablename__ = "admission_notes"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who created the note
    parent_note_id = Column(Integer, ForeignKey("admission_notes.id"), nullable=True)  # Parent note for replies
    
    # Note Details
    note = Column(Text, nullable=False)  # The note content
    note_type = Column(String(50), nullable=True, default="general")  # e.g., "general", "nursing", "doctor", "vital_signs", "medication"
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    admission = relationship("Admission", back_populates="admission_notes")
    created_by = relationship("User", foreign_keys=[created_by_id])
    parent_note = relationship("AdmissionNote", remote_side=[id], backref="replies")
    
    def __repr__(self):
        return f"<AdmissionNote(id={self.id}, admission_id={self.admission_id}, created_by_id={self.created_by_id}, parent_note_id={self.parent_note_id}, created_at={self.created_at})>"


class DiagnosisType(str, enum.Enum):
    """Diagnosis type enumeration for tracking diagnosis progression"""
    ADMISSION = "admission"  # Diagnosis at time of admission
    WORKING = "working"      # Working diagnosis during stay
    DISCHARGE = "discharge"  # Final diagnosis at discharge
    COMPLICATING = "complicating"  # Complicating conditions


class AdmissionDiagnosis(Base):
    """
    SQLAlchemy Model for tracking diagnoses throughout patient admission.
    Allows structured tracking from admission diagnosis through working diagnosis to discharge diagnosis.
    """
    __tablename__ = "admission_diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False)
    diagnosed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Doctor who diagnosed
    
    # Diagnosis Details
    diagnosis = Column(Text, nullable=False)  # The diagnosis description
    icd_code = Column(String(20), nullable=True)  # ICD-10 code (optional)
    diagnosis_type = Column(Enum(DiagnosisType), nullable=False, default=DiagnosisType.ADMISSION)
    
    # Timestamps
    diagnosed_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    admission = relationship("Admission", back_populates="diagnoses")
    diagnosed_by = relationship("User", foreign_keys=[diagnosed_by_id])
    
    def __repr__(self):
        return f"<AdmissionDiagnosis(id={self.id}, admission_id={self.admission_id}, diagnosis='{self.diagnosis[:30]}...', type={self.diagnosis_type.value})>"


class WoundCareType(str, enum.Enum):
    """Wound care type enumeration"""
    SURGICAL = "surgical"
    TRAUMATIC = "traumatic"
    PRESSURE = "pressure"
    DIABETIC = "diabetic"
    BURNS = "burns"
    OTHER = "other"


class WoundCondition(str, enum.Enum):
    """Wound condition enumeration"""
    CLEAN = "clean"
    INFECTED = "infected"
    GRANULATING = "granulating"
    NECROTIC = "necrotic"
    HEALED = "healed"


class WoundCare(Base):
    """
    SQLAlchemy Model for tracking wound care and dressing changes during admission.
    """
    __tablename__ = "wound_care"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Nurse who performed wound care
    
    # Wound Details
    wound_location = Column(String(200), nullable=False)  # e.g., "Left leg", "Surgical site", "Back"
    wound_type = Column(Enum(WoundCareType), nullable=False, default=WoundCareType.OTHER)
    wound_description = Column(Text, nullable=True)  # Detailed description of wound
    
    # Care Details
    dressing_date = Column(DateTime, server_default=func.now())
    dressing_type = Column(String(100), nullable=True)  # e.g., "Sterile gauze", "Transparent dressing"
    wound_condition = Column(Enum(WoundCondition), nullable=True)
    
    # Measurements
    length_cm = Column(Numeric(5, 2), nullable=True)
    width_cm = Column(Numeric(5, 2), nullable=True)
    depth_cm = Column(Numeric(5, 2), nullable=True)
    
    # Exudate
    exudate_type = Column(String(50), nullable=True)  # e.g., "Serous", "Sanguineous", "Purulent"
    exudate_amount = Column(String(20), nullable=True)  # e.g., "Minimal", "Moderate", "Heavy"
    
    # Notes and Observations
    notes = Column(Text, nullable=True)
    next_dressing_date = Column(DateTime, nullable=True)  # Scheduled next dressing change
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Soft deletion
    is_active = Column(Boolean, default=True)
    
    # Relationships
    admission = relationship("Admission", back_populates="wound_care_records")
    performed_by = relationship("User", foreign_keys=[performed_by_id])
    
    def __repr__(self):
        return f"<WoundCare(id={self.id}, admission_id={self.admission_id}, location='{self.wound_location}', type={self.wound_type.value})>"

