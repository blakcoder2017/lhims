"""add_ghs_birth_delivery_fields

Revision ID: add_ghs_birth_delivery_fields
Revises: add_birth_labour_delivery_fields
Create Date: 2026-02-24 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_ghs_birth_delivery_fields'
down_revision: Union[str, Sequence[str], None] = 'add_birth_labour_delivery_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add GHS-compliant birth/delivery fields to match Ghana Health Service forms."""
    
    # === DELIVERY OUTCOME SECTION ===
    # Weeks of pregnancy
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS weeks_of_pregnancy INTEGER')
    op.execute("COMMENT ON COLUMN birth_records.weeks_of_pregnancy IS 'Weeks of pregnancy at delivery (gestational age)'")
    
    # Time of delivery (AM/PM)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS time_of_delivery_am_pm VARCHAR(10)')
    op.execute("COMMENT ON COLUMN birth_records.time_of_delivery_am_pm IS 'Time of delivery: AM or PM'")
    
    # Time of placenta delivery (AM/PM)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS time_of_placenta_delivery_am_pm VARCHAR(10)')
    op.execute("COMMENT ON COLUMN birth_records.time_of_placenta_delivery_am_pm IS 'Time of placenta delivery: AM or PM'")
    
    # Duration of labour - minutes (additional to hours)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS duration_labour_minutes INTEGER')
    op.execute("COMMENT ON COLUMN birth_records.duration_labour_minutes IS 'Duration of labour in minutes'")
    
    # Indication for Vacuum / Caesarean Section
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS indication_for_vacuum_cs TEXT')
    op.execute("COMMENT ON COLUMN birth_records.indication_for_vacuum_cs IS 'Clinical indication for vacuum extraction or caesarean section'")
    
    # Anaesthesia type
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS anaesthesia VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.anaesthesia IS 'Type of anaesthesia used: None, Epidural, Spinal, General'")
    
    # Blood transfusion
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS blood_transfusion BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.blood_transfusion IS 'Whether blood transfusion was given during delivery'")
    
    # Manual removal of placenta
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS manual_removal_placenta BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.manual_removal_placenta IS 'Whether manual removal of placenta was required'")
    
    # State of perineum
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS state_of_perineum VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.state_of_perineum IS 'State of perineum after delivery: Intact, Tear, Episiotomy'")
    
    # Labour & delivery complications (free text)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS labour_delivery_complications TEXT')
    op.execute("COMMENT ON COLUMN birth_records.labour_delivery_complications IS 'Free text field for labour and delivery complications'")
    
    # Place of delivery (Hospital, Health Centre, CHPS, Home, Other)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS place_of_delivery VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.place_of_delivery IS 'Place of delivery: Hospital, Health Centre, CHPS, Home, Other'")
    
    # Breastfeeding started within 30 minutes
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS breastfeeding_30min BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.breastfeeding_30min IS 'Whether breastfeeding was initiated within 30 minutes of birth'")
    
    # Baby placed skin-to-skin with mother
    # Note: skin_to_skin already exists, adding reason field
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS skin_to_skin_reason TEXT')
    op.execute("COMMENT ON COLUMN birth_records.skin_to_skin_reason IS 'Reason if baby was not placed skin-to-skin with mother'")
    
    # === BABY'S CONDITION AT BIRTH ===
    # (Most fields already exist - adding new ones)
    
    # Number of babies (Single, Twin, Triplet, Other)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS number_of_babies_type VARCHAR(20)')
    op.execute("COMMENT ON COLUMN birth_records.number_of_babies_type IS 'Type of multiple birth: Single, Twin, Triplet, Other'")
    
    # Baby complications
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_complications TEXT')
    op.execute("COMMENT ON COLUMN birth_records.baby_complications IS 'Complications at birth for the baby'")
    
    # Referred to (facility)
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS referred_to_facility VARCHAR(200)')
    op.execute("COMMENT ON COLUMN birth_records.referred_to_facility IS 'Facility baby was referred to'")
    
    # === BABY DISCHARGE SUMMARY ===
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_date_baby DATE')
    op.execute("COMMENT ON COLUMN birth_records.discharge_date_baby IS 'Date of baby discharge'")
    
    # General examination at discharge
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_heart_rate INTEGER')
    op.execute("COMMENT ON COLUMN birth_records.discharge_heart_rate IS 'Baby heart rate at discharge (/min)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_respiratory_rate INTEGER')
    op.execute("COMMENT ON COLUMN birth_records.discharge_respiratory_rate IS 'Baby respiratory rate at discharge (/min)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_temperature NUMERIC(5, 1)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_temperature IS 'Baby temperature at discharge (°C)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_weight NUMERIC(6, 3)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_weight IS 'Baby weight at discharge (kg)'")
    
    # Feeding status at discharge
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS breastfeeding_initiated_discharge BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.breastfeeding_initiated_discharge IS 'Whether breastfeeding/breast milk was initiated at discharge'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_suckling_established BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.baby_suckling_established IS 'Whether baby suckling is established at discharge'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS meconium_passed BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.meconium_passed IS 'Whether meconium has been passed'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS urine_passed BOOLEAN')
    op.execute("COMMENT ON COLUMN birth_records.urine_passed IS 'Whether urine has been passed'")
    
    # Eye care
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS eye_care_given VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.eye_care_given IS 'Eye care given: Chloramphenicol, Tetracycline, or None'")
    
    # Immunisation dates
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS cord_care_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.cord_care_date IS 'Date of cord care'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS vitamin_k_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.vitamin_k_date IS 'Date Vitamin K was administered'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS bcg_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.bcg_date IS 'Date BCG vaccine was given'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS hepatitis_b_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.hepatitis_b_date IS 'Date Hepatitis B vaccine was given'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS oral_polio_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.oral_polio_date IS 'Date Oral Polio Vaccine (OPV) was given'")
    
    # Baby's condition at discharge
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_condition_at_discharge VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.baby_condition_at_discharge IS 'Baby condition at discharge: Normal, Abnormal'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_condition_abnormal_specify TEXT')
    op.execute("COMMENT ON COLUMN birth_records.baby_condition_abnormal_specify IS 'Specify if baby condition at discharge is abnormal'")
    
    # === MOTHER'S CONDITION AT DISCHARGE ===
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_date_mother DATE')
    op.execute("COMMENT ON COLUMN birth_records.discharge_date_mother IS 'Date of mother discharge'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_mother_bp VARCHAR(20)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_mother_bp IS 'Mother blood pressure at discharge (mmHg)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_mother_pulse INTEGER')
    op.execute("COMMENT ON COLUMN birth_records.discharge_mother_pulse IS 'Mother pulse rate at discharge (/min)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_mother_temperature NUMERIC(5, 1)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_mother_temperature IS 'Mother temperature at discharge (°C)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_uterus_condition VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_uterus_condition IS 'Condition of uterus at discharge: Contracted, Not contracted'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_fundal_height NUMERIC(5, 1)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_fundal_height IS 'Fundal height at discharge (cm)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_lochia_colour VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_lochia_colour IS 'Colour of lochia at discharge'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_lochia_odour VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_lochia_odour IS 'Odour of lochia at discharge'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_perineum_condition VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_perineum_condition IS 'Condition of perineum/CS wound at discharge: Clean, Infected, Other'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_breast_condition VARCHAR(50)')
    op.execute("COMMENT ON COLUMN birth_records.discharge_breast_condition IS 'Condition of breast at discharge: Lactating, Not lactating, Engorged'")
    
    # === POSTNATAL CARE (PNC) PLAN ===
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS next_visit_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.next_visit_date IS 'Date of next visit'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS pnc1_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.pnc1_date IS 'PNC 1 date (24-48 hours after delivery)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS pnc2_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.pnc2_date IS 'PNC 2 date (6th/7th day)'")
    
    op.execute('ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS pnc3_date DATE')
    op.execute("COMMENT ON COLUMN birth_records.pnc3_date IS 'PNC 3 date (6 weeks)'")
    
    # === ADDITIONAL ENHANCEMENTS ===
    # Delivery type - expanded options for GHS
    # Note: delivery_type already exists, we add new options via UI
    
    # Relative as birth attendant (add to enum)
    # This is handled in the application layer
    
    # Create indexes for new commonly queried fields
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_gestational_weeks ON birth_records(weeks_of_pregnancy)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_place_of_delivery ON birth_records(place_of_delivery)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_birth_outcome_discharge ON birth_records(birth_outcome, baby_condition_at_discharge)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_birth_records_pnc_dates ON birth_records(pnc1_date, pnc2_date, pnc3_date)')


def downgrade() -> None:
    """Remove GHS-compliant birth/delivery fields from birth_records."""
    
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS idx_birth_records_pnc_dates')
    op.execute('DROP INDEX IF EXISTS idx_birth_records_birth_outcome_discharge')
    op.execute('DROP INDEX IF EXISTS idx_birth_records_place_of_delivery')
    op.execute('DROP INDEX IF EXISTS idx_birth_records_gestational_weeks')
    
    # Drop PNC columns
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS pnc3_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS pnc2_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS pnc1_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS next_visit_date')
    
    # Drop mother's condition at discharge columns
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_breast_condition')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_perineum_condition')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_lochia_odour')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_lochia_colour')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_fundal_height')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_uterus_condition')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_mother_temperature')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_mother_pulse')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_mother_bp')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_date_mother')
    
    # Drop baby condition at discharge columns
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS baby_condition_abnormal_specify')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS baby_condition_at_discharge')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS oral_polio_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS hepatitis_b_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS bcg_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS vitamin_k_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS cord_care_date')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS eye_care_given')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS urine_passed')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS meconium_passed')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS baby_suckling_established')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS breastfeeding_initiated_discharge')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_weight')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_temperature')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_respiratory_rate')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_heart_rate')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS discharge_date_baby')
    
    # Drop baby's condition at birth columns
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS referred_to_facility')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS baby_complications')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS number_of_babies_type')
    
    # Drop delivery outcome columns
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS place_of_delivery')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS labour_delivery_complications')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS state_of_perineum')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS manual_removal_placenta')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS blood_transfusion')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS anaesthesia')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS indication_for_vacuum_cs')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS duration_labour_minutes')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS time_of_placenta_delivery_am_pm')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS time_of_delivery_am_pm')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS weeks_of_pregnancy')
    
    # Note: skin_to_skin_reason should be dropped but skin_to_skin kept
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS skin_to_skin_reason')
    op.execute('ALTER TABLE birth_records DROP COLUMN IF EXISTS breastfeeding_30min')
