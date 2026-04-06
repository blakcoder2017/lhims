#!/usr/bin/env python3
"""
Complete Ghana Lab Menu Seeder

This script creates:
1. Lab Test Catalog entries (lab_tests table)
2. Lab Templates with parameters
3. Reference Ranges linked to templates

All tests from the hospital-approved test menu are included.

Usage:
    python3 seed_complete_lab_menu.py
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from uuid import uuid4

from app.main import app
from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import LabTemplate, LabTemplateVersion, LabReferenceRange, LabOptionSet

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_menu():
    """Complete Ghana hospital-approved test menu with templates and reference ranges."""
    
    return [
        # ==================== HAEMATOLOGY ====================
        {
            "test_name": "Full Blood Count (FBC)",
            "test_code": "FBC",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Complete blood count with differential",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "hb": {"code": "hb", "type": "numeric", "label": "Haemoglobin", "unit": "g/dL", "decimals": 1},
                    "hct": {"code": "hct", "type": "numeric", "label": "Hematocrit", "unit": "%", "decimals": 1},
                    "rbc_count": {"code": "rbc_count", "type": "numeric", "label": "RBC Count", "unit": "x10^12/L", "decimals": 2},
                    "wbc_count": {"code": "wbc_count", "type": "numeric", "label": "WBC Count", "unit": "x10^9/L", "decimals": 2},
                    "neutrophils": {"code": "neutrophils", "type": "numeric", "label": "Neutrophils", "unit": "%", "decimals": 1},
                    "lymphocytes": {"code": "lymphocytes", "type": "numeric", "label": "Lymphocytes", "unit": "%", "decimals": 1},
                    "monocytes": {"code": "monocytes", "type": "numeric", "label": "Monocytes", "unit": "%", "decimals": 1},
                    "eosinophils": {"code": "eosinophils", "type": "numeric", "label": "Eosinophils", "unit": "%", "decimals": 1},
                    "basophils": {"code": "basophils", "type": "numeric", "label": "Basophils", "unit": "%", "decimals": 1},
                    "platelet_count": {"code": "platelet_count", "type": "numeric", "label": "Platelet Count", "unit": "x10^9/L", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "hb", "sex": "M", "age_min_days": 6570, "high": 17.5, "low": 12.5, "critical_low": 7.0, "critical_high": 20.0, "unit": "g/dL"},
                {"field_code": "hb", "sex": "F", "age_min_days": 6570, "high": 15.5, "low": 11.5, "critical_low": 7.0, "critical_high": 20.0, "unit": "g/dL"},
                {"field_code": "hb", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, "high": 22.5, "low": 14.5, "critical_low": 10.0, "critical_high": 25.0, "unit": "g/dL"},
                {"field_code": "hct", "sex": "M", "age_min_days": 6570, "high": 50, "low": 36, "unit": "%"},
                {"field_code": "hct", "sex": "F", "age_min_days": 6570, "high": 46, "low": 34, "unit": "%"},
                {"field_code": "rbc_count", "sex": "M", "age_min_days": 6570, "high": 6.5, "low": 4.5, "unit": "x10^12/L"},
                {"field_code": "rbc_count", "sex": "F", "age_min_days": 6570, "high": 5.8, "low": 3.8, "unit": "x10^12/L"},
                {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 0, "high": 11.0, "low": 4.0, "critical_low": 2.0, "critical_high": 30.0, "unit": "x10^9/L"},
                {"field_code": "platelet_count", "sex": "ANY", "age_min_days": 0, "high": 400, "low": 150, "critical_low": 20, "critical_high": 1000, "unit": "x10^9/L"}
            ]
        },
        {
            "test_name": "Haemoglobin (Hb)",
            "test_code": "HB",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Haemoglobin estimation",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "hb": {"code": "hb", "type": "numeric", "label": "Haemoglobin", "unit": "g/dL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "hb", "sex": "M", "age_min_days": 6570, "high": 17.5, "low": 12.5, "critical_low": 7.0, "critical_high": 20.0, "unit": "g/dL"},
                {"field_code": "hb", "sex": "F", "age_min_days": 6570, "high": 15.5, "low": 11.5, "critical_low": 7.0, "critical_high": 20.0, "unit": "g/dL"},
                {"field_code": "hb", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, "high": 22.5, "low": 14.5, "critical_low": 10.0, "critical_high": 25.0, "unit": "g/dL"}
            ]
        },
        {
            "test_name": "ESR",
            "test_code": "ESR",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "Whole Blood",
            "description": "Erythrocyte Sedimentation Rate",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "esr": {"code": "esr", "type": "numeric", "label": "ESR", "unit": "mm/hr", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "esr", "sex": "M", "age_min_days": 6570, "high": 15, "low": 0, "unit": "mm/hr"},
                {"field_code": "esr", "sex": "F", "age_min_days": 6570, "high": 20, "low": 0, "unit": "mm/hr"},
                {"field_code": "esr", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "high": 15, "low": 0, "unit": "mm/hr"}
            ]
        },
        {
            "test_name": "Reticulocyte Count",
            "test_code": "RETIC",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Reticulocyte count",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "retic_count": {"code": "retic_count", "type": "numeric", "label": "Reticulocyte Count", "unit": "%", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "retic_count", "sex": "ANY", "age_min_days": 0, "high": 2.5, "low": 0.5, "unit": "%"}
            ]
        },
        {
            "test_name": "Coombs Test",
            "test_code": "COOMBS",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Direct Coombs test",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "coombs": {"code": "coombs", "type": "choice", "label": "Coombs Test", "options": ["Negative", "Positive"]}
                }
            },
            "reference_ranges": [
                {"field_code": "coombs", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"}
            ]
        },
        {
            "test_name": "Sickling Test",
            "test_code": "SICKLE",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Sickle cell test",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "sickling": {"code": "sickling", "type": "choice", "label": "Sickling", "options": ["Negative", "Positive", "Trait", "Disease"]}
                }
            },
            "reference_ranges": [
                {"field_code": "sickling", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive,Trait,Disease"}
            ]
        },
        {
            "test_name": "Blood Grouping",
            "test_code": "BG",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "ABO and Rhesus blood grouping",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "abo_group": {"code": "abo_group", "type": "choice", "label": "ABO Group", "options": ["A", "B", "AB", "O"]},
                    "rh_type": {"code": "rh_type", "type": "choice", "label": "Rh Type", "options": ["Positive", "Negative"]}
                }
            }
        },
        {
            "test_name": "HB ELECTROPHORESIS (HB PHENOTYPE)",
            "test_code": "HBELEC",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Haemoglobin electrophoresis for sickle cell screening and phenotype determination",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "sickle_cell_screening": {"code": "sickle_cell_screening", "type": "choice", "label": "Sickle Cell Screening", 
                                            "options": ["Negative", "Positive", "Not Done"]},
                    "hb_phenotype": {"code": "hb_phenotype", "type": "choice", "label": "HB-Phenotype", 
                                   "options": ["AA", "AS", "SS", "AC", "SC", "CC", "Other"]}
                }
            }
        },
        {
            "test_name": "G6PD",
            "test_code": "G6PD",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Glucose-6-Phosphate Dehydrogenase",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "g6pd": {"code": "g6pd", "type": "numeric", "label": "G6PD", "unit": "U/gHb", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "g6pd", "sex": "ANY", "age_min_days": 0, "high": 10.0, "low": 4.6, "unit": "U/gHb"}
            ]
        },
        {
            "test_name": "BF for MP",
            "test_code": "BFMP",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "Blood Smear",
            "description": "Blood film for Malaria Parasite",
            "template": {
                "discipline": "HEMATOLOGY",
                "fields": {
                    "malaria": {"code": "malaria", "type": "choice", "label": "Malaria Parasite", "options": ["Negative", "Positive"]},
                    "parasite_species": {"code": "parasite_species", "type": "choice", "label": "Species", "options": ["P.falciparum", "P.vivax", "P.malariae", "P.ovale", "Mixed"]}
                }
            },
            "reference_ranges": [
                {"field_code": "malaria", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"}
            ]
        },

        # ==================== BIOCHEMISTRY ====================
        {
            "test_name": "Liver Function Test (LFT)",
            "test_code": "LFT",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Liver function test panel",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "alt": {"code": "alt", "type": "numeric", "label": "ALT", "unit": "U/L", "decimals": 0},
                    "ast": {"code": "ast", "type": "numeric", "label": "AST", "unit": "U/L", "decimals": 0},
                    "alp": {"code": "alp", "type": "numeric", "label": "ALP", "unit": "U/L", "decimals": 0},
                    "total_bilirubin": {"code": "total_bilirubin", "type": "numeric", "label": "Total Bilirubin", "unit": "mg/dL", "decimals": 2},
                    "direct_bilirubin": {"code": "direct_bilirubin", "type": "numeric", "label": "Direct Bilirubin", "unit": "mg/dL", "decimals": 2},
                    "total_protein": {"code": "total_protein", "type": "numeric", "label": "Total Protein", "unit": "g/dL", "decimals": 1},
                    "albumin": {"code": "albumin", "type": "numeric", "label": "Albumin", "unit": "g/dL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "alt", "sex": "M", "age_min_days": 6570, "high": 40, "low": 0, "critical_high": 500, "unit": "U/L"},
                {"field_code": "alt", "sex": "F", "age_min_days": 6570, "high": 32, "low": 0, "critical_high": 500, "unit": "U/L"},
                {"field_code": "ast", "sex": "M", "age_min_days": 6570, "high": 37, "low": 0, "critical_high": 500, "unit": "U/L"},
                {"field_code": "ast", "sex": "F", "age_min_days": 6570, "high": 31, "low": 0, "critical_high": 500, "unit": "U/L"},
                {"field_code": "alp", "sex": "ANY", "age_min_days": 6570, "high": 140, "low": 20, "critical_high": 500, "unit": "U/L"},
                {"field_code": "total_bilirubin", "sex": "ANY", "age_min_days": 6570, "high": 1.2, "low": 0.2, "critical_high": 10.0, "unit": "mg/dL"},
                {"field_code": "albumin", "sex": "ANY", "age_min_days": 0, "high": 5.5, "low": 3.5, "unit": "g/dL"},
                {"field_code": "total_protein", "sex": "ANY", "age_min_days": 0, "high": 8.3, "low": 6.0, "unit": "g/dL"}
            ]
        },
        {
            "test_name": "Renal Function Test (RFT)",
            "test_code": "RFT",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Renal function test (BUE & Creatinine)",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "creatinine": {"code": "creatinine", "type": "numeric", "label": "Creatinine", "unit": "mg/dL", "decimals": 2},
                    "bun": {"code": "bun", "type": "numeric", "label": "BUN", "unit": "mg/dL", "decimals": 1},
                    "egfr": {"code": "egfr", "type": "numeric", "label": "eGFR", "unit": "mL/min", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "high": 1.3, "low": 0.7, "critical_high": 6.0, "unit": "mg/dL"},
                {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "high": 1.1, "low": 0.6, "critical_high": 6.0, "unit": "mg/dL"},
                {"field_code": "bun", "sex": "ANY", "age_min_days": 0, "high": 20, "low": 7, "critical_high": 60, "unit": "mg/dL"},
                {"field_code": "egfr", "sex": "ANY", "age_min_days": 6570, "high": 120, "low": 90, "unit": "mL/min"}
            ]
        },
        {
            "test_name": "Electrolytes",
            "test_code": "ELECT",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum electrolytes",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "sodium": {"code": "sodium", "type": "numeric", "label": "Sodium (Na)", "unit": "mEq/L", "decimals": 0},
                    "potassium": {"code": "potassium", "type": "numeric", "label": "Potassium (K)", "unit": "mEq/L", "decimals": 1},
                    "chloride": {"code": "chloride", "type": "numeric", "label": "Chloride (Cl)", "unit": "mEq/L", "decimals": 0},
                    "bicarbonate": {"code": "bicarbonate", "type": "numeric", "label": "Bicarbonate", "unit": "mEq/L", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "high": 145, "low": 136, "critical_low": 120, "critical_high": 160, "unit": "mEq/L"},
                {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "high": 5.0, "low": 3.5, "critical_low": 2.5, "critical_high": 6.5, "unit": "mEq/L"},
                {"field_code": "chloride", "sex": "ANY", "age_min_days": 0, "high": 106, "low": 98, "unit": "mEq/L"},
                {"field_code": "bicarbonate", "sex": "ANY", "age_min_days": 0, "high": 28, "low": 22, "unit": "mEq/L"}
            ]
        },
        {
            "test_name": "Lipid Profile",
            "test_code": "LIPID",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum (Fasting)",
            "description": "Complete lipid profile",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "cholesterol_total": {"code": "cholesterol_total", "type": "numeric", "label": "Total Cholesterol", "unit": "mg/dL", "decimals": 0},
                    "triglycerides": {"code": "triglycerides", "type": "numeric", "label": "Triglycerides", "unit": "mg/dL", "decimals": 0},
                    "ldl_cholesterol": {"code": "ldl_cholesterol", "type": "numeric", "label": "LDL Cholesterol", "unit": "mg/dL", "decimals": 0},
                    "hdl_cholesterol": {"code": "hdl_cholesterol", "type": "numeric", "label": "HDL Cholesterol", "unit": "mg/dL", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "cholesterol_total", "sex": "ANY", "age_min_days": 0, "high": 200, "low": 0, "critical_high": 300, "unit": "mg/dL"},
                {"field_code": "triglycerides", "sex": "ANY", "age_min_days": 0, "high": 150, "low": 0, "critical_high": 500, "unit": "mg/dL"},
                {"field_code": "ldl_cholesterol", "sex": "ANY", "age_min_days": 0, "high": 100, "low": 0, "critical_high": 190, "unit": "mg/dL"},
                {"field_code": "hdl_cholesterol", "sex": "M", "age_min_days": 0, "high": 60, "low": 40, "unit": "mg/dL"},
                {"field_code": "hdl_cholesterol", "sex": "F", "age_min_days": 0, "high": 70, "low": 50, "unit": "mg/dL"}
            ]
        },
        {
            "test_name": "Fasting Blood Sugar (FBS)",
            "test_code": "FBS",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Plasma (Fasting)",
            "description": "Fasting blood glucose",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "glucose_fasting": {"code": "glucose_fasting", "type": "numeric", "label": "Fasting Blood Sugar", "unit": "mg/dL", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "glucose_fasting", "sex": "ANY", "age_min_days": 0, "high": 100, "low": 70, "critical_low": 40, "critical_high": 400, "unit": "mg/dL"}
            ]
        },
        {
            "test_name": "Random Blood Sugar (RBS)",
            "test_code": "RBS",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Plasma",
            "description": "Random blood glucose",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "glucose_random": {"code": "glucose_random", "type": "numeric", "label": "Random Blood Sugar", "unit": "mg/dL", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "glucose_random", "sex": "ANY", "age_min_days": 0, "high": 140, "low": 70, "critical_low": 40, "critical_high": 400, "unit": "mg/dL"}
            ]
        },
        {
            "test_name": "HbA1c",
            "test_code": "HBA1C",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Glycated haemoglobin",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "hba1c": {"code": "hba1c", "type": "numeric", "label": "HbA1c", "unit": "%", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "hba1c", "sex": "ANY", "age_min_days": 0, "high": 5.6, "low": 4.0, "unit": "%"}
            ]
        },
        {
            "test_name": "Serum Bilirubin",
            "test_code": "BILI",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Total and direct bilirubin",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "total_bilirubin": {"code": "total_bilirubin", "type": "numeric", "label": "Total Bilirubin", "unit": "mg/dL", "decimals": 2},
                    "direct_bilirubin": {"code": "direct_bilirubin", "type": "numeric", "label": "Direct Bilirubin", "unit": "mg/dL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "total_bilirubin", "sex": "ANY", "age_min_days": 6570, "high": 1.2, "low": 0.2, "critical_high": 10.0, "unit": "mg/dL"},
                {"field_code": "direct_bilirubin", "sex": "ANY", "age_min_days": 0, "high": 0.3, "low": 0.0, "unit": "mg/dL"}
            ]
        },

        # ==================== THYROID ====================
        {
            "test_name": "Thyroid Profile",
            "test_code": "THYROID",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "TSH, T3, T4",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "tsh": {"code": "tsh", "type": "numeric", "label": "TSH", "unit": "mIU/L", "decimals": 2},
                    "ft4": {"code": "ft4", "type": "numeric", "label": "Free T4", "unit": "ng/dL", "decimals": 2},
                    "ft3": {"code": "ft3", "type": "numeric", "label": "Free T3", "unit": "pg/mL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "tsh", "sex": "ANY", "age_min_days": 6570, "high": 4.0, "low": 0.4, "critical_low": 0.1, "critical_high": 10.0, "unit": "mIU/L"},
                {"field_code": "ft4", "sex": "ANY", "age_min_days": 6570, "high": 1.8, "low": 0.8, "critical_low": 0.1, "critical_high": 4.0, "unit": "ng/dL"},
                {"field_code": "ft3", "sex": "ANY", "age_min_days": 6570, "high": 4.2, "low": 2.3, "critical_low": 1.0, "critical_high": 6.0, "unit": "pg/mL"}
            ]
        },

        # ==================== HORMONES ====================
        {
            "test_name": "Testosterone",
            "test_code": "TESTO",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum testosterone",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "testosterone": {"code": "testosterone", "type": "numeric", "label": "Testosterone", "unit": "ng/dL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "testosterone", "sex": "M", "age_min_days": 6570, "high": 1000, "low": 300, "unit": "ng/dL"},
                {"field_code": "testosterone", "sex": "F", "age_min_days": 6570, "high": 70, "low": 15, "unit": "ng/dL"}
            ]
        },
        {
            "test_name": "FSH",
            "test_code": "FSH",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Follicle Stimulating Hormone",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "fsh": {"code": "fsh", "type": "numeric", "label": "FSH", "unit": "mIU/mL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "fsh", "sex": "M", "age_min_days": 6570, "high": 18.0, "low": 1.0, "unit": "mIU/mL"},
                {"field_code": "fsh", "sex": "F", "age_min_days": 6570, "age_max_days": 12775, "high": 12.5, "low": 3.5, "unit": "mIU/mL"},
                {"field_code": "fsh", "sex": "F", "age_min_days": 12775, "high": 134.8, "low": 25.8, "unit": "mIU/mL"}
            ]
        },
        {
            "test_name": "LH",
            "test_code": "LH",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Luteinizing Hormone",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "lh": {"code": "lh", "type": "numeric", "label": "LH", "unit": "mIU/mL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "lh", "sex": "M", "age_min_days": 6570, "high": 8.0, "low": 1.2, "unit": "mIU/mL"},
                {"field_code": "lh", "sex": "F", "age_min_days": 6570, "age_max_days": 12775, "high": 12.0, "low": 2.0, "unit": "mIU/mL"},
                {"field_code": "lh", "sex": "F", "age_min_days": 12775, "high": 62.0, "low": 15.0, "unit": "mIU/mL"}
            ]
        },
        {
            "test_name": "Progesterone",
            "test_code": "PROG",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum progesterone",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "progesterone": {"code": "progesterone", "type": "numeric", "label": "Progesterone", "unit": "ng/mL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "progesterone", "sex": "M", "age_min_days": 6570, "high": 0.3, "low": 0.1, "unit": "ng/mL"},
                {"field_code": "progesterone", "sex": "F", "age_min_days": 6570, "high": 0.3, "low": 0.1, "unit": "ng/mL"}
            ]
        },
        {
            "test_name": "Estrogen/Estradiol",
            "test_code": "E2",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum estradiol",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "estradiol": {"code": "estradiol", "type": "numeric", "label": "Estradiol (E2)", "unit": "pg/mL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "estradiol", "sex": "M", "age_min_days": 6570, "high": 50, "low": 10, "unit": "pg/mL"},
                {"field_code": "estradiol", "sex": "F", "age_min_days": 6570, "age_max_days": 12775, "high": 400, "low": 30, "unit": "pg/mL"},
                {"field_code": "estradiol", "sex": "F", "age_min_days": 12775, "high": 30, "low": 10, "unit": "pg/mL"}
            ]
        },
        {
            "test_name": "Prolactin",
            "test_code": "PRL",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum prolactin",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "prolactin": {"code": "prolactin", "type": "numeric", "label": "Prolactin", "unit": "ng/mL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "prolactin", "sex": "M", "age_min_days": 6570, "high": 15.0, "low": 4.0, "critical_high": 25.0, "unit": "ng/mL"},
                {"field_code": "prolactin", "sex": "F", "age_min_days": 6570, "high": 23.0, "low": 4.0, "critical_high": 25.0, "unit": "ng/mL"}
            ]
        },
        {
            "test_name": "Cortisol",
            "test_code": "CORT",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum (Morning)",
            "description": "Morning serum cortisol",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "cortisol": {"code": "cortisol", "type": "numeric", "label": "Cortisol", "unit": "mcg/dL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "cortisol", "sex": "ANY", "age_min_days": 6570, "high": 25.0, "low": 5.0, "critical_low": 3.0, "critical_high": 30.0, "unit": "mcg/dL"}
            ]
        },
        {
            "test_name": "PSA",
            "test_code": "PSA",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Prostate Specific Antigen",
            "template": {
                "discipline": "HORMONAL",
                "fields": {
                    "psa": {"code": "psa", "type": "numeric", "label": "PSA", "unit": "ng/mL", "decimals": 2}
                }
            },
            "reference_ranges": [
                {"field_code": "psa", "sex": "M", "age_min_days": 14600, "age_max_days": 36500, "high": 4.0, "low": 0.0, "critical_high": 10.0, "unit": "ng/mL"},
                {"field_code": "psa", "sex": "M", "age_min_days": 36500, "high": 6.5, "low": 0.0, "critical_high": 10.0, "unit": "ng/mL"}
            ]
        },

        # ==================== VIROLOGY ====================
        {
            "test_name": "HIV 1 & 2",
            "test_code": "HIV",
            "test_category": "Virology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "HIV 1 & 2 screening",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "hiv_1_2": {"code": "hiv_1_2", "type": "choice", "label": "HIV 1 & 2", "options": ["Negative", "Positive", "Indeterminate"]}
                }
            },
            "reference_ranges": [
                {"field_code": "hiv_1_2", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive,Indeterminate"}
            ]
        },
        {
            "test_name": "HIV Viral Load",
            "test_code": "HIVVL",
            "test_category": "Virology",
            "test_type": "Quantitative",
            "specimen_type": "Plasma (EDTA)",
            "description": "HIV viral load",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "hiv_viral_load": {"code": "hiv_viral_load", "type": "numeric", "label": "HIV Viral Load", "unit": "copies/mL", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "hiv_viral_load", "sex": "ANY", "age_min_days": 0, "high": 20, "low": 0, "unit": "copies/mL"}
            ]
        },
        {
            "test_name": "CD4 Count",
            "test_code": "CD4",
            "test_category": "Virology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "CD4 T-cell count",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "cd4_count": {"code": "cd4_count", "type": "numeric", "label": "CD4 Count", "unit": "cells/mm3", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "cd4_count", "sex": "ANY", "age_min_days": 6570, "high": 1500, "low": 500, "critical_low": 200, "unit": "cells/mm3"}
            ]
        },
        {
            "test_name": "Hepatitis B Surface Antigen",
            "test_code": "HBSAG",
            "test_category": "Virology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "HBsAg screening",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "hbsag": {"code": "hbsag", "type": "choice", "label": "HBsAg", "options": ["Negative", "Positive"]}
                }
            },
            "reference_ranges": [
                {"field_code": "hbsag", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"}
            ]
        },
        {
            "test_name": "Hepatitis B Viral Load",
            "test_code": "HBVVL",
            "test_category": "Virology",
            "test_type": "Quantitative",
            "specimen_type": "Plasma",
            "description": "HBV viral load",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "hbv_viral_load": {"code": "hbv_viral_load", "type": "numeric", "label": "HBV Viral Load", "unit": "IU/mL", "decimals": 0}
                }
            },
            "reference_ranges": [
                {"field_code": "hbv_viral_load", "sex": "ANY", "age_min_days": 0, "high": 20, "low": 0, "unit": "IU/mL"}
            ]
        },
        {
            "test_name": "HCV",
            "test_code": "HCV",
            "test_category": "Virology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Hepatitis C antibody",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "hcv": {"code": "hcv", "type": "choice", "label": "HCV", "options": ["Negative", "Positive"]}
                }
            },
            "reference_ranges": [
                {"field_code": "hcv", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"}
            ]
        },
        {
            "test_name": "Syphilis (VDRL)",
            "test_code": "VDRL",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "VDRL test for syphilis",
            "template": {
                "discipline": "VIROLOGY",
                "fields": {
                    "vdrl": {"code": "vdrl", "type": "choice", "label": "VDRL", "options": ["Non-reactive", "Reactive", "Weakly reactive"]}
                }
            },
            "reference_ranges": [
                {"field_code": "vdrl", "sex": "ANY", "age_min_days": 0, "text_range": "Non-reactive,Reactive,Weakly reactive"}
            ]
        },
        {
            "test_name": "Widal",
            "test_code": "WIDAL",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Widal test for typhoid",
            "template": {
                "discipline": "SEROLOGY",
                "fields": {
                    "widal": {"code": "widal", "type": "choice", "label": "Widal", "options": ["Negative", "Positive 1:40", "Positive 1:80", "Positive 1:160", "Positive 1:320"]}
                }
            },
            "reference_ranges": [
                {"field_code": "widal", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive 1:40,Positive 1:80,Positive 1:160,Positive 1:320"}
            ]
        },
        {
            "test_name": "Pregnancy Test (Urine)",
            "test_code": "PTU",
            "test_category": "Biochemistry",
            "test_type": "Qualitative",
            "specimen_type": "Urine",
            "description": "Urine pregnancy test",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "pregnancy_test_urine": {"code": "pregnancy_test_urine", "type": "choice", "label": "Pregnancy Test", "options": ["Negative", "Positive"]}
                }
            },
            "reference_ranges": [
                {"field_code": "pregnancy_test_urine", "sex": "F", "age_min_days": 4380, "age_max_days": 18250, "text_range": "Negative,Positive"}
            ]
        },
        {
            "test_name": "Pregnancy Test (Serum)",
            "test_code": "PTS",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum β-HCG",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "beta_hcg": {"code": "beta_hcg", "type": "numeric", "label": "β-HCG", "unit": "mIU/mL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "beta_hcg", "sex": "F", "age_min_days": 4380, "age_max_days": 18250, "high": 5.0, "low": 0, "unit": "mIU/mL"}
            ]
        },
        {
            "test_name": "H. pylori (Blood)",
            "test_code": "HPYLORIB",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "H. pylori antibody",
            "template": {
                "discipline": "SEROLOGY",
                "fields": {
                    "h_pylori_blood": {"code": "h_pylori_blood", "type": "choice", "label": "H. pylori", "options": ["Negative", "Positive"]}
                }
            },
            "reference_ranges": [
                {"field_code": "h_pylori_blood", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"}
            ]
        },
        {
            "test_name": "AFP",
            "test_code": "AFP",
            "test_category": "Tumor Markers",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Alpha Fetoprotein",
            "template": {
                "discipline": "BIOCHEMISTRY",
                "fields": {
                    "afp": {"code": "afp", "type": "numeric", "label": "AFP", "unit": "ng/mL", "decimals": 1}
                }
            },
            "reference_ranges": [
                {"field_code": "afp", "sex": "ANY", "age_min_days": 6570, "high": 10, "low": 0, "unit": "ng/mL"}
            ]
        },

        # ==================== MICROBIOLOGY ====================
        {
            "test_name": "Urine C/S",
            "test_code": "URINECS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Urine (Midstream)",
            "description": "Urine culture and sensitivity",
            "template": {
                "discipline": "MICROBIOLOGY",
                "fields": {
                    "culture_result": {"code": "culture_result", "type": "choice", "label": "Culture Result", "options": ["No growth", "Mixed growth", "Pure growth"]},
                    "organism": {"code": "organism", "type": "text", "label": "Organism Isolated"},
                    "sensitivity": {"code": "sensitivity", "type": "text", "label": "Sensitivity Pattern"}
                }
            }
        },
        {
            "test_name": "Blood C/S",
            "test_code": "BLOODCS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Blood (Sterile)",
            "description": "Blood culture and sensitivity",
            "template": {
                "discipline": "MICROBIOLOGY",
                "fields": {
                    "culture_result": {"code": "culture_result", "type": "choice", "label": "Culture Result", "options": ["No growth", "Growth"]},
                    "organism": {"code": "organism", "type": "text", "label": "Organism Isolated"},
                    "sensitivity": {"code": "sensitivity", "type": "text", "label": "Sensitivity Pattern"}
                }
            }
        },
        {
            "test_name": "Stool C/S",
            "test_code": "STOOLCS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Stool",
            "description": "Stool culture and sensitivity",
            "template": {
                "discipline": "MICROBIOLOGY",
                "fields": {
                    "culture_result": {"code": "culture_result", "type": "choice", "label": "Culture Result", "options": ["No pathogens isolated", "Pathogens isolated"]},
                    "organism": {"code": "organism", "type": "text", "label": "Organism Isolated"},
                    "parasite": {"code": "parasite", "type": "choice", "label": "Parasite", "options": ["Not seen", "Ova", "Cyst", "Trophozoite"]}
                }
            }
        },
        {
            "test_name": "Sputum C/S",
            "test_code": "SPUTUMCS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Sputum",
            "description": "Sputum culture and sensitivity",
            "template": {
                "discipline": "MICROBIOLOGY",
                "fields": {
                    "culture_result": {"code": "culture_result", "type": "choice", "label": "Culture Result", "options": ["No growth", "Normal flora", "Pathogenic growth"]},
                    "organism": {"code": "organism", "type": "text", "label": "Organism Isolated"},
                    "afb": {"code": "afb", "type": "choice", "label": "AFB", "options": ["Not seen", "Seen", "Scanty"]}
                }
            }
        },
        {
            "test_name": "Wound Swab C/S",
            "test_code": "WOUNDCS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Wound Swab",
            "description": "Wound swab culture and sensitivity",
            "template": {
                "discipline": "MICROBIOLOGY",
                "fields": {
                    "culture_result": {"code": "culture_result", "type": "choice", "label": "Culture Result", "options": ["No growth", "Mixed growth", "Pure growth"]},
                    "organism": {"code": "organism", "type": "text", "label": "Organism Isolated"},
                    "sensitivity": {"code": "sensitivity", "type": "text", "label": "Sensitivity Pattern"}
                }
            }
        },
        {
            "test_name": "HVS C/S",
            "test_code": "HVS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "High Vaginal Swab",
            "description": "HVS culture and sensitivity",
            "template": {
                "discipline": "MICROBIOLOGY",
                "fields": {
                    "culture_result": {"code": "culture_result", "type": "choice", "label": "Culture Result", "options": ["No growth", "Mixed growth", "Pure growth"]},
                    "organism": {"code": "organism", "type": "text", "label": "Organism Isolated"},
                    "sensitivity": {"code": "sensitivity", "type": "text", "label": "Sensitivity Pattern"}
                }
            }
        }
    ]


def seed_complete_menu(db: Session):
    """Seed the complete lab menu with templates and reference ranges."""
    
    test_menu = get_test_menu()
    tests_created = 0
    templates_created = 0
    ranges_created = 0
    
    for test_data in test_menu:
        # Check if test exists
        existing_test = db.query(LabTest).filter(
            LabTest.test_code == test_data["test_code"]
        ).first()
        
        if existing_test:
            test = existing_test
            print(f"  Updating test: {test_data['test_name']}")
        else:
            test = LabTest(
                test_name=test_data["test_name"],
                test_code=test_data["test_code"],
                test_category=test_data["test_category"],
                test_type=test_data["test_type"],
                specimen_type=test_data["specimen_type"],
                description=test_data["description"]
            )
            db.add(test)
            db.flush()
            tests_created += 1
            print(f"  Creating test: {test_data['test_name']}")
        
        # Create template
        template_data = test_data.get("template", {})
        discipline = template_data.get("discipline", test_data["test_category"].upper())
        
        template = db.query(LabTemplate).filter(
            LabTemplate.name == test_data["test_name"]
        ).first()
        
        if not template:
            template = LabTemplate(
                name=test_data["test_name"],
                discipline=discipline,
                status="PUBLISHED",
                current_version=1
            )
            db.add(template)
            db.flush()
            templates_created += 1
        
        # Check if template version exists
        existing_version = db.query(LabTemplateVersion).filter(
            LabTemplateVersion.template_id == template.id,
            LabTemplateVersion.version == 1
        ).first()
        
        # Create template version with fields
        schema_json = {
            "meta": {
                "name": test_data["test_name"],
                "discipline": discipline,
                "version": 1,
                "description": test_data["description"]
            },
            "layout": {
                "sections": [
                    {
                        "id": "sec_main",
                        "title": "Results",
                        "rows": [
                            {
                                "columns": [
                                    {"width": 12, "items": list(template_data.get("fields", {}).keys())}
                                ]
                            }
                        ]
                    }
                ]
            },
            "fields": template_data.get("fields", {}),
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
        
        if existing_version:
            # Update existing version
            existing_version.schema_json = schema_json
            print(f"    Updating template version for: {test_data['test_name']}")
        else:
            version = LabTemplateVersion(
                template_id=template.id,
                version=1,
                status="PUBLISHED",
                schema_json=schema_json
            )
            db.add(version)
        
        # Update test with template link
        test.template_id = template.id
        test.template_version = 1
        
        # Create reference ranges
        for rr_data in test_data.get("reference_ranges", []):
            # Check if range exists
            existing_rr = db.query(LabReferenceRange).filter(
                LabReferenceRange.field_code == rr_data.get("field_code", ""),
                LabReferenceRange.sex == rr_data.get("sex", "ANY"),
                LabReferenceRange.age_min_days == rr_data.get("age_min_days")
            ).first()
            
            if not existing_rr:
                rr = LabReferenceRange(
                    field_code=rr_data.get("field_code", ""),
                    sex=rr_data.get("sex", "ANY"),
                    age_min_days=rr_data.get("age_min_days"),
                    age_max_days=rr_data.get("age_max_days"),
                    low=Decimal(str(rr_data["low"])) if "low" in rr_data else None,
                    high=Decimal(str(rr_data["high"])) if "high" in rr_data else None,
                    critical_low=Decimal(str(rr_data["critical_low"])) if "critical_low" in rr_data else None,
                    critical_high=Decimal(str(rr_data["critical_high"])) if "critical_high" in rr_data else None,
                    unit=rr_data.get("unit"),
                    text_range=rr_data.get("text_range")
                )
                db.add(rr)
                ranges_created += 1
    
    db.commit()
    return tests_created, templates_created, ranges_created


def main():
    print("Starting Complete Ghana Lab Menu seeder...")
    print("This will create lab tests, templates, and reference ranges...")
    
    db = SessionLocal()
    try:
        tests, templates, ranges = seed_complete_menu(db)
        print(f"\n✓ Seeding complete!")
        print(f"  - Tests created/updated: {tests}")
        print(f"  - Templates created: {templates}")
        print(f"  - Reference ranges created: {ranges}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
