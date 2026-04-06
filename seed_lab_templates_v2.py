#!/usr/bin/env python3
"""
Seed script for comprehensive lab test templates with CORRECT units and organized layout.
Run this script to populate the database with standard lab test templates.

Usage:
    python3 seed_lab_templates_v2.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabOptionSet, LabReferenceRange
)
from app.models.user_models import User

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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


def create_cbc_template_v2(db: Session, admin_user_id: int):
    """Create Complete Blood Count (CBC) template - IMPROVED."""
    print("Creating CBC template v2...")
    
    # Delete existing template if any
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Complete Blood Count (CBC)").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
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
                        {"columns": [{"items": ["hb"], "width": 6}, {"items": ["hct"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_rbc",
                    "title": "Red Blood Cell Indices",
                    "rows": [
                        {"columns": [{"items": ["rbc_count"], "width": 3}, {"items": ["mcv"], "width": 3}, {"items": ["mch"], "width": 3}, {"items": ["mchc"], "width": 3}]}
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
                        {"columns": [{"items": ["neutrophils"], "width": 4}, {"items": ["lymphocytes"], "width": 4}, {"items": ["monocytes"], "width": 4}]},
                        {"columns": [{"items": ["eosinophils"], "width": 4}, {"items": ["basophils"], "width": 4}]}
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
                        {"columns": [{"items": ["rbcmorph"], "width": 4}, {"items": ["wbc_morph"], "width": 4}, {"items": ["platelet_morph"], "width": 4}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Additional Notes",
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
                "critical": {"low": 7.0, "high": 20.0}
            },
            "hct": {
                "code": "hct",
                "label": "Hematocrit (Hct)",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "critical": {"low": 20.0, "high": 60.0}
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
                "critical": {"low": 2.0, "high": 30.0}
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
                "critical": {"low": 20.0, "high": 1000.0}
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
                "label": "Additional Notes / Interpretation",
                "type": "text"
            }
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
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
        change_note="Initial CBC template v2 - corrected units",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created CBC template v2: {tmpl.id}")
    return tmpl


def create_lft_template_v2(db: Session, admin_user_id: int):
    """Create Liver Function Tests template - IMPROVED."""
    print("Creating LFT template v2...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Liver Function Tests (LFT)").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
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
                        {"columns": [{"items": ["total_bili"], "width": 4}, {"items": ["direct_bili"], "width": 4}, {"items": ["indirect_bili"], "width": 4}]}
                    ]
                },
                {
                    "id": "sec_enzymes",
                    "title": "Liver Enzymes",
                    "rows": [
                        {"columns": [{"items": ["alt"], "width": 3}, {"items": ["ast"], "width": 3}, {"items": ["alp"], "width": 3}, {"items": ["ggt"], "width": 3}]}
                    ]
                },
                {
                    "id": "sec_proteins",
                    "title": "Proteins",
                    "rows": [
                        {"columns": [{"items": ["total_protein"], "width": 4}, {"items": ["albumin"], "width": 4}, {"items": ["globulin"], "width": 4}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Additional Notes",
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
                "critical": {"high": 170.0}
            },
            "direct_bili": {
                "code": "direct_bili",
                "label": "Direct Bilirubin",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 1,
                "critical": {"high": 85.0}
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
                "critical": {"high": 500.0}
            },
            "ast": {
                "code": "ast",
                "label": "AST (SGOT)",
                "type": "numeric",
                "unit": "U/L",
                "decimals": 0,
                "critical": {"high": 500.0}
            },
            "alp": {
                "code": "alp",
                "label": "Alkaline Phosphatase",
                "type": "numeric",
                "unit": "U/L",
                "decimals": 0,
                "critical": {"high": 400.0}
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
                "critical": {"low": 20.0}
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
                "label": "Additional Notes / Interpretation",
                "type": "text"
            }
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
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
        change_note="Initial LFT template v2",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created LFT template v2: {tmpl.id}")
    return tmpl


def create_rft_template_v2(db: Session, admin_user_id: int):
    """Create Renal Function Tests template - IMPROVED."""
    print("Creating RFT template v2...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Renal Function Tests (RFT)").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
    schema = {
        "meta": {
            "name": "Renal Function Tests (RFT)",
            "discipline": "CHEMISTRY",
            "description": "Kidney function test panel"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_kidney",
                    "title": "Kidney Function",
                    "rows": [
                        {"columns": [{"items": ["creatinine"], "width": 4}, {"items": ["urea"], "width": 4}, {"items": ["egfr"], "width": 4}]}
                    ]
                },
                {
                    "id": "sec_electrolytes1",
                    "title": "Electrolytes - Major",
                    "rows": [
                        {"columns": [{"items": ["sodium"], "width": 4}, {"items": ["potassium"], "width": 4}, {"items": ["chloride"], "width": 4}]}
                    ]
                },
                {
                    "id": "sec_electrolytes2",
                    "title": "Electrolytes - Other",
                    "rows": [
                        {"columns": [{"items": ["bicarbonate"], "width": 4}, {"items": ["uric_acid"], "width": 4}]}
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Additional Notes",
                    "rows": [
                        {"columns": [{"items": ["comment"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "creatinine": {
                "code": "creatinine",
                "label": "Creatinine",
                "type": "numeric",
                "unit": "μmol/L",
                "decimals": 0,
                "critical": {"high": 707.0}
            },
            "urea": {
                "code": "urea",
                "label": "Urea",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": {"high": 35.0}
            },
            "egfr": {
                "code": "egfr",
                "label": "eGFR",
                "type": "numeric",
                "unit": "mL/min/1.73m²",
                "decimals": 1,
                "critical": {"low": 15.0}
            },
            "sodium": {
                "code": "sodium",
                "label": "Sodium (Na)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 0,
                "critical": {"low": 120.0, "high": 160.0}
            },
            "potassium": {
                "code": "potassium",
                "label": "Potassium (K)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": {"low": 2.5, "high": 6.5}
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
                "label": "Bicarbonate (HCO₃)",
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
                "label": "Additional Notes / Interpretation",
                "type": "text"
            }
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
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
        change_note="Initial RFT template v2",
        created_by_id=admin_user_id
    )
    db.add(version)
    db.commit()
    db.refresh(tmpl)
    
    print(f"Created RFT template v2: {tmpl.id}")
    return tmpl


def create_reference_ranges_v2(db: Session):
    """Create reference ranges with CORRECT units."""
    print("Creating reference ranges v2...")
    
    # Clear existing ranges
    db.query(LabReferenceRange).delete()
    
    # Reference ranges for CBC - units: g/dL for Hb/Hct, x10^12/L for RBC, x10^9/L for WBC/Platelets
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
    
    # Reference ranges for LFT - units: μmol/L for bilirubin, U/L for enzymes, g/L for proteins
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
    
    # Reference ranges for RFT - units: μmol/L for creatinine/uric acid, mmol/L for urea/electrolytes
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
    
    # Reference ranges for Glucose - mmol/L
    glucose_ranges = [
        {"field_code": "fasting_glucose", "sex": "ANY", "low": 3.9, "high": 6.1, "unit": "mmol/L"},
    ]
    
    # Reference ranges for HbA1c - %
    hba1c_ranges = [
        {"field_code": "hba1c_value", "sex": "ANY", "low": 4.0, "high": 5.6, "unit": "%"},
    ]
    
    # Reference ranges for Urinalysis
    urine_ranges = [
        {"field_code": "ph", "sex": "ANY", "low": 5.0, "high": 8.0, "unit": ""},
        {"field_code": "specific_gravity", "sex": "ANY", "low": 1.005, "high": 1.030, "unit": ""},
    ]
    
    all_ranges = cbc_ranges + lft_ranges + rft_ranges + glucose_ranges + hba1c_ranges + urine_ranges
    
    for rr in all_ranges:
        db_rr = LabReferenceRange(
            field_code=rr["field_code"],
            sex=rr["sex"],
            low=rr["low"],
            high=rr["high"],
            unit=rr["unit"]
        )
        db.add(db_rr)
    
    db.commit()
    print(f"Created {len(all_ranges)} reference ranges v2")


def update_lab_tests(db: Session, templates: dict):
    """Update lab test catalog entries with new template IDs."""
    print("Updating lab test catalog...")
    
    tests_data = [
        {"test_name": "Complete Blood Count (CBC)", "test_code": "CBC", "template": templates.get("CBC")},
        {"test_name": "Liver Function Tests (LFT)", "test_code": "LFT", "template": templates.get("LFT")},
        {"test_name": "Renal Function Tests (RFT)", "test_code": "RFT", "template": templates.get("RFT")},
    ]
    
    for test_data in tests_data:
        template = test_data.pop("template")
        test = db.query(LabTest).filter(LabTest.test_code == test_data["test_code"]).first()
        if test and template:
            test.template_id = template.id
            test.template_version = template.current_version
            print(f"Updated {test.test_name} with new template")
    
    db.commit()


def seed_lab_templates_v2():
    """Main function to seed all lab templates v2."""
    print("=" * 60)
    print("SEEDING LAB TEMPLATES V2 - IMPROVED LAYOUT & UNITS")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("ERROR: Admin user not found. Run init_db.py first.")
            return
        
        admin_user_id = admin_user.id
        print(f"Using admin user ID: {admin_user_id}")
        
        create_option_sets(db)
        
        templates = {}
        templates["CBC"] = create_cbc_template_v2(db, admin_user_id)
        templates["LFT"] = create_lft_template_v2(db, admin_user_id)
        templates["RFT"] = create_rft_template_v2(db, admin_user_id)
        
        create_reference_ranges_v2(db)
        
        update_lab_tests(db, templates)
        
        print("=" * 60)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_lab_templates_v2()
