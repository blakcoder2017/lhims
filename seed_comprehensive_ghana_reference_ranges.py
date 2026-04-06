#!/usr/bin/env python3
"""
Comprehensive Ghana Lab Reference Ranges - DHIMS2/GHS Standards
=================================================================
This script adds ALL reference ranges for Ghana Hospital EMR based on:
- Ghana Health Service (GHS) standards
- DHIMS2 lab test requirements
- West African clinical reference values

This is a PROACTIVE seed - it adds ranges BEFORE new templates need them,
so we don't have to update reference ranges every time a new template is added.

All operations are idempotent (safe to re-run).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')

# Comprehensive Ghana Lab Reference Ranges
# Format: (field_code, sex, age_min_days, age_max_days, low, high, unit, critical_low, critical_high)
# Age: 0=birth, 365=1yr, 6570=18yrs, 25550=70yrs

REFERENCE_RANGES = [
    # =========================================================================
    # HAEMATOLOGY - Full Blood Count (FBC)
    # =========================================================================
    
    # Haemoglobin (g/dL) - Ghana standard
    ('hb', 'M', 0, 28, 13.5, 23.5, 'g/dL', 7.0, None),
    ('hb', 'M', 28, 365, 9.5, 13.5, 'g/dL', 7.0, None),
    ('hb', 'M', 365, 2190, 10.5, 13.5, 'g/dL', 7.0, None),
    ('hb', 'M', 2190, 6570, 11.0, 14.5, 'g/dL', 7.0, None),
    ('hb', 'M', 6570, 25550, 13.0, 17.0, 'g/dL', 7.0, None),
    ('hb', 'F', 0, 28, 13.5, 23.5, 'g/dL', 7.0, None),
    ('hb', 'F', 28, 365, 9.5, 13.5, 'g/dL', 7.0, None),
    ('hb', 'F', 365, 2190, 10.5, 13.5, 'g/dL', 7.0, None),
    ('hb', 'F', 2190, 6570, 11.0, 14.0, 'g/dL', 7.0, None),
    ('hb', 'F', 6570, 25550, 12.0, 15.0, 'g/dL', 7.0, None),
    
    # Hb (alternative field code)
    ('hb_value', 'M', 0, 28, 13.5, 23.5, 'g/dL', 7.0, None),
    ('hb_value', 'M', 28, 365, 9.5, 13.5, 'g/dL', 7.0, None),
    ('hb_value', 'M', 365, 2190, 10.5, 13.5, 'g/dL', 7.0, None),
    ('hb_value', 'M', 2190, 6570, 11.0, 14.5, 'g/dL', 7.0, None),
    ('hb_value', 'M', 6570, 25550, 13.0, 17.0, 'g/dL', 7.0, None),
    ('hb_value', 'F', 0, 28, 13.5, 23.5, 'g/dL', 7.0, None),
    ('hb_value', 'F', 28, 365, 9.5, 13.5, 'g/dL', 7.0, None),
    ('hb_value', 'F', 365, 2190, 10.5, 13.5, 'g/dL', 7.0, None),
    ('hb_value', 'F', 2190, 6570, 11.0, 14.0, 'g/dL', 7.0, None),
    ('hb_value', 'F', 6570, 25550, 12.0, 15.0, 'g/dL', 7.0, None),
    
    # PCV/HCT (%)
    ('hct', 'M', 0, 28, 40, 68, '%', 25, None),
    ('hct', 'M', 28, 365, 28, 42, '%', 25, None),
    ('hct', 'M', 365, 6570, 30, 40, '%', 25, None),
    ('hct', 'M', 6570, 25550, 40, 52, '%', 25, None),
    ('hct', 'F', 0, 28, 40, 68, '%', 25, None),
    ('hct', 'F', 28, 365, 28, 42, '%', 25, None),
    ('hct', 'F', 365, 6570, 30, 40, '%', 25, None),
    ('hct', 'F', 6570, 25550, 36, 46, '%', 25, None),
    
    # RBC Count (×10¹²/L)
    ('rbc_count', 'M', 0, 28, 3.5, 6.5, 'x10^12/L', 2.5, None),
    ('rbc_count', 'M', 28, 365, 3.0, 5.0, 'x10^12/L', 2.5, None),
    ('rbc_count', 'M', 365, 6570, 3.5, 5.0, 'x10^12/L', 2.5, None),
    ('rbc_count', 'M', 6570, 25550, 4.2, 6.0, 'x10^12/L', 2.5, None),
    ('rbc_count', 'F', 0, 28, 3.5, 6.5, 'x10^12/L', 2.5, None),
    ('rbc_count', 'F', 28, 365, 3.0, 5.0, 'x10^12/L', 2.5, None),
    ('rbc_count', 'F', 365, 6570, 3.5, 5.0, 'x10^12/L', 2.5, None),
    ('rbc_count', 'F', 6570, 25550, 3.8, 5.2, 'x10^12/L', 2.5, None),
    
    # WBC Count (×10⁹/L)
    ('wbc_count', 'ANY', 0, 28, 6.0, 18.0, 'x10^9/L', 2.0, 30.0),
    ('wbc_count', 'ANY', 28, 365, 6.0, 15.0, 'x10^9/L', 2.0, 25.0),
    ('wbc_count', 'ANY', 365, 6570, 5.0, 12.0, 'x10^9/L', 2.0, 20.0),
    ('wbc_count', 'ANY', 6570, 25550, 4.0, 11.0, 'x10^9/L', 2.0, 20.0),
    
    # Platelet Count (×10⁹/L)
    ('platelet_count', 'ANY', 0, 28, 100, 400, 'x10^9/L', 50, 600),
    ('platelet_count', 'ANY', 28, 365, 150, 400, 'x10^9/L', 50, 600),
    ('platelet_count', 'ANY', 365, 6570, 150, 400, 'x10^9/L', 50, 600),
    ('platelet_count', 'ANY', 6570, 25550, 150, 400, 'x10^9/L', 50, 600),
    
    # MCV (fL)
    ('mcv', 'ANY', 0, 28, 70, 100, 'fL', 50, None),
    ('mcv', 'ANY', 28, 365, 70, 85, 'fL', 50, None),
    ('mcv', 'ANY', 365, 6570, 70, 85, 'fL', 50, None),
    ('mcv', 'ANY', 6570, 25550, 76, 96, 'fL', 50, None),
    
    # MCH (pg)
    ('mch', 'ANY', 0, 28, 25, 35, 'pg', 15, None),
    ('mch', 'ANY', 28, 365, 22, 30, 'pg', 15, None),
    ('mch', 'ANY', 365, 6570, 23, 31, 'pg', 15, None),
    ('mch', 'ANY', 6570, 25550, 26, 32, 'pg', 15, None),
    
    # MCHC (g/dL)
    ('mchc', 'ANY', 0, 28, 30, 36, 'g/dL', 20, None),
    ('mchc', 'ANY', 28, 365, 28, 34, 'g/dL', 20, None),
    ('mchc', 'ANY', 365, 6570, 30, 35, 'g/dL', 20, None),
    ('mchc', 'ANY', 6570, 25550, 32, 36, 'g/dL', 20, None),
    
    # Reticulocytes (%)
    ('retic', 'ANY', 0, 28, 2, 6, '%', 0.5, None),
    ('retic', 'ANY', 28, 365, 0.5, 3, '%', 0.5, None),
    ('retic', 'ANY', 365, 6570, 0.5, 2.5, '%', 0.5, None),
    ('retic', 'ANY', 6570, 25550, 0.5, 2.0, '%', 0.5, None),
    
    # Retic Count (alternative)
    ('retic_count', 'ANY', 0, 28, 2, 6, '%', 0.5, None),
    ('retic_count', 'ANY', 28, 365, 0.5, 3, '%', 0.5, None),
    ('retic_count', 'ANY', 365, 6570, 0.5, 2.5, '%', 0.5, None),
    ('retic_count', 'ANY', 6570, 25550, 0.5, 2.0, '%', 0.5, None),
    
    # Differential Count
    ('neutrophils', 'ANY', 0, 28, 30, 70, '%', 20, None),
    ('neutrophils', 'ANY', 28, 365, 20, 60, '%', 15, None),
    ('neutrophils', 'ANY', 365, 6570, 30, 60, '%', 15, None),
    ('neutrophils', 'ANY', 6570, 25550, 40, 70, '%', 20, None),
    
    ('lymphocytes', 'ANY', 0, 28, 20, 60, '%', 10, None),
    ('lymphocytes', 'ANY', 28, 365, 40, 80, '%', 15, None),
    ('lymphocytes', 'ANY', 365, 6570, 30, 60, '%', 15, None),
    ('lymphocytes', 'ANY', 6570, 25550, 20, 45, '%', 10, None),
    
    ('monocytes', 'ANY', 0, 25550, 2, 10, '%', 0, None),
    ('eosinophils', 'ANY', 0, 25550, 1, 6, '%', 0, None),
    ('basophils', 'ANY', 0, 25550, 0, 2, '%', 0, None),
    
    # =========================================================================
    # ESR (Erythrocyte Sedimentation Rate) - mm/hr
    # =========================================================================
    ('esr_value', 'M', 0, 365, 2, 20, 'mm/hr', None, None),
    ('esr_value', 'M', 365, 6570, 2, 15, 'mm/hr', None, None),
    ('esr_value', 'M', 6570, 25550, 2, 20, 'mm/hr', None, None),
    ('esr_value', 'F', 0, 365, 2, 20, 'mm/hr', None, None),
    ('esr_value', 'F', 365, 6570, 2, 20, 'mm/hr', None, None),
    ('esr_value', 'F', 6570, 25550, 2, 30, 'mm/hr', None, None),
    
    # =========================================================================
    # BIOCHEMISTRY - LIVER FUNCTION TESTS
    # =========================================================================
    
    # ALT (U/L)
    ('alt', 'M', 0, 365, 0, 40, 'U/L', None, 500),
    ('alt', 'M', 365, 2190, 0, 35, 'U/L', None, 400),
    ('alt', 'M', 2190, 6570, 0, 40, 'U/L', None, 500),
    ('alt', 'M', 6570, 25550, 0, 40, 'U/L', None, 500),
    ('alt', 'F', 0, 365, 0, 35, 'U/L', None, 400),
    ('alt', 'F', 365, 2190, 0, 30, 'U/L', None, 400),
    ('alt', 'F', 2190, 6570, 0, 35, 'U/L', None, 400),
    ('alt', 'F', 6570, 25550, 0, 32, 'U/L', None, 500),
    
    # AST (U/L)
    ('ast', 'M', 0, 365, 0, 50, 'U/L', None, 500),
    ('ast', 'M', 365, 2190, 0, 45, 'U/L', None, 500),
    ('ast', 'M', 2190, 6570, 0, 40, 'U/L', None, 500),
    ('ast', 'M', 6570, 25550, 0, 37, 'U/L', None, 500),
    ('ast', 'F', 0, 365, 0, 45, 'U/L', None, 500),
    ('ast', 'F', 365, 2190, 0, 40, 'U/L', None, 500),
    ('ast', 'F', 2190, 6570, 0, 35, 'U/L', None, 500),
    ('ast', 'F', 6570, 25550, 0, 31, 'U/L', None, 500),
    
    # ALP (U/L)
    ('alp', 'ANY', 0, 28, 100, 400, 'U/L', None, 800),
    ('alp', 'ANY', 28, 365, 150, 500, 'U/L', None, 800),
    ('alp', 'ANY', 365, 6570, 100, 350, 'U/L', None, 600),
    ('alp', 'ANY', 6570, 25550, 20, 140, 'U/L', None, 500),
    
    # GGT (U/L)
    ('ggt', 'M', 0, 365, 0, 80, 'U/L', None, None),
    ('ggt', 'M', 365, 6570, 0, 60, 'U/L', None, None),
    ('ggt', 'M', 6570, 25550, 0, 55, 'U/L', None, None),
    ('ggt', 'F', 0, 365, 0, 70, 'U/L', None, None),
    ('ggt', 'F', 365, 6570, 0, 50, 'U/L', None, None),
    ('ggt', 'F', 6570, 25550, 0, 38, 'U/L', None, None),
    
    # Total Bilirubin (μmol/L)
    ('total_bilirubin', 'ANY', 0, 28, 10, 200, 'μmol/L', None, 250),
    ('total_bilirubin', 'ANY', 28, 365, 3.4, 20.5, 'μmol/L', None, 50),
    ('total_bilirubin', 'ANY', 365, 6570, 3.4, 20.5, 'μmol/L', None, 50),
    ('total_bilirubin', 'ANY', 6570, 25550, 3.4, 20.5, 'μmol/L', None, 50),
    
    # Direct Bilirubin (μmol/L)
    ('direct_bilirubin', 'ANY', 0, 28, 1, 10, 'μmol/L', None, 20),
    ('direct_bilirubin', 'ANY', 28, 365, 0, 8.6, 'μmol/L', None, 20),
    ('direct_bilirubin', 'ANY', 365, 6570, 0, 8.6, 'μmol/L', None, 20),
    ('direct_bilirubin', 'ANY', 6570, 25550, 0, 8.6, 'μmol/L', None, 20),
    
    # Indirect Bilirubin (μmol/L)
    ('indirect_bilirubin', 'ANY', 0, 28, 5, 150, 'μmol/L', None, 200),
    ('indirect_bilirubin', 'ANY', 28, 365, 3.4, 17, 'μmol/L', None, 40),
    ('indirect_bilirubin', 'ANY', 365, 6570, 3.4, 17, 'μmol/L', None, 40),
    ('indirect_bilirubin', 'ANY', 6570, 25550, 3.4, 17, 'μmol/L', None, 40),
    
    # Total Protein (g/L)
    ('total_protein', 'ANY', 0, 365, 45, 75, 'g/L', 35, None),
    ('total_protein', 'ANY', 365, 6570, 55, 80, 'g/L', 40, None),
    ('total_protein', 'ANY', 6570, 25550, 60, 83, 'g/L', 50, None),
    
    # Albumin (g/L)
    ('albumin', 'ANY', 0, 365, 25, 45, 'g/L', 15, None),
    ('albumin', 'ANY', 365, 6570, 30, 48, 'g/L', 20, None),
    ('albumin', 'ANY', 6570, 25550, 35, 50, 'g/L', 25, None),
    
    # Globulin (g/L)
    ('globulin', 'ANY', 0, 365, 15, 35, 'g/L', None, None),
    ('globulin', 'ANY', 365, 6570, 20, 35, 'g/L', None, None),
    ('globulin', 'ANY', 6570, 25550, 20, 35, 'g/L', None, None),
    
    # LDH (U/L)
    ('ldh', 'ANY', 0, 365, 150, 400, 'U/L', None, 600),
    ('ldh', 'ANY', 365, 6570, 140, 350, 'U/L', None, 500),
    ('ldh', 'ANY', 6570, 25550, 140, 280, 'U/L', None, 500),
    ('ldh_value', 'ANY', 0, 365, 150, 400, 'U/L', None, 600),
    ('ldh_value', 'ANY', 365, 6570, 140, 350, 'U/L', None, 500),
    ('ldh_value', 'ANY', 6570, 25550, 140, 280, 'U/L', None, 500),
    
    # =========================================================================
    # RENAL FUNCTION TESTS
    # =========================================================================
    
    # Creatinine (μmol/L)
    ('creatinine', 'M', 0, 365, 18, 35, 'μmol/L', None, None),
    ('creatinine', 'M', 365, 6570, 18, 44, 'μmol/L', None, None),
    ('creatinine', 'M', 6570, 25550, 62, 115, 'μmol/L', None, 707),
    ('creatinine', 'F', 0, 365, 18, 35, 'μmol/L', None, None),
    ('creatinine', 'F', 365, 6570, 18, 44, 'μmol/L', None, None),
    ('creatinine', 'F', 6570, 25550, 44, 97, 'μmol/L', None, 707),
    
    # Creatinine Value (alternative)
    ('creatinine_value', 'M', 0, 365, 18, 35, 'μmol/L', None, None),
    ('creatinine_value', 'M', 365, 6570, 18, 44, 'μmol/L', None, None),
    ('creatinine_value', 'M', 6570, 25550, 62, 115, 'μmol/L', None, 707),
    ('creatinine_value', 'F', 0, 365, 18, 35, 'μmol/L', None, None),
    ('creatinine_value', 'F', 365, 6570, 18, 44, 'μmol/L', None, None),
    ('creatinine_value', 'F', 6570, 25550, 44, 97, 'μmol/L', None, 707),
    
    # Urea (mmol/L)
    ('urea', 'ANY', 0, 365, 1.8, 6.5, 'mmol/L', None, 35.7),
    ('urea', 'ANY', 365, 6570, 2.2, 7.0, 'mmol/L', None, 35.7),
    ('urea', 'ANY', 6570, 25550, 2.9, 8.2, 'mmol/L', None, 35.7),
    
    # Uric Acid (μmol/L)
    ('uric_acid', 'M', 0, 365, 100, 230, 'μmol/L', None, None),
    ('uric_acid', 'M', 365, 6570, 120, 350, 'μmol/L', None, None),
    ('uric_acid', 'M', 6570, 25550, 142, 339, 'μmol/L', None, None),
    ('uric_acid', 'F', 0, 365, 100, 230, 'μmol/L', None, None),
    ('uric_acid', 'F', 365, 6570, 120, 350, 'μmol/L', None, None),
    ('uric_acid', 'F', 6570, 25550, 202, 416, 'μmol/L', None, None),
    
    # Uric Acid Value (alternative)
    ('uric_acid_value', 'M', 0, 365, 100, 230, 'μmol/L', None, None),
    ('uric_acid_value', 'M', 365, 6570, 120, 350, 'μmol/L', None, None),
    ('uric_acid_value', 'M', 6570, 25550, 142, 339, 'μmol/L', None, None),
    ('uric_acid_value', 'F', 0, 365, 100, 230, 'μmol/L', None, None),
    ('uric_acid_value', 'F', 365, 6570, 120, 350, 'μmol/L', None, None),
    ('uric_acid_value', 'F', 6570, 25550, 202, 416, 'μmol/L', None, None),
    
    # eGFR (mL/min/1.73m²)
    ('gfr_value', 'ANY', 0, 365, 40, 120, 'mL/min/1.73m²', 15, None),
    ('gfr_value', 'ANY', 365, 6570, 60, 120, 'mL/min/1.73m²', 15, None),
    ('gfr_value', 'ANY', 6570, 25550, 90, 120, 'mL/min/1.73m²', 15, None),
    
    # eGFR (alternative field code)
    ('egfr', 'ANY', 0, 365, 40, 120, 'mL/min/1.73m²', 15, None),
    ('egfr', 'ANY', 365, 6570, 60, 120, 'mL/min/1.73m²', 15, None),
    ('egfr', 'ANY', 6570, 25550, 90, 120, 'mL/min/1.73m²', 15, None),
    
    # =========================================================================
    # ELECTROLYTES
    # =========================================================================
    
    # Sodium (mmol/L)
    ('sodium', 'ANY', 0, 365, 133, 145, 'mmol/L', 120, 155),
    ('sodium', 'ANY', 365, 6570, 136, 145, 'mmol/L', 120, 155),
    ('sodium', 'ANY', 6570, 25550, 136, 145, 'mmol/L', 120, 155),
    
    # Potassium (mmol/L)
    ('potassium', 'ANY', 0, 365, 3.5, 6.0, 'mmol/L', 2.5, 7.0),
    ('potassium', 'ANY', 365, 6570, 3.5, 5.5, 'mmol/L', 2.5, 7.0),
    ('potassium', 'ANY', 6570, 25550, 3.5, 5.0, 'mmol/L', 2.5, 7.0),
    
    # Chloride (mmol/L)
    ('chloride', 'ANY', 0, 365, 95, 110, 'mmol/L', 80, 120),
    ('chloride', 'ANY', 365, 6570, 96, 110, 'mmol/L', 80, 120),
    ('chloride', 'ANY', 6570, 25550, 98, 106, 'mmol/L', 80, 120),
    
    # Bicarbonate (mmol/L)
    ('bicarbonate', 'ANY', 0, 365, 18, 28, 'mmol/L', 10, 35),
    ('bicarbonate', 'ANY', 365, 6570, 20, 28, 'mmol/L', 10, 35),
    ('bicarbonate', 'ANY', 6570, 25550, 22, 28, 'mmol/L', 10, 35),
    
    # =========================================================================
    # GLUCOSE & DIABETES
    # =========================================================================
    
    # Fasting Blood Glucose (mmol/L)
    ('fasting_glucose', 'ANY', 0, 365, 2.8, 5.5, 'mmol/L', 1.7, 7.0),
    ('fasting_glucose', 'ANY', 365, 6570, 3.3, 5.5, 'mmol/L', 2.5, 7.0),
    ('fasting_glucose', 'ANY', 6570, 25550, 3.9, 5.8, 'mmol/L', 2.5, 7.0),
    
    # Glucose Value (for RBS/FBS)
    ('glucose_value', 'ANY', 0, 365, 2.8, 6.5, 'mmol/L', 1.7, 11.0),
    ('glucose_value', 'ANY', 365, 6570, 3.3, 6.5, 'mmol/L', 2.5, 11.0),
    ('glucose_value', 'ANY', 6570, 25550, 3.9, 6.1, 'mmol/L', 2.5, 11.0),
    
    # Glucose Random (alternative)
    ('glucose_random', 'ANY', 0, 365, 2.8, 7.0, 'mmol/L', 1.7, 11.0),
    ('glucose_random', 'ANY', 365, 6570, 3.3, 7.0, 'mmol/L', 2.5, 11.0),
    ('glucose_random', 'ANY', 6570, 25550, 3.9, 7.8, 'mmol/L', 2.5, 11.0),
    
    # 1 Hour Glucose (OGTT)
    ('1hr_glucose', 'ANY', 0, 365, 3.0, 8.0, 'mmol/L', None, 11.0),
    ('1hr_glucose', 'ANY', 365, 6570, 3.0, 8.0, 'mmol/L', None, 11.0),
    ('1hr_glucose', 'ANY', 6570, 25550, 3.9, 10.0, 'mmol/L', None, 11.0),
    
    # 2 Hour Glucose (OGTT)
    ('2hr_glucose', 'ANY', 0, 365, 3.0, 7.0, 'mmol/L', None, 11.0),
    ('2hr_glucose', 'ANY', 365, 6570, 3.0, 7.0, 'mmol/L', None, 11.0),
    ('2hr_glucose', 'ANY', 6570, 25550, 3.9, 7.8, 'mmol/L', None, 11.1),
    
    # HbA1c (%)
    ('hba1c_value', 'ANY', 0, 365, 4.0, 6.0, '%', None, 8.0),
    ('hba1c_value', 'ANY', 365, 6570, 4.0, 6.0, '%', None, 8.0),
    ('hba1c_value', 'ANY', 6570, 25550, 4.0, 5.6, '%', None, 8.0),
    
    # =========================================================================
    # LIPID PROFILE
    # =========================================================================
    
    # Total Cholesterol (mmol/L)
    ('total_cholesterol', 'ANY', 0, 365, 2.9, 5.2, 'mmol/L', None, 6.2),
    ('total_cholesterol', 'ANY', 365, 6570, 3.1, 5.2, 'mmol/L', None, 6.2),
    ('total_cholesterol', 'ANY', 6570, 25550, 3.0, 5.0, 'mmol/L', None, 6.2),
    
    # HDL Cholesterol (mmol/L)
    ('hdl_cholesterol', 'M', 0, 365, 0.8, 2.0, 'mmol/L', None, None),
    ('hdl_cholesterol', 'M', 365, 6570, 0.9, 2.0, 'mmol/L', None, None),
    ('hdl_cholesterol', 'M', 6570, 25550, 1.0, 2.0, 'mmol/L', None, None),
    ('hdl_cholesterol', 'F', 0, 365, 0.9, 2.2, 'mmol/L', None, None),
    ('hdl_cholesterol', 'F', 365, 6570, 1.0, 2.2, 'mmol/L', None, None),
    ('hdl_cholesterol', 'F', 6570, 25550, 1.2, 2.4, 'mmol/L', None, None),
    
    # LDL Cholesterol (mmol/L)
    ('ldl_cholesterol', 'ANY', 0, 365, 0, 3.4, 'mmol/L', None, 4.1),
    ('ldl_cholesterol', 'ANY', 365, 6570, 0, 3.4, 'mmol/L', None, 4.1),
    ('ldl_cholesterol', 'ANY', 6570, 25550, 0, 3.0, 'mmol/L', None, 4.1),
    
    # Triglycerides (mmol/L)
    ('triglycerides', 'M', 0, 365, 0.3, 1.5, 'mmol/L', None, 2.3),
    ('triglycerides', 'M', 365, 6570, 0.3, 1.5, 'mmol/L', None, 2.3),
    ('triglycerides', 'M', 6570, 25550, 0.4, 1.7, 'mmol/L', None, 2.3),
    ('triglycerides', 'F', 0, 365, 0.3, 1.5, 'mmol/L', None, 2.3),
    ('trlycerides', 'F', 365, 6570, 0.3, 1.5, 'mmol/L', None, 2.3),
    ('triglycerides', 'F', 6570, 25550, 0.4, 1.7, 'mmol/L', None, 2.3),
    
    # =========================================================================
    # THYROID FUNCTION TESTS
    # =========================================================================
    
    # TSH (mIU/L)
    ('tsh', 'ANY', 0, 28, 1.0, 39.0, 'mIU/L', 0.5, None),
    ('tsh', 'ANY', 28, 365, 1.0, 10.0, 'mIU/L', 0.5, None),
    ('tsh', 'ANY', 365, 2190, 0.7, 6.0, 'mIU/L', 0.5, None),
    ('tsh', 'ANY', 2190, 6570, 0.5, 5.0, 'mIU/L', 0.5, None),
    ('tsh', 'ANY', 6570, 25550, 0.4, 4.2, 'mIU/L', 0.5, 10.0),
    
    # TSH Value (alternative)
    ('tsh_value', 'ANY', 0, 28, 1.0, 39.0, 'mIU/L', 0.5, None),
    ('tsh_value', 'ANY', 28, 365, 1.0, 10.0, 'mIU/L', 0.5, None),
    ('tsh_value', 'ANY', 365, 2190, 0.7, 6.0, 'mIU/L', 0.5, None),
    ('tsh_value', 'ANY', 2190, 6570, 0.5, 5.0, 'mIU/L', 0.5, None),
    ('tsh_value', 'ANY', 6570, 25550, 0.4, 4.2, 'mIU/L', 0.5, 10.0),
    
    # Free T3 (pmol/L)
    ('ft3', 'ANY', 0, 365, 3.0, 8.0, 'pmol/L', None, None),
    ('ft3', 'ANY', 365, 6570, 3.5, 7.5, 'pmol/L', None, None),
    ('ft3', 'ANY', 6570, 25550, 4.0, 7.8, 'pmol/L', None, None),
    
    # FT3 Value (alternative)
    ('ft3_value', 'ANY', 0, 365, 3.0, 8.0, 'pmol/L', None, None),
    ('ft3_value', 'ANY', 365, 6570, 3.5, 7.5, 'pmol/L', None, None),
    ('ft3_value', 'ANY', 6570, 25550, 4.0, 7.8, 'pmol/L', None, None),
    
    # Free T4 (pmol/L)
    ('ft4', 'ANY', 0, 365, 10.0, 28.0, 'pmol/L', None, None),
    ('ft4', 'ANY', 365, 6570, 12.0, 26.0, 'pmol/L', None, None),
    ('ft4', 'ANY', 6570, 25550, 12.0, 22.0, 'pmol/L', None, None),
    
    # FT4 Value (alternative)
    ('ft4_value', 'ANY', 0, 365, 10.0, 28.0, 'pmol/L', None, None),
    ('ft4_value', 'ANY', 365, 6570, 12.0, 26.0, 'pmol/L', None, None),
    ('ft4_value', 'ANY', 6570, 25550, 12.0, 22.0, 'pmol/L', None, None),
    
    # =========================================================================
    # REPRODUCTIVE HORMONES
    # =========================================================================
    
    # Testosterone (nmol/L)
    ('testosterone_value', 'M', 0, 365, 0.1, 1.2, 'nmol/L', None, None),
    ('testosterone_value', 'M', 365, 6570, 0.1, 2.0, 'nmol/L', None, None),
    ('testosterone_value', 'M', 6570, 10950, 0.3, 2.0, 'nmol/L', None, None),
    ('testosterone_value', 'M', 10950, 25550, 8.0, 35.0, 'nmol/L', None, None),
    ('testosterone_value', 'F', 0, 365, 0.1, 0.5, 'nmol/L', None, None),
    ('testosterone_value', 'F', 365, 6570, 0.1, 0.8, 'nmol/L', None, None),
    ('testosterone_value', 'F', 6570, 25550, 0.3, 2.8, 'nmol/L', None, None),
    
    # FSH (IU/L)
    ('fsh_value', 'M', 0, 6570, 0.5, 3.0, 'IU/L', None, None),
    ('fsh_value', 'M', 6570, 25550, 1.0, 12.0, 'IU/L', None, None),
    ('fsh_value', 'F', 0, 6570, 0.5, 4.0, 'IU/L', None, None),
    ('fsh_value', 'F', 6570, 10950, 2.0, 10.0, 'IU/L', None, None),
    ('fsh_value', 'F', 10950, 25550, 3.0, 15.0, 'IU/L', None, None),
    
    # LH (IU/L)
    ('lh_value', 'M', 0, 6570, 0.2, 2.0, 'IU/L', None, None),
    ('lh_value', 'M', 6570, 25550, 1.0, 9.0, 'IU/L', None, None),
    ('lh_value', 'F', 0, 6570, 0.2, 2.0, 'IU/L', None, None),
    ('lh_value', 'F', 6570, 10950, 1.0, 8.0, 'IU/L', None, None),
    ('lh_value', 'F', 10950, 25550, 2.0, 12.0, 'IU/L', None, None),
    
    # Estradiol (pmol/L)
    ('estradiol_value', 'M', 0, 6570, 10, 30, 'pmol/L', None, None),
    ('estradiol_value', 'M', 6570, 25550, 40, 150, 'pmol/L', None, None),
    ('estradiol_value', 'F', 0, 6570, 10, 30, 'pmol/L', None, None),
    ('estradiol_value', 'F', 6570, 10950, 20, 80, 'pmol/L', None, None),
    ('estradiol_value', 'F', 10950, 25550, 70, 600, 'pmol/L', None, None),
    
    # Progesterone (nmol/L)
    ('progesterone_value', 'M', 0, 6570, 0.1, 0.5, 'nmol/L', None, None),
    ('progesterone_value', 'M', 6570, 25550, 0.3, 2.5, 'nmol/L', None, None),
    ('progesterone_value', 'F', 0, 6570, 0.1, 1.0, 'nmol/L', None, None),
    ('progesterone_value', 'F', 6570, 10950, 0.5, 2.0, 'nmol/L', None, None),
    ('progesterone_value', 'F', 10950, 25550, 0.6, 70.0, 'nmol/L', None, None),
    
    # Prolactin (mIU/L)
    ('prolactin_value', 'M', 0, 365, 50, 400, 'mIU/L', None, None),
    ('prolactin_value', 'M', 365, 6570, 50, 350, 'mIU/L', None, None),
    ('prolactin_value', 'M', 6570, 25550, 50, 350, 'mIU/L', None, None),
    ('prolactin_value', 'F', 0, 365, 50, 400, 'mIU/L', None, None),
    ('prolactin_value', 'F', 365, 6570, 50, 350, 'mIU/L', None, None),
    ('prolactin_value', 'F', 6570, 25550, 50, 550, 'mIU/L', None, None),
    
    # =========================================================================
    # OTHER HORMONES
    # =========================================================================
    
    # Cortisol (nmol/L) - morning sample
    ('cortisol_value', 'ANY', 0, 365, 80, 580, 'nmol/L', None, None),
    ('cortisol_value', 'ANY', 365, 6570, 80, 500, 'nmol/L', None, None),
    ('cortisol_value', 'ANY', 6570, 25550, 170, 540, 'nmol/L', None, None),
    
    # DHEA (μmol/L)
    ('dhea_value', 'M', 0, 365, 0.5, 2.5, 'μmol/L', None, None),
    ('dhea_value', 'M', 365, 6570, 1.0, 8.0, 'μmol/L', None, None),
    ('dhea_value', 'M', 6570, 25550, 5.0, 25.0, 'μmol/L', None, None),
    ('dhea_value', 'F', 0, 365, 0.5, 2.5, 'μmol/L', None, None),
    ('dhea_value', 'F', 365, 6570, 1.0, 8.0, 'μmol/L', None, None),
    ('dhea_value', 'F', 6570, 25550, 3.0, 20.0, 'μmol/L', None, None),
    
    # Growth Hormone (mIU/L)
    ('gh_value', 'ANY', 0, 365, 5, 40, 'mIU/L', None, None),
    ('gh_value', 'ANY', 365, 6570, 1, 20, 'mIU/L', None, None),
    ('gh_value', 'ANY', 6570, 25550, 0, 5, 'mIU/L', None, None),
    
    # =========================================================================
    # TUMOR MARKERS
    # =========================================================================
    
    # AFP (ng/mL)
    ('afp_value', 'ANY', 0, 365, 0, 100, 'ng/mL', None, 500),
    ('afp_value', 'ANY', 365, 6570, 0, 30, 'ng/mL', None, 500),
    ('afp_value', 'ANY', 6570, 25550, 0, 10, 'ng/mL', None, 500),
    
    # PSA (ng/mL) - Male only
    ('psa_value', 'M', 0, 365, 0, 0.5, 'ng/mL', None, None),
    ('psa_value', 'M', 365, 6570, 0, 0.5, 'ng/mL', None, None),
    ('psa_value', 'M', 6570, 10950, 0, 1.0, 'ng/mL', None, None),
    ('psa_value', 'M', 10950, 25550, 0, 4.0, 'ng/mL', None, 10.0),
    
    # β-HCG (IU/L)
    ('bhcg_value', 'M', 0, 25550, 0, 5, 'IU/L', None, None),
    ('bhcg_value', 'F', 0, 6570, 0, 5, 'IU/L', None, None),
    ('bhcg_value', 'F', 6570, 10950, 0, 5, 'IU/L', None, None),
    # Note: Female adult non-pregnant range is 0-5 IU/L
    
    # =========================================================================
    # INFECTIOUS DISEASE MARKERS
    # =========================================================================
    
    # CD4 Count (cells/μL)
    ('cd4_count', 'ANY', 0, 365, 500, 2500, 'cells/μL', 500, None),
    ('cd4_count', 'ANY', 365, 730, 1000, 3000, 'cells/μL', 750, None),
    ('cd4_count', 'ANY', 730, 2190, 500, 1500, 'cells/μL', 350, None),
    ('cd4_count', 'ANY', 2190, 6570, 300, 1200, 'cells/μL', 200, None),
    ('cd4_count', 'ANY', 6570, 25550, 500, 1500, 'cells/μL', 200, None),
    
    # CD4 Percentage (%)
    ('cd4_percentage', 'ANY', 0, 365, 25, 65, '%', 15, None),
    ('cd4_percentage', 'ANY', 365, 25550, 30, 60, '%', 15, None),
    
    # HIV Viral Load
    ('hiv_vl_value', 'ANY', 0, 25550, 0, 20, 'copies/mL', None, None),
    ('hiv_vl_log', 'ANY', 0, 25550, 0, 1.7, 'log10', None, None),
    
    # HBV Viral Load
    ('hbv_vl_value', 'ANY', 0, 25550, 0, 10, 'IU/mL', None, None),
    
    # HCV Viral Load
    ('hcv_vl_value', 'ANY', 0, 25550, 0, 15, 'IU/mL', None, None),
    
    # =========================================================================
    # INFLAMMATORY MARKERS
    # =========================================================================
    
    # CRP (mg/L) - CVD Risk Assessment - interpretation-based, no auto-flags
    # < 1.0 mg/L = Low CVD (no inflammation)
    # 1.0-3.0 mg/L = Moderate CVD risk
    # > 3.0 mg/L = High CVD risk
    # > 10 mg/L = May indicate infection (bacterial/viral)
    ('crp_value', 'ANY', 0, 365, None, None, 'mg/L', None, None),
    ('crp_value', 'ANY', 365, 6570, None, None, 'mg/L', None, None),
    ('crp_value', 'ANY', 6570, 25550, None, None, 'mg/L', None, None),
    
    # ASO Titer (IU/mL)
    ('aso_value', 'ANY', 0, 365, 0, 100, 'IU/mL', None, None),
    ('aso_value', 'ANY', 365, 6570, 0, 200, 'IU/mL', None, None),
    ('aso_value', 'ANY', 6570, 25550, 0, 200, 'IU/mL', None, None),
    
    # RA Factor (IU/mL)
    ('ra_titer', 'ANY', 0, 365, 0, 20, 'IU/mL', None, None),
    ('ra_titer', 'ANY', 365, 6570, 0, 15, 'IU/mL', None, None),
    ('ra_titer', 'ANY', 6570, 25550, 0, 20, 'IU/mL', None, None),
    
    # =========================================================================
    # CARDIAC MARKERS
    # =========================================================================
    
    # Troponin I/T (ng/mL)
    ('troponin_quant', 'ANY', 0, 25550, 0, 0.04, 'ng/mL', None, 0.5),
    
    # CK (U/L)
    ('ck_value', 'M', 0, 365, 20, 200, 'U/L', None, None),
    ('ck_value', 'M', 365, 6570, 25, 200, 'U/L', None, None),
    ('ck_value', 'M', 6570, 25550, 30, 200, 'U/L', None, None),
    ('ck_value', 'F', 0, 365, 20, 150, 'U/L', None, None),
    ('ck_value', 'F', 365, 6570, 25, 150, 'U/L', None, None),
    ('ck_value', 'F', 6570, 25550, 30, 150, 'U/L', None, None),
    
    # CK-MB (U/L)
    ('ckmb_value', 'ANY', 0, 365, 0, 25, 'U/L', None, None),
    ('ckmb_value', 'ANY', 365, 6570, 0, 20, 'U/L', None, None),
    ('ckmb_value', 'ANY', 6570, 25550, 0, 16, 'U/L', None, None),
    
    # BNP (pg/mL)
    ('bnp_value', 'ANY', 0, 6570, 0, 100, 'pg/mL', None, None),
    ('bnp_value', 'ANY', 6570, 25550, 0, 100, 'pg/mL', None, 500),
    
    # =========================================================================
    # PANCREATIC TESTS
    # =========================================================================
    
    # Amylase (U/L)
    ('amylase_value', 'ANY', 0, 365, 20, 100, 'U/L', None, None),
    ('amylase_value', 'ANY', 365, 6570, 25, 100, 'U/L', None, None),
    ('amylase_value', 'ANY', 6570, 25550, 28, 100, 'U/L', None, None),
    
    # Lipase (U/L)
    ('lipase_value', 'ANY', 0, 365, 10, 50, 'U/L', None, None),
    ('lipase_value', 'ANY', 365, 6570, 13, 50, 'U/L', None, None),
    ('lipase_value', 'ANY', 6570, 25550, 13, 60, 'U/L', None, None),
    
    # =========================================================================
    # IRON STUDIES
    # =========================================================================
    
    # Serum Iron (μmol/L)
    ('serum_iron', 'M', 0, 365, 5, 20, 'μmol/L', None, None),
    ('serum_iron', 'M', 365, 6570, 8, 22, 'μmol/L', None, None),
    ('serum_iron', 'M', 6570, 25550, 11, 30, 'μmol/L', None, None),
    ('serum_iron', 'F', 0, 365, 5, 20, 'μmol/L', None, None),
    ('serum_iron', 'F', 365, 6570, 8, 22, 'μmol/L', None, None),
    ('serum_iron', 'F', 6570, 25550, 6, 26, 'μmol/L', None, None),
    
    # Ferritin (ng/mL)
    ('ferritin', 'M', 0, 365, 10, 150, 'ng/mL', None, None),
    ('ferritin', 'M', 365, 6570, 15, 150, 'ng/mL', None, None),
    ('ferritin', 'M', 6570, 25550, 20, 250, 'ng/mL', None, None),
    ('ferritin', 'F', 0, 365, 10, 150, 'ng/mL', None, None),
    ('ferritin', 'F', 365, 6570, 15, 150, 'ng/mL', None, None),
    ('ferritin', 'F', 6570, 25550, 10, 120, 'ng/mL', None, None),
    
    # TIBC (μmol/L)
    ('tibc', 'ANY', 0, 365, 40, 80, 'μmol/L', None, None),
    ('tibc', 'ANY', 365, 6570, 45, 85, 'μmol/L', None, None),
    ('tibc', 'ANY', 6570, 25550, 45, 70, 'μmol/L', None, None),
    
    # Transferrin Saturation (%)
    ('transferrin_sat', 'M', 0, 365, 10, 40, '%', None, None),
    ('transferrin_sat', 'M', 365, 6570, 15, 45, '%', None, None),
    ('transferrin_sat', 'M', 6570, 25550, 20, 50, '%', None, None),
    ('transferrin_sat', 'F', 0, 365, 10, 40, '%', None, None),
    ('transferrin_sat', 'F', 365, 6570, 15, 45, '%', None, None),
    ('transferrin_sat', 'F', 6570, 25550, 15, 45, '%', None, None),
    
    # =========================================================================
    # ELECTROLYTES - MINERALS
    # =========================================================================
    
    # Calcium (mmol/L)
    ('calcium_value', 'ANY', 0, 365, 1.8, 2.6, 'mmol/L', 1.5, 3.0),
    ('calcium_value', 'ANY', 365, 6570, 2.0, 2.7, 'mmol/L', 1.5, 3.0),
    ('calcium_value', 'ANY', 6570, 25550, 2.1, 2.5, 'mmol/L', 1.5, 3.0),
    
    # Magnesium (mmol/L)
    ('magnesium_value', 'ANY', 0, 365, 0.6, 0.9, 'mmol/L', 0.4, 1.2),
    ('magnesium_value', 'ANY', 365, 6570, 0.6, 0.9, 'mmol/L', 0.4, 1.2),
    ('magnesium_value', 'ANY', 6570, 25550, 0.7, 1.0, 'mmol/L', 0.4, 1.2),
    
    # Phosphate (mmol/L)
    ('phosphate_value', 'ANY', 0, 365, 1.3, 2.2, 'mmol/L', 0.8, None),
    ('phosphate_value', 'ANY', 365, 6570, 1.3, 1.9, 'mmol/L', 0.8, None),
    ('phosphate_value', 'ANY', 6570, 25550, 0.8, 1.5, 'mmol/L', 0.5, None),
    
    # =========================================================================
    # BODY FLUIDS ANALYSIS
    # =========================================================================
    
    # CSF
    ('csf_glucose', 'ANY', 0, 25550, 2.5, 4.5, 'mmol/L', 1.5, None),
    ('csf_protein', 'ANY', 0, 365, 0.15, 1.0, 'g/L', None, 1.5),
    ('csf_protein', 'ANY', 365, 6570, 0.15, 0.6, 'g/L', None, 1.0),
    ('csf_protein', 'ANY', 6570, 25550, 0.15, 0.45, 'g/L', None, 1.0),
    ('csf_wbc', 'ANY', 0, 365, 0, 10, 'cells/μL', None, 100),
    ('csf_wbc', 'ANY', 365, 6570, 0, 5, 'cells/μL', None, 50),
    ('csf_wbc', 'ANY', 6570, 25550, 0, 5, 'cells/μL', None, 50),
    ('csf_rbc', 'ANY', 0, 25550, 0, 0, 'cells/μL', None, None),
    ('csf_lymphocytes', 'ANY', 0, 25550, 0, 40, '%', None, None),
    ('csf_neutrophils', 'ANY', 0, 25550, 0, 5, '%', None, 50),
    
    # Ascitic Fluid
    ('ascitic_glucose', 'ANY', 0, 25550, 3.9, 5.6, 'mmol/L', 2.2, None),
    ('ascitic_protein', 'ANY', 0, 25550, 0, 25, 'g/L', None, None),
    ('ascitic_wbc', 'ANY', 0, 25550, 0, 250, 'cells/μL', None, 1000),
    ('ascitic_rbc', 'ANY', 0, 25550, 0, 10, 'cells/μL', None, None),
    ('ascitic_lymphocytes', 'ANY', 0, 25550, 0, 70, '%', None, None),
    
    # Pleural Fluid
    ('pleural_glucose', 'ANY', 0, 25550, 3.9, 5.6, 'mmol/L', 2.2, None),
    ('pleural_protein', 'ANY', 0, 25550, 0, 30, 'g/L', None, None),
    ('pleural_wbc', 'ANY', 0, 25550, 0, 1000, 'cells/μL', None, None),
    ('pleural_rbc', 'ANY', 0, 25550, 0, 10, 'cells/μL', None, None),
    
    # =========================================================================
    # URINALYSIS
    # =========================================================================
    # Note: Urine tests are often qualitative but some have numeric ranges
    ('ph', 'ANY', 0, 25550, 4.5, 8.0, '', None, None),
    ('specific_gravity', 'ANY', 0, 25550, 1.005, 1.030, '', None, None),
    
    # =========================================================================
    # ADDITIONAL COMMON TESTS (DHIMS2/GHS)
    # =========================================================================
    
    # Full sets for any missing combinations
    ('wbc_value', 'ANY', 0, 28, 6.0, 18.0, 'x10^9/L', 2.0, 30.0),
    ('wbc_value', 'ANY', 28, 365, 6.0, 15.0, 'x10^9/L', 2.0, 25.0),
    ('wbc_value', 'ANY', 365, 6570, 5.0, 12.0, 'x10^9/L', 2.0, 20.0),
    ('wbc_value', 'ANY', 6570, 25550, 4.0, 11.0, 'x10^9/L', 2.0, 20.0),
    
    ('platelet_value', 'ANY', 0, 28, 100, 400, 'x10^9/L', 50, 600),
    ('platelet_value', 'ANY', 28, 365, 150, 400, 'x10^9/L', 50, 600),
    ('platelet_value', 'ANY', 365, 6570, 150, 400, 'x10^9/L', 50, 600),
    ('platelet_value', 'ANY', 6570, 25550, 150, 400, 'x10^9/L', 50, 600),
]


def insert_comprehensive_ranges():
    """Insert all comprehensive reference ranges."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        inserted_count = 0
        skipped_count = 0
        
        for (field_code, sex, age_min, age_max, low, high, unit, crit_low, crit_high) in REFERENCE_RANGES:
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
        
        conn.commit()
    
    return inserted_count, skipped_count


def main():
    print("=" * 70)
    print("Comprehensive Ghana Lab Reference Ranges - DHIMS2/GHS Standards")
    print("=" * 70)
    print(f"\nDatabase: {DATABASE_URL}")
    print(f"Total ranges to process: {len(REFERENCE_RANGES)}")
    
    inserted, skipped = insert_comprehensive_ranges()
    
    print(f"\n{'=' * 70}")
    print(f"COMPLETED:")
    print(f"  - Inserted: {inserted} new reference ranges")
    print(f"  - Skipped (already exist): {skipped}")
    print(f"{'=' * 70}")
    
    # Get final stats
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM lab_reference_ranges"))
        total = result.fetchone()[0]
        result = conn.execute(text("SELECT COUNT(DISTINCT field_code) FROM lab_reference_ranges"))
        unique = result.fetchone()[0]
        print(f"\nDatabase Stats:")
        print(f"  - Total reference ranges: {total}")
        print(f"  - Unique field codes: {unique}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
