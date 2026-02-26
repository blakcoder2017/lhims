#!/usr/bin/env python3
"""
Comprehensive Lab Test Template Seeder
Creates templates with parameters for all 138 lab tests.

Usage:
    python3 seed_lab_templates_with_parameters.py

Requirements:
    - Database must be initialized
    - Lab test catalog should already be populated (run seed_lab_templates_comprehensive.py first)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabReferenceRange
)
from app.models.user_models import User

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# TEMPLATE DEFINITIONS
# Each template includes: meta, layout, fields
# =============================================================================

def get_template_definitions():
    """Return all template definitions with parameters."""
    
    templates = {}
    
    # ==================== HEMATOLOGY TEMPLATES ====================
    
    templates["Complete Blood Count (CBC)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Complete blood count with differential",
        "layout": {
            "sections": [
                {"id": "sec_hb", "title": "Hemoglobin & Hematocrit", "rows": [{"columns": [{"items": ["hb"], "width": 6}, {"items": ["hct"], "width": 6}]}]},
                {"id": "sec_rbc", "title": "Red Blood Cells", "rows": [{"columns": [{"items": ["rbc_count"], "width": 3}, {"items": ["mcv"], "width": 3}, {"items": ["mch"], "width": 3}, {"items": ["mchc"], "width": 3}]}]},
                {"id": "sec_wbc", "title": "White Blood Cells", "rows": [{"columns": [{"items": ["wbc_count"], "width": 12}]}]},
                {"id": "sec_diff", "title": "Differential Count", "rows": [{"columns": [{"items": ["neutrophils"], "width": 4}, {"items": ["lymphocytes"], "width": 4}, {"items": ["monocytes"], "width": 4}]},
                    {"columns": [{"items": ["eosinophils"], "width": 4}, {"items": ["basophils"], "width": 4}]}]},
                {"id": "sec_plt", "title": "Platelets", "rows": [{"columns": [{"items": ["platelet_count"], "width": 12}]}]},
                {"id": "sec_morph", "title": "Morphology", "rows": [{"columns": [{"items": ["rbcmorph"], "width": 4}, {"items": ["wbc_morph"], "width": 4}, {"items": ["platelet_morph"], "width": 4}]}]},
                {"id": "sec_notes", "title": "Notes", "rows": [{"columns": [{"items": ["remarks"], "width": 12}]}]}
            ]
        },
        "fields": {
            "hb": {"code": "hb", "label": "Hemoglobin (Hb)", "type": "numeric", "unit": "g/dL", "decimals": 1, "critical": {"low": 7.0, "high": 20.0}},
            "hct": {"code": "hct", "label": "Hematocrit (Hct)", "type": "numeric", "unit": "%", "decimals": 1, "critical": {"low": 20.0, "high": 60.0}},
            "rbc_count": {"code": "rbc_count", "label": "RBC Count", "type": "numeric", "unit": "x10^12/L", "decimals": 2},
            "mcv": {"code": "mcv", "label": "MCV", "type": "numeric", "unit": "fL", "decimals": 1},
            "mch": {"code": "mch", "label": "MCH", "type": "numeric", "unit": "pg", "decimals": 1},
            "mchc": {"code": "mchc", "label": "MCHC", "type": "numeric", "unit": "g/dL", "decimals": 1},
            "wbc_count": {"code": "wbc_count", "label": "WBC Count", "type": "numeric", "unit": "x10^9/L", "decimals": 2, "critical": {"low": 2.0, "high": 30.0}},
            "neutrophils": {"code": "neutrophils", "label": "Neutrophils", "type": "numeric", "unit": "%", "decimals": 1},
            "lymphocytes": {"code": "lymphocytes", "label": "Lymphocytes", "type": "numeric", "unit": "%", "decimals": 1},
            "monocytes": {"code": "monocytes", "label": "Monocytes", "type": "numeric", "unit": "%", "decimals": 1},
            "eosinophils": {"code": "eosinophils", "label": "Eosinophils", "type": "numeric", "unit": "%", "decimals": 1},
            "basophils": {"code": "basophils", "label": "Basophils", "type": "numeric", "unit": "%", "decimals": 1},
            "platelet_count": {"code": "platelet_count", "label": "Platelet Count", "type": "numeric", "unit": "x10^9/L", "decimals": 0, "critical": {"low": 20.0, "high": 1000.0}},
            "rbcmorph": {"code": "rbcmorph", "label": "RBC Morphology", "type": "text", "multiline": True},
            "wbc_morph": {"code": "wbc_morph", "label": "WBC Morphology", "type": "text", "multiline": True},
            "platelet_morph": {"code": "platelet_morph", "label": "Platelet Morphology", "type": "text", "multiline": True},
            "remarks": {"code": "remarks", "label": "Remarks", "type": "text", "multiline": True}
        }
    }
    
    templates["Peripheral Blood Smear"] = {
        "discipline": "HEMATOLOGY",
        "description": "Microscopic examination of blood cells",
        "layout": {
            "sections": [
                {"id": "sec_rbc", "title": "RBC Findings", "rows": [{"columns": [{"items": ["rbcmorph"], "width": 12}]}]},
                {"id": "sec_wbc", "title": "WBC Findings", "rows": [{"columns": [{"items": ["wbc_morph"], "width": 12}]}]},
                {"id": "sec_plt", "title": "Platelet Findings", "rows": [{"columns": [{"items": ["platelet_morph"], "width": 12}]}]},
                {"id": "sec_parasite", "title": "Parasites", "rows": [{"columns": [{"items": ["parasites"], "width": 12}]}]},
                {"id": "sec_impression", "title": "Impression", "rows": [{"columns": [{"items": ["impression"], "width": 12}]}]}
            ]
        },
        "fields": {
            "rbcmorph": {"code": "rbcmorph", "label": "RBC Morphology", "type": "text", "multiline": True},
            "wbc_morph": {"code": "wbc_morph", "label": "WBC", "type": "text", "multiline": True},
            "platelet_morph": {"code": "platelet_morph", "label": "Platelets", "type": "text", "multiline": True},
            "parasites": {"code": "parasites", "label": "Blood Parasites", "type": "text", "multiline": True},
            "impression": {"code": "impression", "label": "Impression", "type": "text", "multiline": True}
        }
    }
    
    templates["Erythrocyte Sedimentation Rate (ESR)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Non-specific inflammation marker",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["esr_value"], "width": 12}]}]}]},
        "fields": {
            "esr_value": {"code": "esr_value", "label": "ESR", "type": "numeric", "unit": "mm/hr", "decimals": 0}
        }
    }
    
    templates["Reticulocyte Count"] = {
        "discipline": "HEMATOLOGY",
        "description": "Bone marrow function assessment",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["retic_count"], "width": 6}, {"items": ["retic_abs"], "width": 6}]}]}]},
        "fields": {
            "retic_count": {"code": "retic_count", "label": "Reticulocyte Count", "type": "numeric", "unit": "%", "decimals": 2},
            "retic_abs": {"code": "retic_abs", "label": "Absolute Reticulocyte Count", "type": "numeric", "unit": "x10^9/L", "decimals": 2}
        }
    }
    
    templates["Sickle Cell Test"] = {
        "discipline": "HEMATOLOGY",
        "description": "Sickle cell disease screening",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["sickle_result"], "width": 12}]}]}]},
        "fields": {
            "sickle_result": {"code": "sickle_result", "label": "Sickle Cell Test", "type": "select", "options": ["Negative", "Positive", "Sickle Cell Trait", "Sickle Cell Disease"]}
        }
    }
    
    templates["Hemoglobin Electrophoresis"] = {
        "discipline": "HEMATOLOGY",
        "description": "Hemoglobin variant analysis",
        "layout": {
            "sections": [
                {"id": "sec_hb", "title": "Hemoglobin Fractions", "rows": [{"columns": [{"items": ["hba"], "width": 4}, {"items": ["hba2"], "width": 4}, {"items": ["hbf"], "width": 4}]}]},
                {"id": "sec_variant", "title": "Abnormal Hemoglobins", "rows": [{"columns": [{"items": ["hb_variant"], "width": 12}]}]},
                {"id": "sec_interp", "title": "Interpretation", "rows": [{"columns": [{"items": ["interpretation"], "width": 12}]}]}
            ]
        },
        "fields": {
            "hba": {"code": "hba", "label": "HbA", "type": "numeric", "unit": "%", "decimals": 1},
            "hba2": {"code": "hba2", "label": "HbA2", "type": "numeric", "unit": "%", "decimals": 1},
            "hbf": {"code": "hbf", "label": "HbF", "type": "numeric", "unit": "%", "decimals": 1},
            "hb_variant": {"code": "hb_variant", "label": "Abnormal Hb", "type": "text"},
            "interpretation": {"code": "interpretation", "label": "Interpretation", "type": "text", "multiline": True}
        }
    }
    
    templates["Prothrombin Time (PT)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Extrinsic coagulation pathway",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["pt_value"], "width": 6}, {"items": ["pt_inr"], "width": 6}]}]}]},
        "fields": {
            "pt_value": {"code": "pt_value", "label": "PT", "type": "numeric", "unit": "seconds", "decimals": 1, "critical": {"high": 50.0}},
            "pt_inr": {"code": "pt_inr", "label": "INR", "type": "numeric", "unit": "ratio", "decimals": 2}
        }
    }
    
    templates["Activated Partial Thromboplastin Time (APTT)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Intrinsic coagulation pathway",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["aptt_value"], "width": 12}]}]}]},
        "fields": {
            "aptt_value": {"code": "aptt_value", "label": "APTT", "type": "numeric", "unit": "seconds", "decimals": 1, "critical": {"high": 100.0}}
        }
    }
    
    templates["Coagulation Profile (PT, APTT, INR)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Complete coagulation screening",
        "layout": {
            "sections": [
                {"id": "sec_pt", "title": "Prothrombin Time", "rows": [{"columns": [{"items": ["pt_value"], "width": 6}, {"items": ["pt_inr"], "width": 6}]}]},
                {"id": "sec_aptt", "title": "APTT", "rows": [{"columns": [{"items": ["aptt_value"], "width": 12}]}]}
            ]
        },
        "fields": {
            "pt_value": {"code": "pt_value", "label": "PT", "type": "numeric", "unit": "seconds", "decimals": 1},
            "pt_inr": {"code": "pt_inr", "label": "INR", "type": "numeric", "unit": "ratio", "decimals": 2},
            "aptt_value": {"code": "aptt_value", "label": "APTT", "type": "numeric", "unit": "seconds", "decimals": 1}
        }
    }
    
    templates["D-Dimer"] = {
        "discipline": "HEMATOLOGY",
        "description": "Fibrin degradation product",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ddimer_value"], "width": 12}]}]}]},
        "fields": {
            "ddimer_value": {"code": "ddimer_value", "label": "D-Dimer", "type": "numeric", "unit": "μg/mL", "decimals": 2}
        }
    }
    
    templates["Fibrinogen"] = {
        "discipline": "HEMATOLOGY",
        "description": "Coagulation factor I",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["fibrinogen_value"], "width": 12}]}]}]},
        "fields": {
            "fibrinogen_value": {"code": "fibrinogen_value", "label": "Fibrinogen", "type": "numeric", "unit": "mg/dL", "decimals": 0}
        }
    }
    
    templates["Iron Studies (Iron, Ferritin, TIBC)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Iron deficiency anemia workup",
        "layout": {
            "sections": [
                {"id": "sec_iron", "title": "Iron Studies", "rows": [{"columns": [{"items": ["serum_iron"], "width": 4}, {"items": ["ferritin"], "width": 4}, {"items": ["tibc"], "width": 4}]}]},
                {"id": "sec_sat", "title": "Saturation", "rows": [{"columns": [{"items": ["transferrin_sat"], "width": 12}]}]}
            ]
        },
        "fields": {
            "serum_iron": {"code": "serum_iron", "label": "Serum Iron", "type": "numeric", "unit": "μg/dL", "decimals": 0},
            "ferritin": {"code": "ferritin", "label": "Ferritin", "type": "numeric", "unit": "ng/mL", "decimals": 0},
            "tibc": {"code": "tibc", "label": "TIBC", "type": "numeric", "unit": "μg/dL", "decimals": 0},
            "transferrin_sat": {"code": "transferrin_sat", "label": "Transferrin Saturation", "type": "numeric", "unit": "%", "decimals": 1}
        }
    }
    
    templates["Serum Ferritin"] = {
        "discipline": "HEMATOLOGY",
        "description": "Body iron stores",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ferritin_value"], "width": 12}]}]}]},
        "fields": {
            "ferritin_value": {"code": "ferritin_value", "label": "Ferritin", "type": "numeric", "unit": "ng/mL", "decimals": 0}
        }
    }
    
    templates["Vitamin B12"] = {
        "discipline": "HEMATOLOGY",
        "description": "Vitamin B12 level",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["b12_value"], "width": 12}]}]}]},
        "fields": {
            "b12_value": {"code": "b12_value", "label": "Vitamin B12", "type": "numeric", "unit": "pg/mL", "decimals": 0}
        }
    }
    
    templates["Folate"] = {
        "discipline": "HEMATOLOGY",
        "description": "Folic acid level",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["folate_value"], "width": 12}]}]}]},
        "fields": {
            "folate_value": {"code": "folate_value", "label": "Folate", "type": "numeric", "unit": "ng/mL", "decimals": 1}
        }
    }
    
    # ==================== CHEMISTRY TEMPLATES ====================
    
    templates["Liver Function Tests (LFT)"] = {
        "discipline": "CHEMISTRY",
        "description": "Comprehensive liver function assessment",
        "layout": {
            "sections": [
                {"id": "sec_bilirubin", "title": "Bilirubin", "rows": [{"columns": [{"items": ["tbil"], "width": 6}, {"items": ["dbil"], "width": 6}]}]},
                {"id": "sec_enzymes", "title": "Liver Enzymes", "rows": [{"columns": [{"items": ["alt"], "width": 4}, {"items": ["ast"], "width": 4}, {"items": ["alp"], "width": 4}]},
                    {"columns": [{"items": ["ggt"], "width": 4}, {"items": ["ldh"], "width": 4}]}]},
                {"id": "sec_protein", "title": "Proteins", "rows": [{"columns": [{"items": ["tp"], "width": 4}, {"items": ["alb"], "width": 4}, {"items": ["glob"], "width": 4}]}]}
            ]
        },
        "fields": {
            "tbil": {"code": "tbil", "label": "Total Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1, "critical": {"high": 171.0}},
            "dbil": {"code": "dbil", "label": "Direct Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1},
            "alt": {"code": "alt", "label": "ALT", "type": "numeric", "unit": "U/L", "decimals": 0, "critical": {"high": 500.0}},
            "ast": {"code": "ast", "label": "AST", "type": "numeric", "unit": "U/L", "decimals": 0, "critical": {"high": 500.0}},
            "alp": {"code": "alp", "label": "ALP", "type": "numeric", "unit": "U/L", "decimals": 0},
            "ggt": {"code": "ggt", "label": "GGT", "type": "numeric", "unit": "U/L", "decimals": 0},
            "ldh": {"code": "ldh", "label": "LDH", "type": "numeric", "unit": "U/L", "decimals": 0},
            "tp": {"code": "tp", "label": "Total Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
            "alb": {"code": "alb", "label": "Albumin", "type": "numeric", "unit": "g/L", "decimals": 1, "critical": {"low": 20.0}},
            "glob": {"code": "glob", "label": "Globulin", "type": "numeric", "unit": "g/L", "decimals": 1}
        }
    }
    
    templates["Renal Function Tests (RFT)"] = {
        "discipline": "CHEMISTRY",
        "description": "Kidney function assessment",
        "layout": {
            "sections": [
                {"id": "sec_renal", "title": "Renal Markers", "rows": [{"columns": [{"items": ["urea"], "width": 4}, {"items": ["creat"], "width": 4}, {"items": ["egfr"], "width": 4}]}]},
                {"id": "sec_elect", "title": "Electrolytes", "rows": [{"columns": [{"items": ["na"], "width": 3}, {"items": ["k"], "width": 3}, {"items": ["cl"], "width": 3}, {"items": ["hco3"], "width": 3}]}]}
            ]
        },
        "fields": {
            "urea": {"code": "urea", "label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"high": 35.7}},
            "creat": {"code": "creat", "label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0, "critical": {"high": 707.0}},
            "egfr": {"code": "egfr", "label": "eGFR", "type": "numeric", "unit": "mL/min/1.73m²", "decimals": 0, "critical": {"low": 15.0}},
            "na": {"code": "na", "label": "Sodium", "type": "numeric", "unit": "mmol/L", "decimals": 1, "critical": {"low": 120.0, "high": 160.0}},
            "k": {"code": "k", "label": "Potassium", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"low": 2.5, "high": 6.5}},
            "cl": {"code": "cl", "label": "Chloride", "type": "numeric", "unit": "mmol/L", "decimals": 1},
            "hco3": {"code": "hco3", "label": "Bicarbonate", "type": "numeric", "unit": "mmol/L", "decimals": 1}
        }
    }
    
    templates["Serum Electrolytes (Na, K, Cl, HCO3)"] = {
        "discipline": "CHEMISTRY",
        "description": "Electrolyte panel",
        "layout": {"sections": [{"id": "sec_elect", "title": "Electrolytes", "rows": [{"columns": [{"items": ["na"], "width": 3}, {"items": ["k"], "width": 3}, {"items": ["cl"], "width": 3}, {"items": ["hco3"], "width": 3}]}]}]},
        "fields": {
            "na": {"code": "na", "label": "Sodium (Na+)", "type": "numeric", "unit": "mmol/L", "decimals": 1, "critical": {"low": 120.0, "high": 160.0}},
            "k": {"code": "k", "label": "Potassium (K+)", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"low": 2.5, "high": 6.5}},
            "cl": {"code": "cl", "label": "Chloride (Cl-)", "type": "numeric", "unit": "mmol/L", "decimals": 1},
            "hco3": {"code": "hco3", "label": "Bicarbonate (HCO3-)", "type": "numeric", "unit": "mmol/L", "decimals": 1}
        }
    }
    
    templates["Sodium (Na+)"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum sodium",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["na_value"], "width": 12}]}]}]},
        "fields": {
            "na_value": {"code": "na_value", "label": "Sodium", "type": "numeric", "unit": "mmol/L", "decimals": 1, "critical": {"low": 120.0, "high": 160.0}}
        }
    }
    
    templates["Potassium (K+)"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum potassium",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["k_value"], "width": 12}]}]}]},
        "fields": {
            "k_value": {"code": "k_value", "label": "Potassium", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"low": 2.5, "high": 6.5}}
        }
    }
    
    templates["Chloride (Cl-)"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum chloride",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["cl_value"], "width": 12}]}]}]},
        "fields": {
            "cl_value": {"code": "cl_value", "label": "Chloride", "type": "numeric", "unit": "mmol/L", "decimals": 1}
        }
    }
    
    templates["Bicarbonate (HCO3)"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum bicarbonate",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["hco3_value"], "width": 12}]}]}]},
        "fields": {
            "hco3_value": {"code": "hco3_value", "label": "Bicarbonate", "type": "numeric", "unit": "mmol/L", "decimals": 1}
        }
    }
    
    templates["Lipid Profile"] = {
        "discipline": "CHEMISTRY",
        "description": "Cardiovascular risk assessment",
        "layout": {
            "sections": [
                {"id": "sec_lipids", "title": "Lipid Panel", "rows": [{"columns": [{"items": ["chol"], "width": 4}, {"items": ["tg"], "width": 4}, {"items": ["hdl"], "width": 4}]},
                    {"columns": [{"items": ["ldl"], "width": 4}, {"items": ["vldl"], "width": 4}]}]}
            ]
        },
        "fields": {
            "chol": {"code": "chol", "label": "Total Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"high": 10.0}},
            "tg": {"code": "tg", "label": "Triglycerides", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "hdl": {"code": "hdl", "label": "HDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "ldl": {"code": "ldl", "label": "LDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "vldl": {"code": "vldl", "label": "VLDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Total Cholesterol"] = {
        "discipline": "CHEMISTRY",
        "description": "Total cholesterol",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["chol_value"], "width": 12}]}]}]},
        "fields": {
            "chol_value": {"code": "chol_value", "label": "Total Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Triglycerides"] = {
        "discipline": "CHEMISTRY",
        "description": "Triglyceride level",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["tg_value"], "width": 12}]}]}]},
        "fields": {
            "tg_value": {"code": "tg_value", "label": "Triglycerides", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["HDL Cholesterol"] = {
        "discipline": "CHEMISTRY",
        "description": "High-density lipoprotein",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["hdl_value"], "width": 12}]}]}]},
        "fields": {
            "hdl_value": {"code": "hdl_value", "label": "HDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["LDL Cholesterol"] = {
        "discipline": "CHEMISTRY",
        "description": "Low-density lipoprotein",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ldl_value"], "width": 12}]}]}]},
        "fields": {
            "ldl_value": {"code": "ldl_value", "label": "LDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Fasting Blood Glucose"] = {
        "discipline": "CHEMISTRY",
        "description": "Fasting blood sugar",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["fbg_value"], "width": 12}]}]}]},
        "fields": {
            "fbg_value": {"code": "fbg_value", "label": "Fasting Blood Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"low": 2.2, "high": 27.8}}
        }
    }
    
    templates["Random Blood Glucose"] = {
        "discipline": "CHEMISTRY",
        "description": "Random blood sugar",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["rbg_value"], "width": 12}]}]}]},
        "fields": {
            "rbg_value": {"code": "rbg_value", "label": "Random Blood Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": {"low": 2.2, "high": 27.8}}
        }
    }
    
    templates["HbA1c (Glycated Hemoglobin)"] = {
        "discipline": "CHEMISTRY",
        "description": "Long-term diabetes control",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["hba1c_value"], "width": 12}]}]}]},
        "fields": {
            "hba1c_value": {"code": "hba1c_value", "label": "HbA1c", "type": "numeric", "unit": "%", "decimals": 1}
        }
    }
    
    templates["Oral Glucose Tolerance Test (OGTT)"] = {
        "discipline": "CHEMISTRY",
        "description": "Diabetes diagnostic test",
        "layout": {
            "sections": [
                {"id": "sec_fasting", "title": "Fasting", "rows": [{"columns": [{"items": ["fbg_value"], "width": 12}]}]},
                {"id": "sec_2hr", "title": "2-Hour Postprandial", "rows": [{"columns": [{"items": ["ppbg_value"], "width": 12}]}]}
            ]
        },
        "fields": {
            "fbg_value": {"code": "fbg_value", "label": "Fasting", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "ppbg_value": {"code": "ppbg_value", "label": "2-Hour PP", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Total Bilirubin"] = {
        "discipline": "CHEMISTRY",
        "description": "Total bilirubin",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["tbil_value"], "width": 12}]}]}]},
        "fields": {
            "tbil_value": {"code": "tbil_value", "label": "Total Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1}
        }
    }
    
    templates["Direct Bilirubin"] = {
        "discipline": "CHEMISTRY",
        "description": "Conjugated bilirubin",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["dbil_value"], "width": 12}]}]}]},
        "fields": {
            "dbil_value": {"code": "dbil_value", "label": "Direct Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1}
        }
    }
    
    templates["Alanine Aminotransferase (ALT)"] = {
        "discipline": "CHEMISTRY",
        "description": "Liver enzyme - hepatocellular injury",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["alt_value"], "width": 12}]}]}]},
        "fields": {
            "alt_value": {"code": "alt_value", "label": "ALT", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Aspartate Aminotransferase (AST)"] = {
        "discipline": "CHEMISTRY",
        "description": "Liver enzyme - hepatocellular injury",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ast_value"], "width": 12}]}]}]},
        "fields": {
            "ast_value": {"code": "ast_value", "label": "AST", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Alkaline Phosphatase (ALP)"] = {
        "discipline": "CHEMISTRY",
        "description": "Liver enzyme - cholestasis",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["alp_value"], "width": 12}]}]}]},
        "fields": {
            "alp_value": {"code": "alp_value", "label": "ALP", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Gamma-Glutamyl Transferase (GGT)"] = {
        "discipline": "CHEMISTRY",
        "description": "Liver enzyme - cholestasis",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ggt_value"], "width": 12}]}]}]},
        "fields": {
            "ggt_value": {"code": "ggt_value", "label": "GGT", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Total Protein"] = {
        "discipline": "CHEMISTRY",
        "description": "Total serum protein",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["tp_value"], "width": 12}]}]}]},
        "fields": {
            "tp_value": {"code": "tp_value", "label": "Total Protein", "type": "numeric", "unit": "g/L", "decimals": 1}
        }
    }
    
    templates["Serum Albumin"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum albumin",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["alb_value"], "width": 12}]}]}]},
        "fields": {
            "alb_value": {"code": "alb_value", "label": "Albumin", "type": "numeric", "unit": "g/L", "decimals": 1}
        }
    }
    
    templates["Urea"] = {
        "discipline": "CHEMISTRY",
        "description": "Blood urea nitrogen",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["urea_value"], "width": 12}]}]}]},
        "fields": {
            "urea_value": {"code": "urea_value", "label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Creatinine"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum creatinine",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["creat_value"], "width": 12}]}]}]},
        "fields": {
            "creat_value": {"code": "creat_value", "label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0}
        }
    }
    
    templates["Uric Acid"] = {
        "discipline": "CHEMISTRY",
        "description": "Uric acid - gout marker",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ua_value"], "width": 12}]}]}]},
        "fields": {
            "ua_value": {"code": "ua_value", "label": "Uric Acid", "type": "numeric", "unit": "μmol/L", "decimals": 0}
        }
    }
    
    templates["Calcium"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum calcium",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ca_value"], "width": 12}]}]}]},
        "fields": {
            "ca_value": {"code": "ca_value", "label": "Calcium", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Phosphorus"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum phosphorus",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["phos_value"], "width": 12}]}]}]},
        "fields": {
            "phos_value": {"code": "phos_value", "label": "Phosphorus", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Magnesium"] = {
        "discipline": "CHEMISTRY",
        "description": "Serum magnesium",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["mg_value"], "width": 12}]}]}]},
        "fields": {
            "mg_value": {"code": "mg_value", "label": "Magnesium", "type": "numeric", "unit": "mmol/L", "decimals": 2}
        }
    }
    
    templates["Amylase"] = {
        "discipline": "CHEMISTRY",
        "description": "Pancreatic enzyme - acute pancreatitis",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["amyl_value"], "width": 12}]}]}]},
        "fields": {
            "amyl_value": {"code": "amyl_value", "label": "Amylase", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Lipase"] = {
        "discipline": "CHEMISTRY",
        "description": "Pancreatic enzyme - acute pancreatitis",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["lipase_value"], "width": 12}]}]}]},
        "fields": {
            "lipase_value": {"code": "lipase_value", "label": "Lipase", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Creatine Kinase (CK)"] = {
        "discipline": "CHEMISTRY",
        "description": "Muscle injury marker",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ck_value"], "width": 12}]}]}]},
        "fields": {
            "ck_value": {"code": "ck_value", "label": "Creatine Kinase (CK)", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["Lactate Dehydrogenase (LDH)"] = {
        "discipline": "CHEMISTRY",
        "description": "Tissue damage marker",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ldh_value"], "width": 12}]}]}]},
        "fields": {
            "ldh_value": {"code": "ldh_value", "label": "LDH", "type": "numeric", "unit": "U/L", "decimals": 0}
        }
    }
    
    templates["C-Reactive Protein (CRP)"] = {
        "discipline": "CHEMISTRY",
        "description": "Inflammation marker",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["crp_value"], "width": 12}]}]}]},
        "fields": {
            "crp_value": {"code": "crp_value", "label": "CRP", "type": "numeric", "unit": "mg/L", "decimals": 1}
        }
    }
    
    # ==================== THYROID TEMPLATES ====================
    
    templates["Thyroid Stimulating Hormone (TSH)"] = {
        "discipline": "CHEMISTRY",
        "description": "Thyroid function screening",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["tsh_value"], "width": 12}]}]}]},
        "fields": {
            "tsh_value": {"code": "tsh_value", "label": "TSH", "type": "numeric", "unit": "mIU/L", "decimals": 2}
        }
    }
    
    templates["Free T4 (fT4)"] = {
        "discipline": "CHEMISTRY",
        "description": "Active thyroid hormone",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ft4_value"], "width": 12}]}]}]},
        "fields": {
            "ft4_value": {"code": "ft4_value", "label": "Free T4", "type": "numeric", "unit": "pmol/L", "decimals": 2}
        }
    }
    
    templates["Free T3 (fT3)"] = {
        "discipline": "CHEMISTRY",
        "description": "Active thyroid hormone",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["ft3_value"], "width": 12}]}]}]},
        "fields": {
            "ft3_value": {"code": "ft3_value", "label": "Free T3", "type": "numeric", "unit": "pmol/L", "decimals": 2}
        }
    }
    
    templates["Thyroid Profile (TSH, fT4)"] = {
        "discipline": "CHEMISTRY",
        "description": "Basic thyroid panel",
        "layout": {
            "sections": [
                {"id": "sec_results", "title": "Thyroid Profile", "rows": [{"columns": [{"items": ["tsh_value"], "width": 6}, {"items": ["ft4_value"], "width": 6}]}]}
            ]
        },
        "fields": {
            "tsh_value": {"code": "tsh_value", "label": "TSH", "type": "numeric", "unit": "mIU/L", "decimals": 2},
            "ft4_value": {"code": "ft4_value", "label": "Free T4", "type": "numeric", "unit": "pmol/L", "decimals": 2}
        }
    }
    
    # ==================== URINALYSIS TEMPLATES ====================
    
    templates["Urinalysis (Complete)"] = {
        "discipline": "URINALYSIS",
        "description": "Complete urinalysis - physical, chemical, microscopic",
        "layout": {
            "sections": [
                {"id": "sec_physical", "title": "Physical", "rows": [{"columns": [{"items": ["color"], "width": 4}, {"items": ["clarity"], "width": 4}, {"items": ["urine_sg"], "width": 4}]}]},
                {"id": "sec_chemical", "title": "Chemical (Dipstick)", "rows": [{"columns": [{"items": ["ph"], "width": 3}, {"items": ["protein"], "width": 3}, {"items": ["glucose"], "width": 3}, {"items": ["ketones"], "width": 3}]},
                    {"columns": [{"items": ["blood"], "width": 3}, {"items": ["bilirubin"], "width": 3}, {"items": ["urobilinogen"], "width": 3}, {"items": ["nitrite"], "width": 3}]},
                    {"columns": [{"items": ["leukocytes"], "width": 12}]}]},
                {"id": "sec_microscopic", "title": "Microscopic", "rows": [{"columns": [{"items": ["wbc_hpf"], "width": 4}, {"items": ["rbc_hpf"], "width": 4}, {"items": ["epithelial"], "width": 4}]},
                    {"columns": [{"items": ["casts"], "width": 6}, {"items": ["crystals"], "width": 6}]},
                    {"columns": [{"items": ["bacteria"], "width": 12}]}]}
            ]
        },
        "fields": {
            "color": {"code": "color", "label": "Color", "type": "select", "options": ["Pale Yellow", "Yellow", "Dark Yellow", "Amber", "Brown", "Red", "Green"]},
            "clarity": {"code": "clarity", "label": "Clarity", "type": "select", "options": ["Clear", "Slightly Cloudy", "Cloudy", "Turbid"]},
            "urine_sg": {"code": "urine_sg", "label": "Specific Gravity", "type": "numeric", "unit": "SG", "decimals": 3},
            "ph": {"code": "ph", "label": "pH", "type": "numeric", "unit": "", "decimals": 1},
            "protein": {"code": "protein", "label": "Protein", "type": "select", "options": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
            "glucose": {"code": "glucose", "label": "Glucose", "type": "select", "options": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
            "ketones": {"code": "ketones", "label": "Ketones", "type": "select", "options": ["Negative", "Trace", "1+", "2+", "3+"]},
            "blood": {"code": "blood", "label": "Blood", "type": "select", "options": ["Negative", "Trace", "Non-hemolyzed", "Hemolyzed"]},
            "bilirubin": {"code": "bilirubin", "label": "Bilirubin", "type": "select", "options": ["Negative", "1+", "2+", "3+"]},
            "urobilinogen": {"code": "urobilinogen", "label": "Urobilinogen", "type": "select", "options": ["Normal", "1+", "2+", "3+"]},
            "nitrite": {"code": "nitrite", "label": "Nitrite", "type": "select", "options": ["Negative", "Positive"]},
            "leukocytes": {"code": "leukocytes", "label": "Leukocytes", "type": "select", "options": ["Negative", "Positive"]},
            "wbc_hpf": {"code": "wbc_hpf", "label": "WBC/HPF", "type": "select", "options": ["0-1", "1-5", "5-10", "10-20", ">20"]},
            "rbc_hpf": {"code": "rbc_hpf", "label": "RBC/HPF", "type": "select", "options": ["0-1", "1-5", "5-10", "10-20", ">20"]},
            "epithelial": {"code": "epithelial", "label": "Epithelial Cells", "type": "text"},
            "casts": {"code": "casts", "label": "Casts", "type": "text"},
            "crystals": {"code": "crystals", "label": "Crystals", "type": "text"},
            "bacteria": {"code": "bacteria", "label": "Bacteria", "type": "text"}
        }
    }
    
    templates["Urine Dipstick"] = {
        "discipline": "URINALYSIS",
        "description": "Urine chemistry using dipstick",
        "layout": {
            "sections": [
                {"id": "sec_physical", "title": "Physical", "rows": [{"columns": [{"items": ["color"], "width": 6}, {"items": ["clarity"], "width": 6}]}]},
                {"id": "sec_chemical", "title": "Chemical", "rows": [{"columns": [{"items": ["ph"], "width": 4}, {"items": ["protein"], "width": 4}, {"items": ["glucose"], "width": 4}]},
                    {"columns": [{"items": ["ketones"], "width": 4}, {"items": ["blood"], "width": 4}, {"items": ["nitrite"], "width": 4}]}]}
            ]
        },
        "fields": {
            "color": {"code": "color", "label": "Color", "type": "select", "options": ["Pale Yellow", "Yellow", "Dark Yellow", "Amber", "Brown", "Red"]},
            "clarity": {"code": "clarity", "label": "Clarity", "type": "select", "options": ["Clear", "Slightly Cloudy", "Cloudy", "Turbid"]},
            "ph": {"code": "ph", "label": "pH", "type": "numeric", "unit": "", "decimals": 1},
            "protein": {"code": "protein", "label": "Protein", "type": "select", "options": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
            "glucose": {"code": "glucose", "label": "Glucose", "type": "select", "options": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
            "ketones": {"code": "ketones", "label": "Ketones", "type": "select", "options": ["Negative", "Trace", "1+", "2+", "3+"]},
            "blood": {"code": "blood", "label": "Blood", "type": "select", "options": ["Negative", "Trace", "Non-hemolyzed", "Hemolyzed"]},
            "nitrite": {"code": "nitrite", "label": "Nitrite", "type": "select", "options": ["Negative", "Positive"]}
        }
    }
    
    # ==================== BLOOD BANK TEMPLATES ====================
    
    templates["Blood Grouping (ABO & Rh)"] = {
        "discipline": "BLOOD BANK",
        "description": "ABO and Rhesus blood group",
        "layout": {
            "sections": [
                {"id": "sec_abo", "title": "ABO Group", "rows": [{"columns": [{"items": ["abo_group"], "width": 12}]}]},
                {"id": "sec_rh", "title": "Rh Type", "rows": [{"columns": [{"items": ["rh_type"], "width": 12}]}]},
                {"id": "sec_notes", "title": "Notes", "rows": [{"columns": [{"items": ["notes"], "width": 12}]}]}
            ]
        },
        "fields": {
            "abo_group": {"code": "abo_group", "label": "ABO Group", "type": "select", "options": ["A", "B", "AB", "O"]},
            "rh_type": {"code": "rh_type", "label": "Rh Factor", "type": "select", "options": ["Positive", "Negative"]},
            "notes": {"code": "notes", "label": "Notes", "type": "text", "multiline": True}
        }
    }
    
    templates["Crossmatch"] = {
        "discipline": "BLOOD BANK",
        "description": "Compatibility testing for transfusion",
        "layout": {
            "sections": [
                {"id": "sec_result", "title": "Crossmatch Result", "rows": [{"columns": [{"items": ["xm_result"], "width": 6}, {"items": ["units"], "width": 6}]}]},
                {"id": "sec_notes", "title": "Notes", "rows": [{"columns": [{"items": ["notes"], "width": 12}]}]}
            ]
        },
        "fields": {
            "xm_result": {"code": "xm_result", "label": "Crossmatch", "type": "select", "options": ["Compatible", "Incompatible"]},
            "units": {"code": "units", "label": "Units Reserved", "type": "numeric", "unit": "units", "decimals": 0},
            "notes": {"code": "notes", "label": "Notes", "type": "text", "multiline": True}
        }
    }
    
    # ==================== SEROLOGY TEMPLATES (Generic for rapid tests) ====================
    
    templates["HIV 1 & 2 (Rapid)"] = {
        "discipline": "SEROLOGY",
        "description": "HIV screening test",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["hiv_result"], "width": 12}]}]}]},
        "fields": {
            "hiv_result": {"code": "hiv_result", "label": "HIV 1&2", "type": "select", "options": ["Negative", "Positive", "Indeterminate"]}
        }
    }
    
    templates["Hepatitis B Surface Antigen (HBsAg)"] = {
        "discipline": "SEROLOGY",
        "description": "Hepatitis B infection marker",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["hbsag_result"], "width": 12}]}]}]},
        "fields": {
            "hbsag_result": {"code": "hbsag_result", "label": "HBsAg", "type": "select", "options": ["Non-reactive", "Reactive"]}
        }
    }
    
    templates["Hepatitis C Antibody"] = {
        "discipline": "SEROLOGY",
        "description": "Hepatitis C screening",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["hcv_result"], "width": 12}]}]}]},
        "fields": {
            "hcv_result": {"code": "hcv_result", "label": "HCV Antibody", "type": "select", "options": ["Non-reactive", "Reactive"]}
        }
    }
    
    templates["Typhoid (Widal Test)"] = {
        "discipline": "SEROLOGY",
        "description": "Salmonella typhi antibody",
        "layout": {
            "sections": [
                {"id": "sec_o", "title": "O Antigen", "rows": [{"columns": [{"items": ["widal_o"], "width": 12}]}]},
                {"id": "sec_h", "title": "H Antigen", "rows": [{"columns": [{"items": ["widal_h"], "width": 12}]}]},
                {"id": "sec_interp", "title": "Interpretation", "rows": [{"columns": [{"items": ["interpretation"], "width": 12}]}]}
            ]
        },
        "fields": {
            "widal_o": {"code": "widal_o", "label": "O Agglutinins", "type": "select", "options": ["Negative", "O:1:40", "O:1:80", "O:1:160", "O:1:320"]},
            "widal_h": {"code": "widal_h", "label": "H Agglutinins", "type": "select", "options": ["Negative", "H:1:40", "H:1:80", "H:1:160", "H:1:320"]},
            "interpretation": {"code": "interpretation", "label": "Interpretation", "type": "text"}
        }
    }
    
    templates["Malaria Rapid Diagnostic Test (RDT)"] = {
        "discipline": "PARASITOLOGY",
        "description": "Rapid malaria antigen detection",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["malaria_result"], "width": 12}]}]}]},
        "fields": {
            "malaria_result": {"code": "malaria_result", "label": "Malaria RDT", "type": "select", "options": ["Negative", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"]}
        }
    }
    
    templates["Malaria Blood Smear"] = {
        "discipline": "PARASITOLOGY",
        "description": "Malaria parasite identification",
        "layout": {
            "sections": [
                {"id": "sec_thick", "title": "Thick Film", "rows": [{"columns": [{"items": ["thick_film"], "width": 12}]}]},
                {"id": "sec_thin", "title": "Thin Film", "rows": [{"columns": [{"items": ["thin_film"], "width": 6}, {"items": ["parasite_count"], "width": 6}]}]}
            ]
        },
        "fields": {
            "thick_film": {"code": "thick_film", "label": "Thick Film", "type": "select", "options": ["No parasites seen", "Parasites seen"]},
            "thin_film": {"code": "thin_film", "label": "Species", "type": "select", "options": ["P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed", "No parasites"]},
            "parasite_count": {"code": "parasite_count", "label": "Parasite Count", "type": "text"}
        }
    }
    
    templates["Syphilis (VDRL/RPR)"] = {
        "discipline": "SEROLOGY",
        "description": "Syphilis screening",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["vdrl_result"], "width": 12}]}]}]},
        "fields": {
            "vdrl_result": {"code": "vdrl_result", "label": "VDRL/RPR", "type": "select", "options": ["Non-reactive", "Reactive", "Weakly Reactive"]}
        }
    }
    
    templates["Pregnancy Test (Urine)"] = {
        "discipline": "CHEMISTRY",
        "description": "Urine hCG pregnancy test",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["pregnancy_result"], "width": 12}]}]}]},
        "fields": {
            "pregnancy_result": {"code": "pregnancy_result", "label": "Pregnancy Test", "type": "select", "options": ["Negative", "Positive"]}
        }
    }
    
    templates["Serum Beta hCG"] = {
        "discipline": "CHEMISTRY",
        "description": "Quantitative pregnancy test",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["bhcg_value"], "width": 12}]}]}]},
        "fields": {
            "bhcg_value": {"code": "bhcg_value", "label": "β-hCG", "type": "numeric", "unit": "mIU/mL", "decimals": 1}
        }
    }
    
    templates["Dengue NS1 Antigen"] = {
        "discipline": "SEROLOGY",
        "description": "Dengue early detection",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["deng_ns1"], "width": 12}]}]}]},
        "fields": {
            "deng_ns1": {"code": "deng_ns1", "label": "Dengue NS1", "type": "select", "options": ["Negative", "Positive"]}
        }
    }
    
    templates["COVID-19 Antigen"] = {
        "discipline": "SEROLOGY",
        "description": "SARS-CoV-2 antigen detection",
        "layout": {"sections": [{"id": "sec_result", "title": "Result", "rows": [{"columns": [{"items": ["covid_ag"], "width": 12}]}]}]},
        "fields": {
            "covid_ag": {"code": "covid_ag", "label": "COVID-19 Antigen", "type": "select", "options": ["Negative", "Positive"]}
        }
    }
    
    # ==================== MICROBIOLOGY TEMPLATES ====================
    
    templates["Urine Culture & Sensitivity"] = {
        "discipline": "MICROBIOLOGY",
        "description": "Bacterial culture and antibiotic sensitivity",
        "layout": {
            "sections": [
                {"id": "sec_culture", "title": "Culture", "rows": [{"columns": [{"items": ["growth"], "width": 6}, {"items": ["organism"], "width": 6}]}]},
                {"id": "sec_sensitivity", "title": "Sensitivity", "rows": [{"columns": [{"items": ["sensitivity"], "width": 12}]}]},
                {"id": "sec_notes", "title": "Notes", "rows": [{"columns": [{"items": ["notes"], "width": 12}]}]}
            ]
        },
        "fields": {
            "growth": {"code": "growth", "label": "Growth", "type": "select", "options": ["No Growth", "Mixed Growth", "Scanty", "Light", "Moderate", "Heavy"]},
            "organism": {"code": "organism", "label": "Organism Isolated", "type": "text"},
            "sensitivity": {"code": "sensitivity", "label": "Sensitivity Pattern", "type": "text", "multiline": True},
            "notes": {"code": "notes", "label": "Lab Notes", "type": "text", "multiline": True}
        }
    }
    
    templates["Blood Culture"] = {
        "discipline": "MICROBIOLOGY",
        "description": "Bacterial/fungal culture from blood",
        "layout": {
            "sections": [
                {"id": "sec_culture", "title": "Culture Result", "rows": [{"columns": [{"items": ["growth"], "width": 6}, {"items": ["organism"], "width": 6}]}]},
                {"id": "sec_notes", "title": "Notes", "rows": [{"columns": [{"items": ["notes"], "width": 12}]}]}
            ]
        },
        "fields": {
            "growth": {"code": "growth", "label": "Growth", "type": "select", "options": ["No Growth", "Contaminated", "Growth - See organism"]},
            "organism": {"code": "organism", "label": "Organism", "type": "text"},
            "notes": {"code": "notes", "label": "Notes", "type": "text", "multiline": True}
        }
    }
    
    templates["Stool Culture"] = {
        "discipline": "MICROBIOLOGY",
        "description": "Bacterial culture for enteric pathogens",
        "layout": {
            "sections": [
                {"id": "sec_culture", "title": "Culture", "rows": [{"columns": [{"items": ["salmonella"], "width": 4}, {"items": ["shigella"], "width": 4}, {"items": ["campylobacter"], "width": 4}]},
                    {"columns": [{"items": ["e_coli"], "width": 6}, {"items": ["others"], "width": 6}]}]}
            ]
        },
        "fields": {
            "salmonella": {"code": "salmonella", "label": "Salmonella", "type": "select", "options": ["Not Isolated", "Isolated"]},
            "shigella": {"code": "shigella", "label": "Shigella", "type": "select", "options": ["Not Isolated", "Isolated"]},
            "campylobacter": {"code": "campylobacter", "label": "Campylobacter", "type": "select", "options": ["Not Isolated", "Isolated"]},
            "e_coli": {"code": "e_coli", "label": "E. coli O157", "type": "select", "options": ["Not Isolated", "Isolated"]},
            "others": {"code": "others", "label": "Other Findings", "type": "text"}
        }
    }
    
    templates["Stool Microscopy (Ova & Cysts)"] = {
        "discipline": "MICROBIOLOGY",
        "description": "Parasitology examination",
        "layout": {
            "sections": [
                {"id": "sec_micro", "title": "Microscopy", "rows": [{"columns": [{"items": ["ova"], "width": 6}, {"items": ["cysts"], "width": 6}]}]},
                {"id": "sec_other", "title": "Other Findings", "rows": [{"columns": [{"items": ["others"], "width": 12}]}]}
            ]
        },
        "fields": {
            "ova": {"code": "ova", "label": "Ova", "type": "select", "options": ["Not Seen", "Ascaris lumbricoides", "Hookworm", "Trichuris trichiura", "Taenia spp.", "Hymenolepis nana", "Other"]},
            "cysts": {"code": "cysts", "label": "Cysts", "type": "select", "options": ["Not Seen", "Giardia lamblia", "Entamoeba histolytica", "Cryptosporidium", "Other"]},
            "others": {"code": "others", "label": "Other Findings", "type": "text"}
        }
    }
    
    templates["Sputum for AFB"] = {
        "discipline": "MICROBIOLOGY",
        "description": "Acid-fast bacilli stain for tuberculosis",
        "layout": {
            "sections": [
                {"id": "sec_afb", "title": "AFB Stain", "rows": [{"columns": [{"items": ["afb_result"], "width": 12}]}]},
                {"id": "sec_scanty", "title": "Quantitation", "rows": [{"columns": [{"items": ["quantitation"], "width": 12}]}]}
            ]
        },
        "fields": {
            "afb_result": {"code": "afb_result", "label": "AFB Stain", "type": "select", "options": ["Negative", "1+", "2+", "3+", "Scanty"]},
            "quantitation": {"code": "quantitation", "label": "Quantitation", "type": "text"}
        }
    }
    
    # ==================== PROFILE TEMPLATES ====================
    
    templates["Pre-operative Profile"] = {
        "discipline": "PROFILE",
        "description": "Surgical clearance profile",
        "layout": {
            "sections": [
                {"id": "sec_hem", "title": "Hematology", "rows": [{"columns": [{"items": ["hb"], "width": 4}, {"items": ["wbc"], "width": 4}, {"items": ["plt"], "width": 4}]},
                    {"columns": [{"items": ["pt"], "width": 6}, {"items": ["aptt"], "width": 6}]}]},
                {"id": "sec_chem", "title": "Chemistry", "rows": [{"columns": [{"items": ["fbg"], "width": 4}, {"items": ["urea"], "width": 4}, {"items": ["creat"], "width": 4}]},
                    {"columns": [{"items": ["na"], "width": 4}, {"items": ["k"], "width": 4}]}]},
                {"id": "sec_infect", "title": "Infection Screen", "rows": [{"columns": [{"items": ["hiv"], "width": 6}, {"items": ["hbsag"], "width": 6}]},
                    {"columns": [{"items": ["hcv"], "width": 6}, {"items": ["vdrl"], "width": 6}]}]}
            ]
        },
        "fields": {
            "hb": {"code": "hb", "label": "Hb", "type": "numeric", "unit": "g/dL", "decimals": 1},
            "wbc": {"code": "wbc", "label": "WBC", "type": "numeric", "unit": "x10^9/L", "decimals": 2},
            "plt": {"code": "plt", "label": "Platelets", "type": "numeric", "unit": "x10^9/L", "decimals": 0},
            "pt": {"code": "pt", "label": "PT", "type": "numeric", "unit": "sec", "decimals": 1},
            "aptt": {"code": "aptt", "label": "APTT", "type": "numeric", "unit": "sec", "decimals": 1},
            "fbg": {"code": "fbg", "label": "Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "urea": {"code": "urea", "label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "creat": {"code": "creat", "label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0},
            "na": {"code": "na", "label": "Sodium", "type": "numeric", "unit": "mmol/L", "decimals": 1},
            "k": {"code": "k", "label": "Potassium", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "hiv": {"code": "hiv", "label": "HIV", "type": "select", "options": ["Negative", "Positive"]},
            "hbsag": {"code": "hbsag", "label": "HBsAg", "type": "select", "options": ["Negative", "Positive"]},
            "hcv": {"code": "hcv", "label": "HCV", "type": "select", "options": ["Negative", "Positive"]},
            "vdrl": {"code": "vdrl", "label": "VDRL", "type": "select", "options": ["Negative", "Positive"]}
        }
    }
    
    templates["Antenatal Profile 1"] = {
        "discipline": "PROFILE",
        "description": "First antenatal booking profile",
        "layout": {
            "sections": [
                {"id": "sec_hem", "title": "Hematology", "rows": [{"columns": [{"items": ["hb"], "width": 4}, {"items": ["wbc"], "width": 4}, {"items": ["plt"], "width": 4}]},
                    {"columns": [{"items": ["blood_group"], "width": 4}, {"items": ["rh_type"], "width": 4}]}]},
                {"id": "sec_infect", "title": "Infection Screen", "rows": [{"columns": [{"items": ["hiv"], "width": 6}, {"items": ["hbsag"], "width": 6}]},
                    {"columns": [{"items": ["hcv"], "width": 6}, {"items": ["vdrl"], "width": 6}]},
                    {"columns": [{"items": ["rubella"], "width": 12}]}]},
                {"id": "sec_chem", "title": "Chemistry", "rows": [{"columns": [{"items": ["fbg"], "width": 6}, {"items": ["creat"], "width": 6}]}]}
            ]
        },
        "fields": {
            "hb": {"code": "hb", "label": "Hb", "type": "numeric", "unit": "g/dL", "decimals": 1},
            "wbc": {"code": "wbc", "label": "WBC", "type": "numeric", "unit": "x10^9/L", "decimals": 2},
            "plt": {"code": "plt", "label": "Platelets", "type": "numeric", "unit": "x10^9/L", "decimals": 0},
            "blood_group": {"code": "blood_group", "label": "ABO Group", "type": "select", "options": ["A", "B", "AB", "O", "Not Done"]},
            "rh_type": {"code": "rh_type", "label": "Rh Type", "type": "select", "options": ["Positive", "Negative", "Not Done"]},
            "hiv": {"code": "hiv", "label": "HIV", "type": "select", "options": ["Negative", "Positive", "Not Done"]},
            "hbsag": {"code": "hbsag", "label": "HBsAg", "type": "select", "options": ["Negative", "Positive", "Not Done"]},
            "hcv": {"code": "hcv", "label": "HCV", "type": "select", "options": ["Negative", "Positive", "Not Done"]},
            "vdrl": {"code": "vdrl", "label": "VDRL", "type": "select", "options": ["Negative", "Positive", "Not Done"]},
            "rubella": {"code": "rubella", "label": "Rubella IgG", "type": "select", "options": ["Immune", "Not Immune", "Not Done"]},
            "fbg": {"code": "fbg", "label": "Fasting Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "creat": {"code": "creat", "label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0}
        }
    }
    
    templates["Diabetes Profile"] = {
        "discipline": "PROFILE",
        "description": "Diabetes monitoring profile",
        "layout": {
            "sections": [
                {"id": "sec_glucose", "title": "Glucose", "rows": [{"columns": [{"items": ["fbg"], "width": 6}, {"items": ["ppbg"], "width": 6}]},
                    {"columns": [{"items": ["hba1c"], "width": 12}]}]},
                {"id": "sec_lipid", "title": "Lipid Profile", "rows": [{"columns": [{"items": ["chol"], "width": 4}, {"items": ["tg"], "width": 4}, {"items": ["hdl"], "width": 4}]}]},
                {"id": "sec_renal", "title": "Renal Function", "rows": [{"columns": [{"items": ["creat"], "width": 4}, {"items": ["egfr"], "width": 4}, {"items": ["uacr"], "width": 4}]}]}
            ]
        },
        "fields": {
            "fbg": {"code": "fbg", "label": "Fasting Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "ppbg": {"code": "ppbg", "label": "2-Hour PP", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "hba1c": {"code": "hba1c", "label": "HbA1c", "type": "numeric", "unit": "%", "decimals": 1},
            "chol": {"code": "chol", "label": "Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "tg": {"code": "tg", "label": "Triglycerides", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "hdl": {"code": "hdl", "label": "HDL", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "creat": {"code": "creat", "label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0},
            "egfr": {"code": "egfr", "label": "eGFR", "type": "numeric", "unit": "mL/min", "decimals": 0},
            "uacr": {"code": "uacr", "label": "UACR", "type": "numeric", "unit": "mg/mmol", "decimals": 2}
        }
    }
    
    templates["Fever Profile"] = {
        "discipline": "PROFILE",
        "description": "Fever workup panel",
        "layout": {
            "sections": [
                {"id": "sec_hem", "title": "Hematology", "rows": [{"columns": [{"items": ["hb"], "width": 4}, {"items": ["wbc"], "width": 4}, {"items": ["esr"], "width": 4}]},
                    {"columns": [{"items": ["plt"], "width": 12}]}]},
                {"id": "sec_chem", "title": "Chemistry", "rows": [{"columns": [{"items": ["fbg"], "width": 4}, {"items": ["urea"], "width": 4}, {"items": ["creat"], "width": 4}]},
                    {"columns": [{"items": ["alt"], "width": 4}, {"items": ["ast"], "width": 4}]}]},
                {"id": "sec_infect", "title": "Infection Screen", "rows": [{"columns": [{"items": ["crp"], "width": 6}, {"items": ["malaria"], "width": 6}]},
                    {"columns": [{"items": ["widal"], "width": 12}]}]}
            ]
        },
        "fields": {
            "hb": {"code": "hb", "label": "Hb", "type": "numeric", "unit": "g/dL", "decimals": 1},
            "wbc": {"code": "wbc", "label": "WBC", "type": "numeric", "unit": "x10^9/L", "decimals": 2},
            "esr": {"code": "esr", "label": "ESR", "type": "numeric", "unit": "mm/hr", "decimals": 0},
            "plt": {"code": "plt", "label": "Platelets", "type": "numeric", "unit": "x10^9/L", "decimals": 0},
            "fbg": {"code": "fbg", "label": "Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "urea": {"code": "urea", "label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            "creat": {"code": "creat", "label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0},
            "alt": {"code": "alt", "label": "ALT", "type": "numeric", "unit": "U/L", "decimals": 0},
            "ast": {"code": "ast", "label": "AST", "type": "numeric", "unit": "U/L", "decimals": 0},
            "crp": {"code": "crp", "label": "CRP", "type": "numeric", "unit": "mg/L", "decimals": 1},
            "malaria": {"code": "malaria", "label": "Malaria RDT", "type": "select", "options": ["Negative", "Positive"]},
            "widal": {"code": "widal", "label": "Widal", "type": "text"}
        }
    }
    
    return templates


# =============================================================================
# REFERENCE RANGES DATA
# =============================================================================

def get_reference_ranges():
    """Return reference ranges keyed by field code."""
    return {
        # CBC
        "hb": [
            {"sex": "M", "low": 13.0, "high": 17.5, "unit": "g/dL"},
            {"sex": "F", "low": 11.5, "high": 16.0, "unit": "g/dL"}
        ],
        "hct": [
            {"sex": "M", "low": 40.0, "high": 54.0, "unit": "%"},
            {"sex": "F", "low": 36.0, "high": 48.0, "unit": "%"}
        ],
        "rbc_count": [{"sex": "ANY", "low": 4.0, "high": 6.0, "unit": "x10^12/L"}],
        "wbc_count": [{"sex": "ANY", "low": 4.0, "high": 11.0, "unit": "x10^9/L"}],
        "platelet_count": [{"sex": "ANY", "low": 150, "high": 450, "unit": "x10^9/L"}],
        "mcv": [{"sex": "ANY", "low": 80.0, "high": 100.0, "unit": "fL"}],
        "mch": [{"sex": "ANY", "low": 27.0, "high": 33.0, "unit": "pg"}],
        "mchc": [{"sex": "ANY", "low": 32.0, "high": 36.0, "unit": "g/dL"}],
        
        # Chemistry - Liver
        "alt": [{"sex": "ANY", "low": 0.0, "high": 40.0, "unit": "U/L"}],
        "ast": [{"sex": "ANY", "low": 0.0, "high": 40.0, "unit": "U/L"}],
        "alp": [{"sex": "ANY", "low": 44.0, "high": 147.0, "unit": "U/L"}],
        "ggt": [{"sex": "M", "low": 0.0, "high": 55.0, "unit": "U/L"}, {"sex": "F", "low": 0.0, "high": 38.0, "unit": "U/L"}],
        "tbil": [{"sex": "ANY", "low": 0.0, "high": 21.0, "unit": "μmol/L"}],
        "dbil": [{"sex": "ANY", "low": 0.0, "high": 8.0, "unit": "μmol/L"}],
        "tp": [{"sex": "ANY", "low": 60.0, "high": 80.0, "unit": "g/L"}],
        "alb": [{"sex": "ANY", "low": 35.0, "high": 55.0, "unit": "g/L"}],
        
        # Chemistry - Kidney
        "urea": [{"sex": "ANY", "low": 2.9, "high": 8.2, "unit": "mmol/L"}],
        "creat": [{"sex": "M", "low": 62.0, "high": 115.0, "unit": "μmol/L"}, {"sex": "F", "low": 53.0, "high": 97.0, "unit": "μmol/L"}],
        "egfr": [{"sex": "ANY", "low": 90.0, "high": 120.0, "unit": "mL/min/1.73m²"}],
        
        # Electrolytes
        "na": [{"sex": "ANY", "low": 136.0, "high": 145.0, "unit": "mmol/L"}],
        "k": [{"sex": "ANY", "low": 3.5, "high": 5.0, "unit": "mmol/L"}],
        "cl": [{"sex": "ANY", "low": 98.0, "high": 106.0, "unit": "mmol/L"}],
        "hco3": [{"sex": "ANY", "low": 22.0, "high": 29.0, "unit": "mmol/L"}],
        
        # Lipids
        "chol": [{"sex": "ANY", "low": 0.0, "high": 5.2, "unit": "mmol/L"}],
        "tg": [{"sex": "ANY", "low": 0.0, "high": 1.7, "unit": "mmol/L"}],
        "hdl": [{"sex": "M", "low": 1.0, "high": 1.9, "unit": "mmol/L"}, {"sex": "F", "low": 1.2, "high": 2.2, "unit": "mmol/L"}],
        "ldl": [{"sex": "ANY", "low": 0.0, "high": 3.4, "unit": "mmol/L"}],
        
        # Glucose
        "fbg": [{"sex": "ANY", "low": 3.9, "high": 6.1, "unit": "mmol/L"}],
        "hba1c": [{"sex": "ANY", "low": 4.0, "high": 6.0, "unit": "%"}],
        
        # Minerals
        "ca": [{"sex": "ANY", "low": 2.1, "high": 2.6, "unit": "mmol/L"}],
        "phos": [{"sex": "ANY", "low": 0.8, "high": 1.5, "unit": "mmol/L"}],
        "mg": [{"sex": "ANY", "low": 0.7, "high": 1.1, "unit": "mmol/L"}],
        "ua": [{"sex": "M", "low": 150.0, "high": 440.0, "unit": "μmol/L"}, {"sex": "F", "low": 90.0, "high": 360.0, "unit": "μmol/L"}],
        
        # Enzymes
        "amyl": [{"sex": "ANY", "low": 28.0, "high": 100.0, "unit": "U/L"}],
        "lipase": [{"sex": "ANY", "low": 13.0, "high": 60.0, "unit": "U/L"}],
        "ck": [{"sex": "M", "low": 38.0, "high": 174.0, "unit": "U/L"}, {"sex": "F", "low": 26.0, "high": 140.0, "unit": "U/L"}],
        "ldh": [{"sex": "ANY", "low": 140.0, "high": 280.0, "unit": "U/L"}],
        
        # Thyroid
        "tsh": [{"sex": "ANY", "low": 0.4, "high": 4.0, "unit": "mIU/L"}],
        "ft4": [{"sex": "ANY", "low": 9.0, "high": 25.0, "unit": "pmol/L"}],
        "ft3": [{"sex": "ANY", "low": 3.5, "high": 6.5, "unit": "pmol/L"}],
        
        # Coagulation
        "pt": [{"sex": "ANY", "low": 11.0, "high": 13.5, "unit": "seconds"}],
        "aptt": [{"sex": "ANY", "low": 25.0, "high": 35.0, "unit": "seconds"}],
        
        # ESR
        "esr": [{"sex": "M", "low": 0.0, "high": 15.0, "unit": "mm/hr"}, {"sex": "F", "low": 0.0, "high": 20.0, "unit": "mm/hr"}],
        
        # Urine
        "urine_sg": [{"sex": "ANY", "low": 1.005, "high": 1.030, "unit": ""}],
    }


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def seed_templates():
    """Main function to seed templates."""
    print("=" * 70)
    print("COMPREHENSIVE LAB TEST TEMPLATES SEEDER")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("ERROR: Admin user not found. Run init_db.py first.")
            return
        
        admin_user_id = admin_user.id
        print(f"Using admin user ID: {admin_user_id}")
        
        # Get template definitions
        template_defs = get_template_definitions()
        print(f"\nProcessing {len(template_defs)} template definitions...")
        
        # Get reference ranges
        ref_ranges = get_reference_ranges()
        
        # Create templates
        templates_created = 0
        templates_updated = 0
        
        for name, template_data in template_defs.items():
            # Check if template already exists
            existing = db.query(LabTemplate).filter(LabTemplate.name == name).first()
            
            if existing:
                # Update existing template - create new version or update existing
                template = existing
                
                # Get the current max version
                from sqlalchemy import func
                max_version = db.query(func.max(LabTemplateVersion.version)).filter(
                    LabTemplateVersion.template_id == template.id
                ).scalar() or 0
                
                # Check if we already have this exact template data
                existing_version = db.query(LabTemplateVersion).filter(
                    LabTemplateVersion.template_id == template.id,
                    LabTemplateVersion.version == max_version
                ).first()
                
                # Use existing version if it matches, otherwise create new version
                if existing_version:
                    version = existing_version
                    version.schema_json = {
                        "meta": {
                            "name": name,
                            "discipline": template_data["discipline"],
                            "description": template_data["description"]
                        },
                        "layout": template_data["layout"],
                        "fields": template_data["fields"]
                    }
                else:
                    new_ver_num = max_version + 1
                    version = LabTemplateVersion(
                        template_id=template.id,
                        version=new_ver_num,
                        status="PUBLISHED",
                        schema_json={
                            "meta": {
                                "name": name,
                                "discipline": template_data["discipline"],
                                "description": template_data["description"]
                            },
                            "layout": template_data["layout"],
                            "fields": template_data["fields"]
                        },
                        change_note="Auto-generated template",
                        created_by_id=admin_user_id
                    )
                    db.add(version)
                    template.current_version = new_ver_num
            else:
                # Create new template
                template = LabTemplate(
                    name=name,
                    discipline=template_data["discipline"],
                    status="DRAFT",
                    created_by_id=admin_user_id
                )
                db.add(template)
                db.flush()
                templates_created += 1
            
            # Link to lab test in catalog if exists
            test = db.query(LabTest).filter(LabTest.test_name == name).first()
            if test:
                test.template_id = template.id
                test.template_version = template.current_version
            
            db.flush()
            print(f"  Created/Updated: {name}")
        
        # Create reference ranges
        print("\nCreating reference ranges...")
        ranges_created = 0
        
        for field_code, ranges_list in ref_ranges.items():
            for range_data in ranges_list:
                # Check if already exists
                existing = db.query(LabReferenceRange).filter(
                    LabReferenceRange.field_code == field_code,
                    LabReferenceRange.sex == range_data["sex"]
                ).first()
                
                if not existing:
                    db_range = LabReferenceRange(
                        field_code=field_code,
                        sex=range_data["sex"],
                        low=range_data.get("low"),
                        high=range_data.get("high"),
                        unit=range_data.get("unit")
                    )
                    db.add(db_range)
                    ranges_created += 1
        
        db.commit()
        
        print(f"\nTemplates created: {templates_created}")
        print(f"Reference ranges created: {ranges_created}")
        
        print("\n" + "=" * 70)
        print("TEMPLATE SEEDING COMPLETED!")
        print("=" * 70)
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_templates()
