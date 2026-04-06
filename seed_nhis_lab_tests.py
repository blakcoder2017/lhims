#!/usr/bin/env python3
"""
NHIS-Compliant Laboratory Test Catalog Update
=============================================
Updates LHIMS laboratory test catalog with standardized tests:

1. Full Blood Count (FBC)
2. BF for MPS (Malaria Parasite Test)
3. Widal Test
4. Erythrocyte Sedimentation Rate (ESR)

Features:
- Structured parameters
- Age- and sex-aware reference ranges
- Validation rules
- NHIS-ready report formatting
- Backward compatibility with historical results

Usage:
    python3 seed_nhis_lab_tests.py
"""

import os
import sys
import json
import os

# Set DATABASE_URL directly before any imports
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')
os.environ['DATABASE_URL'] = DATABASE_URL

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime

SQLALCHEMY_DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime

from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabReferenceRange, LabOptionSet
)
from app.models.user_models import User
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_or_create_admin_user(db: Session):
    """Get or create admin user for audit purposes"""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        # Try to find any active user
        admin = db.query(User).filter(User.is_active == True).first()
    return admin


# =============================================================================
# LAB TEST CATALOG DEFINITIONS
# =============================================================================

def get_lab_test_definitions():
    """Define the NHIS-compliant lab tests"""
    return [
        {
            "test_code": "FBC001",
            "test_name": "Full Blood Count (FBC)",
            "test_category": "HEMATOLOGY",
            "description": "Complete blood count with differential - NHIS compliant",
            "cost": 25.00,
            "routine_tat": 2,
            "is_active": True,
            "nhis_code": "FBC001",
            "specimen_type": "EDTA Whole Blood",
            "collection_method": "Automated Hematology Analyzer",
            "storage_requirements": "Room Temperature",
            "test_type": "Quantitative"
        },
        {
            "test_code": "MPS001",
            "test_name": "BF for MPS (Malaria Parasite)",
            "test_category": "PARASITOLOGY",
            "description": "Blood film examination for malaria parasites - NHIS compliant",
            "cost": 15.00,
            "routine_tat": 1,
            "is_active": True,
            "nhis_code": "MPS001",
            "specimen_type": "Finger Prick Blood / EDTA Whole Blood",
            "collection_method": "Microscopy (Giemsa Stained Thick and Thin Films)",
            "storage_requirements": "Room Temperature",
            "test_type": "Qualitative"
        },
        {
            "test_code": "WID001",
            "test_name": "Widal Test",
            "test_category": "SEROLOGY",
            "description": "Salmonella typhi and paratyphi antibody titre - NHIS compliant",
            "cost": 20.00,
            "routine_tat": 4,
            "is_active": True,
            "nhis_code": "WID001",
            "specimen_type": "Serum",
            "collection_method": "Slide Agglutination Test",
            "storage_requirements": "Refrigerate at 2-8°C",
            "test_type": "Titer"
        },
        {
            "test_code": "ESR001",
            "test_name": "Erythrocyte Sedimentation Rate (ESR)",
            "test_category": "HEMATOLOGY",
            "description": "ESR measurement - NHIS compliant",
            "cost": 15.00,
            "routine_tat": 1,
            "is_active": True,
            "nhis_code": "ESR001",
            "specimen_type": "Whole Blood (Sodium Citrate)",
            "collection_method": "Westergren Method",
            "storage_requirements": "Room Temperature",
            "test_type": "Quantitative"
        }
    ]


# =============================================================================
# OPTION SETS DEFINITIONS
# =============================================================================

def get_option_set_definitions():
    """Define reusable option sets for lab fields"""
    return [
        {
            "code": "MALARIA_PARASITES",
            "name": "Malaria Parasites Detected",
            "description": "Options for malaria parasite detection",
            "options_json": [
                {"value": "not_seen", "label": "Not Seen", "is_default": True},
                {"value": "seen", "label": "Seen", "is_default": False}
            ]
        },
        {
            "code": "MALARIA_SPECIES",
            "name": "Malaria Species",
            "description": "Malaria parasite species identification",
            "options_json": [
                {"value": "plasmodium_falciparum", "label": "Plasmodium falciparum", "is_default": False},
                {"value": "plasmodium_malariae", "label": "Plasmodium malariae", "is_default": False},
                {"value": "plasmodium_ovale", "label": "Plasmodium ovale", "is_default": False},
                {"value": "plasmodium_vivax", "label": "Plasmodium vivax", "is_default": False},
                {"value": "mixed_infection", "label": "Mixed Infection", "is_default": False},
                {"value": "not_applicable", "label": "Not Applicable", "is_default": True}
            ]
        },
        {
            "code": "YES_NO",
            "name": "Yes/No Options",
            "description": "Generic yes/no options",
            "options_json": [
                {"value": "no", "label": "No", "is_default": True},
                {"value": "yes", "label": "Yes", "is_default": False}
            ]
        },
        {
            "code": "PARASITE_DENSITY",
            "name": "Parasite Density Grading",
            "description": "Semi-quantitative parasite density",
            "options_json": [
                {"value": "0", "label": "0 (No parasites seen)", "is_default": True},
                {"value": "1plus", "label": "+ (1-10 parasites/100 µL)", "is_default": False},
                {"value": "2plus", "label": "++ (11-100 parasites/100 µL)", "is_default": False},
                {"value": "3plus", "label": "+++ (1-10 parasites/µL)", "is_default": False},
                {"value": "4plus", "label": "++++ (>10 parasites/µL)", "is_default": False}
            ]
        },
        {
            "code": "WIDAL_TITRE",
            "name": "Widal Titre Values",
            "description": "Standardized Widal test titre values",
            "options_json": [
                {"value": "negative", "label": "Negative (<1:80)", "is_default": False},
                {"value": "1:20", "label": "1:20", "is_default": False},
                {"value": "1:40", "label": "1:40", "is_default": False},
                {"value": "1:80", "label": "1:80 (Borderline)", "is_default": False},
                {"value": "1:160", "label": "1:160 (Significant)", "is_default": False},
                {"value": "1:320", "label": "1:320 (Significant)", "is_default": False},
                {"value": "1:640", "label": "1:640 (High)", "is_default": False},
                {"value": "1:1280", "label": "1:1280 (Very High)", "is_default": False}
            ]
        }
    ]


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

def get_template_definitions():
    """Define lab templates with full parameter specifications"""
    
    templates = {}
    
    # ==================== FULL BLOOD COUNT (FBC) ====================
    templates["Full Blood Count (FBC)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Complete Blood Count with differential - NHIS Compliant",
        "test_code": "FBC001",
        "layout": {
            "sections": [
                {"id": "sec_hb", "title": "Hemoglobin & Hematocrit", "rows": [
                    {"columns": [{"items": ["hb"], "width": 6}, {"items": ["hct"], "width": 6}]}
                ]},
                {"id": "sec_rbc", "title": "Red Blood Cell Indices", "rows": [
                    {"columns": [{"items": ["rbc_count"], "width": 3}, {"items": ["mcv"], "width": 3}, {"items": ["mch"], "width": 3}, {"items": ["mchc"], "width": 3}]}
                ]},
                {"id": "sec_wbc", "title": "White Blood Cells", "rows": [
                    {"columns": [{"items": ["wbc_count"], "width": 12}]}
                ]},
                {"id": "sec_diff", "title": "Differential Count", "rows": [
                    {"columns": [{"items": ["neutrophils"], "width": 4}, {"items": ["lymphocytes"], "width": 4}, {"items": ["monocytes"], "width": 4}]},
                    {"columns": [{"items": ["eosinophils"], "width": 4}, {"items": ["basophils"], "width": 4}]}
                ]},
                {"id": "sec_plt", "title": "Platelets", "rows": [
                    {"columns": [{"items": ["platelet_count"], "width": 12}]}
                ]},
                {"id": "sec_morph", "title": "Morphology (Optional)", "rows": [
                    {"columns": [{"items": ["rbcmorph"], "width": 4}, {"items": ["wbc_morph"], "width": 4}, {"items": ["plt_morph"], "width": 4}]}
                ]},
                {"id": "sec_notes", "title": "Notes & Interpretation", "rows": [
                    {"columns": [{"items": ["interpretation"], "width": 12}]}
                ]}
            ]
        },
        "fields": {
            "hb": {
                "code": "hb",
                "label": "Hemoglobin (Hb)",
                "type": "numeric",
                "unit": "g/dL",
                "decimals": 1,
                "min_value": 0,
                "max_value": 30,
                "required": True,
                "critical": {"low": 7.0, "high": 20.0},
                "validation_rules": {"min": 0, "max": 30},
                "clinical_note": "Primary indicator of anemia"
            },
            "hct": {
                "code": "hct",
                "label": "Packed Cell Volume (PCV/HCT)",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "min_value": 0,
                "max_value": 80,
                "required": True,
                "critical": {"low": 20.0, "high": 60.0},
                "validation_rules": {"min": 0, "max": 80},
                "clinical_note": "Ratio of red blood cells to total blood volume"
            },
            "rbc_count": {
                "code": "rbc_count",
                "label": "Red Blood Cell Count (RBC)",
                "type": "numeric",
                "unit": "×10¹²/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 10,
                "required": True,
                "validation_rules": {"min": 0, "max": 10},
                "clinical_note": "Number of red blood cells per liter of blood"
            },
            "mcv": {
                "code": "mcv",
                "label": "Mean Corpuscular Volume (MCV)",
                "type": "numeric",
                "unit": "fL",
                "decimals": 1,
                "min_value": 0,
                "max_value": 150,
                "required": False,
                "validation_rules": {"min": 0, "max": 150},
                "clinical_note": "Average volume of a red blood cell"
            },
            "mch": {
                "code": "mch",
                "label": "Mean Corpuscular Hemoglobin (MCH)",
                "type": "numeric",
                "unit": "pg",
                "decimals": 1,
                "min_value": 0,
                "max_value": 50,
                "required": False,
                "validation_rules": {"min": 0, "max": 50},
                "clinical_note": "Average mass of hemoglobin per red blood cell"
            },
            "mchc": {
                "code": "mchc",
                "label": "Mean Corpuscular Hemoglobin Concentration (MCHC)",
                "type": "numeric",
                "unit": "g/dL",
                "decimals": 1,
                "min_value": 0,
                "max_value": 50,
                "required": False,
                "validation_rules": {"min": 0, "max": 50},
                "clinical_note": "Concentration of hemoglobin in a given volume of packed red blood cells"
            },
            "wbc_count": {
                "code": "wbc_count",
                "label": "Total White Blood Cell Count",
                "type": "numeric",
                "unit": "×10⁹/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 50,
                "required": True,
                "critical": {"low": 2.0, "high": 30.0},
                "validation_rules": {"min": 0, "max": 50},
                "clinical_note": "Total number of white blood cells per liter"
            },
            "neutrophils": {
                "code": "neutrophils",
                "label": "Neutrophils",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "min_value": 0,
                "max_value": 100,
                "required": True,
                "validation_rules": {"min": 0, "max": 100},
                "clinical_note": "Primary defense against bacterial infections"
            },
            "lymphocytes": {
                "code": "lymphocytes",
                "label": "Lymphocytes",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "min_value": 0,
                "max_value": 100,
                "required": True,
                "validation_rules": {"min": 0, "max": 100},
                "clinical_note": "Involved in antibody production and cell-mediated immunity"
            },
            "monocytes": {
                "code": "monocytes",
                "label": "Monocytes",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "min_value": 0,
                "max_value": 100,
                "required": True,
                "validation_rules": {"min": 0, "max": 100},
                "clinical_note": "Phagocytic cells that engulf pathogens and debris"
            },
            "eosinophils": {
                "code": "eosinophils",
                "label": "Eosinophils",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "min_value": 0,
                "max_value": 100,
                "required": True,
                "validation_rules": {"min": 0, "max": 100},
                "clinical_note": "Involved in allergic reactions and parasitic infections"
            },
            "basophils": {
                "code": "basophils",
                "label": "Basophils",
                "type": "numeric",
                "unit": "%",
                "decimals": 1,
                "min_value": 0,
                "max_value": 100,
                "required": True,
                "validation_rules": {"min": 0, "max": 100},
                "clinical_note": "Release histamine and heparin, involved in allergic responses"
            },
            "platelet_count": {
                "code": "platelet_count",
                "label": "Platelet Count",
                "type": "numeric",
                "unit": "×10⁹/L",
                "decimals": 0,
                "min_value": 0,
                "max_value": 1500,
                "required": True,
                "critical": {"low": 20.0, "high": 1000.0},
                "validation_rules": {"min": 0, "max": 1500},
                "clinical_note": "Essential for blood clotting"
            },
            "rbcmorph": {
                "code": "rbcmorph",
                "label": "RBC Morphology",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "e.g., Normocytic, Normochromic"
            },
            "wbc_morph": {
                "code": "wbc_morph",
                "label": "WBC Morphology",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "e.g., Normal appearance"
            },
            "plt_morph": {
                "code": "plt_morph",
                "label": "Platelet Morphology",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "e.g., Adequate, few large platelets"
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Interpretation",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "Overall interpretation of FBC results"
            }
        }
    }
    
    # ==================== MALARIA PARASITE TEST (BF for MPS) ====================
    templates["BF for MPS (Malaria Parasite)"] = {
        "discipline": "PARASITOLOGY",
        "description": "Blood Film Examination for Malaria Parasites - NHIS Compliant",
        "test_code": "MPS001",
        "layout": {
            "sections": [
                {"id": "sec_parasite", "title": "Parasite Detection", "rows": [
                    {"columns": [{"items": ["malaria_parasites"], "width": 12}]}
                ]},
                {"id": "sec_species", "title": "Species Identification", "rows": [
                    {"columns": [{"items": ["malaria_species"], "width": 12}]}
                ]},
                {"id": "sec_gamete", "title": "Gametocytes & Schizonts", "rows": [
                    {"columns": [{"items": ["gametocytes_seen"], "width": 6}, {"items": ["schizonts_seen"], "width": 6}]}
                ]},
                {"id": "sec_count", "title": "Parasite Count", "rows": [
                    {"columns": [{"items": ["trophozoite_count"], "width": 12}]}
                ]},
                {"id": "sec_morph", "title": "Morphology Findings", "rows": [
                    {"columns": [{"items": ["film_quality"], "width": 6}, {"items": ["other_findings"], "width": 6}]}
                ]},
                {"id": "sec_notes", "title": "Notes & Interpretation", "rows": [
                    {"columns": [{"items": ["interpretation"], "width": 12}]}
                ]}
            ]
        },
        "fields": {
            "malaria_parasites": {
                "code": "malaria_parasites",
                "label": "Malaria Parasites (BF)",
                "type": "select",
                "option_set": "MALARIA_PARASITES",
                "required": True,
                "validation_rules": {
                    "required": True,
                    "custom_validation": "malaria parasites presence check"
                },
                "reference_range": {
                    "normal_value": "Not Seen",
                    "normal_range": "Not Seen",
                    "units": "N/A",
                    "all_ages": True,
                    "all_genders": True,
                    "applies_to_neonates": True,
                    "applies_to_children": True,
                    "applies_to_adults": True,
                    "applies_to_elderly": True,
                    "nhis_reference": "NHIS Lab Code: MPS001"
                },
                "clinical_note": "Primary result - presence or absence of malaria parasites",
                "display_order": 1,
                "dependency": None,
                "result_group": "Main Result"
            },
            "malaria_species": {
                "code": "malaria_species",
                "label": "Specie",
                "type": "select",
                "option_set": "MALARIA_SPECIES",
                "required": False,
                "validation_rules": {
                    "conditional_required": {
                        "when_field": "malaria_parasites",
                        "when_value": "seen",
                        "error_message": "Species is required when Malaria Parasites = Seen"
                    }
                },
                "reference_range": {
                    "normal_value": "Not Applicable",
                    "normal_range": "Not Applicable",
                    "units": "N/A",
                    "all_ages": True,
                    "all_genders": True,
                    "applies_to_neonates": True,
                    "applies_to_children": True,
                    "applies_to_adults": True,
                    "applies_to_elderly": True,
                    "nhis_reference": "NHIS Lab Code: MPS001"
                },
                "clinical_note": "Species identification (enabled only if parasites seen)",
                "display_order": 2,
                "dependency": {"field": "malaria_parasites", "value": "seen"},
                "result_group": "Main Result"
            },
            "gametocytes_seen": {
                "code": "gametocytes_seen",
                "label": "Gametocytes Seen",
                "type": "select",
                "option_set": "YES_NO",
                "required": False,
                "validation_rules": {
                    "auto_set_when_not_seen": {
                        "trigger_field": "malaria_parasites",
                        "trigger_value": "not_seen",
                        "set_value": "no",
                        "description": "Auto-set to No when Malaria Parasites = Not Seen"
                    }
                },
                "reference_range": {
                    "normal_value": "No",
                    "normal_range": "No",
                    "units": "N/A",
                    "all_ages": True,
                    "all_genders": True,
                    "applies_to_neonates": True,
                    "applies_to_children": True,
                    "applies_to_adults": True,
                    "applies_to_elderly": True,
                    "nhis_reference": "NHIS Lab Code: MPS001"
                },
                "clinical_note": "Sexual stage parasites (reference: No)",
                "display_order": 3,
                "dependency": {"field": "malaria_parasites", "value": "seen"},
                "result_group": "Morphology"
            },
            "schizonts_seen": {
                "code": "schizonts_seen",
                "label": "Schizonts Seen",
                "type": "select",
                "option_set": "YES_NO",
                "required": False,
                "validation_rules": {
                    "auto_set_when_not_seen": {
                        "trigger_field": "malaria_parasites",
                        "trigger_value": "not_seen",
                        "set_value": "no",
                        "description": "Auto-set to No when Malaria Parasites = Not Seen"
                    }
                },
                "reference_range": {
                    "normal_value": "No",
                    "normal_range": "No",
                    "units": "N/A",
                    "all_ages": True,
                    "all_genders": True,
                    "applies_to_neonates": True,
                    "applies_to_children": True,
                    "applies_to_adults": True,
                    "applies_to_elderly": True,
                    "nhis_reference": "NHIS Lab Code: MPS001"
                },
                "clinical_note": "Merozoite-containing RBCs (reference: No)",
                "display_order": 4,
                "dependency": {"field": "malaria_parasites", "value": "seen"},
                "result_group": "Morphology"
            },
            "trophozoite_count": {
                "code": "trophozoite_count",
                "label": "Trophozoites Count",
                "type": "integer",
                "required": False,
                "min_value": 0,
                "max_value": 99999,
                "validation_rules": {
                    "auto_set_when_not_seen": {
                        "trigger_field": "malaria_parasites",
                        "trigger_value": "not_seen",
                        "set_value": 0,
                        "description": "Auto-set to 0 when Malaria Parasites = Not Seen"
                    },
                    "positive_when_seen": {
                        "condition": "malaria_parasites == seen",
                        "min_value": 0,
                        "error_message": "Trophozoite count must be >= 0 when parasites are seen"
                    }
                },
                "reference_range": {
                    "text_range": "NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL",
                    "units": "Parasites/µL",
                    "unit_display": "Parasites per Microliter (µL)",
                    "all_ages": True,
                    "all_genders": True,
                    "applies_to_neonates": True,
                    "applies_to_children": True,
                    "applies_to_adults": True,
                    "applies_to_elderly": True,
                    "nhis_reference": "NHIS Lab Code: MPS001"
                },
                "clinical_note": "Quantitative parasite count ( parasites per µL or +/++/+++)",
                "display_order": 5,
                "dependency": {"field": "malaria_parasites", "value": "seen"},
                "result_group": "Quantification"
            },
            "film_quality": {
                "code": "film_quality",
                "label": "Film Quality",
                "type": "text",
                "required": False,
                "placeholder": "e.g., Good quality, adequately stained"
            },
            "other_findings": {
                "code": "other_findings",
                "label": "Other Findings",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "e.g., No other parasites seen"
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Interpretation",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "Clinical interpretation of malaria test results"
            }
        },
        # Cross-field validation rules
        "validation_rules": {
            "rule_1": {
                "name": "Auto-clear when Not Seen",
                "description": "If Malaria Parasites = Not Seen, auto-set: Species=Not Applicable, Gametocytes=No, Schizonts=No, Trophozoites=0",
                "condition": "malaria_parasites == 'not_seen'",
                "actions": [
                    {"field": "malaria_species", "action": "set_value", "value": "not_applicable"},
                    {"field": "gametocytes_seen", "action": "set_value", "value": "no"},
                    {"field": "schizonts_seen", "action": "set_value", "value": "no"},
                    {"field": "trophozoite_count", "action": "set_value", "value": 0}
                ]
            },
            "rule_2": {
                "name": "Species Required When Seen",
                "description": "If Malaria Parasites = Seen, Species becomes mandatory",
                "condition": "malaria_parasites == 'seen'",
                "validation": {
                    "field": "malaria_species",
                    "rule": "required",
                    "error_message": "Species is required when Malaria Parasites are detected"
                }
            },
            "rule_3": {
                "name": "At Least One Positive Finding",
                "description": "When Malaria Parasites = Seen, at least one of: Gametocytes=Yes OR Schizonts=Yes OR Trophozoites>0 must be true",
                "condition": "malaria_parasites == 'seen'",
                "validation": {
                    "expression": "gametocytes_seen == 'yes' OR schizonts_seen == 'yes' OR trophozoite_count > 0",
                    "error_message": "At least one of Gametocytes, Schizonts, or Trophozoite Count must be positive when parasites are seen"
                }
            }
        },
        # Report configuration
        "report_config": {
            "display_order": [
                "malaria_parasites",
                "malaria_species",
                "gametocytes_seen",
                "schizonts_seen",
                "trophozoite_count"
            ],
            "show_reference_ranges": True,
            "show_clinical_notes": True,
            "nhis_compliant": True,
            "ghs_approved": True,
            "structured_export": {
                "csv": True,
                "api": True,
                "nhis_reporting": True
            }
        },
        # Age and gender configuration
        "demographic_config": {
            "age_dependent": False,
            "gender_dependent": False,
            "applies_to_all_ages": True,
            "applies_to_all_genders": True,
            "record_age_for_epidemiology": True,
            "record_gender_for_epidemiology": True,
            "age_categories": ["neonates", "children", "adults", "elderly"]
        }
    }
    
    # ==================== WIDAL TEST ====================
    templates["Widal Test"] = {
        "discipline": "SEROLOGY",
        "description": "Salmonella typhi and paratyphi antibody titre - NHIS Compliant",
        "test_code": "WID001",
        "layout": {
            "sections": [
                {"id": "sec_antigen_o", "title": "Flagellar (H) and Somatic (O) Antigens", "rows": [
                    {"columns": [{"items": ["salmonella_typhi_o"], "width": 6}, {"items": ["salmonella_typhi_h"], "width": 6}]}
                ]},
                {"id": "sec_antigen_paratyphi", "title": "Paratyphi Antigens", "rows": [
                    {"columns": [{"items": ["salmonella_paratyphi_ah"], "width": 6}, {"items": ["salmonella_paratyphi_bh"], "width": 6}]}
                ]},
                {"id": "sec_interpretation", "title": "Interpretation", "rows": [
                    {"columns": [{"items": ["interpretation"], "width": 12}]}
                ]},
                {"id": "sec_notes", "title": "Notes", "rows": [
                    {"columns": [{"items": ["clinical_notes"], "width": 12}]}
                ]}
            ]
        },
        "fields": {
            "salmonella_typhi_o": {
                "code": "salmonella_typhi_o",
                "label": "Salmonella typhi O (Somatic)",
                "type": "select",
                "option_set": "WIDAL_TITRE",
                "required": True,
                "validation_rules": {"required": True},
                "clinical_note": "Somatic antigen - significant titre ≥1:160",
                "highlight_significant": True
            },
            "salmonella_typhi_h": {
                "code": "salmonella_typhi_h",
                "label": "Salmonella typhi H (Flagellar)",
                "type": "select",
                "option_set": "WIDAL_TITRE",
                "required": True,
                "validation_rules": {"required": True},
                "clinical_note": "Flagellar antigen - significant titre ≥1:160",
                "highlight_significant": True
            },
            "salmonella_paratyphi_ah": {
                "code": "salmonella_paratyphi_ah",
                "label": "Salmonella paratyphi A (AH)",
                "type": "select",
                "option_set": "WIDAL_TITRE",
                "required": False,
                "validation_rules": {},
                "clinical_note": "Paratyphi A flagellar antigen - significant titre ≥1:160",
                "highlight_significant": True
            },
            "salmonella_paratyphi_bh": {
                "code": "salmonella_paratyphi_bh",
                "label": "Salmonella paratyphi B (BH)",
                "type": "select",
                "option_set": "WIDAL_TITRE",
                "required": False,
                "validation_rules": {},
                "clinical_note": "Paratyphi B flagellar antigen - significant titre ≥1:160",
                "highlight_significant": True
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Serological Interpretation",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "e.g., Significant for S. typhi O and H suggest current/recent infection"
            },
            "clinical_notes": {
                "code": "clinical_notes",
                "label": "Clinical Notes",
                "type": "text",
                "multiline": True,
                "required": False,
                "default_value": "Widal test should be interpreted alongside clinical findings and other investigations. A four-fold rise in titre in paired samples is more diagnostic than a single elevated result."
            }
        }
    }
    
    # ==================== ERYTHROCYTE SEDIMENTATION RATE (ESR) ====================
    templates["Erythrocyte Sedimentation Rate (ESR)"] = {
        "discipline": "HEMATOLOGY",
        "description": "Erythrocyte Sedimentation Rate - NHIS Compliant",
        "test_code": "ESR001",
        "layout": {
            "sections": [
                {"id": "sec_esr", "title": "ESR Measurement", "rows": [
                    {"columns": [{"items": ["esr_value"], "width": 12}]}
                ]},
                {"id": "sec_method", "title": "Method Details", "rows": [
                    {"columns": [{"items": ["method_used"], "width": 6}, {"items": ["collection_time"], "width": 6}]}
                ]},
                {"id": "sec_notes", "title": "Notes & Interpretation", "rows": [
                    {"columns": [{"items": ["interpretation"], "width": 12}]}
                ]}
            ]
        },
        "fields": {
            "esr_value": {
                "code": "esr_value",
                "label": "ESR",
                "type": "numeric",
                "unit": "mm/hr",
                "decimals": 0,
                "min_value": 0,
                "max_value": 150,
                "required": True,
                "critical": {"high": 100.0},
                "validation_rules": {"min": 0, "max": 150},
                "clinical_note": "Erythrocyte sedimentation rate - non-specific inflammation marker"
            },
            "method_used": {
                "code": "method_used",
                "label": "Method",
                "type": "text",
                "required": False,
                "default_value": "Westergren Method",
                "validation_rules": {}
            },
            "collection_time": {
                "code": "collection_time",
                "label": "Blood Collection Time",
                "type": "text",
                "required": False,
                "placeholder": "e.g., 09:30 AM"
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Interpretation",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "Clinical interpretation of ESR result"
            }
        }
    }
    
    return templates


# =============================================================================
# REFERENCE RANGE DEFINITIONS
# =============================================================================

def get_reference_range_definitions():
    """Define age- and sex-specific reference ranges"""
    # Age groups in days: 
    # Neonate: 0-28 days
    # Infant: 28-365 days
    # Child: 365-6570 days (up to 18 years)
    # Adult: 6570+ days (18+ years)
    
    # For elderly (65+): add 10 years to age boundary (25550 days = 70 years)
    
    return [
        # ==================== FULL BLOOD COUNT ====================
        
        # Hemoglobin (g/dL) - Sex-specific, age-dependent
        # Adult Male: 13.0-17.0
        {"field_code": "hb", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": 13.0, "high": 17.0, "unit": "g/dL", "critical_low": 7.0, "critical_high": None},
        # Adult Female: 12.0-15.0
        {"field_code": "hb", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": 12.0, "high": 15.0, "unit": "g/dL", "critical_low": 7.0, "critical_high": None},
        # Children (5-18 years): 10.5-14.0
        {"field_code": "hb", "sex": "ANY", "age_min_days": 1825, "age_max_days": 6570, "low": 10.5, "high": 14.0, "unit": "g/dL", "critical_low": 7.0, "critical_high": None},
        # Younger children (1-5 years): 10.5-14.0
        {"field_code": "hb", "sex": "ANY", "age_min_days": 365, "age_max_days": 1825, "low": 10.5, "high": 14.0, "unit": "g/dL", "critical_low": 7.0, "critical_high": None},
        # Infant (28 days - 1 year): 9.5-13.5
        {"field_code": "hb", "sex": "ANY", "age_min_days": 28, "age_max_days": 365, "low": 9.5, "high": 13.5, "unit": "g/dL", "critical_low": 7.0, "critical_high": None},
        # Neonate (0-28 days): 13.5-23.5
        {"field_code": "hb", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, "low": 13.5, "high": 23.5, "unit": "g/dL", "critical_low": 10.0, "critical_high": None},
        
        # PCV/HCT (%) - Sex-specific
        # Adult Male: 40-52%
        {"field_code": "hct", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": 40.0, "high": 52.0, "unit": "%", "critical_low": 20.0, "critical_high": None},
        # Adult Female: 36-48%
        {"field_code": "hct", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": 36.0, "high": 48.0, "unit": "%", "critical_low": 20.0, "critical_high": None},
        # Children: 30-40%
        {"field_code": "hct", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "low": 30.0, "high": 40.0, "unit": "%", "critical_low": 20.0, "critical_high": None},
        # Infant: 28-42%
        {"field_code": "hct", "sex": "ANY", "age_min_days": 28, "age_max_days": 365, "low": 28.0, "high": 42.0, "unit": "%", "critical_low": 20.0, "critical_high": None},
        # Neonate: 40-68%
        {"field_code": "hct", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, "low": 40.0, "high": 68.0, "unit": "%", "critical_low": 25.0, "critical_high": None},
        
        # RBC Count (×10¹²/L) - Sex-specific
        # Adult Male: 4.5-5.9
        {"field_code": "rbc_count", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": 4.5, "high": 5.9, "unit": "×10¹²/L", "critical_low": 2.5, "critical_high": None},
        # Adult Female: 4.1-5.1
        {"field_code": "rbc_count", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": 4.1, "high": 5.1, "unit": "×10¹²/L", "critical_low": 2.5, "critical_high": None},
        # Children: 3.5-5.0
        {"field_code": "rbc_count", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "low": 3.5, "high": 5.0, "unit": "×10¹²/L", "critical_low": 2.5, "critical_high": None},
        
        # WBC Count (×10⁹/L) - All ages: 4.0-11.0 (except neonates)
        {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 4.0, "high": 11.0, "unit": "×10⁹/L", "critical_low": 2.0, "critical_high": 30.0},
        {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "low": 4.0, "high": 11.0, "unit": "×10⁹/L", "critical_low": 2.0, "critical_high": 25.0},
        {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 28, "age_max_days": 365, "low": 6.0, "high": 15.0, "unit": "×10⁹/L", "critical_low": 2.0, "critical_high": 25.0},
        {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, "low": 9.0, "high": 18.0, "unit": "×10⁹/L", "critical_low": 5.0, "critical_high": 30.0},
        
        # Platelet Count (×10⁹/L) - All ages: 150-450
        {"field_code": "platelet_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 150.0, "high": 450.0, "unit": "×10⁹/L", "critical_low": 20.0, "critical_high": 1000.0},
        
        # Differential Count (%) - All ages
        # Neutrophils: 40-75%
        {"field_code": "neutrophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 40.0, "high": 75.0, "unit": "%", "critical_low": None, "critical_high": None},
        # Lymphocytes: 20-45%
        {"field_code": "lymphocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 20.0, "high": 45.0, "unit": "%", "critical_low": None, "critical_high": None},
        # Monocytes: 2-10%
        {"field_code": "monocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 2.0, "high": 10.0, "unit": "%", "critical_low": None, "critical_high": None},
        # Eosinophils: 1-6%
        {"field_code": "eosinophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 1.0, "high": 6.0, "unit": "%", "critical_low": None, "critical_high": None},
        # Basophils: 0-1%
        {"field_code": "basophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 0.0, "high": 1.0, "unit": "%", "critical_low": None, "critical_high": None},
        
        # MCV (fL) - All ages: 76-96 (adult)
        {"field_code": "mcv", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 76.0, "high": 96.0, "unit": "fL", "critical_low": 50.0, "critical_high": None},
        {"field_code": "mcv", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "low": 70.0, "high": 86.0, "unit": "fL", "critical_low": 50.0, "critical_high": None},
        
        # MCH (pg) - All ages: 26-32 (adult)
        {"field_code": "mch", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 26.0, "high": 32.0, "unit": "pg", "critical_low": 15.0, "critical_high": None},
        
        # MCHC (g/dL) - All ages: 32-36 (adult)
        {"field_code": "mchc", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 32.0, "high": 36.0, "unit": "g/dL", "critical_low": None, "critical_high": None},
        
        # ==================== MALARIA PARASITE TEST ====================
        
        # Malaria parasites: Not Seen (normal)
        {"field_code": "malaria_parasites", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": None, "critical_low": None, "critical_high": None, "text_range": "Not Seen"},
        
        # Gametocytes: No (normal)
        {"field_code": "gametocytes_seen", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": None, "critical_low": None, "critical_high": None, "text_range": "No"},
        
        # Schizonts: No (normal)
        {"field_code": "schizonts_seen", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": None, "critical_low": None, "critical_high": None, "text_range": "No"},
        
        # Parasite count: 0 (normal)
        {"field_code": "parasite_density", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": None, "critical_low": None, "critical_high": None, "text_range": "0"},
        
        # Trophozoites Count: Semi-quantitative interpretation scale
        {"field_code": "trophozoite_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": "Parasites/µL", "critical_low": None, "critical_high": None, "text_range": "NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL"},
        
        # ==================== WIDAL TEST ====================
        
        # All Widal antigens - Normal ≤1:80, Significant ≥1:160
        {"field_code": "salmonella_typhi_o", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": "titre", "critical_low": None, "critical_high": None, "text_range": "≤1:80 (Normal) / ≥1:160 (Significant)"},
        {"field_code": "salmonella_typhi_h", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": "titre", "critical_low": None, "critical_high": None, "text_range": "≤1:80 (Normal) / ≥1:160 (Significant)"},
        {"field_code": "salmonella_paratyphi_ah", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": "titre", "critical_low": None, "critical_high": None, "text_range": "≤1:80 (Normal) / ≥1:160 (Significant)"},
        {"field_code": "salmonella_paratyphi_bh", "sex": "ANY", "age_min_days": 0, "age_max_days": 99999, "low": None, "high": None, "unit": "titre", "critical_low": None, "critical_high": None, "text_range": "≤1:80 (Normal) / ≥1:160 (Significant)"},
        
        # ==================== ESR ====================
        
        # Adult Male: 0-15 mm/hr
        {"field_code": "esr_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": 0.0, "high": 15.0, "unit": "mm/hr", "critical_low": None, "critical_high": 100.0},
        # Adult Female: 0-20 mm/hr
        {"field_code": "esr_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": 0.0, "high": 20.0, "unit": "mm/hr", "critical_low": None, "critical_high": 100.0},
        # Children: 0-10 mm/hr
        {"field_code": "esr_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": 0.0, "high": 10.0, "unit": "mm/hr", "critical_low": None, "critical_high": 50.0},
    ]


# =============================================================================
# MAIN SEEDING FUNCTIONS
# =============================================================================

def seed_lab_tests(db: Session):
    """Create or update lab test catalog entries"""
    print("\n" + "="*60)
    print("SEEDING LAB TEST CATALOG")
    print("="*60)
    
    tests = get_lab_test_definitions()
    created_count = 0
    updated_count = 0
    
    for test_data in tests:
        existing = db.query(LabTest).filter(
            LabTest.test_code == test_data["test_code"]
        ).first()
        
        if existing:
            # Update existing test
            for key, value in test_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            updated_count += 1
            print(f"  ✓ Updated: {test_data['test_name']} ({test_data['test_code']})")
        else:
            # Create new test
            db_test = LabTest(**test_data)
            db.add(db_test)
            created_count += 1
            print(f"  ✓ Created: {test_data['test_name']} ({test_data['test_code']})")
    
    db.commit()
    print(f"\n  Summary: {created_count} created, {updated_count} updated")
    return created_count, updated_count


def seed_option_sets(db: Session):
    """Create or update option sets"""
    print("\n" + "="*60)
    print("SEEDING OPTION SETS")
    print("="*60)
    
    option_sets = get_option_set_definitions()
    created_count = 0
    updated_count = 0
    
    for opt_set_data in option_sets:
        existing = db.query(LabOptionSet).filter(
            LabOptionSet.code == opt_set_data["code"]
        ).first()
        
        if existing:
            # Update existing
            existing.options_json = opt_set_data["options_json"]
            updated_count += 1
            print(f"  ✓ Updated: {opt_set_data['code']}")
        else:
            # Create new - only code and options_json fields
            db_opt_set = LabOptionSet(
                code=opt_set_data["code"],
                options_json=opt_set_data["options_json"]
            )
            db.add(db_opt_set)
            created_count += 1
            print(f"  ✓ Created: {opt_set_data['code']}")
    
    db.commit()
    print(f"\n  Summary: {created_count} created, {updated_count} updated")
    return created_count, updated_count


def seed_templates(db: Session, admin_user):
    """Create or update lab templates"""
    print("\n" + "="*60)
    print("SEEDING LAB TEMPLATES")
    print("="*60)
    
    templates = get_template_definitions()
    created_count = 0
    updated_count = 0
    
    for template_name, template_data in templates.items():
        # Check if template exists
        existing = db.query(LabTemplate).filter(
            LabTemplate.name == template_name
        ).first()
        
        if existing:
            # Update existing template - create new version
            schema_json = {
                "discipline": template_data["discipline"],
                "description": template_data["description"],
                "test_code": template_data.get("test_code"),
                "layout": template_data["layout"],
                "fields": template_data["fields"],
                "nhis_compliant": True,
                "version": "2.0",
                "updated_date": datetime.utcnow().isoformat()
            }
            
            # Get the next version number
            next_version = (existing.current_version or 0) + 1
            
            # Create new version
            version = LabTemplateVersion(
                template_id=existing.id,
                version=next_version,
                status="PUBLISHED",
                schema_json=schema_json,
                change_note="NHIS-compliant update with age/sex reference ranges",
                created_by_id=admin_user.id if admin_user else None
            )
            db.add(version)
            
            # Update current version
            existing.current_version = next_version
            existing.discipline = template_data["discipline"]
            existing.status = "PUBLISHED"
            existing.updated_at = datetime.utcnow()
            
            updated_count += 1
            print(f"  ✓ Updated: {template_name}")
        else:
            # Create new template
            schema_json = {
                "discipline": template_data["discipline"],
                "description": template_data["description"],
                "test_code": template_data.get("test_code"),
                "layout": template_data["layout"],
                "fields": template_data["fields"],
                "nhis_compliant": True,
                "version": "1.0",
                "created_date": datetime.utcnow().isoformat()
            }
            
            db_template = LabTemplate(
                name=template_name,
                discipline=template_data["discipline"],
                status="PUBLISHED",
                current_version=1,
                created_by_id=admin_user.id if admin_user else None
            )
            db.add(db_template)
            db.flush()  # Get the ID
            
            # Create first version
            version = LabTemplateVersion(
                template_id=db_template.id,
                version=1,
                status="PUBLISHED",
                schema_json=schema_json,
                change_note="Initial NHIS-compliant template",
                created_by_id=admin_user.id if admin_user else None
            )
            db.add(version)
            
            created_count += 1
            print(f"  ✓ Created: {template_name}")
    
    db.commit()
    print(f"\n  Summary: {created_count} created, {updated_count} updated")
    return created_count, updated_count


def seed_reference_ranges(db: Session):
    """Create or update reference ranges"""
    print("\n" + "="*60)
    print("SEEDING REFERENCE RANGES")
    print("="*60)
    
    ranges = get_reference_range_definitions()
    created_count = 0
    updated_count = 0
    
    for range_data in ranges:
        # Check if reference range exists
        query = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == range_data["field_code"],
            LabReferenceRange.sex == range_data.get("sex", "ANY")
        )
        
        if range_data.get("age_min_days") is not None:
            query = query.filter(LabReferenceRange.age_min_days == range_data["age_min_days"])
        
        existing = query.first()
        
        if existing:
            # Update existing
            for key, value in range_data.items():
                if key != "field_code" and hasattr(existing, key):
                    setattr(existing, key, value)
            updated_count += 1
        else:
            # Create new
            db_range = LabReferenceRange(**range_data)
            db.add(db_range)
            created_count += 1
    
    db.commit()
    print(f"\n  Summary: {created_count} created, {updated_count} updated")
    return created_count, updated_count


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("NHIS-COMPLIANT LABORATORY TEST CATALOG UPDATE")
    print("="*60)
    print(f"Database: {SQLALCHEMY_DATABASE_URL[:50]}...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get admin user for audit
        admin_user = get_or_create_admin_user(db)
        print(f"Using admin user: {admin_user.username if admin_user else 'None'}")
        
        # Run seeders
        test_created, test_updated = seed_lab_tests(db)
        opt_created, opt_updated = seed_option_sets(db)
        template_created, template_updated = seed_templates(db, admin_user)
        range_created, range_updated = seed_reference_ranges(db)
        
        # Summary
        print("\n" + "="*60)
        print("SEEDING COMPLETE - SUMMARY")
        print("="*60)
        print(f"  Lab Tests: {test_created} created, {test_updated} updated")
        print(f"  Option Sets: {opt_created} created, {opt_updated} updated")
        print(f"  Templates: {template_created} created, {template_updated} updated")
        print(f"  Reference Ranges: {range_created} created, {range_updated} updated")
        print("\n" + "="*60)
        print("NHIS-COMPLIANT TESTS ADDED/UPDATED:")
        print("="*60)
        print("  1. Full Blood Count (FBC) - FBC001")
        print("     - Age/sex-specific reference ranges")
        print("     - Full differential count")
        print("     - Critical value alerts")
        print("  2. BF for MPS (Malaria Parasite) - MPS001")
        print("     - Species identification")
        print("     - Parasite density grading")
        print("     - Auto-disable dependent fields")
        print("  3. Widal Test - WID001")
        print("     - Standardized titre values")
        print("     - Significant titre highlighting")
        print("     - Clinical interpretation notes")
        print("  4. ESR - ESR001")
        print("     - Age/sex-specific ranges")
        print("     - Elevated result flagging")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
