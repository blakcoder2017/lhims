#!/usr/bin/env python3
"""
Lab Catalog Fix Script
======================
Fixes the issues identified in the lab catalog audit:
1. Links orphaned tests to templates
2. Adds missing reference ranges
3. Adds missing age/sex specific ranges

Usage:
    python3 fix_lab_catalog_issues.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')

engine = create_engine(DATABASE_URL)


def link_tests_to_templates():
    """Link orphaned tests to their corresponding templates."""
    print("\n=== LINKING TESTS TO TEMPLATES ===\n")
    
    # Mapping of test codes to template names
    test_template_map = {
        'CS_SPUTUM': 'Lab Test - SPUTUM_AFB',  # Use existing template
        'CS_STOOL': 'Lab Test - STOOL_CULTURE',  # Use existing template
        'CS_URINE': 'Lab Test - URINE_CULTURE',  # Use existing template
        'CS_WOUND': 'Lab Test - WOUND_SWAB',  # Use existing template
        'FEMALE_INFERTILITY': 'Lab Test - FSH',  # Reuse related template
        'FERRITIN': 'Lab Test - IRON_STUDIES',  # Part of iron studies
        'HBV_PROFILE': 'Lab Test - HBSAG',  # Reuse hepatitis template
        'TIBC': 'Lab Test - IRON_STUDIES',  # Part of iron studies
    }
    
    with engine.connect() as conn:
        for test_code, template_name in test_template_map.items():
            # Get template ID
            result = conn.execute(text(
                "SELECT id FROM lab_templates WHERE name = :name"
            ), {'name': template_name})
            template_row = result.fetchone()
            
            if template_row:
                template_id = template_row[0]
                
                # Update the test to link to template
                conn.execute(text("""
                    UPDATE lab_tests 
                    SET template_id = :template_id 
                    WHERE test_code = :test_code
                """), {'template_id': template_id, 'test_code': test_code})
                
                print(f"  ✓ Linked {test_code} -> {template_name}")
            else:
                print(f"  ✗ Template not found: {template_name}")
        
        conn.commit()
    
    print("\nDone linking tests to templates!")


def add_missing_reference_ranges():
    """Add missing reference ranges for fields identified in the audit."""
    print("\n=== ADDING MISSING REFERENCE RANGES ===\n")
    
    # Additional reference ranges to add
    additional_ranges = [
        # Urine RE - casts, bacteria, crystals
        ('urine_casts', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Negative,Rare,Few,Moderate,Many'),
        ('urine_bacteria', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Nil,Rare,Few,Moderate,Many'),
        ('urine_crystals', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'None,Rare,Present'),
        
        # Stool RE - ova and parasites
        ('stool_ova', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Not seen,Rare,Present'),
        ('stool_parasites', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Not seen,Rare,Present'),
        
        # CSF appearance
        ('csf_appearance', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Clear,Slightly turbid,Turbid,Bloody'),
        
        # Ascitic fluid appearance
        ('ascitic_appearance', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Clear,Sero-sanguinous,Sanguinous,Turbid'),
        
        # Pleural fluid appearance
        ('pleural_appearance', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Clear,Sero-sanguinous,Sanguinous,Turbid'),
        
        # VDRL titer
        ('vdrl_titer', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Negative,1:1,1:2,1:4,1:8,1:16,1:32,1:64,1:128'),
        
        # Indirect Coombs
        ('indirect_coombs', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'Negative,Positive'),
        
        # Parasite density for BF_MP
        ('parasite_density', 'ANY', 0, 36500, 0, 100000, 'parasites/μL', None, None, None),
        
        # HIV kit name (text field - no range needed)
        
        # Semen analysis fields - add ranges
        ('semen_volume', 'ANY', 18, 36500, 1.5, 5.0, 'mL', 0.5, None),
        ('semen_ph', 'ANY', 18, 36500, 7.2, 8.0, 'pH', 7.0, 9.0),
        ('sperm_count', 'ANY', 18, 36500, 15, 200, 'million/mL', 5, None),
        ('progressive_sperm', 'ANY', 18, 36500, 32, 100, '%', 0, None),
        ('normal_forms', 'ANY', 18, 36500, 4, 100, '%', 0, None),
        ('liquefaction', 'ANY', 18, 36500, 15, 60, 'minutes', 5, 120),
        
        # Culture-related fields (these are qualitative)
        ('culture_growth', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'No Growth,Light,Moderate,Heavy,Mixed'),
        ('organism', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'None,Various...'),
        
        # HVS culture
        ('hvs_culture', 'ANY', 0, 36500, None, None, 'text_range', None, None, 'No Growth,Normal Flora,Pathogen Isolated'),
    ]
    
    with engine.connect() as conn:
        for range_data in additional_ranges:
            field_code = range_data[0]
            sex = range_data[1]
            age_min = range_data[2]
            age_max = range_data[3]
            low = range_data[4]
            high = range_data[5]
            unit = range_data[6]
            critical_low = range_data[7]
            critical_high = range_data[8]
            text_range = range_data[9] if len(range_data) > 9 else None
            
            try:
                conn.execute(text("""
                    INSERT INTO lab_reference_ranges 
                    (field_code, sex, age_min_days, age_max_days, low, high, unit, critical_low, critical_high, text_range)
                    VALUES (:field_code, :sex, :age_min, :age_max, :low, :high, :unit, :critical_low, :critical_high, :text_range)
                    ON CONFLICT DO NOTHING
                """), {
                    'field_code': field_code,
                    'sex': sex,
                    'age_min': age_min,
                    'age_max': age_max,
                    'low': low,
                    'high': high,
                    'unit': unit,
                    'critical_low': critical_low,
                    'critical_high': critical_high,
                    'text_range': text_range
                })
                print(f"  ✓ Added range for {field_code}")
            except Exception as e:
                print(f"  ✗ Error adding {field_code}: {e}")
        
        conn.commit()
    
    print("\nDone adding reference ranges!")


def add_age_sex_specific_ranges():
    """Add additional age/sex specific ranges for clinically significant parameters."""
    print("\n=== ADDING AGE/SEX SPECIFIC RANGES ===\n")
    
    # Additional ranges for better clinical accuracy
    additional_ranges = [
        # Amylase - add sex-specific (slightly higher in females)
        ('amylase_value', 'M', 0, 365, 20, 100, 'U/L', None, 300),
        ('amylase_value', 'M', 365, 6570, 25, 100, 'U/L', None, 300),
        ('amylase_value', 'M', 6570, 25550, 25, 125, 'U/L', None, 300),
        ('amylase_value', 'F', 0, 365, 20, 95, 'U/L', None, 300),
        ('amylase_value', 'F', 365, 6570, 25, 95, 'U/L', None, 300),
        ('amylase_value', 'F', 6570, 25550, 25, 115, 'U/L', None, 300),
        
        # Lipase - add sex-specific
        ('lipase_value', 'M', 0, 365, 2, 35, 'U/L', None, 100),
        ('lipase_value', 'M', 365, 6570, 3, 40, 'U/L', None, 100),
        ('lipase_value', 'M', 6570, 25550, 3, 60, 'U/L', None, 100),
        ('lipase_value', 'F', 0, 365, 2, 32, 'U/L', None, 100),
        ('lipase_value', 'F', 365, 6570, 3, 38, 'U/L', None, 100),
        ('lipase_value', 'F', 6570, 25550, 3, 55, 'U/L', None, 100),
        
        # LDH - add sex-specific
        ('ldh_value', 'M', 0, 365, 150, 400, 'U/L', None, 600),
        ('ldh_value', 'M', 365, 6570, 140, 350, 'U/L', None, 500),
        ('ldh_value', 'M', 6570, 25550, 140, 280, 'U/L', None, 500),
        ('ldh_value', 'F', 0, 365, 160, 420, 'U/L', None, 600),
        ('ldh_value', 'F', 365, 6570, 150, 370, 'U/L', None, 500),
        ('ldh_value', 'F', 6570, 25550, 150, 300, 'U/L', None, 500),
        
        # Calcium - add pediatric ranges
        ('calcium_value', 'ANY', 0, 28, 7.0, 12.0, 'mg/dL', 6.0, 14.0),
        ('calcium_value', 'ANY', 28, 365, 8.5, 11.5, 'mg/dL', 7.0, 13.0),
        ('calcium_value', 'ANY', 365, 6570, 8.8, 10.8, 'mg/dL', 7.5, 12.0),
        ('calcium_value', 'ANY', 6570, 25550, 8.5, 10.5, 'mg/dL', 7.0, 12.0),
        
        # Magnesium - add pediatric ranges
        ('magnesium_value', 'ANY', 0, 365, 1.5, 2.5, 'mg/dL', 1.0, 3.5),
        ('magnesium_value', 'ANY', 365, 6570, 1.7, 2.3, 'mg/dL', 1.2, 3.0),
        ('magnesium_value', 'ANY', 6570, 25550, 1.5, 2.5, 'mg/dL', 1.0, 3.5),
        
        # Phosphate - add pediatric ranges
        ('phosphate_value', 'ANY', 0, 28, 3.5, 8.0, 'mg/dL', 2.5, 10.0),
        ('phosphate_value', 'ANY', 28, 365, 4.0, 7.0, 'mg/dL', 3.0, 9.0),
        ('phosphate_value', 'ANY', 365, 6570, 3.5, 6.5, 'mg/dL', 2.5, 8.0),
        ('phosphate_value', 'ANY', 6570, 25550, 2.5, 4.5, 'mg/dL', 1.5, 6.0),
        
        # BNP - add pediatric ranges
        ('bnp_value', 'ANY', 0, 365, 0, 250, 'pg/mL', None, 500),
        ('bnp_value', 'ANY', 365, 6570, 0, 150, 'pg/mL', None, 300),
        ('bnp_value', 'ANY', 6570, 18250, 0, 100, 'pg/mL', None, 250),
        ('bnp_value', 'ANY', 18250, 36500, 0, 150, 'pg/mL', None, 300),
        
        # Uric Acid - add pediatric ranges
        ('uric_acid_value', 'M', 0, 365, 2.0, 6.0, 'mg/dL', None, None),
        ('uric_acid_value', 'M', 365, 6570, 2.5, 7.0, 'mg/dL', None, None),
        ('uric_acid_value', 'M', 6570, 25550, 3.5, 7.2, 'mg/dL', None, None),
        ('uric_acid_value', 'F', 0, 365, 2.0, 5.5, 'mg/dL', None, None),
        ('uric_acid_value', 'F', 365, 6570, 2.5, 6.5, 'mg/dL', None, None),
        ('uric_acid_value', 'F', 6570, 25550, 2.4, 6.0, 'mg/dL', None, None),
    ]
    
    with engine.connect() as conn:
        for range_data in additional_ranges:
            field_code = range_data[0]
            sex = range_data[1]
            age_min = range_data[2]
            age_max = range_data[3]
            low = range_data[4]
            high = range_data[5]
            unit = range_data[6]
            critical_low = range_data[7]
            critical_high = range_data[8]
            
            try:
                conn.execute(text("""
                    INSERT INTO lab_reference_ranges 
                    (field_code, sex, age_min_days, age_max_days, low, high, unit, critical_low, critical_high)
                    VALUES (:field_code, :sex, :age_min, :age_max, :low, :high, :unit, :critical_low, :critical_high)
                    ON CONFLICT DO NOTHING
                """), {
                    'field_code': field_code,
                    'sex': sex,
                    'age_min': age_min,
                    'age_max': age_max,
                    'low': low,
                    'high': high,
                    'unit': unit,
                    'critical_low': critical_low,
                    'critical_high': critical_high
                })
                print(f"  ✓ Added {field_code} ({sex}, {age_min}-{age_max} days)")
            except Exception as e:
                print(f"  ✗ Error adding {field_code}: {e}")
        
        conn.commit()
    
    print("\nDone adding age/sex specific ranges!")


def main():
    print("="*60)
    print("LAB CATALOG FIX SCRIPT")
    print("="*60)
    
    # Step 1: Link orphaned tests to templates
    link_tests_to_templates()
    
    # Step 2: Add missing reference ranges
    add_missing_reference_ranges()
    
    # Step 3: Add age/sex specific ranges
    add_age_sex_specific_ranges()
    
    print("\n" + "="*60)
    print("ALL FIXES COMPLETED!")
    print("="*60)
    print("\nPlease verify the changes by running the audit again.")


if __name__ == "__main__":
    main()
