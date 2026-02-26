-- Baby Discharge Summary Table
-- Stores individual discharge information for each baby - essential for multiple births

CREATE TABLE IF NOT EXISTS baby_discharge_summaries (
    id SERIAL PRIMARY KEY,
    birth_record_id INTEGER NOT NULL UNIQUE REFERENCES birth_records(id) ON DELETE CASCADE,
    
    -- Discharge Date
    discharge_date DATE,
    
    -- General Examination at Discharge
    heart_rate INTEGER,  -- /min
    respiratory_rate INTEGER,  -- /min
    temperature NUMERIC(5, 1),  -- °C
    weight_at_discharge NUMERIC(6, 3),  -- kg (especially for NICU)
    
    -- Feeding Status
    breastfeeding_initiated BOOLEAN,
    suckling_established BOOLEAN,
    meconium_passed BOOLEAN,
    urine_passed BOOLEAN,
    
    -- Eye Care
    eye_care_given VARCHAR(50),
    
    -- Immunisation Dates
    cord_care_date DATE,
    vitamin_k_date DATE,
    bcg_date DATE,
    hepatitis_b_date DATE,
    oral_polio_date DATE,
    
    -- Baby's Condition at Discharge
    condition VARCHAR(50),  -- Normal, Abnormal, Referral, NICU, Died
    abnormal_specify TEXT,  -- If Abnormal, specify
    
    -- Referred to facility (if Referral)
    referred_to VARCHAR(200),
    
    -- Additional notes
    notes TEXT,
    
    -- Recording metadata
    recorded_by_id INTEGER REFERENCES users(id),
    created_at DATE DEFAULT CURRENT_DATE,
    updated_at DATE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_baby_discharge_birth_record 
ON baby_discharge_summaries(birth_record_id);

COMMENT ON TABLE baby_discharge_summaries IS 'Baby Discharge Summary - stores individual discharge info per baby for multiple birth tracking';
