-- =============================================
-- LHIMS GHS Birth Delivery Fields Migration
-- Run this SQL manually to add GHS-compliant fields
-- =============================================

-- === DELIVERY OUTCOME SECTION ===

-- Weeks of pregnancy
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS weeks_of_pregnancy INTEGER;
COMMENT ON COLUMN birth_records.weeks_of_pregnancy IS 'Weeks of pregnancy at delivery (gestational age)';

-- Time of delivery (AM/PM)
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS time_of_delivery_am_pm VARCHAR(10);
COMMENT ON COLUMN birth_records.time_of_delivery_am_pm IS 'Time of delivery: AM or PM';

-- Time of placenta delivery (AM/PM)
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS time_of_placenta_delivery_am_pm VARCHAR(10);
COMMENT ON COLUMN birth_records.time_of_placenta_delivery_am_pm IS 'Time of placenta delivery: AM or PM';

-- Duration of labour - minutes
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS duration_labour_minutes INTEGER;
COMMENT ON COLUMN birth_records.duration_labour_minutes IS 'Duration of labour in minutes';

-- Indication for Vacuum / Caesarean Section
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS indication_for_vacuum_cs TEXT;
COMMENT ON COLUMN birth_records.indication_for_vacuum_cs IS 'Clinical indication for vacuum extraction or caesarean section';

-- Anaesthesia type
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS anaesthesia VARCHAR(50);
COMMENT ON COLUMN birth_records.anaesthesia IS 'Type of anaesthesia used: None, Epidural, Spinal, General';

-- Blood transfusion
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS blood_transfusion BOOLEAN;
COMMENT ON COLUMN birth_records.blood_transfusion IS 'Whether blood transfusion was given during delivery';

-- Manual removal of placenta
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS manual_removal_placenta BOOLEAN;
COMMENT ON COLUMN birth_records.manual_removal_placenta IS 'Whether manual removal of placenta was required';

-- State of perineum
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS state_of_perineum VARCHAR(50);
COMMENT ON COLUMN birth_records.state_of_perineum IS 'State of perineum after delivery: Intact, Tear, Episiotomy';

-- Labour & delivery complications
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS labour_delivery_complications TEXT;
COMMENT ON COLUMN birth_records.labour_delivery_complications IS 'Free text field for labour and delivery complications';

-- Place of delivery
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS place_of_delivery VARCHAR(50);
COMMENT ON COLUMN birth_records.place_of_delivery IS 'Place of delivery: Hospital, Health Centre, CHPS, Home, Other';

-- Breastfeeding started within 30 minutes
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS breastfeeding_30min BOOLEAN;
COMMENT ON COLUMN birth_records.breastfeeding_30min IS 'Whether breastfeeding was initiated within 30 minutes of birth';

-- Skin to skin reason
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS skin_to_skin_reason TEXT;
COMMENT ON COLUMN birth_records.skin_to_skin_reason IS 'Reason if baby was not placed skin-to-skin with mother';

-- === BABY'S CONDITION AT BIRTH ===

-- Number of babies type
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS number_of_babies_type VARCHAR(20);
COMMENT ON COLUMN birth_records.number_of_babies_type IS 'Type of multiple birth: Single, Twin, Triplet, Other';

-- Baby complications
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_complications TEXT;
COMMENT ON COLUMN birth_records.baby_complications IS 'Complications at birth for the baby';

-- Referred to facility
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS referred_to_facility VARCHAR(200);
COMMENT ON COLUMN birth_records.referred_to_facility IS 'Facility baby was referred to';

-- === BABY DISCHARGE SUMMARY ===

ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_date_baby DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_heart_rate INTEGER;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_respiratory_rate INTEGER;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_temperature NUMERIC(5, 1);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_weight NUMERIC(6, 3);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS breastfeeding_initiated_discharge BOOLEAN;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_suckling_established BOOLEAN;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS meconium_passed BOOLEAN;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS urine_passed BOOLEAN;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS eye_care_given VARCHAR(50);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS cord_care_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS vitamin_k_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS bcg_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS hepatitis_b_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS oral_polio_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_condition_at_discharge VARCHAR(50);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS baby_condition_abnormal_specify TEXT;

-- === MOTHER'S CONDITION AT DISCHARGE ===

ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_date_mother DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_mother_bp VARCHAR(20);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_mother_pulse INTEGER;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_mother_temperature NUMERIC(5, 1);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_uterus_condition VARCHAR(50);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_fundal_height NUMERIC(5, 1);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_lochia_colour VARCHAR(50);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_lochia_odour VARCHAR(50);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_perineum_condition VARCHAR(50);
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS discharge_breast_condition VARCHAR(50);

-- === POSTNATAL CARE (PNC) PLAN ===

ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS next_visit_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS pnc1_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS pnc2_date DATE;
ALTER TABLE birth_records ADD COLUMN IF NOT EXISTS pnc3_date DATE;

-- === CREATE INDEXES ===

CREATE INDEX IF NOT EXISTS idx_birth_records_gestational_weeks ON birth_records(weeks_of_pregnancy);
CREATE INDEX IF NOT EXISTS idx_birth_records_place_of_delivery ON birth_records(place_of_delivery);
CREATE INDEX IF NOT EXISTS idx_birth_records_birth_outcome_discharge ON birth_records(birth_outcome, baby_condition_at_discharge);
CREATE INDEX IF NOT EXISTS idx_birth_records_pnc_dates ON birth_records(pnc1_date, pnc2_date, pnc3_date);

-- Add comments
COMMENT ON COLUMN birth_records.discharge_date_baby IS 'Date of baby discharge';
COMMENT ON COLUMN birth_records.discharge_heart_rate IS 'Baby heart rate at discharge (/min)';
COMMENT ON COLUMN birth_records.discharge_respiratory_rate IS 'Baby respiratory rate at discharge (/min)';
COMMENT ON COLUMN birth_records.discharge_temperature IS 'Baby temperature at discharge (°C)';
COMMENT ON COLUMN birth_records.discharge_weight IS 'Baby weight at discharge (kg)';
COMMENT ON COLUMN birth_records.breastfeeding_initiated_discharge IS 'Whether breastfeeding/breast milk was initiated at discharge';
COMMENT ON COLUMN birth_records.baby_suckling_established IS 'Whether baby suckling is established at discharge';
COMMENT ON COLUMN birth_records.meconium_passed IS 'Whether meconium has been passed';
COMMENT ON COLUMN birth_records.urine_passed IS 'Whether urine has been passed';
COMMENT ON COLUMN birth_records.eye_care_given IS 'Eye care given: Chloramphenicol, Tetracycline, or None';
COMMENT ON COLUMN birth_records.cord_care_date IS 'Date of cord care';
COMMENT ON COLUMN birth_records.vitamin_k_date IS 'Date Vitamin K was administered';
COMMENT ON COLUMN birth_records.bcg_date IS 'Date BCG vaccine was given';
COMMENT ON COLUMN birth_records.hepatitis_b_date IS 'Date Hepatitis B vaccine was given';
COMMENT ON COLUMN birth_records.oral_polio_date IS 'Date Oral Polio Vaccine (OPV) was given';
COMMENT ON COLUMN birth_records.baby_condition_at_discharge IS 'Baby condition at discharge: Normal, Abnormal';
COMMENT ON COLUMN birth_records.baby_condition_abnormal_specify IS 'Specify if baby condition at discharge is abnormal';
COMMENT ON COLUMN birth_records.discharge_date_mother IS 'Date of mother discharge';
COMMENT ON COLUMN birth_records.discharge_mother_bp IS 'Mother blood pressure at discharge (mmHg)';
COMMENT ON COLUMN birth_records.discharge_mother_pulse IS 'Mother pulse rate at discharge (/min)';
COMMENT ON COLUMN birth_records.discharge_mother_temperature IS 'Mother temperature at discharge (°C)';
COMMENT ON COLUMN birth_records.discharge_uterus_condition IS 'Condition of uterus at discharge: Contracted, Not contracted';
COMMENT ON COLUMN birth_records.discharge_fundal_height IS 'Fundal height at discharge (cm)';
COMMENT ON COLUMN birth_records.discharge_lochia_colour IS 'Colour of lochia at discharge';
COMMENT ON COLUMN birth_records.discharge_lochia_odour IS 'Odour of lochia at discharge';
COMMENT ON COLUMN birth_records.discharge_perineum_condition IS 'Condition of perineum/CS wound at discharge: Clean, Infected, Other';
COMMENT ON COLUMN birth_records.discharge_breast_condition IS 'Condition of breast at discharge: Lactating, Not lactating, Engorged';
COMMENT ON COLUMN birth_records.next_visit_date IS 'Date of next visit';
COMMENT ON COLUMN birth_records.pnc1_date IS 'PNC 1 date (24-48 hours after delivery)';
COMMENT ON COLUMN birth_records.pnc2_date IS 'PNC 2 date (6th/7th day)';
COMMENT ON COLUMN birth_records.pnc3_date IS 'PNC 3 date (6 weeks)';

-- Verify columns added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'birth_records' 
AND column_name LIKE '%pnc%' 
OR column_name LIKE '%discharge%'
ORDER BY column_name;
