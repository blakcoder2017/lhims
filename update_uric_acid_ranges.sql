-- Update URIC ACID reference ranges in the database
-- Run this SQL script directly on your PostgreSQL database

-- First, try to UPDATE existing records
-- Update lab_reference_ranges table for uric_acid (field-based reference ranges)
UPDATE lab_reference_ranges 
SET 
    low = 142.0, 
    high = 339.0,
    unit = 'μmol/L'
WHERE 
    field_code = 'uric_acid' 
    AND sex = 'M' 
    AND age_min_days = 6570 
    AND age_max_days = 25550;

UPDATE lab_reference_ranges 
SET 
    low = 202.0, 
    high = 416.0,
    unit = 'μmol/L'
WHERE 
    field_code = 'uric_acid' 
    AND sex = 'F' 
    AND age_min_days = 6570 
    AND age_max_days = 25550;

-- Update for uric_acid_value (alternative field code)
UPDATE lab_reference_ranges 
SET 
    low = 142.0, 
    high = 339.0,
    unit = 'μmol/L'
WHERE 
    field_code = 'uric_acid_value' 
    AND sex = 'M' 
    AND age_min_days = 6570 
    AND age_max_days = 25550;

UPDATE lab_reference_ranges 
SET 
    low = 202.0, 
    high = 416.0,
    unit = 'μmol/L'
WHERE 
    field_code = 'uric_acid_value' 
    AND sex = 'F' 
    AND age_min_days = 6570 
    AND age_max_days = 25550;

-- If no records exist, INSERT new ones
-- Insert for uric_acid (Male)
INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid', 'M', 6570, 25550, 142.0, 339.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid' AND sex = 'M' AND age_min_days = 6570 AND age_max_days = 25550);

-- Insert for uric_acid (Female)
INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid', 'F', 6570, 25550, 202.0, 416.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid' AND sex = 'F' AND age_min_days = 6570 AND age_max_days = 25550);

-- Insert for uric_acid_value (Male)
INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid_value', 'M', 6570, 25550, 142.0, 339.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid_value' AND sex = 'M' AND age_min_days = 6570 AND age_max_days = 25550);

-- Insert for uric_acid_value (Female)
INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid_value', 'F', 6570, 25550, 202.0, 416.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid_value' AND sex = 'F' AND age_min_days = 6570 AND age_max_days = 25550);

-- Also insert pediatric ranges (1-18 years = 365-6570 days)
INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid', 'M', 365, 6570, 120.0, 350.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid' AND sex = 'M' AND age_min_days = 365 AND age_max_days = 6570);

INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid', 'F', 365, 6570, 120.0, 350.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid' AND sex = 'F' AND age_min_days = 365 AND age_max_days = 6570);

INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid_value', 'M', 365, 6570, 120.0, 350.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid_value' AND sex = 'M' AND age_min_days = 365 AND age_max_days = 6570);

INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at, updated_at)
SELECT 'uric_acid_value', 'F', 365, 6570, 120.0, 350.0, 'μmol/L', NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM lab_reference_ranges WHERE field_code = 'uric_acid_value' AND sex = 'F' AND age_min_days = 365 AND age_max_days = 6570);

-- Verify the updates
SELECT field_code, sex, age_min_days, age_max_days, low, high, unit 
FROM lab_reference_ranges 
WHERE field_code IN ('uric_acid', 'uric_acid_value') 
AND age_min_days >= 365
ORDER BY field_code, sex, age_min_days;
