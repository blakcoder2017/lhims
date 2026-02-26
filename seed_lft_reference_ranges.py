#!/usr/bin/env python3
"""
Fix LFT Reference Ranges for Ghana Hospital EMR
================================================
Issues identified:
1. Bilirubin unit mismatch - indirect uses mg/dL but template uses μmol/L
2. Missing pediatric ranges for ALT, AST, GGT
3. Missing sex-specific ranges for bilirubin
4. Duplicates with conflicting units

All operations are idempotent (safe to re-run).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')

# LFT Reference Ranges to add/update
# Ghana/West African standards

LFT_RANGES = [
    # ===== ALT (Alanine Aminotransferase) =====
    # Adult: Male 0-40 U/L, Female 0-32 U/L
    # Pediatric (Ghana standard):
    ('alt', 'M', 0, 365, 0, 40, 'U/L', None, 500),
    ('alt', 'M', 365, 2190, 0, 35, 'U/L', None, 400),
    ('alt', 'M', 2190, 6570, 0, 40, 'U/L', None, 500),
    ('alt', 'M', 6570, 25550, 0, 40, 'U/L', None, 500),
    ('alt', 'F', 0, 365, 0, 35, 'U/L', None, 400),
    ('alt', 'F', 365, 2190, 0, 30, 'U/L', None, 400),
    ('alt', 'F', 2190, 6570, 0, 35, 'U/L', None, 400),
    ('alt', 'F', 6570, 25550, 0, 32, 'U/L', None, 500),
    
    # ===== AST (Aspartate Aminotransferase) =====
    # Adult: Male 0-37 U/L, Female 0-31 U/L
    ('ast', 'M', 0, 365, 0, 50, 'U/L', None, 500),
    ('ast', 'M', 365, 2190, 0, 45, 'U/L', None, 500),
    ('ast', 'M', 2190, 6570, 0, 40, 'U/L', None, 500),
    ('ast', 'M', 6570, 25550, 0, 37, 'U/L', None, 500),
    ('ast', 'F', 0, 365, 0, 45, 'U/L', None, 500),
    ('ast', 'F', 365, 2190, 0, 40, 'U/L', None, 500),
    ('ast', 'F', 2190, 6570, 0, 35, 'U/L', None, 500),
    ('ast', 'F', 6570, 25550, 0, 31, 'U/L', None, 500),
    
    # ===== GGT (Gamma-Glutamyl Transferase) =====
    # Adult: Male 0-55 U/L, Female 0-38 U/L
    ('ggt', 'M', 0, 365, 0, 80, 'U/L', None, None),
    ('ggt', 'M', 365, 6570, 0, 60, 'U/L', None, None),
    ('ggt', 'M', 6570, 25550, 0, 55, 'U/L', None, None),
    ('ggt', 'F', 0, 365, 0, 70, 'U/L', None, None),
    ('ggt', 'F', 365, 6570, 0, 50, 'U/L', None, None),
    ('ggt', 'F', 6570, 25550, 0, 38, 'U/L', None, None),
    
    # ===== ALP (Alkaline Phosphatase) =====
    # Already has ranges but let's add more age groups
    ('alp', 'ANY', 0, 365, 150, 500, 'U/L', None, 800),
    
    # ===== Total Bilirubin =====
    # Adult: 3.4-20.5 μmol/L (0.2-1.2 mg/dL)
    # Neonates: higher (physiological jaundice)
    ('total_bilirubin', 'ANY', 0, 28, 10, 200, 'μmol/L', None, 250),
    ('total_bilirubin', 'ANY', 28, 365, 3.4, 20.5, 'μmol/L', None, 50),
    ('total_bilirubin', 'ANY', 365, 6570, 3.4, 20.5, 'μmol/L', None, 50),
    ('total_bilirubin', 'ANY', 6570, 25550, 3.4, 20.5, 'μmol/L', None, 50),
    
    # ===== Direct Bilirubin =====
    # Adult: 0-8.6 μmol/L (0-0.5 mg/dL)
    ('direct_bilirubin', 'ANY', 0, 28, 1, 10, 'μmol/L', None, 20),
    ('direct_bilirubin', 'ANY', 28, 365, 0, 8.6, 'μmol/L', None, 20),
    ('direct_bilirubin', 'ANY', 365, 6570, 0, 8.6, 'μmol/L', None, 20),
    ('direct_bilirubin', 'ANY', 6570, 25550, 0, 8.6, 'μmol/L', None, 20),
    
    # ===== Indirect Bilirubin (in μmol/L) =====
    # Total - Direct = Indirect
    # 3.4-20.5 - 0-8.6 = ~3.4-20 μmol/L (0.2-1.2 mg/dL)
    # mg/dL × 17.1 = μmol/L
    ('indirect_bilirubin', 'ANY', 0, 28, 5, 150, 'μmol/L', None, 200),
    ('indirect_bilirubin', 'ANY', 28, 365, 3.4, 17, 'μmol/L', None, 40),
    ('indirect_bilirubin', 'ANY', 365, 6570, 3.4, 17, 'μmol/L', None, 40),
    ('indirect_bilirubin', 'ANY', 6570, 25550, 3.4, 17, 'μmol/L', None, 40),
    
    # ===== Total Protein =====
    # Already has g/dL ranges - let's ensure consistent
    ('total_protein', 'ANY', 0, 365, 4.5, 7.5, 'g/dL', 3.5, None),
    ('total_protein', 'ANY', 365, 6570, 5.5, 8.0, 'g/dL', 4.0, None),
    ('total_protein', 'ANY', 6570, 25550, 6.0, 8.3, 'g/dL', 5.0, None),
    
    # ===== Albumin =====
    # Adult: 35-50 g/L (3.5-5.0 g/dL)
    # Neonates: lower
    ('albumin', 'ANY', 0, 365, 25, 45, 'g/L', 15, None),
    ('albumin', 'ANY', 365, 6570, 30, 48, 'g/L', 20, None),
    ('albumin', 'ANY', 6570, 25550, 35, 50, 'g/L', 25, None),
    
    # ===== LDH (Lactate Dehydrogenase) =====
    # Added for completeness - often included in LFT
    ('ldh', 'ANY', 0, 365, 150, 400, 'U/L', None, 600),
    ('ldh', 'ANY', 365, 6570, 140, 350, 'U/L', None, 500),
    ('ldh', 'ANY', 6570, 25550, 140, 280, 'U/L', None, 500),
]


def fix_lft_ranges():
    """Fix LFT reference ranges."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        inserted_count = 0
        skipped_count = 0
        
        for (field_code, sex, age_min, age_max, low, high, unit, crit_low, crit_high) in LFT_RANGES:
            # Check if this exact range exists
            check = conn.execute(text(f"""
                SELECT id FROM lab_reference_ranges 
                WHERE field_code = '{field_code}' 
                AND sex = '{sex}'
                AND age_min_days = {age_min}
                AND age_max_days = {age_max}
                AND unit = '{unit}'
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
            print(f"  Added: {field_code} ({sex}) age {age_min}-{age_max}d: {low}-{high} {unit}")
        
        conn.commit()
    
    return inserted_count, skipped_count


def main():
    print("=" * 60)
    print("Fixing LFT Reference Ranges for Ghana Hospital EMR")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL}")
    
    inserted, skipped = fix_lft_ranges()
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETED:")
    print(f"  - Inserted: {inserted} new LFT reference ranges")
    print(f"  - Skipped (already exist): {skipped}")
    print(f"{'=' * 60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
