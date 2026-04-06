#!/usr/bin/env python3
"""
Seed LOINC codes for Ghana Laboratory Tests
============================================
This script populates common LOINC codes for Ghana lab tests.
Run this after running the migration to add loinc_code column.

Usage:
    python seed_loinc_codes.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')

# LOINC code mappings for Ghana lab tests
LOINC_MAPPINGS = [
    # Haematology
    ("Haemoglobin (Hb)", "718-7"),
    ("Hb", "718-7"),
    ("Hemoglobin", "718-7"),
    ("Full Blood Count", "58410-2"),  # FBC panel
    ("Complete Blood Count", "58410-2"),
    ("FBC", "58410-2"),
    ("CBC", "58410-2"),
    ("Hematocrit", "4544-3"),
    ("HCT", "4544-3"),
    ("Packed Cell Volume", "4544-3"),
    ("PCV", "4544-3"),
    ("WBC Count", "6690-2"),
    ("White Blood Cell", "6690-2"),
    ("Leukocyte Count", "6690-2"),
    ("RBC Count", "789-8"),
    ("Red Blood Cell", "789-8"),
    ("Erythrocyte Count", "789-8"),
    ("Platelet Count", "777-3"),
    ("Platelets", "777-3"),
    ("Thrombocyte Count", "777-3"),
    ("MCV", "787-2"),
    ("Mean Corpuscular Volume", "787-2"),
    ("MCH", "785-6"),
    ("Mean Corpuscular Hemoglobin", "785-6"),
    ("MCHC", "786-4"),
    ("Mean Corpuscular Hb Concentration", "786-4"),
    ("RDW", "788-6"),
    ("Red Cell Distribution Width", "788-6"),
    ("Neutrophils", "751-8"),
    ("Neutrophil Count", "751-8"),
    ("Lymphocytes", "731-0"),
    ("Lymphocyte Count", "731-0"),
    ("Monocytes", "742-4"),
    ("Monocyte Count", "742-4"),
    ("Eosinophils", "711-2"),
    ("Eosinophil Count", "711-2"),
    ("Basophils", "704-7"),
    ("Basophil Count", "704-7"),
    ("ESR", "30341-2"),
    ("Erythrocyte Sedimentation Rate", "30341-2"),
    ("PS", "595-4"),  # Parasite smear - not exact
    ("Malaria Parasite", "25131-0"),
    ("Blood Film", "10524-0"),
    
    # Liver Function Tests
    ("ALT", "1742-6"),
    ("Alanine Aminotransferase", "1742-6"),
    ("SGPT", "1742-6"),
    ("AST", "1920-8"),
    ("Aspartate Aminotransferase", "1920-8"),
    ("SGOT", "1920-8"),
    ("ALP", "2208-6"),
    ("Alkaline Phosphatase", "2208-6"),
    ("Total Bilirubin", "1975-2"),
    ("Bilirubin Total", "1975-2"),
    ("Direct Bilirubin", "1974-5"),
    ("Bilirubin Conjugated", "1974-5"),
    ("Indirect Bilirubin", "1971-1"),
    ("Total Protein", "2885-2"),
    ("TP", "2885-2"),
    ("Albumin", "1751-7"),
    ("ALB", "1751-7"),
    ("Globulin", "2339-8"),  # Calculated
    ("GGT", "2324-2"),
    ("Gamma GT", "2324-2"),
    ("Gamma-Glutamyltransferase", "2324-2"),
    
    # Kidney Function Tests
    ("Creatinine", "2160-0"),
    ("BUN", "3094-0"),
    ("Blood Urea Nitrogen", "3094-0"),
    ("Urea", "3094-0"),
    ("Uric Acid", "3084-1"),
    ("Sodium", "2951-2"),
    ("Na", "2951-2"),
    ("Potassium", "2823-3"),
    ("K", "2823-3"),
    ("Chloride", "2075-0"),
    ("Cl", "2075-0"),
    ("Bicarbonate", "1968-7"),
    ("HCO3", "1968-7"),
    ("CO2", "1968-7"),
    
    # Lipid Profile
    ("Total Cholesterol", "2093-3"),
    ("Cholesterol", "2093-3"),
    ("Triglycerides", "2571-8"),
    ("TG", "2571-8"),
    ("HDL Cholesterol", "2085-9"),
    ("HDL", "2085-9"),
    ("LDL Cholesterol", "2089-1"),
    ("LDL", "2089-1"),
    ("VLDL", "13457-5"),
    
    # Glucose & Diabetes
    ("Fasting Blood Glucose", "1558-6"),
    ("FBG", "1558-6"),
    ("Fasting Glucose", "1558-6"),
    ("Random Blood Glucose", "2345-7"),
    ("RBG", "2345-7"),
    ("Random Glucose", "2345-7"),
    ("HbA1c", "4548-4"),
    ("Glycated Hemoglobin", "4548-4"),
    ("HbA1", "4548-4"),
    ("2-Hour Postprandial", "15074-8"),
    ("2HPP", "15074-8"),
    
    # Thyroid Function Tests
    ("TSH", "3016-3"),
    ("Thyroid Stimulating Hormone", "3016-3"),
    ("Free T4", "3024-7"),
    ("Free Thyroxine", "3024-7"),
    ("FT4", "3024-7"),
    ("Free T3", "3043-7"),
    ("Free Triiodothyronine", "3043-7"),
    ("FT3", "3043-7"),
    ("Total T4", "3022-1"),
    ("Total Thyroxine", "3022-1"),
    ("TT4", "3022-1"),
    
    # Infectious Disease Serology
    ("HBsAg", "22322-1"),
    ("Hepatitis B Surface Antigen", "22322-1"),
    ("HBsAb", "22323-9"),
    ("Hepatitis B Surface Antibody", "22323-9"),
    ("HBcAb", "22324-7"),
    ("Hepatitis B Core Antibody", "22324-7"),
    ("Hepatitis C Antibody", "22326-2"),
    ("HCV", "22326-2"),
    ("HIV 1&2", "42717-5"),
    ("HIV", "42717-5"),
    ("HIV Screening", "42717-5"),
    ("VDRL", "4476-5"),
    ("Syphilis", "4476-5"),
    ("RPR", "4476-5"),
    ("TPHA", "4477-3"),
    ("Rubella IgG", "8014-5"),
    ("Rubella IgM", "8015-2"),
    ("Toxoplasma IgG", "8016-0"),
    ("Toxoplasma IgM", "8017-8"),
    ("CMV IgG", "8018-6"),
    ("CMV IgM", "8019-4"),
    
    # Urinalysis
    ("Urine Protein", "2888-6"),
    ("Protein (Urine)", "2888-6"),
    ("Urine Glucose", "25428-4"),
    ("Glucose (Urine)", "25428-4"),
    ("Urine Blood", "2335-8"),
    ("Blood (Urine)", "2335-8"),
    ("Urine Ketones", "2514-8"),
    ("Ketones (Urine)", "2514-8"),
    ("Urine pH", "2756-6"),
    ("pH (Urine)", "2756-6"),
    ("Urine Specific Gravity", "5817-6"),
    ("SG (Urine)", "5817-6"),
    ("Urine Nitrite", "2889-4"),
    ("Nitrite (Urine)", "2889-4"),
    ("Urine Leukocytes", "2890-2"),
    ("Leukocytes (Urine)", "2890-2"),
    ("Urine Bilirubin", "2336-6"),
    ("Bilirubin (Urine)", "2336-6"),
    ("Urine Urobilinogen", "20412-2"),
    ("Urobilinogen (Urine)", "20412-2"),
    
    # CSF Analysis
    ("CSF Cell Count", "594-7"),
    ("CSF WBC", "595-4"),
    ("CSF Protein", "2339-0"),
    ("Protein (CSF)", "2339-0"),
    ("CSF Glucose", "2827-4"),
    ("Glucose (CSF)", "2827-4"),
    ("CSF Opening Pressure", "2650-8"),
    
    # Pregnancy Tests
    ("Pregnancy Test", "2118-7"),
    ("Beta HCG", "2118-7"),
    ("hCG", "2118-7"),
    ("Quantitative Beta HCG", "19185-6"),
    
    # Tumor Markers
    ("AFP", "4274-5"),
    ("Alpha Fetoprotein", "4274-5"),
    ("CEA", "2039-7"),
    ("Carcinoembryonic Antigen", "2039-7"),
    ("PSA", "29271-1"),
    ("Prostate Specific Antigen", "29271-1"),
    ("Free PSA", "10830-9"),
    
    # Inflammatory Markers
    ("CRP", "1988-5"),
    ("C-Reactive Protein", "1988-5"),
    ("ESR", "30341-2"),
    ("Erythrocyte Sedimentation Rate", "30341-2"),
    ("Rheumatoid Factor", "2410-6"),
    ("RF", "2410-6"),
    ("ASO Titer", "26760-4"),
    ("ASO", "26760-4"),
    
    # Electrolytes
    ("Ionized Calcium", "1994-3"),
    ("iCa", "1994-3"),
    ("Total Calcium", "17861-6"),
    ("Ca", "17861-6"),
    ("Magnesium", "2601-7"),
    ("Mg", "2601-7"),
    ("Phosphate", "2777-1"),
    ("PO4", "2777-1"),
    ("Phosphorus", "2777-1"),
    
    # Iron Studies
    ("Serum Iron", "2498-4"),
    ("Iron", "2498-4"),
    ("Ferritin", "2278-4"),
    ("TIBC", "2587-6"),
    ("Total Iron Binding Capacity", "2587-6"),
    ("Transferrin Saturation", "35094-1"),
]


def seed_loinc_codes():
    """Seed LOINC codes to lab_tests table"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    updated_count = 0
    not_found_count = 0
    
    for test_name, loinc_code in LOINC_MAPPINGS:
        # Find test by name
        result = session.execute(
            text(f"UPDATE lab_tests SET loinc_code = '{loinc_code}' "
                 f"WHERE (test_name ILIKE '%{test_name}%' OR test_name = '{test_name}') "
                 f"AND (loinc_code IS NULL OR loinc_code = '') "
                 f"RETURNING id")
        )
        
        # Check if any row was updated
        rows = result.fetchall()
        if rows:
            updated_count += 1
            print(f"✓ Updated: {test_name} -> {loinc_code}")
        else:
            not_found_count += 1
            print(f"✗ Not found: {test_name}")
    
    session.commit()
    session.close()
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Updated: {updated_count}")
    print(f"  Not found: {not_found_count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    seed_loinc_codes()
