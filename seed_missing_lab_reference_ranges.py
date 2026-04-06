#!/usr/bin/env python3
"""
Seed Missing Lab Reference Ranges
==================================
This script adds missing reference ranges for lab tests that have templates
but are missing reference range definitions.

Key fixes:
- mp_result: Blood Film for Malaria Parasite (choice field - text range)
- hb_value: Alternative field code for Haemoglobin
- Other missing fields from templates

Usage:
    python3 seed_missing_lab_reference_ranges.py
"""

import sys
import os
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

# Database URL - update this to your actual database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/lhims")

# Age group constants (in days)
NEONATE_MAX = 28       # 0-28 days
INFANT_MAX = 365       # 1-12 months
TODDLER_MAX = 1095     # 1-3 years
CHILD_MAX = 4745       # 3-12 years  
ADOLESCENT_MAX = 6570  # 12-18 years
ADULT_MAX = 25550      # 18-70 years
ELDERLY_MAX = 36500    # 70-100 years


def get_missing_reference_ranges():
    """Define missing reference ranges with age and gender logic."""
    ranges = []
    
    # ========== PARASITOLOGY ==========
    
    # Blood Film for Malaria Parasite - mp_result field
    ranges.extend([
        {"field_code": "mp_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,P. falciparum,P. vivax,P. malariae,P. ovale,Mixed", "unit": None},
    ])
    
    # Microfilaria
    ranges.extend([
        {"field_code": "microfilaria", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # ========== HAEMATOLOGY - Alternative field codes ==========
    
    # Haemoglobin - hb_value (alternative to hb)
    ranges.extend([
        {"field_code": "hb_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("13.0"), "high": Decimal("17.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("12.0"), "high": Decimal("15.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 28,
         "low": Decimal("14.5"), "high": Decimal("22.5"), "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"},
        {"field_code": "hb_value", "sex": "ANY", "age_min_days": 29, "age_max_days": 365,
         "low": Decimal("9.5"), "high": Decimal("13.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb_value", "sex": "ANY", "age_min_days": 366, "age_max_days": 4745,
         "low": Decimal("11.5"), "high": Decimal("14.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
    ])
    
    # PCV/HCT - hct_value
    ranges.extend([
        {"field_code": "hct_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("36"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("34"), "high": Decimal("46"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570,
         "low": Decimal("32"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
    ])
    
    # Sickling Test
    ranges.extend([
        {"field_code": "sickling_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive,Trait,Disease", "unit": None},
    ])
    
    # G6PD
    ranges.extend([
        {"field_code": "g6pd_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "-", "unit": None},
    ])
    
    # Direct Coombs
    ranges.extend([
        {"field_code": "direct_coombs", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # ABO Group
    ranges.extend([
        {"field_code": "abo_group", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "A,B,AB,O", "unit": None},
    ])
    
    # Rhesus Factor
    ranges.extend([
        {"field_code": "rhesus_factor", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Positive,Negative", "unit": None},
    ])
    
    # ========== CLINICAL PATHOLOGY / URINALYSIS ==========
    
    # Urine Appearance
    ranges.extend([
        {"field_code": "appearance", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Clear,Slightly cloudy,Cloudy,Turbid", "unit": None},
    ])
    
    # Urine Colour
    ranges.extend([
        {"field_code": "colour", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Pale yellow,Yellow,Dark yellow,Amber,Brown,Red", "unit": None},
    ])
    
    # Urine pH
    ranges.extend([
        {"field_code": "urine_ph", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("4.5"), "high": Decimal("8.0"), "unit": ""},
    ])
    
    # Urine Specific Gravity
    ranges.extend([
        {"field_code": "specific_gravity", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("1.005"), "high": Decimal("1.030"), "unit": ""},
    ])
    
    # Urine Protein
    ranges.extend([
        {"field_code": "urine_protein", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Trace,1+,2+,3+,4+", "unit": None},
    ])
    
    # Urine Glucose
    ranges.extend([
        {"field_code": "urine_glucose", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Trace,1+,2+,3+,4+", "unit": None},
    ])
    
    # Urine Ketones
    ranges.extend([
        {"field_code": "urine_ketones", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Trace,1+,2+,3+", "unit": None},
    ])
    
    # Urine Blood
    ranges.extend([
        {"field_code": "urine_blood", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Trace,1+,2+,3+", "unit": None},
    ])
    
    # Urine Nitrite
    ranges.extend([
        {"field_code": "urine_nitrite", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # Urine Leukocytes
    ranges.extend([
        {"field_code": "urine_leukocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Trace,1+,2+,3+", "unit": None},
    ])
    
    # Urine Bilirubin
    ranges.extend([
        {"field_code": "urine_bilirubin", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,1+,2+,3+", "unit": None},
    ])
    
    # Urine Urobilinogen
    ranges.extend([
        {"field_code": "urine_urobilinogen", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Normal,1+,2+,3+,4+", "unit": None},
    ])
    
    # Pregnancy Test
    ranges.extend([
        {"field_code": "pregnancy_result", "sex": "F", "age_min_days": 4380, "age_max_days": 18250,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # ========== SEROLOGY / VIROLOGY ==========
    
    # HIV
    ranges.extend([
        {"field_code": "hiv_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive,Indeterminate", "unit": None},
    ])
    
    # HBsAg
    ranges.extend([
        {"field_code": "hbsag_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # Anti-HBs
    ranges.extend([
        {"field_code": "hbsab_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive,<10,>10", "unit": "mIU/mL"},
    ])
    
    # HBcAb
    ranges.extend([
        {"field_code": "hbcab_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # HCV
    ranges.extend([
        {"field_code": "hcv_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # VDRL
    ranges.extend([
        {"field_code": "vdrl_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Non-reactive,Reactive,Weakly reactive", "unit": None},
    ])
    
    # TPHA
    ranges.extend([
        {"field_code": "tpha_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Non-reactive,Reactive", "unit": None},
    ])
    
    # Widal
    ranges.extend([
        {"field_code": "widal_to", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,1:40,1:80,1:160,1:320", "unit": None},
        {"field_code": "widal_th", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,1:40,1:80,1:160,1:320", "unit": None},
    ])
    
    # Gonorrhoea
    ranges.extend([
        {"field_code": "gonorrhoea_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # Chlamydia
    ranges.extend([
        {"field_code": "chlamydia_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # H. pylori
    ranges.extend([
        {"field_code": "hpylori_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # AFP
    ranges.extend([
        {"field_code": "afp_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # Rheumatoid Factor
    ranges.extend([
        {"field_code": "ra_result", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # Troponin
    ranges.extend([
        {"field_code": "troponin_qual", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "text_range": "Negative,Positive", "unit": None},
    ])
    
    # ========== ADDITIONAL BIOCHEMISTRY ==========
    
    # TSH (alternative field code)
    ranges.extend([
        {"field_code": "tsh", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("0.4"), "high": Decimal("4.0"), "unit": "mIU/L"},
    ])
    
    # Urea (alternative field code)
    ranges.extend([
        {"field_code": "urea_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("2.9"), "high": Decimal("8.2"), "unit": "mmol/L"},
    ])
    
    # Creatinine (alternative field code)
    ranges.extend([
        {"field_code": "creatinine_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("62"), "high": Decimal("106"), "unit": "μmol/L"},
        {"field_code": "creatinine_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("44"), "high": Decimal("80"), "unit": "μmol/L"},
    ])
    
    # Total Cholesterol (alternative field code)
    ranges.extend([
        {"field_code": "cholesterol_total", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("5.2"), "unit": "mmol/L"},
    ])
    
    # LDL Cholesterol
    ranges.extend([
        {"field_code": "ldl_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("3.4"), "unit": "mmol/L"},
    ])
    
    # HDL Cholesterol
    ranges.extend([
        {"field_code": "hdl_value", "sex": "M", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("1.0"), "high": Decimal("2.2"), "unit": "mmol/L"},
        {"field_code": "hdl_value", "sex": "F", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("1.2"), "high": Decimal("2.7"), "unit": "mmol/L"},
    ])
    
    # Triglycerides (alternative field code)
    ranges.extend([
        {"field_code": "triglycerides_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("1.7"), "unit": "mmol/L"},
    ])
    
    # eGFR (alternative field code)
    ranges.extend([
        {"field_code": "gfr_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("90"), "high": Decimal("120"), "unit": "mL/min/1.73m²"},
    ])
    
    # Potassium (alternative field code)
    ranges.extend([
        {"field_code": "potassium_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("3.5"), "high": Decimal("5.0"), "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mmol/L"},
    ])
    
    # Chloride (alternative field code)
    ranges.extend([
        {"field_code": "chloride_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("98"), "high": Decimal("106"), "unit": "mmol/L"},
    ])
    
    # Bicarbonate (alternative field code)
    ranges.extend([
        {"field_code": "bicarbonate_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("22"), "high": Decimal("29"), "unit": "mmol/L"},
    ])
    
    # Ferritin
    ranges.extend([
        {"field_code": "ferritin", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("30"), "high": Decimal("400"), "unit": "ng/mL"},
        {"field_code": "ferritin", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("13"), "high": Decimal("150"), "unit": "ng/mL"},
    ])
    
    # TIBC
    ranges.extend([
        {"field_code": "tibc", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("44.8"), "high": Decimal("73.4"), "unit": "μmol/L"},
    ])
    
    # HIV Viral Load
    ranges.extend([
        {"field_code": "hiv_vl_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("20"), "unit": "copies/mL"},
    ])
    
    # HBV Viral Load
    ranges.extend([
        {"field_code": "hbv_vl_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("20"), "unit": "IU/mL"},
    ])
    
    # HCV Viral Load
    ranges.extend([
        {"field_code": "hcv_vl_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("15"), "unit": "IU/mL"},
    ])
    
    # β-HCG
    ranges.extend([
        {"field_code": "bhcg_value", "sex": "F", "age_min_days": 4380, "age_max_days": 18250,
         "low": Decimal("0"), "high": Decimal("5.0"), "unit": "IU/L"},
    ])
    
    # BNP
    ranges.extend([
        {"field_code": "bnp_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("100"), "unit": "pg/mL"},
    ])
    
    return ranges


def seed_reference_ranges(conn):
    """Insert missing reference ranges into the database."""
    print("=" * 70)
    print("Adding Missing Lab Reference Ranges")
    print("=" * 70)
    
    ranges = get_missing_reference_ranges()
    print(f"\nTotal reference ranges to add: {len(ranges)}")
    
    inserted = 0
    skipped = 0
    
    for rr in ranges:
        field_code = rr.get("field_code")
        sex = rr.get("sex", "ANY")
        age_min = rr.get("age_min_days", 0)
        age_max = rr.get("age_max_days")
        
        # Check if range already exists
        query = text("""
            SELECT id FROM lab_reference_ranges
            WHERE field_code = :fc 
            AND (sex = :sex OR (sex IS NULL AND :sex IS NULL))
            AND age_min_days = :age_min
            AND (age_max_days = :age_max OR (age_max_days IS NULL AND :age_max IS NULL))
            LIMIT 1
        """)
        
        result = conn.execute(query, {
            "fc": field_code, 
            "sex": sex, 
            "age_min": age_min, 
            "age_max": age_max
        })
        existing = result.fetchone()
        
        if existing:
            skipped += 1
            print(f"  ⏭️  SKIP: {field_code} (sex={sex}, age={age_min}-{age_max}) - already exists")
            continue
        
        # Insert new reference range
        low = rr.get("low")
        high = rr.get("high")
        critical_low = rr.get("critical_low")
        critical_high = rr.get("critical_high")
        unit = rr.get("unit")
        text_range = rr.get("text_range")
        
        insert_query = text("""
            INSERT INTO lab_reference_ranges 
            (field_code, sex, age_min_days, age_max_days, low, high, 
             critical_low, critical_high, unit, text_range, created_at)
            VALUES 
            (:fc, :sex, :age_min, :age_max, :low, :high, 
             :crit_low, :crit_high, :unit, :text_range, NOW())
        """)
        
        conn.execute(insert_query, {
            "fc": field_code,
            "sex": sex,
            "age_min": age_min,
            "age_max": age_max,
            "low": low,
            "high": high,
            "crit_low": critical_low,
            "crit_high": critical_high,
            "unit": unit,
            "text_range": text_range
        })
        
        inserted += 1
        print(f"  ✅ INSERT: {field_code} (sex={sex}, age={age_min}-{age_max or '∞'})")
    
    conn.commit()
    
    print(f"\n{'=' * 70}")
    print(f"Summary:")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped:  {skipped}")
    print(f"  Total:    {len(ranges)}")
    print(f"{'=' * 70}")
    
    return inserted, skipped


def main():
    """Main function to seed missing reference ranges."""
    print("\n" + "=" * 70)
    print("LAB MISSING REFERENCE RANGES SEEDER")
    print("=" * 70)
    
    # Create database engine
    print(f"\nConnecting to database: {DATABASE_URL[:30]}...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        inserted, skipped = seed_reference_ranges(conn)
    
    print("\n✅ Seeding complete!")
    return inserted, skipped


if __name__ == "__main__":
    main()
