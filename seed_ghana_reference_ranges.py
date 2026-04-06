#!/usr/bin/env python3
"""
Ghana Laboratory Reference Ranges Seeder

This script populates the database with Ghana-appropriate reference ranges
for all the hospital-approved test menu.

Reference ranges are based on Ghanaian clinical standards and include:
- Age-specific ranges (Newborn, Infant, Child, Adult, Elderly)
- Sex-specific ranges (Male, Female)
- Critical thresholds for emergency notification

Usage:
    python3 seed_ghana_reference_ranges.py

Requirements:
    - Database must be initialized
    - Run from the project root directory
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

# Import via app.main to ensure proper model loading order
from app.main import app
from app.core.config import settings
from app.models.lab_template_models import LabReferenceRange

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_reference_ranges():
    """Return all Ghana-appropriate reference ranges."""
    
    ranges = []
    
    # ==================== HEMATOLOGY ====================
    
    # Hemoglobin (Hb) - Age and sex specific
    ranges.extend([
        # Adult Male
        {"field_code": "hb", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("12.5"), "high": Decimal("17.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Adult Female
        {"field_code": "hb", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("11.5"), "high": Decimal("15.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Adolescent (13-18)
        {"field_code": "hb", "sex": "ANY", "age_min_days": 4745, "age_max_days": 6570, 
         "low": Decimal("12.0"), "high": Decimal("16.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Child (6-12)
        {"field_code": "hb", "sex": "ANY", "age_min_days": 2190, "age_max_days": 4745, 
         "low": Decimal("11.5"), "high": Decimal("15.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Preschool (3-5)
        {"field_code": "hb", "sex": "ANY", "age_min_days": 1095, "age_max_days": 2190, 
         "low": Decimal("11.0"), "high": Decimal("14.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Toddler (1-3)
        {"field_code": "hb", "sex": "ANY", "age_min_days": 365, "age_max_days": 1095, 
         "low": Decimal("10.5"), "high": Decimal("14.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Infant (1-12 months)
        {"field_code": "hb", "sex": "ANY", "age_min_days": 30, "age_max_days": 365, 
         "low": Decimal("9.5"), "high": Decimal("13.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Newborn (0-28 days)
        {"field_code": "hb", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, 
         "low": Decimal("14.5"), "high": Decimal("22.5"), "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"},
    ])
    
    # Hematocrit (Hct)
    ranges.extend([
        {"field_code": "hct", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("36"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("34"), "high": Decimal("46"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, 
         "low": Decimal("32"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
    ])
    
    # RBC Count
    ranges.extend([
        {"field_code": "rbc_count", "sex": "M", "age_min_days": 6570, "age_max_days": None, 
         "low": Decimal("4.5"), "high": Decimal("6.5"), "unit": "x10^12/L"},
        {"field_code": "rbc_count", "sex": "F", "age_min_days": 6570, "age_max_days": None, 
         "low": Decimal("3.8"), "high": Decimal("5.8"), "unit": "x10^12/L"},
        {"field_code": "rbc_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, 
         "low": Decimal("3.8"), "high": Decimal("6.0"), "unit": "x10^12/L"},
    ])
    
    # WBC Count
    ranges.extend([
        {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("4.0"), "high": Decimal("11.0"), "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10^9/L"},
    ])
    
    # Platelet Count
    ranges.extend([
        {"field_code": "platelet_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("150"), "high": Decimal("400"), "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "x10^9/L"},
    ])
    
    # Neutrophils
    ranges.extend([
        {"field_code": "neutrophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("40"), "high": Decimal("75"), "unit": "%"},
    ])
    
    # Lymphocytes
    ranges.extend([
        {"field_code": "lymphocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("20"), "high": Decimal("50"), "unit": "%"},
    ])
    
    # Monocytes
    ranges.extend([
        {"field_code": "monocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("2"), "high": Decimal("10"), "unit": "%"},
    ])
    
    # Eosinophils
    ranges.extend([
        {"field_code": "eosinophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("1"), "high": "6", "unit": "%"},
    ])
    
    # Basophils
    ranges.extend([
        {"field_code": "basophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("2"), "unit": "%"},
    ])
    
    # MCV
    ranges.extend([
        {"field_code": "mcv", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("80"), "high": Decimal("100"), "unit": "fL"},
    ])
    
    # MCH
    ranges.extend([
        {"field_code": "mch", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("27"), "high": Decimal("33"), "unit": "pg"},
    ])
    
    # MCHC
    ranges.extend([
        {"field_code": "mchc", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("31.5"), "high": Decimal("35.5"), "unit": "g/dL"},
    ])
    
    # ESR (Erythrocyte Sedimentation Rate)
    ranges.extend([
        # Adult Male
        {"field_code": "esr", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("15"), "unit": "mm/hr"},
        # Adult Female
        {"field_code": "esr", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("20"), "unit": "mm/hr"},
        # Child
        {"field_code": "esr", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, 
         "low": Decimal("0"), "high": Decimal("15"), "unit": "mm/hr"},
    ])
    
    # Reticulocyte Count
    ranges.extend([
        {"field_code": "retic_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0.5"), "high": Decimal("2.5"), "unit": "%"},
    ])
    
    # ==================== BIOCHEMISTRY ====================
    
    # Glucose (Fasting)
    ranges.extend([
        {"field_code": "glucose_fasting", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("70"), "high": Decimal("100"), "critical_low": Decimal("40"), "critical_high": Decimal("400"), "unit": "mg/dL"},
    ])
    
    # Random Blood Sugar
    ranges.extend([
        {"field_code": "glucose_random", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("70"), "high": Decimal("140"), "critical_low": Decimal("40"), "critical_high": Decimal("400"), "unit": "mg/dL"},
    ])
    
    # HbA1c
    ranges.extend([
        {"field_code": "hba1c", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("4.0"), "high": Decimal("5.6"), "unit": "%"},
    ])
    
    # Total Cholesterol
    ranges.extend([
        {"field_code": "cholesterol_total", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("200"), "critical_high": Decimal("300"), "unit": "mg/dL"},
    ])
    
    # LDL Cholesterol
    ranges.extend([
        {"field_code": "ldl_cholesterol", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("100"), "critical_high": Decimal("190"), "unit": "mg/dL"},
    ])
    
    # HDL Cholesterol
    ranges.extend([
        {"field_code": "hdl_cholesterol", "sex": "M", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("40"), "high": Decimal("60"), "unit": "mg/dL"},
        {"field_code": "hdl_cholesterol", "sex": "F", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("50"), "high": Decimal("70"), "unit": "mg/dL"},
    ])
    
    # Triglycerides
    ranges.extend([
        {"field_code": "triglycerides", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("150"), "critical_high": Decimal("500"), "unit": "mg/dL"},
    ])
    
    # Creatinine
    ranges.extend([
        {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0.7"), "high": Decimal("1.3"), "critical_high": Decimal("6.0"), "unit": "mg/dL"},
        {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0.6"), "high": Decimal("1.1"), "critical_high": Decimal("6.0"), "unit": "mg/dL"},
    ])
    
    # Blood Urea Nitrogen
    ranges.extend([
        {"field_code": "bun", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("7"), "high": Decimal("20"), "critical_high": Decimal("60"), "unit": "mg/dL"},
    ])
    
    # Sodium
    ranges.extend([
        {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("136"), "high": Decimal("145"), "critical_low": Decimal("120"), "critical_high": Decimal("160"), "unit": "mEq/L"},
    ])
    
    # Potassium
    ranges.extend([
        {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("3.5"), "high": Decimal("5.0"), "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mEq/L"},
    ])
    
    # Chloride
    ranges.extend([
        {"field_code": "chloride", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("98"), "high": Decimal("106"), "critical_low": Decimal("80"), "critical_high": Decimal("120"), "unit": "mEq/L"},
    ])
    
    # Bicarbonate
    ranges.extend([
        {"field_code": "bicarbonate", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("22"), "high": Decimal("28"), "critical_low": Decimal("10"), "critical_high": Decimal("40"), "unit": "mEq/L"},
    ])
    
    # Calcium
    ranges.extend([
        {"field_code": "calcium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("8.5"), "high": Decimal("10.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("14.0"), "unit": "mg/dL"},
    ])
    
    # Magnesium
    ranges.extend([
        {"field_code": "magnesium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("1.5"), "high": Decimal("2.5"), "critical_low": Decimal("1.0"), "critical_high": Decimal("4.0"), "unit": "mg/dL"},
    ])
    
    # Phosphate
    ranges.extend([
        {"field_code": "phosphate", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("2.5"), "high": Decimal("4.5"), "critical_low": Decimal("1.0"), "critical_high": Decimal("7.0"), "unit": "mg/dL"},
    ])
    
    # Total Protein
    ranges.extend([
        {"field_code": "total_protein", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("6.0"), "high": Decimal("8.3"), "unit": "g/dL"},
    ])
    
    # Albumin
    ranges.extend([
        {"field_code": "albumin", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("3.5"), "high": Decimal("5.5"), "unit": "g/dL"},
    ])
    
    # Total Bilirubin
    ranges.extend([
        {"field_code": "bilirubin_total", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0.2"), "high": Decimal("1.2"), "critical_high": Decimal("10.0"), "unit": "mg/dL"},
        # Newborn
        {"field_code": "bilirubin_total", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, 
         "low": Decimal("0.2"), "high": Decimal("8.0"), "critical_high": Decimal("15.0"), "unit": "mg/dL"},
    ])
    
    # Direct Bilirubin
    ranges.extend([
        {"field_code": "bilirubin_direct", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0.0"), "high": Decimal("0.3"), "unit": "mg/dL"},
    ])
    
    # ALT (Alanine Aminotransferase)
    ranges.extend([
        {"field_code": "alt", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("40"), "critical_high": Decimal("500"), "unit": "U/L"},
        {"field_code": "alt", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("32"), "critical_high": Decimal("500"), "unit": "U/L"},
    ])
    
    # AST (Aspartate Aminotransferase)
    ranges.extend([
        {"field_code": "ast", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("37"), "critical_high": Decimal("500"), "unit": "U/L"},
        {"field_code": "ast", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("31"), "critical_high": Decimal("500"), "unit": "U/L"},
    ])
    
    # ALP (Alkaline Phosphatase)
    ranges.extend([
        {"field_code": "alp", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("20"), "high": Decimal("140"), "critical_high": Decimal("500"), "unit": "U/L"},
        # Child (higher normal)
        {"field_code": "alp", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, 
         "low": Decimal("100"), "high": Decimal("350"), "critical_high": Decimal("500"), "unit": "U/L"},
    ])
    
    # GGT (Gamma-Glutamyl Transferase)
    ranges.extend([
        {"field_code": "ggt", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("55"), "unit": "U/L"},
        {"field_code": "ggt", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("38"), "unit": "U/L"},
    ])
    
    # Iron
    ranges.extend([
        {"field_code": "iron", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("60"), "high": Decimal("170"), "unit": "mcg/dL"},
        {"field_code": "iron", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("37"), "high": Decimal("145"), "unit": "mcg/dL"},
    ])
    
    # Ferritin
    ranges.extend([
        {"field_code": "ferritin", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("20"), "high": Decimal("250"), "unit": "ng/mL"},
        {"field_code": "ferritin", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("10"), "high": Decimal("120"), "unit": "ng/mL"},
    ])
    
    # Uric Acid (μmol/L)
    ranges.extend([
        {"field_code": "uric_acid", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("142"), "high": Decimal("339"), "critical_high": Decimal("450"), "unit": "μmol/L"},
        {"field_code": "uric_acid", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("202"), "high": Decimal("416"), "critical_high": Decimal("500"), "unit": "μmol/L"},
    ])
    
    # GFR (estimated)
    ranges.extend([
        {"field_code": "egfr", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("90"), "high": Decimal("120"), "unit": "mL/min/1.73m²"},
        {"field_code": "egfr", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("90"), "high": Decimal("120"), "unit": "mL/min/1.73m²"},
    ])
    
    # ==================== THYROID PROFILE ====================
    
    # TSH
    ranges.extend([
        {"field_code": "tsh", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0.4"), "high": Decimal("4.0"), "critical_low": Decimal("0.1"), "critical_high": Decimal("10.0"), "unit": "mIU/L"},
    ])
    
    # Free T4
    ranges.extend([
        {"field_code": "ft4", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0.8"), "high": Decimal("1.8"), "critical_low": Decimal("0.1"), "critical_high": Decimal("4.0"), "unit": "ng/dL"},
    ])
    
    # Free T3
    ranges.extend([
        {"field_code": "ft3", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("2.3"), "high": Decimal("4.2"), "critical_low": Decimal("1.0"), "critical_high": Decimal("6.0"), "unit": "pg/mL"},
    ])
    
    # ==================== HORMONES ====================
    
    # Testosterone
    ranges.extend([
        {"field_code": "testosterone", "sex": "M", "age_min_days": 6570, "age_max_days": 21900, 
         "low": Decimal("300"), "high": Decimal("1000"), "unit": "ng/dL"},
        {"field_code": "testosterone", "sex": "M", "age_min_days": 21900, "age_max_days": 36500, 
         "low": Decimal("240"), "high": Decimal("840"), "unit": "ng/dL"},
        {"field_code": "testosterone", "sex": "M", "age_min_days": 36500, "age_max_days": None, 
         "low": Decimal("80"), "high": Decimal("300"), "unit": "ng/dL"},
        {"field_code": "testosterone", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("15"), "high": Decimal("70"), "unit": "ng/dL"},
    ])
    
    # FSH
    ranges.extend([
        {"field_code": "fsh", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("1.0"), "high": Decimal("18.0"), "unit": "mIU/mL"},
        {"field_code": "fsh", "sex": "F", "age_min_days": 6570, "age_max_days": 12775,  # Pre-menopause
         "low": Decimal("3.5"), "high": Decimal("12.5"), "unit": "mIU/mL"},
        {"field_code": "fsh", "sex": "F", "age_min_days": 12775, "age_max_days": None,  # Post-menopause
         "low": Decimal("25.8"), "high": Decimal("134.8"), "unit": "mIU/mL"},
    ])
    
    # LH
    ranges.extend([
        {"field_code": "lh", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("1.2"), "high": Decimal("8.0"), "unit": "mIU/mL"},
        {"field_code": "lh", "sex": "F", "age_min_days": 6570, "age_max_days": 12775,
         "low": Decimal("2.0"), "high": Decimal("12.0"), "unit": "mIU/mL"},
        {"field_code": "lh", "sex": "F", "age_min_days": 12775, "age_max_days": None,
         "low": Decimal("15.0"), "high": Decimal("62.0"), "unit": "mIU/mL"},
    ])
    
    # Estradiol
    ranges.extend([
        {"field_code": "estradiol", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("10"), "high": Decimal("50"), "unit": "pg/mL"},
        {"field_code": "estradiol", "sex": "F", "age_min_days": 6570, "age_max_days": 12775,
         "low": Decimal("30"), "high": Decimal("400"), "unit": "pg/mL"},
        {"field_code": "estradiol", "sex": "F", "age_min_days": 12775, "age_max_days": None,
         "low": Decimal("10"), "high": Decimal("30"), "unit": "pg/mL"},
    ])
    
    # Progesterone
    ranges.extend([
        {"field_code": "progesterone", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0.1"), "high": Decimal("0.3"), "unit": "ng/mL"},
        {"field_code": "progesterone", "sex": "F", "age_min_days": 6570, "age_max_days": 12775,
         "low": Decimal("0.1"), "high": Decimal("0.3"), "unit": "ng/mL"},  # Follicular
    ])
    
    # Prolactin
    ranges.extend([
        {"field_code": "prolactin", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("4.0"), "high": Decimal("15.0"), "critical_high": Decimal("25.0"), "unit": "ng/mL"},
        {"field_code": "prolactin", "sex": "F", "age_min_days": 6570, "age_max_days": 12775,
         "low": Decimal("4.0"), "high": Decimal("23.0"), "critical_high": Decimal("25.0"), "unit": "ng/mL"},
    ])
    
    # Cortisol (Morning)
    ranges.extend([
        {"field_code": "cortisol", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("5.0"), "high": Decimal("25.0"), "critical_low": Decimal("3.0"), "critical_high": Decimal("30.0"), "unit": "mcg/dL"},
    ])
    
    # ==================== HEPATITIS ====================
    
    # Qualitative tests use text_range instead
    ranges.extend([
        {"field_code": "hbsag", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
        {"field_code": "hiv_1_2", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Indeterminate"},
        {"field_code": "hcv", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
        {"field_code": "vdrl", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Non-reactive,Reactive,Weakly reactive"},
        {"field_code": "widal", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive 1:40,Positive 1:80,Positive 1:160,Positive 1:320"},
        {"field_code": "h_pylori_blood", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
        {"field_code": "h_pylori_stool", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
        {"field_code": "pregnancy_test_urine", "sex": "F", "age_min_days": 4380, "age_max_days": 18250, 
         "text_range": "Negative,Positive"},
        {"field_code": "pregnancy_test_serum", "sex": "F", "age_min_days": 4380, "age_max_days": 18250, 
         "text_range": "Negative,Positive"},
    ])
    
    # ==================== PREGNANCY TESTS ====================
    
    # Beta-HCG
    ranges.extend([
        {"field_code": "beta_hcg", "sex": "F", "age_min_days": 4380, "age_max_days": 18250, 
         "low": Decimal("0"), "high": Decimal("5.0"), "unit": "mIU/mL"},  # Non-pregnant
    ])
    
    # ==================== CD4 & VIRAL LOAD ====================
    
    # CD4 Count
    ranges.extend([
        {"field_code": "cd4_count", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("500"), "high": Decimal("1500"), "critical_low": Decimal("200"), "unit": "cells/mm³"},
    ])
    
    # HIV Viral Load
    ranges.extend([
        {"field_code": "hiv_viral_load", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "low": Decimal("0"), "high": Decimal("20"), "unit": "copies/mL"},
    ])
    
    # HBV Viral Load
    ranges.extend([
        {"field_code": "hbv_viral_load", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "low": Decimal("0"), "high": Decimal("20"), "unit": "IU/mL"},
    ])
    
    # HCV Viral Load
    ranges.extend([
        {"field_code": "hcv_viral_load", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "low": Decimal("0"), "high": Decimal("15"), "unit": "IU/mL"},
    ])
    
    # ==================== TUMOR MARKERS ====================
    
    # AFP
    ranges.extend([
        {"field_code": "afp", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("10"), "unit": "ng/mL"},
    ])
    
    # PSA
    ranges.extend([
        {"field_code": "psa", "sex": "M", "age_min_days": 14600, "age_max_days": 36500, 
         "low": Decimal("0.0"), "high": Decimal("4.0"), "critical_high": Decimal("10.0"), "unit": "ng/mL"},
        {"field_code": "psa", "sex": "M", "age_min_days": 36500, "age_max_days": None, 
         "low": Decimal("0.0"), "high": Decimal("6.5"), "critical_high": Decimal("10.0"), "unit": "ng/mL"},
    ])
    
    # ==================== ADDITIONAL HORMONES ====================
    
    # DHEA-Sulphate (DHEA-S)
    ranges.extend([
        {"field_code": "dhea_s", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("80"), "high": Decimal("560"), "unit": "mcg/dL"},
        {"field_code": "dhea_s", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("18"), "high": Decimal("370"), "unit": "mcg/dL"},
    ])
    
    # Growth Hormone (GH)
    ranges.extend([
        {"field_code": "growth_hormone", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("5.0"), "unit": "ng/mL"},
    ])
    
    # Anti-Mullerian Hormone (AMH)
    ranges.extend([
        {"field_code": "amh", "sex": "F", "age_min_days": 6570, "age_max_days": 12775, 
         "low": Decimal("1.0"), "high": Decimal("4.0"), "unit": "ng/mL"},
        {"field_code": "amh", "sex": "F", "age_min_days": 12775, "age_max_days": 18250, 
         "low": Decimal("0.2"), "high": Decimal("1.0"), "unit": "ng/mL"},
    ])
    
    # ==================== ADDITIONAL BIOCHEMISTRY ====================
    
    # TIBC (Total Iron Binding Capacity)
    ranges.extend([
        {"field_code": "tibc", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("250"), "high": Decimal("450"), "unit": "mcg/dL"},
    ])
    
    # Transferrin Saturation
    ranges.extend([
        {"field_code": "transferrin_sat", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("20"), "high": Decimal("50"), "unit": "%"},
        {"field_code": "transferrin_sat", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("15"), "high": Decimal("50"), "unit": "%"},
    ])
    
    # Serum Amylase
    ranges.extend([
        {"field_code": "amylase", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("25"), "high": Decimal("125"), "critical_high": Decimal("300"), "unit": "U/L"},
    ])
    
    # Serum Lipase
    ranges.extend([
        {"field_code": "lipase", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("10"), "high": Decimal("140"), "critical_high": Decimal("300"), "unit": "U/L"},
    ])
    
    # Creatine Kinase (CK)
    ranges.extend([
        {"field_code": "ck", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("38"), "high": Decimal("174"), "critical_high": Decimal("500"), "unit": "U/L"},
        {"field_code": "ck", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("26"), "high": Decimal("140"), "critical_high": Decimal("500"), "unit": "U/L"},
    ])
    
    # CK-MB
    ranges.extend([
        {"field_code": "ck_mb", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("25"), "critical_high": Decimal("50"), "unit": "ng/mL"},
    ])
    
    # Lactate Dehydrogenase (LDH)
    ranges.extend([
        {"field_code": "ldh", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("140"), "high": Decimal("280"), "critical_high": Decimal("500"), "unit": "U/L"},
    ])
    
    # Troponin I
    ranges.extend([
        {"field_code": "troponin_i", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("0.04"), "critical_high": Decimal("0.5"), "unit": "ng/mL"},
    ])
    
    # Troponin T
    ranges.extend([
        {"field_code": "troponin_t", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("0.1"), "critical_high": Decimal("0.5"), "unit": "ng/mL"},
    ])
    
    # BNP (B-type Natriuretic Peptide)
    ranges.extend([
        {"field_code": "bnp", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("100"), "critical_high": Decimal("500"), "unit": "pg/mL"},
        {"field_code": "bnp", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("150"), "critical_high": Decimal("500"), "unit": "pg/mL"},
    ])
    
    # ==================== INFLAMMATORY MARKERS ====================
    
    # C-Reactive Protein (CRP) - CVD Risk Assessment
    # Interpretation-based range, no auto-flags
    # < 1.0 mg/L = Low CVD (no inflammation)
    # 1.0-3.0 mg/L = Moderate CVD risk
    # > 3.0 mg/L = High CVD risk
    # > 10 mg/L = May indicate infection (bacterial/viral)
    ranges.extend([
        {"field_code": "crp", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": None, "high": None, "critical_high": None, "unit": "mg/L",
         "text_range": "< 1.0 mg/L Low CVD (no inflammation)\n1.0-3.0 mg/L Moderate CVD risk (No inflammation situation)\n> 3.0 mg/L High CVD risk (No inflammation situation)\n> 10 There may be other infections (bacteria infections or viral infections)"},
    ])
    
    # ASO Titer
    ranges.extend([
        {"field_code": "aso_titer", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("200"), "unit": "IU/mL"},
    ])
    
    # Rheumatoid Factor
    ranges.extend([
        {"field_code": "rheumatoid_factor", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("14"), "unit": "IU/mL"},
    ])
    
    # ==================== ADDITIONAL TUMOR MARKERS ====================
    
    # CEA (Carcinoembryonic Antigen)
    ranges.extend([
        {"field_code": "cea", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("0"), "high": Decimal("5.0"), "critical_high": Decimal("10.0"), "unit": "ng/mL"},
    ])
    
    # Free PSA
    ranges.extend([
        {"field_code": "psa_free", "sex": "M", "age_min_days": 14600, "age_max_days": 36500, 
         "low": Decimal("0.0"), "high": Decimal("1.0"), "unit": "ng/mL"},
        {"field_code": "psa_free", "sex": "M", "age_min_days": 36500, "age_max_days": None, 
         "low": Decimal("0.0"), "high": Decimal("1.5"), "unit": "ng/mL"},
    ])
    
    # ==================== ADDITIONAL SEROLOGY ====================
    
    # HAV IgM
    ranges.extend([
        {"field_code": "hav_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # HAV Total
    ranges.extend([
        {"field_code": "hav_total", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # HEV IgM
    ranges.extend([
        {"field_code": "hev_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # HBsAb (Hepatitis B Surface Antibody)
    ranges.extend([
        {"field_code": "hbsab", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # HBcAb Total
    ranges.extend([
        {"field_code": "hbcab_total", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # HBcAb IgM
    ranges.extend([
        {"field_code": "hbcab_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # TPHA
    ranges.extend([
        {"field_code": "tpha", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Non-reactive,Reactive"},
    ])
    
    # Rubella IgG
    ranges.extend([
        {"field_code": "rubella_igg", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Equivocal"},
    ])
    
    # Rubella IgM
    ranges.extend([
        {"field_code": "rubella_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Equivocal"},
    ])
    
    # Toxoplasma IgG
    ranges.extend([
        {"field_code": "toxoplasma_igg", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Equivocal"},
    ])
    
    # Toxoplasma IgM
    ranges.extend([
        {"field_code": "toxoplasma_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Equivocal"},
    ])
    
    # CMV IgG
    ranges.extend([
        {"field_code": "cmv_igg", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Equivocal"},
    ])
    
    # CMV IgM
    ranges.extend([
        {"field_code": "cmv_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive,Equivocal"},
    ])
    
    # HSV 1&2 IgG
    ranges.extend([
        {"field_code": "hsv_igg", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # HSV 1&2 IgM
    ranges.extend([
        {"field_code": "hsv_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # Chlamydia IgG
    ranges.extend([
        {"field_code": "chlamydia_igg", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # Typhi IgM
    ranges.extend([
        {"field_code": "typhi_igm", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    # Gonorrhoea (NGAL)
    ranges.extend([
        {"field_code": "gonorrhoea", "sex": "ANY", "age_min_days": 0, "age_max_days": None, 
         "text_range": "Negative,Positive"},
    ])
    
    return ranges


def seed_reference_ranges(db: Session):
    """Seed the database with Ghana reference ranges."""
    
    ranges = get_reference_ranges()
    created = 0
    skipped = 0
    
    for range_data in ranges:
        # Check if already exists
        existing = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == range_data["field_code"],
            LabReferenceRange.sex == range_data.get("sex", "ANY"),
            LabReferenceRange.age_min_days == range_data.get("age_min_days"),
            LabReferenceRange.age_max_days == range_data.get("age_max_days")
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        rr = LabReferenceRange(
            field_code=range_data["field_code"],
            sex=range_data.get("sex", "ANY"),
            age_min_days=range_data.get("age_min_days"),
            age_max_days=range_data.get("age_max_days"),
            low=range_data.get("low"),
            high=range_data.get("high"),
            critical_low=range_data.get("critical_low"),
            critical_high=range_data.get("critical_high"),
            unit=range_data.get("unit"),
            text_range=range_data.get("text_range")
        )
        db.add(rr)
        created += 1
    
    db.commit()
    print(f"Created {created} reference ranges, skipped {created} existing.")
    return created, skipped


def main():
    """Main function to seed reference ranges."""
    print("Starting Ghana Lab Reference Ranges seeder...")
    
    db = SessionLocal()
    try:
        created, skipped = seed_reference_ranges(db)
        print(f"\n✓ Seeding complete!")
        print(f"  - Created: {created} new reference ranges")
        print(f"  - Skipped: {skipped} existing ranges")
    except Exception as e:
        print(f"\n✗ Error seeding reference ranges: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
