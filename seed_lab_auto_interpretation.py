#!/usr/bin/env python3
"""
Lab Auto-Interpretation Rules
=============================
This script adds rules to automatically interpret lab results based on values.
For example: "Possible anemia" if Hb is below normal.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')


# Auto-interpretation rules
RULES = [
    # HAEMATOLOGY
    ("hb_value", "low", "Possible anemia - requires clinical correlation", "warning"),
    ("hb_value", "critical_low", "Severe anemia - urgent clinical review required", "critical"),
    ("hb_value", "high", "Possible polycythemia - investigate cause", "warning"),
    
    ("wbc_count", "low", "Leukopenia - increased infection risk", "warning"),
    ("wbc_count", "high", "Leukocytosis - likely infection or inflammation", "warning"),
    ("wbc_count", "critical_high", "Severe leukocytosis - urgent review needed", "critical"),
    
    ("platelet_count", "low", "Thrombocytopenia - bleeding risk", "warning"),
    ("platelet_count", "critical_low", "Severe thrombocytopenia - bleeding risk", "critical"),
    
    # LIVER
    ("alt", "high", "Liver cell damage - hepatitis, drugs, alcohol", "warning"),
    ("alt", "critical_high", "Severe liver injury - urgent review", "critical"),
    ("ast", "high", "Liver or muscle damage", "warning"),
    ("total_bilirubin", "high", "Jaundice - investigate cause", "warning"),
    ("total_bilirubin", "critical_high", "Severe jaundice - urgent management", "critical"),
    
    # RENAL
    ("creatinine", "high", "Renal impairment - acute or chronic kidney disease", "warning"),
    ("creatinine", "critical_high", "Acute kidney injury - urgent management", "critical"),
    ("urea", "high", "Renal impairment or dehydration", "warning"),
    
    # GLUCOSE
    ("glucose_value", "high", "Hyperglycemia - possible diabetes", "warning"),
    ("glucose_value", "critical_high", "Diabetic emergency - possible DKA/HHS", "critical"),
    ("glucose_value", "low", "Hypoglycemia", "warning"),
    ("glucose_value", "critical_low", "Severe hypoglycemia - medical emergency", "critical"),
    ("hba1c_value", "high", "Poor glycemic control - diabetes", "warning"),
    
    # LIPIDS
    ("total_cholesterol", "high", "Hypercholesterolemia - cardiovascular risk", "info"),
    ("ldl_cholesterol", "high", "High LDL - increased CV risk", "warning"),
    ("hdl_cholesterol", "low", "Low HDL - increased CV risk", "info"),
    ("triglycerides", "high", "Hypertriglyceridemia - pancreatitis risk", "warning"),
    
    # THYROID
    ("tsh", "high", "Hypothyroidism - primary", "warning"),
    ("tsh", "low", "Hyperthyroidism", "warning"),
    
    # CARDIAC
    ("troponin_quant", "high", "Myocardial infarction - urgent management", "critical"),
    ("ck_value", "high", "Muscle damage - cardiac or skeletal", "warning"),
    ("ckmb_value", "high", "Myocardial injury", "critical"),
    
    # ELECTROLYTES
    ("sodium", "low", "Hyponatremia - causes many", "warning"),
    ("sodium", "critical_low", "Severe hyponatremia - neurological risk", "critical"),
    ("sodium", "high", "Hypernatremia - dehydration", "warning"),
    ("potassium", "low", "Hypokalemia - cardiac risk", "warning"),
    ("potassium", "critical_low", "Severe hypokalemia - arrhythmia risk", "critical"),
    ("potassium", "high", "Hyperkalemia - cardiac risk", "warning"),
    ("potassium", "critical_high", "Severe hyperkalemia - arrhythmia risk", "critical"),
    
    # INFECTIOUS
    ("cd4_count", "low", "Advanced immunosuppression", "warning"),
    ("cd4_count", "critical_low", "Severe immunosuppression - AIDS", "critical"),
    ("hiv_vl_value", "high", "High viral load - uncontrolled HIV", "warning"),
]


def main():
    print("=" * 70)
    print("Lab Auto-Interpretation Rules")
    print("=" * 70)
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Create table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lab_interpretation_rules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                field_code VARCHAR(100) NOT NULL,
                condition VARCHAR(50) NOT NULL,
                interpretation TEXT NOT NULL,
                severity VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("  Table created/verified")
        
        # Insert rules
        inserted = 0
        for field_code, condition, interpretation, severity in RULES:
            check = conn.execute(text("""
                SELECT id FROM lab_interpretation_rules 
                WHERE field_code = :fc AND condition = :cond
            """), {"fc": field_code, "cond": condition})
            
            if not check.fetchone():
                conn.execute(text("""
                    INSERT INTO lab_interpretation_rules 
                    (field_code, condition, interpretation, severity)
                    VALUES (:fc, :cond, :interp, :sev)
                """), {"fc": field_code, "cond": condition, "interp": interpretation, "sev": severity})
                inserted += 1
        
        conn.commit()
    
    print(f"  Inserted: {inserted} rules")
    print("\n" + "=" * 70)
    print("COMPLETED")
    print("=" * 70)
    print("""
Auto-interpretation rules added for:
- Haematology (Hb, WBC, Platelets)
- Liver Function (ALT, AST, Bilirubin)
- Renal Function (Creatinine, Urea)
- Glucose/Diabetes
- Lipid Profile
- Thyroid (TSH)
- Cardiac (Troponin, CK, CK-MB)
- Electrolytes (Na, K)
- Infectious Disease (CD4, HIV VL)
    """)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
