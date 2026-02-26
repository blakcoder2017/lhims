#!/usr/bin/env python3
"""
Add Missing Reference Ranges for Ghana Hospital EMR
=====================================================
This script adds the 28 missing reference ranges identified:
- Fluid analysis (ascitic, pleural, CSF)
- Viral loads (HIV, HBV, HCV)
- Hormones (AFP, β-HCG, DHEA, GH)
- Other biochemistry (globulin, indirect bilirubin, CD4%, RA factor, troponin quant)

All ranges use Ghana/West African standards where applicable.
All operations are idempotent (safe to re-run).
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')

# Reference ranges to add - using Ghana/West African standards
# Format: (field_code, sex, age_min_days, age_max_days, low, high, unit, critical_low, critical_high)

REFERENCE_RANGES = [
    # ===== AFP (Alpha-fetoprotein) - tumor marker =====
    # Adult reference range: 0-10 ng/mL (some sources up to 15)
    ('afp_value', 'ANY', 6570, 25550, 0, 10, 'ng/mL', None, 500),
    
    # ===== ASCITIC FLUID ANALYSIS =====
    # Ascitic fluid is abnormal accumulation of fluid in peritoneal cavity
    # Glucose: similar to blood glucose (70-100 mg/dL)
    ('ascitic_glucose', 'ANY', 0, 25550, 70, 100, 'mg/dL', 40, None),
    # Protein: <2.5 g/dL = transudate, >2.5 g/dL = exudate
    ('ascitic_protein', 'ANY', 0, 25550, 0, 2.5, 'g/dL', None, None),
    # WBC: <250 cells/μL normal, >250 suggests SBP
    ('ascitic_wbc', 'ANY', 0, 25550, 0, 250, 'cells/μL', None, 1000),
    # RBC: normally 0, blood indicates traumatic tap
    ('ascitic_rbc', 'ANY', 0, 25550, 0, 10, 'cells/μL', None, None),
    # Lymphocytes: predominance suggests TB/peritoneal carcinomatosis
    ('ascitic_lymphocytes', 'ANY', 0, 25550, 0, 70, '%', None, None),
    
    # ===== PLEURAL FLUID ANALYSIS =====
    # Glucose: similar to blood (70-100 mg/dL)
    ('pleural_glucose', 'ANY', 0, 25550, 70, 100, 'mg/dL', 40, None),
    # Protein: <3 g/dL = transudate, >3 g/dL = exudate
    ('pleural_protein', 'ANY', 0, 25550, 0, 3, 'g/dL', None, None),
    # WBC: <1000 cells/μL normal
    ('pleural_wbc', 'ANY', 0, 25550, 0, 1000, 'cells/μL', None, None),
    # RBC: normally 0
    ('pleural_rbc', 'ANY', 0, 25550, 0, 10, 'cells/μL', None, None),
    
    # ===== CSF (Cerebrospinal Fluid) ANALYSIS =====
    # Glucose: 45-80 mg/dL (about 60% of blood glucose)
    ('csf_glucose', 'ANY', 0, 25550, 45, 80, 'mg/dL', 30, None),
    # Protein: 15-45 mg/dL (adults), higher in children
    ('csf_protein', 'ANY', 0, 365, 15, 100, 'mg/dL', None, 150),
    ('csf_protein', 'ANY', 365, 6570, 15, 60, 'mg/dL', None, 100),
    ('csf_protein', 'ANY', 6570, 25550, 15, 45, 'mg/dL', None, 100),
    # WBC: 0-5 cells/μL (adults), 0-10 (children)
    ('csf_wbc', 'ANY', 0, 365, 0, 10, 'cells/μL', None, 100),
    ('csf_wbc', 'ANY', 365, 6570, 0, 5, 'cells/μL', None, 50),
    ('csf_wbc', 'ANY', 6570, 25550, 0, 5, 'cells/μL', None, 50),
    # RBC: normally 0
    ('csf_rbc', 'ANY', 0, 25550, 0, 0, 'cells/μL', None, None),
    # Lymphocytes: 0-40% of WBC (normal)
    ('csf_lymphocytes', 'ANY', 0, 25550, 0, 40, '%', None, None),
    # Neutrophils: 0-5% (should be minimal)
    ('csf_neutrophils', 'ANY', 0, 25550, 0, 5, '%', None, 50),
    
    # ===== β-HCG (Beta Human Chorionic Gonadotropin) =====
    # Male: <5 IU/L (undetectable)
    ('bhcg_value', 'M', 6570, 25550, 0, 5, 'IU/L', None, None),
    # Non-pregnant female: <5 IU/L
    ('bhcg_value', 'F', 6570, 25550, 0, 5, 'IU/L', None, None),
    # Pregnancy ranges (for reference - first trimester rises)
    # Note: In practice, positive = pregnant, negative = not
    
    # ===== CD4 COUNT & PERCENTAGE =====
    # CD4 Count: cells/μL
    # Adult normal: 500-1500 cells/μL
    # HIV staging: <200 = AIDS, 200-350 = moderate, 350-500 = early, >500 = normal
    ('cd4_count', 'ANY', 6570, 25550, 500, 1500, 'cells/μL', 200, None),
    # Pediatric CD4 counts differ by age
    ('cd4_count', 'ANY', 365, 730, 1000, 3000, 'cells/μL', 750, None),  # 1-2 years
    ('cd4_count', 'ANY', 730, 2190, 500, 1500, 'cells/μL', 350, None),  # 2-6 years
    ('cd4_count', 'ANY', 2190, 6570, 300, 1200, 'cells/μL', 200, None),  # 6-18 years
    # CD4 Percentage: 30-60% of total lymphocytes (more stable marker)
    ('cd4_percentage', 'ANY', 0, 365, 25, 65, '%', 15, None),  # <1 year
    ('cd4_percentage', 'ANY', 365, 25550, 30, 60, '%', 15, None),  # >1 year
    
    # ===== DHEA (Dehydroepiandrosterone) =====
    # Adult male: 1800-8000 ng/dL
    ('dhea_value', 'M', 6570, 25550, 1800, 8000, 'ng/dL', None, None),
    # Adult female: 1000-6000 ng/dL
    ('dhea_value', 'F', 6570, 25550, 1000, 6000, 'ng/dL', None, None),
    # Children (decline with age): use lower ranges
    
    # ===== Growth Hormone (GH) =====
    # Fasting: <5 ng/mL (some sources <10)
    # GH varies significantly by age, sex, and time of day
    ('gh_value', 'M', 6570, 25550, 0, 5, 'ng/mL', None, None),
    ('gh_value', 'F', 6570, 25550, 0, 5, 'ng/mL', None, None),
    # Children: higher normal ranges
    
    # ===== Globulin (Total Protein - Albumin calculation) =====
    # Total globulin = Total protein - Albumin
    # Normal: 2-3.5 g/dL (some sources 2.5-3.5)
    ('globulin', 'ANY', 0, 365, 1.5, 3.5, 'g/dL', None, None),
    ('globulin', 'ANY', 365, 6570, 2.0, 3.5, 'g/dL', None, None),
    ('globulin', 'ANY', 6570, 25550, 2.0, 3.5, 'g/dL', None, None),
    
    # ===== Indirect Bilirubin =====
    # Total bilirubin - Direct bilirubin
    # Normal: 0.2-1.0 mg/dL (some sources up to 1.2)
    ('indirect_bilirubin', 'ANY', 0, 365, 0.2, 1.2, 'mg/dL', None, None),
    ('indirect_bilirubin', 'ANY', 365, 25550, 0.2, 1.0, 'mg/dL', None, None),
    
    # ===== VIRAL LOAD TESTS =====
    # HIV Viral Load
    # Undetectable: <20 copies/mL (or <50 depending on assay)
    # Log value is log10
    ('hiv_vl_value', 'ANY', 0, 25550, 0, 20, 'copies/mL', None, None),
    ('hiv_vl_log', 'ANY', 0, 25550, 0, 1.7, 'log10', None, None),  # log10(50) ≈ 1.7
    
    # HBV Viral Load
    # Undetectable: <10 IU/mL (some assays <20)
    ('hbv_vl_value', 'ANY', 0, 25550, 0, 10, 'IU/mL', None, None),
    
    # HCV Viral Load  
    # Undetectable: <15 IU/mL
    ('hcv_vl_value', 'ANY', 0, 25550, 0, 15, 'IU/mL', None, None),
    
    # ===== Rheumatoid Factor (RA Factor) =====
    # Negative: <20 IU/mL (some labs <14)
    # Positive: >20 IU/mL (moderate 20-40, high >40)
    ('ra_titer', 'ANY', 0, 25550, 0, 20, 'IU/mL', None, None),
    
    # ===== Troponin (Quantitative) =====
    # Troponin I: <0.04 ng/mL normal (some <0.03)
    # Troponin T: <0.01 ng/mL normal
    # Both indicate myocardial infarction when elevated
    ('troponin_quant', 'ANY', 0, 25550, 0, 0.04, 'ng/mL', None, 0.5),  # Critical high = MI
]


def insert_reference_ranges():
    """Insert missing reference ranges into the database."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check existing ranges
        result = conn.execute(text("SELECT field_code FROM lab_reference_ranges LIMIT 1"))
        existing_codes = set()
        result = conn.execute(text("SELECT DISTINCT field_code FROM lab_reference_ranges"))
        for row in result:
            existing_codes.add(row[0])
        
        inserted_count = 0
        skipped_count = 0
        
        for (field_code, sex, age_min, age_max, low, high, unit, crit_low, crit_high) in REFERENCE_RANGES:
            # Skip if range already exists for this field_code + sex + age combo
            check = conn.execute(text(f"""
                SELECT id FROM lab_reference_ranges 
                WHERE field_code = '{field_code}' 
                AND sex = '{sex}'
                AND age_min_days = {age_min}
                AND age_max_days = {age_max}
            """))
            if check.fetchone():
                skipped_count += 1
                continue
            
            # Insert the new range
            conn.execute(text(f"""
                INSERT INTO lab_reference_ranges 
                (field_code, sex, age_min_days, age_max_days, low, high, unit, 
                 critical_low, critical_high, facility_id, created_at)
                VALUES 
                ('{field_code}', '{sex}', {age_min}, {age_max}, {low}, {high}, '{unit}',
                 {('NULL' if crit_low is None else crit_low)}, 
                 {('NULL' if crit_high is None else crit_high)},
                 1, NOW())
            """))
            inserted_count += 1
            print(f"  Added: {field_code} ({sex}) age {age_min}-{age_max} days: {low}-{high} {unit}")
        
        conn.commit()
    
    return inserted_count, skipped_count


def main():
    print("=" * 60)
    print("Adding Missing Reference Ranges for Ghana Hospital EMR")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL}")
    
    inserted, skipped = insert_reference_ranges()
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETED:")
    print(f"  - Inserted: {inserted} new reference ranges")
    print(f"  - Skipped (already exist): {skipped}")
    print(f"{'=' * 60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
