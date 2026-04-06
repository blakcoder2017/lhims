#!/usr/bin/env python3
"""
Seed script for comprehensive lab test templates with parameters and reference ranges.
Run this script to populate the database with standard lab test templates.

Usage:
    python seed_lab_templates.py

Requirements:
    - Database must be initialized (run init_db.py first)
    - Admin user must exist
"""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabOptionSet, LabReferenceRange
)
from app.models.lab_models import ReferenceRange
from app.models.user_models import User

# Database setup
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# COMPREHENSIVE LAB TEST TEMPLATES
# Each template includes:
# - Test parameters with field codes
# - Reference ranges for each parameter (by gender and age)
# =============================================================================

def create_option_sets(db: Session):
    """Create reusable option sets for lab tests."""
    print("Creating option sets...")
    
    option_sets_data = {
        "BLOOD_GROUP_OPTIONS": ["A", "B", "AB", "O"],
        "RH_FACTOR": ["Positive", "Negative"],
        "DIPSTICK_PROTEIN": ["Negative", "Trace", "1+", "2+", "3+", "4+"],
        "DIPSTICK_GLUCOSE": ["Negative", "Trace", "1+", "2+", "3+", "4+"],
        "DIPSTICK_KETONES": ["Negative", "Trace", "1+", "2+", "3+"],
        "DIPSTICK_BLOOD": ["Negative", "Trace", "Non-hemolyzed", "Hemolyzed"],
        "DIPSTICK_BILIRUBIN": ["Negative", "1+", "2+", "3+"],
        "DIPSTICK_UROBILINOGEN": ["Normal", "1+", "2+", "3+"],
        "DIPSTICK_NITRITE": ["Negative", "Positive"],
        "DIPSTICK_LEUKOCYTES": ["Negative", "Positive"],
        "MICROSCOPY_HPF": ["0-1", "1-5", "5-10", "10-20", ">20"],
        "WBC_MORPHOLOGY": ["Normal", "Left Shift", "Toxic Granulation", "Doehle Bodies"],
        "RBC_MORPHOLOGY": ["Normocytic", "Microcytic", "Macrocytic", "Hypochromic", "Anisocytosis", "Poikilocytosis"],
        "PLATELET_MORPHOLOGY": ["Adequate", "Reduced", "Increased", "Clumped"],
        "SICKLING_TEST": ["Negative", "Positive", "Sickle Cell Trait", "Sickle Cell Disease"],
        "MALARIA_RDT": ["Negative", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"],
        "Hepatitis_B_SURFACE": ["Non-reactive", "Reactive"],
        "Hepatitis_C_RESULT": ["Non-reactive", "Reactive"],
        "HIV_RESULT": ["Negative", "Positive", "Indeterminate"],
        "SYPHILIS_RESULT": ["Non-reactive", "Reactive"],
        "URINE_COLOR": ["Pale Yellow", "Yellow", "Dark Yellow", "Amber", "Brown", "Red"],
        "URINE_CLARITY": ["Clear", "Slightly Cloudy", "Cloudy", "Turbid"],
    }
    
    for code, options in option_sets_data.items():
        existing = db.query(LabOptionSet).filter(LabOptionSet.code == code).first()
        if not existing:
            obj = LabOptionSet(code=code, options_json=options)
            db.add(obj)
    
    db.commit()
    print(f"Created {len(option_sets_data)} option sets")


def create_cbc_template(db: Session, admin_user_id: int):
    """Create Complete Blood Count (CBC) template."""
    print("Creating CBC template...")
    
    # Check if template already exists
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Complete Blood Count (CBC)").first()
    if existing:
        print("CBC template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Complete Blood Count (CBC)",
            "discipline": "HEMATOLOGY",
            "description": "Complete blood count with differential"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_hemoglobin",
                    "title": "Hemoglobin & Hematocrit",
                    "rows": [
                        {"columns": [{"items": ["hb", "hct"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_rbc",
                    "title": "Red Blood Cell Indices",
                    "rows": [
                        {"columns": [{"items": ["rbc_count", "mcv", "mch", "mchc"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_wbc",
                    "title": "White Blood Cell Count",
                    "rows": [
                        {"columns": [{"items": ["wbc_count"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_differential",
                    "title": "Differential Count",
                    "rows": [
                        {"columns": [{"items": ["neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_platelets",
                    "title": "Platelets",
                    "rows": [
                        {"columns": [{"items": ["platelet_count"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_morphology",
                    "title": "Morphology",
                    "rows": [
                        {"columns": [{"items": ["rbcmorph", "wbc_morph", "platelet_morph"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "hb": {
                "code": "hb",
                "label": "Hemoglobin (Hb)",
                "type": "numeric",
                "unit": "g/dL",
                "decimals": 1,
                "critical": True,
                "critical_low": 7.0,
                "critical_high": 20.0
            },
            "hct": {
                "code": "hct",
                "label": "Hematocrit (Hct)",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "critical": True,
                "critical_low": 20.0,
                "critical_high": 60.0
            },
            "rbc_count": {
                "code": "rbc_count",
                "label": "RBC Count",
                "type": "numeric",
                "unit": "x10^12/L",
                "decimals": 2
            },
            "mcv": {
                "code": "mcv",
                "label": "MCV",
                "type": "numeric",
                "unit": "fL",
                "decimals": 1
            },
            "mch": {
                "code": "mch",
                "label": "MCH",
                "type": "numeric",
                "unit": "pg",
                "decimals": 1
            },
            "mchc": {
                "code": "mchc",
                "label": "MCHC",
                "type": "numeric",
                "unit": "g/dL",
                "decimals": 1
            },
            "wbc_count": {
                "code": "wbc_count",
                "label": "WBC Count",
                "type": "numeric",
                "unit": "x10^9/L",
                "decimals": 2,
                "critical": True,
                "critical_low": 2.0,
                "critical_high": 30.0
            },
            "neutrophils": {
                "code": "neutrophils",
                "label": "Neutrophils",
                "type": "numeric",
                "unit": "%",
                "decimals": 1
            },
            "lymphocytes": {
                "code": "lymphocytes",
                "label": "Lymphocytes",
                "type": "numeric",
                "unit": "%",
                "decimals": 1
            },
            "monocytes": {
                "code": "monocytes",
                "label": "Monocytes",
                "type": "numeric",
                "unit": "%",
                "decimals": 1
            },
            "eosinophils": {
                "code": "eosinophils",
                "label": "Eosinophils",
                "type": "numeric",
                "unit": "%",
                "decimals": 1
            },
            "basophils": {
                "code": "basophils",
                "label": "Basophils",
                "type": "numeric",
                "unit": "%",
                "decimals": 1
            },
            "platelet_count": {
                "code": "platelet_count",
                "label": "Platelet Count",
                "type": "numeric",
                "unit": "x10^9/L",
                "decimals": 0,
                "critical": True,
                "critical_low": 20.0,
                "critical_high": 1000.0
            },
            "rbcmorph": {
                "code": "rbcmorph",
                "label": "RBC Morphology",
                "type": "multichoice",
                "optionSet": "RBC_MORPHOLOGY"
            },
            "wbc_morph": {
                "code": "wbc_morph",
                "label": "WBC Morphology",
                "type": "multichoice",
                "optionSet": "WBC_MORPHOLOGY"
            },
            "platelet_morph": {
                "code": "platelet_morph",
                "label": "Platelet Morphology",
                "type": "choice",
                "optionSet": "PLATELET_MORPHOLOGY"
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Complete Blood Count (CBC)",
        discipline="HEMATOLOGY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial CBC template with all parameters and reference ranges",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created CBC template: {tmpl.id}")
    return tmpl


def create_lft_template(db: Session, admin_user_id: int):
    """Create Liver Function Tests template."""
    print("Creating LFT template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Liver Function Tests (LFT)").first()
    if existing:
        print("LFT template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Liver Function Tests (LFT)",
            "discipline": "CHEMISTRY",
            "description": "Comprehensive liver function test panel"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_bilirubin",
                    "title": "Bilirubin",
                    "rows": [
                        {"columns": [{"items": ["total_bili", "direct_bili", "indirect_bili"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_enzymes",
                    "title": "Liver Enzymes",
                    "rows": [
                        {"columns": [{"items": ["alt", "ast", "alp", "ggt"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_proteins",
                    "title": "Proteins",
                    "rows": [
                        {"columns": [{"items": ["total_protein", "albumin", "globulin"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "total_bili": {
                "code": "total_bili",
                "label": "Total Bilirubin",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 1,
                "critical": True,
                "critical_high": 170.0
            },
            "direct_bili": {
                "code": "direct_bili",
                "label": "Direct Bilirubin",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 1,
                "critical": True,
                "critical_high": 85.0
            },
            "indirect_bili": {
                "code": "indirect_bili",
                "label": "Indirect Bilirubin",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 1
            },
            "alt": {
                "code": "alt",
                "label": "ALT (SGPT)",
                "type": "numeric",
                "unit": "U/L",
                "decimals": 0,
                "critical": True,
                "critical_high": 500.0
            },
            "ast": {
                "code": "ast",
                "label": "AST (SGOT)",
                "type": "numeric",
                "unit": "U/L",
                "decimals": 0,
                "critical": True,
                "critical_high": 500.0
            },
            "alp": {
                "code": "alp",
                "label": "Alkaline Phosphatase",
                "type": "numeric",
                "unit": "U/L",
                "decimals": 0,
                "critical": True,
                "critical_high": 400.0
            },
            "ggt": {
                "code": "ggt",
                "label": "GGT",
                "type": "numeric",
                "unit": "U/L",
                "decimals": 0
            },
            "total_protein": {
                "code": "total_protein",
                "label": "Total Protein",
                "type": "numeric",
                "unit": "g/L",
                "decimals": 1
            },
            "albumin": {
                "code": "albumin",
                "label": "Albumin",
                "type": "numeric",
                "unit": "g/L",
                "decimals": 1,
                "critical": True,
                "critical_low": 20.0
            },
            "globulin": {
                "code": "globulin",
                "label": "Globulin",
                "type": "numeric",
                "unit": "g/L",
                "decimals": 1
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Liver Function Tests (LFT)",
        discipline="CHEMISTRY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial LFT template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created LFT template: {tmpl.id}")
    return tmpl


def create_rft_template(db: Session, admin_user_id: int):
    """Create Renal Function Tests template."""
    print("Creating RFT template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Renal Function Tests (RFT)").first()
    if existing:
        print("RFT template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Renal Function Tests (RFT)",
            "discipline": "CHEMISTRY",
            "description": "Kidney function test panel"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_urea",
                    "title": "Kidney Function",
                    "rows": [
                        {"columns": [{"items": ["urea", "creatinine", "egfr"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_electrolytes",
                    "title": "Electrolytes",
                    "rows": [
                        {"columns": [{"items": ["sodium", "potassium", "chloride", "bicarbonate"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_uric",
                    "title": "Uric Acid",
                    "rows": [
                        {"columns": [{"items": ["uric_acid"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "urea": {
                "code": "urea",
                "label": "Urea",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": True,
                "critical_high": 35.0
            },
            "creatinine": {
                "code": "creatinine",
                "label": "Creatinine",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 0,
                "critical": True,
                "critical_high": 707.0
            },
            "egfr": {
                "code": "egfr",
                "label": "eGFR",
                "type": "numeric",
                "unit": "mL/min/1.73m²",
                "decimals": 1,
                "critical": True,
                "critical_low": 15.0
            },
            "sodium": {
                "code": "sodium",
                "label": "Sodium (Na)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 0,
                "critical": True,
                "critical_low": 120.0,
                "critical_high": 160.0
            },
            "potassium": {
                "code": "potassium",
                "label": "Potassium (K)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": True,
                "critical_low": 2.5,
                "critical_high": 6.5
            },
            "chloride": {
                "code": "chloride",
                "label": "Chloride (Cl)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 0
            },
            "bicarbonate": {
                "code": "bicarbonate",
                "label": "Bicarbonate (HCO3)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 0
            },
            "uric_acid": {
                "code": "uric_acid",
                "label": "Uric Acid",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 0
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Renal Function Tests (RFT)",
        discipline="CHEMISTRY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial RFT template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created RFT template: {tmpl.id}")
    return tmpl


def create_lipid_template(db: Session, admin_user_id: int):
    """Create Lipid Profile template."""
    print("Creating Lipid Profile template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Lipid Profile").first()
    if existing:
        print("Lipid Profile template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Lipid Profile",
            "discipline": "CHEMISTRY",
            "description": "Complete lipid profile including cholesterol and triglycerides"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_cholesterol",
                    "title": "Cholesterol",
                    "rows": [
                        {"columns": [{"items": ["total_chol", "hdl", "ldl", "vldl"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_trig",
                    "title": "Triglycerides",
                    "rows": [
                        {"columns": [{"items": ["triglycerides"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_ratio",
                    "title": "Ratios",
                    "rows": [
                        {"columns": [{"items": ["chol_hdl_ratio"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "total_chol": {
                "code": "total_chol",
                "label": "Total Cholesterol",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "critical": True,
                "critical_high": 10.0
            },
            "hdl": {
                "code": "hdl",
                "label": "HDL Cholesterol",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "critical": True,
                "critical_low": 0.5
            },
            "ldl": {
                "code": "ldl",
                "label": "LDL Cholesterol",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "critical": True,
                "critical_high": 6.5
            },
            "vldl": {
                "code": "vldl",
                "label": "VLDL Cholesterol",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2
            },
            "triglycerides": {
                "code": "triglycerides",
                "label": "Triglycerides",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "critical": True,
                "critical_high": 11.3
            },
            "chol_hdl_ratio": {
                "code": "chol_hdl_ratio",
                "label": "Total Cholesterol/HDL Ratio",
                "type": "numeric",
                "unit": "ratio",
                "decimals": 1,
                "calculated": True,
                "formula": "total_chol / hdl"
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Lipid Profile",
        discipline="CHEMISTRY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Lipid Profile template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created Lipid Profile template: {tmpl.id}")
    return tmpl


def create_urinalysis_template(db: Session, admin_user_id: int):
    """Create Urinalysis template."""
    print("Creating Urinalysis template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Urinalysis").first()
    if existing:
        print("Urinalysis template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Urinalysis",
            "discipline": "GENERAL",
            "description": "Complete urinalysis with dipstick and microscopy"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_physical",
                    "title": "Physical Examination",
                    "rows": [
                        {"columns": [{"items": ["urine_color", "urine_clarity"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_dipstick",
                    "title": "Dipstick Results",
                    "rows": [
                        {"columns": [{"items": ["ph", "specific_gravity", "protein", "glucose", "ketones", "blood", "bilirubin", "urobilinogen", "nitrite", "leukocytes"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_microscopy",
                    "title": "Microscopy",
                    "rows": [
                        {"columns": [{"items": ["wbc_hpf", "rbc_hpf", "epithelial", "casts", "crystals", "bacteria", "yeast"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "urine_color": {
                "code": "urine_color",
                "label": "Color",
                "type": "choice",
                "optionSet": "URINE_COLOR"
            },
            "urine_clarity": {
                "code": "urine_clarity",
                "label": "Clarity",
                "type": "choice",
                "optionSet": "URINE_CLARITY"
            },
            "ph": {
                "code": "ph",
                "label": "pH",
                "type": "numeric",
                "unit": "",
                "decimals": 1
            },
            "specific_gravity": {
                "code": "specific_gravity",
                "label": "Specific Gravity",
                "type": "numeric",
                "unit": "",
                "decimals": 2
            },
            "protein": {
                "code": "protein",
                "label": "Protein",
                "type": "choice",
                "optionSet": "DIPSTICK_PROTEIN"
            },
            "glucose": {
                "code": "glucose",
                "label": "Glucose",
                "type": "choice",
                "optionSet": "DIPSTICK_GLUCOSE"
            },
            "ketones": {
                "code": "ketones",
                "label": "Ketones",
                "type": "choice",
                "optionSet": "DIPSTICK_KETONES"
            },
            "blood": {
                "code": "blood",
                "label": "Blood",
                "type": "choice",
                "optionSet": "DIPSTICK_BLOOD"
            },
            "bilirubin": {
                "code": "bilirubin",
                "label": "Bilirubin",
                "type": "choice",
                "optionSet": "DIPSTICK_BILIRUBIN"
            },
            "urobilinogen": {
                "code": "urobilinogen",
                "label": "Urobilinogen",
                "type": "choice",
                "optionSet": "DIPSTICK_UROBILINOGEN"
            },
            "nitrite": {
                "code": "nitrite",
                "label": "Nitrite",
                "type": "choice",
                "optionSet": "DIPSTICK_NITRITE"
            },
            "leukocytes": {
                "code": "leukocytes",
                "label": "Leukocytes",
                "type": "choice",
                "optionSet": "DIPSTICK_LEUKOCYTES"
            },
            "wbc_hpf": {
                "code": "wbc_hpf",
                "label": "WBC/HPF",
                "type": "choice",
                "optionSet": "MICROSCOPY_HPF"
            },
            "rbc_hpf": {
                "code": "rbc_hpf",
                "label": "RBC/HPF",
                "type": "choice",
                "optionSet": "MICROSCOPY_HPF"
            },
            "epithelial": {
                "code": "epithelial",
                "label": "Epithelial Cells",
                "type": "text"
            },
            "casts": {
                "code": "casts",
                "label": "Casts",
                "type": "text"
            },
            "crystals": {
                "code": "crystals",
                "label": "Crystals",
                "type": "text"
            },
            "bacteria": {
                "code": "bacteria",
                "label": "Bacteria",
                "type": "text"
            },
            "yeast": {
                "code": "yeast",
                "label": "Yeast",
                "type": "text"
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Urinalysis",
        discipline="GENERAL",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Urinalysis template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created Urinalysis template: {tmpl.id}")
    return tmpl


def create_fasting_glucose_template(db: Session, admin_user_id: int):
    """Create Fasting Blood Glucose template."""
    print("Creating Fasting Glucose template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Fasting Blood Glucose").first()
    if existing:
        print("Fasting Glucose template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Fasting Blood Glucose",
            "discipline": "CHEMISTRY",
            "description": "Fasting blood glucose measurement"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_glucose",
                    "title": "Glucose Measurement",
                    "rows": [
                        {"columns": [{"items": ["fasting_glucose"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "fasting_glucose": {
                "code": "fasting_glucose",
                "label": "Fasting Blood Glucose",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": True,
                "critical_low": 2.2,
                "critical_high": 27.8
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Fasting Blood Glucose",
        discipline="CHEMISTRY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Fasting Glucose template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created Fasting Glucose template: {tmpl.id}")
    return tmpl


def create_hba1c_template(db: Session, admin_user_id: int):
    """Create HbA1c template."""
    print("Creating HbA1c template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "HbA1c").first()
    if existing:
        print("HbA1c template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "HbA1c (Glycated Hemoglobin)",
            "discipline": "CHEMISTRY",
            "description": "Glycated hemoglobin for diabetes monitoring"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_hba1c",
                    "title": "HbA1c Measurement",
                    "rows": [
                        {"columns": [{"items": ["hba1c_value"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "hba1c_value": {
                "code": "hba1c_value",
                "label": "HbA1c",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "critical": True,
                "critical_high": 15.0
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="HbA1c (Glycated Hemoglobin)",
        discipline="CHEMISTRY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial HbA1c template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created HbA1c template: {tmpl.id}")
    return tmpl


def create_blood_group_template(db: Session, admin_user_id: int):
    """Create Blood Grouping template."""
    print("Creating Blood Group template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Blood Grouping").first()
    if existing:
        print("Blood Group template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Blood Grouping",
            "discipline": "BLOODBANK",
            "description": "ABO and Rh blood grouping"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_abogroup",
                    "title": "ABO Group",
                    "rows": [
                        {"columns": [{"items": ["abo_group"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_rh",
                    "title": "Rh Factor",
                    "rows": [
                        {"columns": [{"items": ["rh_factor"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "abo_group": {
                "code": "abo_group",
                "label": "ABO Group",
                "type": "choice",
                "optionSet": "BLOOD_GROUP_OPTIONS"
            },
            "rh_factor": {
                "code": "rh_factor",
                "label": "Rh Factor",
                "type": "choice",
                "optionSet": "RH_FACTOR"
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Blood Grouping",
        discipline="BLOODBANK",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Blood Group template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created Blood Group template: {tmpl.id}")
    return tmpl


def create_typhoid_template(db: Session, admin_user_id: int):
    """Create Typhoid (Widal) template."""
    print("Creating Typhoid (Widal) template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Typhoid (Widal)").first()
    if existing:
        print("Typhoid (Widal) template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Typhoid (Widal)",
            "discipline": "SEROLOGY",
            "description": "Widal test for typhoid fever"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_salmonella",
                    "title": "Salmonella Antigens",
                    "rows": [
                        {"columns": [{"items": ["to", "th", "ao", "ah", "bo", "bh"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_interpretation",
                    "title": "Interpretation",
                    "rows": [
                        {"columns": [{"items": ["interpretation"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "to": {
                "code": "to",
                "label": "S. typhi O (TO)",
                "type": "numeric",
                "unit": "1:",
                "decimals": 0
            },
            "th": {
                "code": "th",
                "label": "S. typhi H (TH)",
                "type": "numeric",
                "unit": "1:",
                "decimals": 0
            },
            "ao": {
                "code": "ao",
                "label": "S. paratyphi A O",
                "type": "numeric",
                "unit": "1:",
                "decimals": 0
            },
            "ah": {
                "code": "ah",
                "label": "S. paratyphi A H",
                "type": "numeric",
                "unit": "1:",
                "decimals": 0
            },
            "bo": {
                "code": "bo",
                "label": "S. paratyphi B O",
                "type": "numeric",
                "unit": "1:",
                "decimals": 0
            },
            "bh": {
                "code": "bh",
                "label": "S. paratyphi B H",
                "type": "numeric",
                "unit": "1:",
                "decimals": 0
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Interpretation",
                "type": "text"
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Typhoid (Widal)",
        discipline="SEROLOGY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Typhoid (Widal) template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created Typhoid (Widal) template: {tmpl.id}")
    return tmpl


def create_malaria_template(db: Session, admin_user_id: int):
    """Create Malaria template."""
    print("Creating Malaria template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Malaria Test (RDT)").first()
    if existing:
        print("Malaria template already exists")
        return existing
    
    schema = {
        "meta": {
            "name": "Malaria Test (RDT)",
            "discipline": "PARASITOLOGY",
            "description": "Malaria rapid diagnostic test"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_rdt",
                    "title": "RDT Result",
                    "rows": [
                        {"columns": [{"items": ["malaria_rdt", "parasite_density"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_microscopy",
                    "title": "Microscopy (if done)",
                    "rows": [
                        {"columns": [{"items": ["species", "parasites_ul"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "malaria_rdt": {
                "code": "malaria_rdt",
                "label": "Malaria RDT",
                "type": "choice",
                "optionSet": "MALARIA_RDT"
            },
            "parasite_density": {
                "code": "parasite_density",
                "label": "Parasite Density (if positive)",
                "type": "numeric",
                "unit": "parasites/μL",
                "decimals": 0
            },
            "species": {
                "code": "species",
                "label": "Species (microscopy)",
                "type": "text"
            },
            "parasites_ul": {
                "code": "parasites_ul",
                "label": "Parasites/μL (microscopy)",
                "type": "numeric",
                "unit": "parasites/μL",
                "decimals": 0
            },
            "comment": {
                "code": "comment",
                "label": "Comments",
                "type": "text"
            }
        }
    }
    
    tmpl = LabTemplate(
        name="Malaria Test (RDT)",
        discipline="PARASITOLOGY",
        status="PUBLISHED",
        current_version=1,
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Malaria template",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created Malaria template: {tmpl.id}")
    return tmpl


def create_reference_ranges(db: Session):
    """Create reference ranges for template fields."""
    print("Creating reference ranges...")
    
    # Reference ranges for CBC
    cbc_ranges = [
        {"field_code": "hb", "sex": "M", "low": 13.0, "high": 17.5, "unit": "g/dL"},
        {"field_code": "hb", "sex": "F", "low": 12.0, "high": 15.5, "unit": "g/dL"},
        {"field_code": "hct", "sex": "M", "low": 41.0, "high": 53.0, "unit": "%"},
        {"field_code": "hct", "sex": "F", "low": 36.0, "high": 46.0, "unit": "%"},
        {"field_code": "rbc_count", "sex": "M", "low": 4.5, "high": 6.0, "unit": "x10^12/L"},
        {"field_code": "rbc_count", "sex": "F", "low": 3.8, "high": 5.5, "unit": "x10^12/L"},
        {"field_code": "mcv", "sex": "ANY", "low": 80.0, "high": 100.0, "unit": "fL"},
        {"field_code": "mch", "sex": "ANY", "low": 27.0, "high": 34.0, "unit": "pg"},
        {"field_code": "mchc", "sex": "ANY", "low": 32.0, "high": 36.0, "unit": "g/dL"},
        {"field_code": "wbc_count", "sex": "ANY", "low": 4.0, "high": 11.0, "unit": "x10^9/L"},
        {"field_code": "neutrophils", "sex": "ANY", "low": 40.0, "high": 75.0, "unit": "%"},
        {"field_code": "lymphocytes", "sex": "ANY", "low": 20.0, "high": 45.0, "unit": "%"},
        {"field_code": "monocytes", "sex": "ANY", "low": 2.0, "high": 10.0, "unit": "%"},
        {"field_code": "eosinophils", "sex": "ANY", "low": 1.0, "high": 6.0, "unit": "%"},
        {"field_code": "basophils", "sex": "ANY", "low": 0.0, "high": 2.0, "unit": "%"},
        {"field_code": "platelet_count", "sex": "ANY", "low": 150.0, "high": 450.0, "unit": "x10^9/L"},
    ]
    
    # Reference ranges for LFT
    lft_ranges = [
        {"field_code": "total_bili", "sex": "ANY", "low": 3.4, "high": 20.5, "unit": "μmol/L"},
        {"field_code": "direct_bili", "sex": "ANY", "low": 0.0, "high": 8.6, "unit": "μmol/L"},
        {"field_code": "alt", "sex": "M", "low": 0.0, "high": 41.0, "unit": "U/L"},
        {"field_code": "alt", "sex": "F", "low": 0.0, "high": 33.0, "unit": "U/L"},
        {"field_code": "ast", "sex": "M", "low": 0.0, "high": 40.0, "unit": "U/L"},
        {"field_code": "ast", "sex": "F", "low": 0.0, "high": 32.0, "unit": "U/L"},
        {"field_code": "alp", "sex": "ANY", "low": 44.0, "high": 147.0, "unit": "U/L"},
        {"field_code": "ggt", "sex": "M", "low": 0.0, "high": 55.0, "unit": "U/L"},
        {"field_code": "ggt", "sex": "F", "low": 0.0, "high": 38.0, "unit": "U/L"},
        {"field_code": "total_protein", "sex": "ANY", "low": 60.0, "high": 80.0, "unit": "g/L"},
        {"field_code": "albumin", "sex": "ANY", "low": 35.0, "high": 50.0, "unit": "g/L"},
        {"field_code": "globulin", "sex": "ANY", "low": 20.0, "high": 35.0, "unit": "g/L"},
    ]
    
    # Reference ranges for RFT
    rft_ranges = [
        {"field_code": "urea", "sex": "ANY", "low": 2.9, "high": 8.2, "unit": "mmol/L"},
        {"field_code": "creatinine", "sex": "M", "low": 64.0, "high": 110.0, "unit": "μmol/L"},
        {"field_code": "creatinine", "sex": "F", "low": 44.0, "high": 80.0, "unit": "μmol/L"},
        {"field_code": "egfr", "sex": "ANY", "low": 90.0, "high": 120.0, "unit": "mL/min/1.73m²"},
        {"field_code": "sodium", "sex": "ANY", "low": 136.0, "high": 145.0, "unit": "mmol/L"},
        {"field_code": "potassium", "sex": "ANY", "low": 3.5, "high": 5.0, "unit": "mmol/L"},
        {"field_code": "chloride", "sex": "ANY", "low": 98.0, "high": 106.0, "unit": "mmol/L"},
        {"field_code": "bicarbonate", "sex": "ANY", "low": 22.0, "high": 29.0, "unit": "mmol/L"},
        {"field_code": "uric_acid", "sex": "M", "low": 142.0, "high": 339.0, "unit": "μmol/L"},
        {"field_code": "uric_acid", "sex": "F", "low": 202.0, "high": 416.0, "unit": "μmol/L"},
    ]
    
    # Reference ranges for Lipid Profile
    lipid_ranges = [
        {"field_code": "total_chol", "sex": "ANY", "low": 0.0, "high": 5.2, "unit": "mmol/L"},
        {"field_code": "hdl", "sex": "M", "low": 1.0, "high": 1.9, "unit": "mmol/L"},
        {"field_code": "hdl", "sex": "F", "low": 1.2, "high": 2.3, "unit": "mmol/L"},
        {"field_code": "ldl", "sex": "ANY", "low": 0.0, "high": 3.4, "unit": "mmol/L"},
        {"field_code": "triglycerides", "sex": "ANY", "low": 0.0, "high": 1.7, "unit": "mmol/L"},
    ]
    
    # Reference ranges for Fasting Glucose
    glucose_ranges = [
        {"field_code": "fasting_glucose", "sex": "ANY", "low": 3.9, "high": 6.1, "unit": "mmol/L"},
    ]
    
    # Reference ranges for HbA1c
    hba1c_ranges = [
        {"field_code": "hba1c_value", "sex": "ANY", "low": 4.0, "high": 5.6, "unit": "%"},
    ]
    
    # Reference ranges for Urinalysis
    urine_ranges = [
        {"field_code": "ph", "sex": "ANY", "low": 5.0, "high": 8.0, "unit": ""},
        {"field_code": "specific_gravity", "sex": "ANY", "low": 1.005, "high": 1.030, "unit": ""},
    ]
    
    # Combine all ranges
    all_ranges = cbc_ranges + lft_ranges + rft_ranges + lipid_ranges + glucose_ranges + hba1c_ranges + urine_ranges
    
    for rr in all_ranges:
        existing = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == rr["field_code"],
            LabReferenceRange.sex == rr["sex"]
        ).first()
        if not existing:
            db_rr = LabReferenceRange(
                field_code=rr["field_code"],
                sex=rr["sex"],
                low=rr["low"],
                high=rr["high"],
                unit=rr["unit"]
            )
            db.add(db_rr)
    
    db.commit()
    print(f"Created {len(all_ranges)} reference ranges")


def create_lab_tests(db: Session, templates: dict):
    """Create lab test catalog entries and link to templates."""
    print("Creating lab test catalog entries...")
    
    tests_data = [
        {
            "test_name": "Complete Blood Count (CBC)",
            "test_code": "CBC",
            "test_category": "Hematology",
            "test_type": "Panel",
            "specimen_type": "EDTA Whole Blood",
            "specimen_volume": "2-3 mL",
            "routine_tat": 4,
            "template": templates.get("CBC")
        },
        {
            "test_name": "Liver Function Tests (LFT)",
            "test_code": "LFT",
            "test_category": "Chemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "specimen_volume": "5 mL",
            "routine_tat": 6,
            "template": templates.get("LFT")
        },
        {
            "test_name": "Renal Function Tests (RFT)",
            "test_code": "RFT",
            "test_category": "Chemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "specimen_volume": "5 mL",
            "routine_tat": 6,
            "template": templates.get("RFT")
        },
        {
            "test_name": "Lipid Profile",
            "test_code": "LIPID",
            "test_category": "Chemistry",
            "test_type": "Panel",
            "specimen_type": "Serum (Fasting)",
            "specimen_volume": "5 mL",
            "routine_tat": 6,
            "template": templates.get("Lipid Profile")
        },
        {
            "test_name": "Urinalysis",
            "test_code": "UA",
            "test_category": "General",
            "test_type": "Panel",
            "specimen_type": "Urine (Mid-stream)",
            "specimen_volume": "10-20 mL",
            "routine_tat": 2,
            "template": templates.get("Urinalysis")
        },
        {
            "test_name": "Fasting Blood Glucose",
            "test_code": "FBG",
            "test_category": "Chemistry",
            "test_type": "Individual",
            "specimen_type": "Sodium Fluoride Plasma",
            "specimen_volume": "2 mL",
            "routine_tat": 2,
            "template": templates.get("Fasting Blood Glucose")
        },
        {
            "test_name": "HbA1c",
            "test_code": "HbA1c",
            "test_category": "Chemistry",
            "test_type": "Individual",
            "specimen_type": "EDTA Whole Blood",
            "specimen_volume": "2 mL",
            "routine_tat": 24,
            "template": templates.get("HbA1c")
        },
        {
            "test_name": "Blood Grouping (ABO & Rh)",
            "test_code": "BG",
            "test_category": "Blood Bank",
            "test_type": "Individual",
            "specimen_type": "EDTA Whole Blood",
            "specimen_volume": "2 mL",
            "routine_tat": 2,
            "template": templates.get("Blood Grouping")
        },
        {
            "test_name": "Typhoid (Widal)",
            "test_code": "WIDAL",
            "test_category": "Serology",
            "test_type": "Individual",
            "specimen_type": "Serum",
            "specimen_volume": "3 mL",
            "routine_tat": 4,
            "template": templates.get("Typhoid (Widal)")
        },
        {
            "test_name": "Malaria Test (RDT)",
            "test_code": "MAL",
            "test_category": "Parasitology",
            "test_type": "Individual",
            "specimen_type": "Capillary Whole Blood",
            "specimen_volume": "5 μL",
            "routine_tat": 1,
            "template": templates.get("Malaria Test (RDT)")
        },
    ]
    
    for test_data in tests_data:
        template = test_data.pop("template")
        existing = db.query(LabTest).filter(LabTest.test_code == test_data["test_code"]).first()
        if existing:
            print(f"Test {test_data['test_name']} already exists, updating template link...")
            if template:
                existing.template_id = template.id
                existing.template_version = template.current_version
        else:
            test = LabTest(
                test_name=test_data["test_name"],
                test_code=test_data["test_code"],
                test_category=test_data["test_category"],
                test_type=test_data["test_type"],
                specimen_type=test_data["specimen_type"],
                specimen_volume=test_data["specimen_volume"],
                routine_tat=test_data["routine_tat"],
                template_id=template.id if template else None,
                template_version=template.current_version if template else None
            )
            db.add(test)
            print(f"Created test: {test_data['test_name']}")
    
    db.commit()
    print(f"Processed {len(tests_data)} lab tests")


def seed_lab_templates():
    """Main function to seed all lab templates."""
    print("=" * 60)
    print("SEEDING LAB TEMPLATES AND TESTS")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("ERROR: Admin user not found. Run init_db.py first.")
            return
        
        admin_user_id = admin_user.id
        print(f"Using admin user ID: {admin_user_id}")
        
        # Create option sets
        create_option_sets(db)
        
        # Create templates
        templates = {}
        templates["CBC"] = create_cbc_template(db, admin_user_id)
        templates["LFT"] = create_lft_template(db, admin_user_id)
        templates["RFT"] = create_rft_template(db, admin_user_id)
        templates["Lipid Profile"] = create_lipid_template(db, admin_user_id)
        templates["Urinalysis"] = create_urinalysis_template(db, admin_user_id)
        templates["Fasting Blood Glucose"] = create_fasting_glucose_template(db, admin_user_id)
        templates["HbA1c"] = create_hba1c_template(db, admin_user_id)
        templates["Blood Grouping"] = create_blood_group_template(db, admin_user_id)
        templates["Typhoid (Widal)"] = create_typhoid_template(db, admin_user_id)
        templates["Malaria Test (RDT)"] = create_malaria_template(db, admin_user_id)
        
        # Create reference ranges
        create_reference_ranges(db)
        
        # Create lab tests in catalog
        create_lab_tests(db, templates)
        
        print("=" * 60)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nCreated templates:")
        for name, tmpl in templates.items():
            print(f"  - {name}: {tmpl.id}")
        print("\nLab staff can now enter results using structured templates!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_lab_templates()
