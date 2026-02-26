"""
Birth / Delivery Models

SQLAlchemy models for birth records and delivery tracking.
Updated for Ghana Health Service (GHS) compliance.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date, Time, Boolean, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class DeliveryType(str, enum.Enum):
    """Delivery type enumeration - GHS compliant"""
    VAGINAL = "vaginal"
    NORMAL = "normal"
    VACUUM = "vacuum"
    CAESAREAN = "caesarean"
    CAESAREAN_SECTION = "caesarean_section"
    ASSISTED = "assisted"
    FORCEPS = "forceps"
    OTHER = "other"


class BirthAttendantCategory(str, enum.Enum):
    """Birth attendant category for Ghana Health Service"""
    DOCTOR = "doctor"
    MIDWIFE = "midwife"
    NURSE = "nurse"
    TBA = "tba"  # Traditional Birth Attendant
    RELATIVE = "relative"  # Added for GHS
    CHO = "cho"  # Community Health Officer
    OTHER = "other"


class BirthOutcome(str, enum.Enum):
    """Birth outcome enumeration - GHS compliant"""
    LIVE = "live"
    LIVE_BIRTH = "live_birth"
    STILLBIRTH = "stillbirth"
    EARLY_NEONATAL_DEATH = "early_neonatal_death"
    NEONATAL_DEATH = "neonatal_death"


class Gender(str, enum.Enum):
    """Baby gender enumeration"""
    MALE = "male"
    FEMALE = "female"
    UNIDENTIFIED = "unidentified"
    UNKNOWN = "unknown"


class DischargeCondition(str, enum.Enum):
    """Discharge condition for mother and baby"""
    STABLE = "stable"
    REFERRAL = "referral"
    DIED = "died"
    OTHER = "other"


class BirthCertificateStatus(str, enum.Enum):
    """Birth certificate registration status"""
    PENDING = "pending"
    REGISTERED = "registered"
    NOT_DONE = "not_done"
    NOT_APPLICABLE = "not_applicable"


class PlacentaStatus(str, enum.Enum):
    """Placenta delivery status - GHS compliant"""
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    RETAINED = "retained"
    OTHER = "other"


class TetanusStatus(str, enum.Enum):
    """Tetanus immunization status"""
    PROTECTED = "protected"
    NOT_PROTECTED = "not_protected"
    UNKNOWN = "unknown"


# === GHS ENUMS - NEW ===

class PlaceOfDelivery(str, enum.Enum):
    """Place of delivery - GHS standard"""
    HOSPITAL = "hospital"
    HEALTH_CENTRE = "health_centre"
    CHPS = "chps"
    HOME = "home"
    OTHER = "other"


class StateOfPerineum(str, enum.Enum):
    """State of perineum after delivery - GHS standard"""
    INTACT = "intact"
    TEAR = "tear"
    EPISIOTOMY = "episiotomy"
    OTHER = "other"


class AnaesthesiaType(str, enum.Enum):
    """Type of anaesthesia used - GHS standard"""
    NONE = "none"
    EPIDURAL = "epidural"
    SPINAL = "spinal"
    GENERAL = "general"
    OTHER = "other"


class NumberOfBabiesType(str, enum.Enum):
    """Number of babies - GHS standard"""
    SINGLE = "single"
    TWIN = "twin"
    TRIPLET = "triplet"
    OTHER = "other"


class BabyConditionAtDischarge(str, enum.Enum):
    """Baby condition at discharge - GHS standard"""
    NORMAL = "normal"
    ABNORMAL = "abnormal"


class UterusCondition(str, enum.Enum):
    """Condition of uterus at discharge - GHS standard"""
    CONTRACTED = "contracted"
    NOT_CONTRACTED = "not_contracted"


class BreastCondition(str, enum.Enum):
    """Condition of breast at discharge - GHS standard"""
    LACTATING = "lactating"
    NOT_LACTATING = "not_lactating"
    ENGORGED = "engorged"


class PerineumCondition(str, enum.Enum):
    """Condition of perineum/CS wound at discharge - GHS standard"""
    CLEAN = "clean"
    INFECTED = "infected"
    OTHER = "other"


class LochiaColour(str, enum.Enum):
    """Colour of lochia - GHS standard"""
    RUBRA = "rubra"
    SEROSA = "serosa"
    ALBA = "alba"
    OTHER = "other"


class LochiaOdour(str, enum.Enum):
    """Odour of lochia - GHS standard"""
    NORMAL = "normal"
    FOUL = "foul"
    OTHER = "other"


class EyeCareGiven(str, enum.Enum):
    """Eye care given - GHS standard"""
    CHLORAMPHENICOL = "chloramphenicol"
    TETRACYCLINE = "tetracycline"
    NONE = "none"


class TimeOfDay(str, enum.Enum):
    """Time of day AM/PM"""
    AM = "AM"
    PM = "PM"


class BirthRecord(Base):
    """
    SQLAlchemy Model for birth records and delivery tracking.
    Tracks deliveries and newborn details for Ghana Health Service compliance.
    Updated with GHS form fields.
    """
    __tablename__ = "birth_records"

    id = Column(Integer, primary_key=True, index=True)

    # Mother
    mother_patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    mother_nhis_number = Column(String(50), nullable=True)  # NHIS Number for claims
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True)  # If mother was IPD
    encounter_id = Column(Integer, ForeignKey("encounters.id"), nullable=True)
    antenatal_visit_id = Column(Integer, ForeignKey("antenatal_visits.id"), nullable=True)  # Link to ANC record

    # === DELIVERY OUTCOME SECTION (GHS) ===
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=True)
    
    # Weeks of pregnancy (GHS new)
    weeks_of_pregnancy = Column(Integer, nullable=True)
    
    # Time of delivery AM/PM (GHS new)
    time_of_delivery_am_pm = Column(String(10), nullable=True)
    
    # Time of placenta delivery AM/PM (GHS new)
    time_of_placenta_delivery_am_pm = Column(String(10), nullable=True)
    
    # Duration of labour (GHS - existing hours + new minutes)
    duration_of_labour_hours = Column(Numeric(10, 2), nullable=True)
    duration_labour_minutes = Column(Integer, nullable=True)  # GHS new
    
    delivery_type = Column(String(30), nullable=False, default=DeliveryType.VAGINAL.value)
    
    # Indication for Vacuum / Caesarean Section (GHS new)
    indication_for_vacuum_cs = Column(Text, nullable=True)
    
    # Anaesthesia (GHS new)
    anaesthesia = Column(String(50), nullable=True)
    
    # Estimated blood loss (GHS - existing)
    estimated_blood_loss_ml = Column(Integer, nullable=True)
    
    # Blood transfusion (GHS new)
    blood_transfusion = Column(Boolean, nullable=True)
    
    # State of placenta & membranes (GHS - enhanced)
    placenta_delivered = Column(String(20), nullable=True)
    
    # Manual removal of placenta (GHS new)
    manual_removal_placenta = Column(Boolean, nullable=True)
    
    # State of perineum (GHS new)
    state_of_perineum = Column(String(50), nullable=True)
    
    # Labour & delivery complications (GHS new)
    labour_delivery_complications = Column(Text, nullable=True)
    
    # Partograph used (GHS - existing)
    partograph_used = Column(Boolean, default=False)
    
    # Birth outcome (GHS - enhanced)
    birth_outcome = Column(String(30), nullable=False, default=BirthOutcome.LIVE.value)

    # Place of delivery (GHS new)
    place_of_delivery = Column(String(50), nullable=True)
    
    # Birth attendant (GHS - existing + enhanced)
    attendant_name = Column(String(200), nullable=True)
    attendant_category = Column(String(20), nullable=True)
    attendant_registration_number = Column(String(50), nullable=True)
    
    # Breastfeeding started within 30 minutes (GHS new)
    breastfeeding_30min = Column(Boolean, nullable=True)
    
    # Baby placed skin-to-skin (GHS - existing + reason)
    skin_to_skin = Column(Boolean, default=False)
    skin_to_skin_reason = Column(Text, nullable=True)  # GHS new - reason if No

    # Baby Information
    baby_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    weight_kg = Column(Numeric(10, 3), nullable=True)
    length_cm = Column(Numeric(10, 2), nullable=True)
    head_circumference_cm = Column(Numeric(10, 2), nullable=True)
    
    # Multiple Birth Information (GHS - enhanced)
    number_of_babies = Column(Integer, default=1)
    number_of_babies_type = Column(String(20), nullable=True)  # GHS new: Single, Twin, Triplet
    birth_order = Column(Integer, nullable=True)
    
    # Gestational Age (Critical for Ghana perinatal surveillance)
    gestational_age_weeks = Column(Integer, nullable=True)
    
    # Birth Weight Category (for child health tracking)
    low_birth_weight = Column(Boolean, default=False)
    very_low_birth_weight = Column(Boolean, default=False)

    # Apgar scores
    apgar_1min = Column(Integer, nullable=True)
    apgar_5min = Column(Integer, nullable=True)
    apgar_10min = Column(Integer, nullable=True)

    # Resuscitation (GHS requirement)
    resuscitation_required = Column(Boolean, default=False)
    resuscitation_type = Column(String(50), nullable=True)
    
    # Congenital malformation (GHS - existing as birth_defects, enhanced)
    birth_defects = Column(Text, nullable=True)
    
    # Complications at birth (GHS new)
    baby_complications = Column(Text, nullable=True)
    
    # Referred to facility (GHS new)
    referred_to_facility = Column(String(200), nullable=True)

    # Immediate Newborn Care
    vitamin_k_administered = Column(Boolean, default=False)
    bcg_vaccine = Column(Boolean, default=False)
    polio_vaccine = Column(Boolean, default=False)
    eye_prophylaxis = Column(Boolean, default=False)
    
    # Additional Newborn Care
    breastfeeding_initiated_1hr = Column(Boolean, default=False)
    nicu_admission = Column(Boolean, default=False)
    kangaroo_care = Column(Boolean, default=False)

    # Place of Birth (GHS vital statistics)
    facility_name = Column(String(200), nullable=True)
    district = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)

    # Staff (internal reference)
    delivered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assisted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Father Information
    father_name = Column(String(200), nullable=True)
    father_contact = Column(String(20), nullable=True)

    # Referral Information
    referred_from = Column(String(200), nullable=True)
    referred_to = Column(String(200), nullable=True)
    referral_reason = Column(Text, nullable=True)
    
    # Medications
    uterotonic_drug = Column(String(100), nullable=True)
    other_medications = Column(Text, nullable=True)
    
    # Mother's Health
    tetanus_status = Column(String(20), nullable=True)
    iptp_doses = Column(Integer, nullable=True)
    
    # Stillbirth Details
    fetal_death_date = Column(Date, nullable=True)
    fetal_death_time = Column(Time, nullable=True)

    # Administrative
    birth_number = Column(String(50), unique=True, nullable=True, index=True)
    birth_notification_number = Column(String(50), nullable=True)
    
    # Birth Certificate
    birth_certificate_status = Column(String(20), default=BirthCertificateStatus.PENDING.value)
    birth_certificate_number = Column(String(50), nullable=True)
    birth_certificate_date = Column(Date, nullable=True)
    
    # === BABY DISCHARGE SUMMARY (GHS NEW) ===
    discharge_date_baby = Column(Date, nullable=True)
    
    # General examination at discharge
    discharge_heart_rate = Column(Integer, nullable=True)
    discharge_respiratory_rate = Column(Integer, nullable=True)
    discharge_temperature = Column(Numeric(5, 1), nullable=True)
    discharge_weight = Column(Numeric(6, 3), nullable=True)
    
    # Feeding status at discharge
    breastfeeding_initiated_discharge = Column(Boolean, nullable=True)
    baby_suckling_established = Column(Boolean, nullable=True)
    meconium_passed = Column(Boolean, nullable=True)
    urine_passed = Column(Boolean, nullable=True)
    
    # Eye care
    eye_care_given = Column(String(50), nullable=True)
    
    # Immunisation dates
    cord_care_date = Column(Date, nullable=True)
    vitamin_k_date = Column(Date, nullable=True)
    bcg_date = Column(Date, nullable=True)
    hepatitis_b_date = Column(Date, nullable=True)
    oral_polio_date = Column(Date, nullable=True)
    
    # Baby's condition at discharge
    baby_condition_at_discharge = Column(String(50), nullable=True)
    baby_condition_abnormal_specify = Column(Text, nullable=True)
    
    # === MOTHER'S CONDITION AT DISCHARGE (GHS NEW) ===
    discharge_date_mother = Column(Date, nullable=True)
    discharge_mother_bp = Column(String(20), nullable=True)
    discharge_mother_pulse = Column(Integer, nullable=True)
    discharge_mother_temperature = Column(Numeric(5, 1), nullable=True)
    discharge_uterus_condition = Column(String(50), nullable=True)
    discharge_fundal_height = Column(Numeric(5, 1), nullable=True)
    discharge_lochia_colour = Column(String(50), nullable=True)
    discharge_lochia_odour = Column(String(50), nullable=True)
    discharge_perineum_condition = Column(String(50), nullable=True)
    discharge_breast_condition = Column(String(50), nullable=True)
    
    # === POSTNATAL CARE (PNC) PLAN (GHS NEW) ===
    next_visit_date = Column(Date, nullable=True)
    pnc1_date = Column(Date, nullable=True)  # 24-48 hours
    pnc2_date = Column(Date, nullable=True)  # 6th/7th day
    pnc3_date = Column(Date, nullable=True)  # 6 weeks
    
    # === EXISTING FIELDS (kept for backward compatibility) ===
    discharge_date = Column(Date, nullable=True)
    mother_discharge_condition = Column(String(20), nullable=True)
    baby_discharge_condition = Column(String(20), nullable=True)
    follow_up_date = Column(Date, nullable=True)
    
    # Baby's Residence
    baby_address = Column(Text, nullable=True)

    # Obstetric History
    gravida = Column(Integer, nullable=True)
    para = Column(Integer, nullable=True)
    
    # Complications and Notes
    complications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    mother = relationship("Patient", foreign_keys=[mother_patient_id], back_populates="birth_records_as_mother")
    admission = relationship("Admission", foreign_keys=[admission_id])
    encounter = relationship("Encounter", foreign_keys=[encounter_id])
    delivered_by = relationship("User", foreign_keys=[delivered_by_id])
    assisted_by = relationship("User", foreign_keys=[assisted_by_id])
    antenatal_visit = relationship("AntenatalVisit", foreign_keys=[antenatal_visit_id])
    baby_discharge = relationship("BabyDischarge", back_populates="birth_record", uselist=False)
