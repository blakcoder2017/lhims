#!/usr/bin/env python3
"""
Comprehensive Lab Template Regeneration Script

This script completely regenerates all lab test templates with:
- Proper schema format (meta, layout.sections, fields, rules, calculated)
- Detailed layout sections for better UI rendering
- Complete reference ranges for all fields
- Ghana-appropriate age/sex-specific ranges
- Critical value thresholds

Usage:
    python3 regenerate_lab_templates.py

Options:
    --test-codes CODE1,CODE2    Regenerate only specific templates (e.g., --test-codes FBC,LFT)
    --update-ranges            Update only reference ranges (preserve custom fields)
    --dry-run                  Preview changes without applying them
    --export FILE               Export templates to JSON file
    --import FILE               Import templates from JSON file
    --list                      List all available template codes

Requirements:
    - Database must be initialized
    - Run from the project root directory
"""

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
from uuid import uuid4

from app.main import app
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ==================== TEMPLATE DEFINITIONS ====================

def get_template_definitions():
    """Return all lab template definitions with proper schema format."""
    
    return [
        # ==================== HAEMATOLOGY ====================
        {
            "test_name": "Full Blood Count (FBC)",
            "test_code": "FBC",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Complete blood count with differential",
            "discipline": "HEMATOLOGY",
            "schema": {
                "meta": {
                    "name": "Full Blood Count (FBC)",
                    "discipline": "HEMATOLOGY",
                    "version": 1,
                    "description": "Complete blood count with differential"
                },
                "layout": {
                    "sections": [
                        {
                            "id": "sec_hemoglobin",
                            "title": "Hemoglobin & Hematocrit",
                            "rows": [{"columns": [{"width": 6, "items": ["hb"]}, {"width": 6, "items": ["hct"]}]}]
                        },
                        {
                            "id": "sec_rbc_indices",
                            "title": "Red Blood Cell Indices",
                            "rows": [{"columns": [{"width": 3, "items": ["rbc_count"]}, {"width": 3, "items": ["mcv"]}, {"width": 3, "items": ["mch"]}, {"width": 3, "items": ["mchc"]}]}]
                        },
                        {
                            "id": "sec_wbc",
                            "title": "White Blood Cell Count",
                            "rows": [{"columns": [{"width": 12, "items": ["wbc_count"]}]}]
                        },
                        {
                            "id": "sec_differential",
                            "title": "Differential Count",
                            "rows": [{"columns": [{"width": 4, "items": ["neutrophils"]}, {"width": 4, "items": ["lymphocytes"]}, {"width": 4, "items": ["monocytes"]}, {"width": 4, "items": ["eosinophils"]}, {"width": 4, "items": ["basophils"]}]}]
                        },
                        {
                            "id": "sec_platelets",
                            "title": "Platelets",
                            "rows": [{"columns": [{"width": 12, "items": ["platelet_count"]}]}]
                        },
                        {
                            "id": "sec_morphology",
                            "title": "Morphology",
                            "rows": [{"columns": [{"width": 12, "items": ["rbcmorph", "wbc_morph", "platelet_morph"]}]}]
                        },
                        {
                            "id": "sec_comment",
                            "title": "Comments",
                            "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]
                        }
                    ]
                },
                "fields": {
                    "hb": {"code": "hb", "label": "Haemoglobin (Hb)", "type": "numeric", "unit": "g/dL", "decimals": 1, "critical": True, "critical_low": 7.0, "critical_high": 20.0},
                    "hct": {"code": "hct", "label": "Hematocrit (Hct)", "type": "numeric", "unit": "%", "decimals": 1, "critical": True, "critical_low": 20.0, "critical_high": 60.0},
                    "rbc_count": {"code": "rbc_count", "label": "RBC Count", "type": "numeric", "unit": "x10^12/L", "decimals": 2},
                    "mcv": {"code": "mcv", "label": "MCV", "type": "numeric", "unit": "fL", "decimals": 1},
                    "mch": {"code": "mch", "label": "MCH", "type": "numeric", "unit": "pg", "decimals": 1},
                    "mchc": {"code": "mchc", "label": "MCHC", "type": "numeric", "unit": "g/dL", "decimals": 1},
                    "wbc_count": {"code": "wbc_count", "label": "WBC Count", "type": "numeric", "unit": "x10^9/L", "decimals": 2, "critical": True, "critical_low": 2.0, "critical_high": 30.0},
                    "neutrophils": {"code": "neutrophils", "label": "Neutrophils", "type": "numeric", "unit": "%", "decimals": 1},
                    "lymphocytes": {"code": "lymphocytes", "label": "Lymphocytes", "type": "numeric", "unit": "%", "decimals": 1},
                    "monocytes": {"code": "monocytes", "label": "Monocytes", "type": "numeric", "unit": "%", "decimals": 1},
                    "eosinophils": {"code": "eosinophils", "label": "Eosinophils", "type": "numeric", "unit": "%", "decimals": 1},
                    "basophils": {"code": "basophils", "label": "Basophils", "type": "numeric", "unit": "%", "decimals": 1},
                    "platelet_count": {"code": "platelet_count", "label": "Platelet Count", "type": "numeric", "unit": "x10^9/L", "decimals": 0, "critical": True, "critical_low": 20.0, "critical_high": 1000.0},
                    "rbcmorph": {"code": "rbcmorph", "label": "RBC Morphology", "type": "multichoice", "options": ["Normocytic", "Microcytic", "Macrocytic", "Hypochromic", "Anisocytosis", "Poikilocytosis"]},
                    "wbc_morph": {"code": "wbc_morph", "label": "WBC Morphology", "type": "multichoice", "options": ["Normal", "Left Shift", "Toxic Granulation", "Doehle Bodies"]},
                    "platelet_morph": {"code": "platelet_morph", "label": "Platelet Morphology", "type": "choice", "options": ["Adequate", "Reduced", "Increased", "Clumped"]},
                    "comment": {"code": "comment", "label": "Comments", "type": "text"}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # Adult Male
                {"field_code": "hb", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("12.5"), "high": Decimal("17.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
                # Adult Female
                {"field_code": "hb", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("11.5"), "high": Decimal("15.5"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
                # Adolescent (13-18)
                {"field_code": "hb", "sex": "ANY", "age_min_days": 4745, "age_max_days": 6570, "low": Decimal("12.0"), "high": Decimal("16.0"), "unit": "g/dL"},
                # Child (6-12)
                {"field_code": "hb", "sex": "ANY", "age_min_days": 2190, "age_max_days": 4745, "low": Decimal("11.5"), "high": Decimal("15.5"), "unit": "g/dL"},
                # Preschool (3-5)
                {"field_code": "hb", "sex": "ANY", "age_min_days": 1095, "age_max_days": 2190, "low": Decimal("11.0"), "high": Decimal("14.0"), "unit": "g/dL"},
                # Toddler (1-3)
                {"field_code": "hb", "sex": "ANY", "age_min_days": 365, "age_max_days": 1095, "low": Decimal("10.5"), "high": Decimal("14.0"), "unit": "g/dL"},
                # Infant (1-12 months)
                {"field_code": "hb", "sex": "ANY", "age_min_days": 30, "age_max_days": 365, "low": Decimal("9.5"), "high": Decimal("13.0"), "unit": "g/dL"},
                # Newborn (0-28 days)
                {"field_code": "hb", "sex": "ANY", "age_min_days": 0, "age_max_days": 28, "low": Decimal("14.5"), "high": Decimal("22.5"), "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"},
                
                # Hematocrit
                {"field_code": "hct", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("36"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
                {"field_code": "hct", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("34"), "high": Decimal("46"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
                {"field_code": "hct", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("32"), "high": Decimal("50"), "unit": "%"},
                
                # RBC Count
                {"field_code": "rbc_count", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("4.5"), "high": Decimal("6.5"), "unit": "x10^12/L"},
                {"field_code": "rbc_count", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("3.8"), "high": Decimal("5.8"), "unit": "x10^12/L"},
                {"field_code": "rbc_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("3.8"), "high": Decimal("6.0"), "unit": "x10^12/L"},
                
                # MCV
                {"field_code": "mcv", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("80"), "high": Decimal("100"), "unit": "fL"},
                # MCH
                {"field_code": "mch", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("27"), "high": Decimal("33"), "unit": "pg"},
                # MCHC
                {"field_code": "mchc", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("31.5"), "high": Decimal("35.5"), "unit": "g/dL"},
                
                # WBC Count
                {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("4.0"), "high": Decimal("11.0"), "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10^9/L"},
                
                # Platelets
                {"field_code": "platelet_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("150"), "high": Decimal("400"), "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "x10^9/L"},
                
                # Differential
                {"field_code": "neutrophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("40"), "high": Decimal("75"), "unit": "%"},
                {"field_code": "lymphocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("20"), "high": Decimal("50"), "unit": "%"},
                {"field_code": "monocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("2"), "high": Decimal("10"), "unit": "%"},
                {"field_code": "eosinophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("1"), "high": Decimal("6"), "unit": "%"},
                {"field_code": "basophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("2"), "unit": "%"},
            ]
        },
        
        # ==================== LIVER FUNCTION TESTS ====================
        {
            "test_name": "Liver Function Test (LFT)",
            "test_code": "LFT",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Liver function test panel",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Liver Function Test (LFT)", "discipline": "CHEMISTRY", "version": 1, "description": "Liver function test panel"},
                "layout": {
                    "sections": [
                        {"id": "sec_bilirubin", "title": "Bilirubin", "rows": [{"columns": [{"width": 6, "items": ["total_bilirubin"]}, {"width": 6, "items": ["direct_bilirubin"]}]}]},
                        {"id": "sec_enzymes", "title": "Liver Enzymes", "rows": [{"columns": [{"width": 6, "items": ["alt"]}, {"width": 6, "items": ["ast"]}, {"width": 6, "items": ["alp"]}, {"width": 6, "items": ["ggt"]}]}]},
                        {"id": "sec_proteins", "title": "Proteins", "rows": [{"columns": [{"width": 4, "items": ["total_protein"]}, {"width": 4, "items": ["albumin"]}, {"width": 4, "items": ["globulin"]}]}]},
                        {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]}
                    ]
                },
                "fields": {
                    "total_bilirubin": {"code": "total_bilirubin", "label": "Total Bilirubin", "type": "numeric", "unit": "µmol/L", "decimals": 1, "critical": True, "critical_high": 171.0},
                    "direct_bilirubin": {"code": "direct_bilirubin", "label": "Direct Bilirubin", "type": "numeric", "unit": "µmol/L", "decimals": 1},
                    "alt": {"code": "alt", "label": "ALT (SGPT)", "type": "numeric", "unit": "U/L", "decimals": 0, "critical": True, "critical_high": 500.0},
                    "ast": {"code": "ast", "label": "AST (SGOT)", "type": "numeric", "unit": "U/L", "decimals": 0, "critical": True, "critical_high": 500.0},
                    "alp": {"code": "alp", "label": "ALP", "type": "numeric", "unit": "U/L", "decimals": 0},
                    "ggt": {"code": "ggt", "label": "GGT", "type": "numeric", "unit": "U/L", "decimals": 0},
                    "total_protein": {"code": "total_protein", "label": "Total Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
                    "albumin": {"code": "albumin", "label": "Albumin", "type": "numeric", "unit": "g/L", "decimals": 1},
                    "globulin": {"code": "globulin", "label": "Globulin", "type": "numeric", "unit": "g/L", "decimals": 1},
                    "comment": {"code": "comment", "label": "Comments", "type": "text"}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # Bilirubin (Adult)
                {"field_code": "total_bilirubin", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("2.0"), "high": Decimal("20.5"), "critical_high": Decimal("171.0"), "unit": "µmol/L"},
                # Bilirubin (Child)
                {"field_code": "total_bilirubin", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("2.0"), "high": Decimal("15.4"), "unit": "µmol/L"},
                # Direct Bilirubin
                {"field_code": "direct_bilirubin", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("5.1"), "unit": "µmol/L"},
                # ALT (Male Adult)
                {"field_code": "alt", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("40"), "critical_high": Decimal("500"), "unit": "U/L"},
                # ALT (Female Adult)
                {"field_code": "alt", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("32"), "critical_high": Decimal("500"), "unit": "U/L"},
                # ALT (Child)
                {"field_code": "alt", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("0"), "high": Decimal("49"), "unit": "U/L"},
                # AST
                {"field_code": "ast", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("37"), "critical_high": Decimal("500"), "unit": "U/L"},
                {"field_code": "ast", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("31"), "critical_high": Decimal("500"), "unit": "U/L"},
                {"field_code": "ast", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("0"), "high": Decimal("50"), "unit": "U/L"},
                # ALP
                {"field_code": "alp", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("20"), "high": Decimal("140"), "critical_high": Decimal("500"), "unit": "U/L"},
                {"field_code": "alp", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("50"), "high": Decimal("350"), "unit": "U/L"},
                # GGT
                {"field_code": "ggt", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("55"), "unit": "U/L"},
                {"field_code": "ggt", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("38"), "unit": "U/L"},
                # Total Protein
                {"field_code": "total_protein", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("60"), "high": Decimal("83"), "unit": "g/L"},
                # Albumin
                {"field_code": "albumin", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("35"), "high": Decimal("55"), "unit": "g/L"},
                # Globulin (calculated)
                {"field_code": "globulin", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("20"), "high": Decimal("35"), "unit": "g/L"},
            ]
        },
        
        # ==================== RENAL FUNCTION TESTS ====================
        {
            "test_name": "Renal Function Test (RFT)",
            "test_code": "RFT",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Renal function test (BUE & Creatinine)",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Renal Function Test (RFT)", "discipline": "CHEMISTRY", "version": 1, "description": "Renal function test panel"},
                "layout": {
                    "sections": [
                        {"id": "sec_renal", "title": "Kidney Function", "rows": [{"columns": [{"width": 4, "items": ["creatinine"]}, {"width": 4, "items": ["urea"]}, {"width": 4, "items": ["egfr"]}]}]},
                        {"id": "sec_electrolytes", "title": "Electrolytes", "rows": [{"columns": [{"width": 3, "items": ["sodium"]}, {"width": 3, "items": ["potassium"]}, {"width": 3, "items": ["chloride"]}, {"width": 3, "items": ["bicarbonate"]}]}]},
                        {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]}
                    ]
                },
                "fields": {
                    "creatinine": {"code": "creatinine", "label": "Creatinine", "type": "numeric", "unit": "µmol/L", "decimals": 0, "critical": True, "critical_low": 44.0, "critical_high": 707.0},
                    "urea": {"code": "urea", "label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 1, "critical_high": 35.7},
                    "egfr": {"code": "egfr", "label": "eGFR", "type": "numeric", "unit": "mL/min", "decimals": 0},
                    "sodium": {"code": "sodium", "label": "Sodium (Na)", "type": "numeric", "unit": "mmol/L", "decimals": 0, "critical": True, "critical_low": 120, "critical_high": 160},
                    "potassium": {"code": "potassium", "label": "Potassium (K)", "type": "numeric", "unit": "mmol/L", "decimals": 1, "critical": True, "critical_low": 2.5, "critical_high": 6.5},
                    "chloride": {"code": "chloride", "label": "Chloride (Cl)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
                    "bicarbonate": {"code": "bicarbonate", "label": "Bicarbonate (HCO3)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
                    "comment": {"code": "comment", "label": "Comments", "type": "text"}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # Creatinine (Male)
                {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("62"), "high": Decimal("115"), "critical_low": Decimal("44"), "critical_high": Decimal("707"), "unit": "µmol/L"},
                # Creatinine (Female)
                {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("53"), "high": Decimal("97"), "critical_low": Decimal("44"), "critical_high": Decimal("707"), "unit": "µmol/L"},
                # Creatinine (Child)
                {"field_code": "creatinine", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("18"), "high": Decimal("62"), "unit": "µmol/L"},
                # Urea
                {"field_code": "urea", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("2.9"), "high": Decimal("8.2"), "critical_high": Decimal("35.7"), "unit": "mmol/L"},
                # eGFR
                {"field_code": "egfr", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("90"), "high": Decimal("120"), "unit": "mL/min"},
                {"field_code": "egfr", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("90"), "high": Decimal("120"), "unit": "mL/min"},
                # Sodium
                {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("136"), "high": Decimal("145"), "critical_low": Decimal("120"), "critical_high": Decimal("160"), "unit": "mmol/L"},
                # Potassium
                {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("3.5"), "high": Decimal("5.0"), "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mmol/L"},
                # Chloride
                {"field_code": "chloride", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("98"), "high": Decimal("106"), "unit": "mmol/L"},
                # Bicarbonate
                {"field_code": "bicarbonate", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("22"), "high": Decimal("28"), "unit": "mmol/L"},
            ]
        },
        
        # ==================== LIPID PROFILE ====================
        {
            "test_name": "Lipid Profile",
            "test_code": "LIPID",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum (Fasting)",
            "description": "Complete lipid profile",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Lipid Profile", "discipline": "CHEMISTRY", "version": 1, "description": "Complete lipid profile"},
                "layout": {
                    "sections": [
                        {"id": "sec_cholesterol", "title": "Cholesterol", "rows": [{"columns": [{"width": 6, "items": ["cholesterol_total"]}, {"width": 6, "items": ["ldl_cholesterol"]}, {"width": 6, "items": ["hdl_cholesterol"]}, {"width": 6, "items": ["vldl_cholesterol"]}]}]},
                        {"id": "sec_triglycerides", "title": "Triglycerides", "rows": [{"columns": [{"width": 12, "items": ["triglycerides"]}]}]},
                        {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]}
                    ]
                },
                "fields": {
                    "cholesterol_total": {"code": "cholesterol_total", "label": "Total Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": True, "critical_high": 7.75},
                    "ldl_cholesterol": {"code": "ldl_cholesterol", "label": "LDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": True, "critical_high": 4.9},
                    "hdl_cholesterol": {"code": "hdl_cholesterol", "label": "HDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                    "vldl_cholesterol": {"code": "vldl_cholesterol", "label": "VLDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                    "triglycerides": {"code": "triglycerides", "label": "Triglycerides", "type": "numeric", "unit": "mmol/L", "decimals": 2, "critical": True, "critical_high": 5.65},
                    "comment": {"code": "comment", "label": "Comments", "type": "text"}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # Total Cholesterol (Adult)
                {"field_code": "cholesterol_total", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("5.2"), "critical_high": Decimal("7.75"), "unit": "mmol/L"},
                # LDL
                {"field_code": "ldl_cholesterol", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("2.6"), "critical_high": Decimal("4.9"), "unit": "mmol/L"},
                # HDL (Male)
                {"field_code": "hdl_cholesterol", "sex": "M", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("1.0"), "high": Decimal("1.55"), "unit": "mmol/L"},
                # HDL (Female)
                {"field_code": "hdl_cholesterol", "sex": "F", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("1.3"), "high": Decimal("1.8"), "unit": "mmol/L"},
                # VLDL
                {"field_code": "vldl_cholesterol", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("0.77"), "unit": "mmol/L"},
                # Triglycerides (Adult fasting)
                {"field_code": "triglycerides", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("1.7"), "critical_high": Decimal("5.65"), "unit": "mmol/L"},
                # Triglycerides (Child)
                {"field_code": "triglycerides", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("0"), "high": Decimal("1.1"), "unit": "mmol/L"},
            ]
        },
        
        # ==================== GLUCOSE TESTS ====================
        {
            "test_name": "Fasting Blood Sugar (FBS)",
            "test_code": "FBS",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Plasma (Fasting)",
            "description": "Fasting blood glucose",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Fasting Blood Sugar (FBS)", "discipline": "CHEMISTRY", "version": 1},
                "layout": {"sections": [{"id": "sec_glucose", "title": "Glucose", "rows": [{"columns": [{"width": 12, "items": ["glucose_fasting"]}]}]}]},
                "fields": {
                    "glucose_fasting": {"code": "glucose_fasting", "label": "Fasting Blood Sugar", "type": "numeric", "unit": "mg/dL", "decimals": 0, "critical": True, "critical_low": 40, "critical_high": 400}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # Normal
                {"field_code": "glucose_fasting", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("70"), "high": Decimal("100"), "critical_low": Decimal("40"), "critical_high": Decimal("400"), "unit": "mg/dL"},
            ]
        },
        
        {
            "test_name": "Random Blood Sugar (RBS)",
            "test_code": "RBS",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Plasma",
            "description": "Random blood glucose",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Random Blood Sugar (RBS)", "discipline": "CHEMISTRY", "version": 1},
                "layout": {"sections": [{"id": "sec_glucose", "title": "Glucose", "rows": [{"columns": [{"width": 12, "items": ["glucose_random"]}]}]}]},
                "fields": {
                    "glucose_random": {"code": "glucose_random", "label": "Random Blood Sugar", "type": "numeric", "unit": "mg/dL", "decimals": 0, "critical": True, "critical_low": 40, "critical_high": 400}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "glucose_random", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("70"), "high": Decimal("140"), "critical_low": Decimal("40"), "critical_high": Decimal("400"), "unit": "mg/dL"},
            ]
        },
        
        {
            "test_name": "HbA1c",
            "test_code": "HBA1C",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Glycated haemoglobin",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "HbA1c", "discipline": "CHEMISTRY", "version": 1},
                "layout": {"sections": [{"id": "sec_hba1c", "title": "HbA1c", "rows": [{"columns": [{"width": 12, "items": ["hba1c"]}]}]}]},
                "fields": {
                    "hba1c": {"code": "hba1c", "label": "HbA1c", "type": "numeric", "unit": "%", "decimals": 1}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "hba1c", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("4.0"), "high": Decimal("5.6"), "unit": "%"},
            ]
        },
        
        # ==================== THYROID PROFILE ====================
        {
            "test_name": "Thyroid Profile",
            "test_code": "THYROID",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "TSH, T3, T4",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Thyroid Profile", "discipline": "CHEMISTRY", "version": 1},
                "layout": {
                    "sections": [
                        {"id": "sec_thyroid", "title": "Thyroid Function", "rows": [{"columns": [{"width": 4, "items": ["tsh"]}, {"width": 4, "items": ["ft4"]}, {"width": 4, "items": ["ft3"]}]}]}
                    ]
                },
                "fields": {
                    "tsh": {"code": "tsh", "label": "TSH", "type": "numeric", "unit": "mIU/L", "decimals": 2, "critical": True, "critical_low": 0.1, "critical_high": 10.0},
                    "ft4": {"code": "ft4", "label": "Free T4", "type": "numeric", "unit": "ng/dL", "decimals": 2, "critical": True, "critical_low": 0.1, "critical_high": 4.0},
                    "ft3": {"code": "ft3", "label": "Free T3", "type": "numeric", "unit": "pg/mL", "decimals": 2, "critical": True, "critical_low": 1.0, "critical_high": 6.0}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # TSH (Adult)
                {"field_code": "tsh", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0.4"), "high": Decimal("4.0"), "critical_low": Decimal("0.1"), "critical_high": Decimal("10.0"), "unit": "mIU/L"},
                # TSH (Child)
                {"field_code": "tsh", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("0.7"), "high": Decimal("6.0"), "unit": "mIU/L"},
                # FT4
                {"field_code": "ft4", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0.8"), "high": Decimal("1.8"), "critical_low": Decimal("0.1"), "critical_high": Decimal("4.0"), "unit": "ng/dL"},
                # FT3
                {"field_code": "ft3", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("2.3"), "high": Decimal("4.2"), "critical_low": Decimal("1.0"), "critical_high": Decimal("6.0"), "unit": "pg/mL"},
            ]
        },
        
        # ==================== HIV & VIRAL TESTS ====================
        {
            "test_name": "HIV 1 & 2",
            "test_code": "HIV",
            "test_category": "Virology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "HIV 1 & 2 screening",
            "discipline": "SEROLOGY",
            "schema": {
                "meta": {"name": "HIV 1 & 2", "discipline": "SEROLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_hiv", "title": "HIV Screening", "rows": [{"columns": [{"width": 12, "items": ["hiv_1_2"]}]}]}]},
                "fields": {
                    "hiv_1_2": {"code": "hiv_1_2", "label": "HIV 1 & 2", "type": "choice", "options": ["Negative", "Positive", "Indeterminate"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "hiv_1_2", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive,Indeterminate"},
            ]
        },
        
        {
            "test_name": "Hepatitis B Surface Antigen",
            "test_code": "HBSAG",
            "test_category": "Virology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "HBsAg screening",
            "discipline": "SEROLOGY",
            "schema": {
                "meta": {"name": "Hepatitis B Surface Antigen", "discipline": "SEROLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_hbv", "title": "Hepatitis B", "rows": [{"columns": [{"width": 12, "items": ["hbsag"]}]}]}]},
                "fields": {
                    "hbsag": {"code": "hbsag", "label": "HBsAg", "type": "choice", "options": ["Negative", "Positive"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "hbsag", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"},
            ]
        },
        
        {
            "test_name": "Hepatitis C Antibody",
            "test_code": "HCV",
            "test_category": "Virology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Hepatitis C antibody",
            "discipline": "SEROLOGY",
            "schema": {
                "meta": {"name": "Hepatitis C Antibody", "discipline": "SEROLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_hcv", "title": "Hepatitis C", "rows": [{"columns": [{"width": 12, "items": ["hcv"]}]}]}]},
                "fields": {
                    "hcv": {"code": "hcv", "label": "HCV", "type": "choice", "options": ["Negative", "Positive"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "hcv", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive"},
            ]
        },
        
        {
            "test_name": "Syphilis (VDRL)",
            "test_code": "VDRL",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "VDRL test for syphilis",
            "discipline": "SEROLOGY",
            "schema": {
                "meta": {"name": "Syphilis (VDRL)", "discipline": "SEROLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_vdrl", "title": "VDRL", "rows": [{"columns": [{"width": 12, "items": ["vdrl"]}]}]}]},
                "fields": {
                    "vdrl": {"code": "vdrl", "label": "VDRL", "type": "choice", "options": ["Non-reactive", "Reactive", "Weakly reactive"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "vdrl", "sex": "ANY", "age_min_days": 0, "text_range": "Non-reactive,Reactive,Weakly reactive"},
            ]
        },
        
        # ==================== BLOOD GROUPING ====================
        {
            "test_name": "Blood Grouping",
            "test_code": "BG",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "ABO and Rhesus blood grouping",
            "discipline": "HEMATOLOGY",
            "schema": {
                "meta": {"name": "Blood Grouping", "discipline": "HEMATOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_blood_group", "title": "Blood Group", "rows": [{"columns": [{"width": 6, "items": ["abo_group"]}, {"width": 6, "items": ["rh_type"]}]}]}]},
                "fields": {
                    "abo_group": {"code": "abo_group", "label": "ABO Group", "type": "choice", "options": ["A", "B", "AB", "O"]},
                    "rh_type": {"code": "rh_type", "label": "Rh Type", "type": "choice", "options": ["Positive", "Negative"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": []
        },
        
        # ==================== SICKLING TEST ====================
        {
            "test_name": "Sickling Test",
            "test_code": "SICKLE",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Sickle cell test",
            "discipline": "HEMATOLOGY",
            "schema": {
                "meta": {"name": "Sickling Test", "discipline": "HEMATOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_sickling", "title": "Sickling", "rows": [{"columns": [{"width": 12, "items": ["sickling"]}]}]}]},
                "fields": {
                    "sickling": {"code": "sickling", "label": "Sickling", "type": "choice", "options": ["Negative", "Positive", "Trait", "Disease"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "sickling", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,Positive,Trait,Disease"},
            ]
        },
        
        # ==================== URINALYSIS ====================
        {
            "test_name": "Urinalysis",
            "test_code": "UA",
            "test_category": "Biochemistry",
            "test_type": "Mixed",
            "specimen_type": "Urine",
            "description": "Complete urinalysis",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Urinalysis", "discipline": "CHEMISTRY", "version": 1},
                "layout": {
                    "sections": [
                        {"id": "sec_physical", "title": "Physical Examination", "rows": [{"columns": [{"width": 6, "items": ["urine_color"]}, {"width": 6, "items": ["urine_clarity"]}]}]},
                        {"id": "sec_dipstick", "title": "Dipstick Results", "rows": [{"columns": [{"width": 4, "items": ["urine_protein"]}, {"width": 4, "items": ["urine_glucose"]}, {"width": 4, "items": ["urine_ketones"]}, {"width": 4, "items": ["urine_blood"]}, {"width": 4, "items": ["urine_bilirubin"]}, {"width": 4, "items": ["urine_urobilinogen"]}, {"width": 4, "items": ["urine_nitrite"]}, {"width": 4, "items": ["urine_leukocytes"]}, {"width": 4, "items": ["urine_ph"]}, {"width": 4, "items": ["urine_sg"]}]}]},
                        {"id": "sec_microscopy", "title": "Microscopy", "rows": [{"columns": [{"width": 6, "items": ["urine_wbc"]}, {"width": 6, "items": ["urine_rbc"]}, {"width": 6, "items": ["urine_epith"]}, {"width": 6, "items": ["urine_bacteria"]}]}]}
                    ]
                },
                "fields": {
                    "urine_color": {"code": "urine_color", "label": "Color", "type": "choice", "options": ["Pale Yellow", "Yellow", "Dark Yellow", "Amber", "Brown", "Red"]},
                    "urine_clarity": {"code": "urine_clarity", "label": "Clarity", "type": "choice", "options": ["Clear", "Slightly Cloudy", "Cloudy", "Turbid"]},
                    "urine_protein": {"code": "urine_protein", "label": "Protein", "type": "choice", "options": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
                    "urine_glucose": {"code": "urine_glucose", "label": "Glucose", "type": "choice", "options": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
                    "urine_ketones": {"code": "urine_ketones", "label": "Ketones", "type": "choice", "options": ["Negative", "Trace", "1+", "2+", "3+"]},
                    "urine_blood": {"code": "urine_blood", "label": "Blood", "type": "choice", "options": ["Negative", "Trace", "Non-hemolyzed", "Hemolyzed"]},
                    "urine_bilirubin": {"code": "urine_bilirubin", "label": "Bilirubin", "type": "choice", "options": ["Negative", "1+", "2+", "3+"]},
                    "urine_urobilinogen": {"code": "urine_urobilinogen", "label": "Urobilinogen", "type": "choice", "options": ["Normal", "1+", "2+", "3+"]},
                    "urine_nitrite": {"code": "urine_nitrite", "label": "Nitrite", "type": "choice", "options": ["Negative", "Positive"]},
                    "urine_leukocytes": {"code": "urine_leukocytes", "label": "Leukocytes", "type": "choice", "options": ["Negative", "Positive"]},
                    "urine_ph": {"code": "urine_ph", "label": "pH", "type": "numeric", "unit": "", "decimals": 1},
                    "urine_sg": {"code": "urine_sg", "label": "Specific Gravity", "type": "numeric", "unit": "", "decimals": 3},
                    "urine_wbc": {"code": "urine_wbc", "label": "WBC/HPF", "type": "choice", "options": ["0-1", "1-5", "5-10", "10-20", ">20"]},
                    "urine_rbc": {"code": "urine_rbc", "label": "RBC/HPF", "type": "choice", "options": ["0-1", "1-5", "5-10", "10-20", ">20"]},
                    "urine_epith": {"code": "urine_epith", "label": "Epithelial Cells", "type": "choice", "options": ["Few", "Moderate", "Many"]},
                    "urine_bacteria": {"code": "urine_bacteria", "label": "Bacteria", "type": "choice", "options": ["None seen", "Present"]},
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "urine_ph", "sex": "ANY", "age_min_days": 0, "low": Decimal("4.5"), "high": Decimal("8.0"), "unit": ""},
                {"field_code": "urine_sg", "sex": "ANY", "age_min_days": 0, "low": Decimal("1.005"), "high": Decimal("1.030"), "unit": ""},
            ]
        },
        
        # ==================== PREGNANCY TEST ====================
        {
            "test_name": "Pregnancy Test (Urine)",
            "test_code": "PTU",
            "test_category": "Biochemistry",
            "test_type": "Qualitative",
            "specimen_type": "Urine",
            "description": "Urine pregnancy test",
            "discipline": "CHEMISTRY",
            "schema": {
                "meta": {"name": "Pregnancy Test (Urine)", "discipline": "CHEMISTRY", "version": 1},
                "layout": {"sections": [{"id": "sec_pregnancy", "title": "Pregnancy Test", "rows": [{"columns": [{"width": 12, "items": ["pregnancy_test_urine"]}]}]}]},
                "fields": {
                    "pregnancy_test_urine": {"code": "pregnancy_test_urine", "label": "Pregnancy Test", "type": "choice", "options": ["Negative", "Positive"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "pregnancy_test_urine", "sex": "F", "age_min_days": 4380, "age_max_days": 18250, "text_range": "Negative,Positive"},
            ]
        },
        
        # ==================== ESR ====================
        {
            "test_name": "ESR",
            "test_code": "ESR",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "Whole Blood",
            "description": "Erythrocyte Sedimentation Rate",
            "discipline": "HEMATOLOGY",
            "schema": {
                "meta": {"name": "ESR", "discipline": "HEMATOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_esr", "title": "ESR", "rows": [{"columns": [{"width": 12, "items": ["esr"]}]}]}]},
                "fields": {
                    "esr": {"code": "esr", "label": "ESR", "type": "numeric", "unit": "mm/hr", "decimals": 0}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                # Adult Male
                {"field_code": "esr", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("15"), "unit": "mm/hr"},
                # Adult Female
                {"field_code": "esr", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("0"), "high": Decimal("20"), "unit": "mm/hr"},
                # Child
                {"field_code": "esr", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "low": Decimal("0"), "high": Decimal("15"), "unit": "mm/hr"},
            ]
        },
        
        # ==================== COAGULATION TESTS ====================
        {
            "test_name": "PT/INR",
            "test_code": "PTINR",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "Citrated Plasma",
            "description": "Prothrombin Time / INR",
            "discipline": "HEMATOLOGY",
            "schema": {
                "meta": {"name": "PT/INR", "discipline": "HEMATOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_coag", "title": "Coagulation", "rows": [{"columns": [{"width": 6, "items": ["pt_seconds"]}, {"width": 6, "items": ["inr"]}]}]}]},
                "fields": {
                    "pt_seconds": {"code": "pt_seconds", "label": "PT (Seconds)", "type": "numeric", "unit": "seconds", "decimals": 1},
                    "inr": {"code": "inr", "label": "INR", "type": "numeric", "unit": "", "decimals": 2}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "pt_seconds", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("11"), "high": Decimal("13.5"), "unit": "seconds"},
                {"field_code": "inr", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("0.8"), "high": Decimal("1.2"), "unit": ""},
            ]
        },
        
        # ==================== WIDAL TEST ====================
        {
            "test_name": "Widal",
            "test_code": "WIDAL",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Widal test for typhoid",
            "discipline": "SEROLOGY",
            "schema": {
                "meta": {"name": "Widal", "discipline": "SEROLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_widal", "title": "Widal Test", "rows": [{"columns": [{"width": 6, "items": ["widal_o"]}, {"width": 6, "items": ["widal_h"]}]}]}]},
                "fields": {
                    "widal_o": {"code": "widal_o", "label": "Widal O", "type": "choice", "options": ["Negative", "1:40", "1:80", "1:160", "1:320"]},
                    "widal_h": {"code": "widal_h", "label": "Widal H", "type": "choice", "options": ["Negative", "1:40", "1:80", "1:160", "1:320"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": [
                {"field_code": "widal_o", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,1:40,1:80,1:160,1:320"},
                {"field_code": "widal_h", "sex": "ANY", "age_min_days": 0, "text_range": "Negative,1:40,1:80,1:160,1:320"},
            ]
        },
        
        # ==================== BLOOD CULTURE ====================
        {
            "test_name": "Blood C/S",
            "test_code": "BLOODCS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Blood (Sterile)",
            "description": "Blood culture and sensitivity",
            "discipline": "MICROBIOLOGY",
            "schema": {
                "meta": {"name": "Blood Culture & Sensitivity", "discipline": "MICROBIOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_culture", "title": "Culture & Sensitivity", "rows": [{"columns": [{"width": 12, "items": ["culture_result"]}, {"width": 12, "items": ["organism"]}, {"width": 12, "items": ["sensitivity"]}]}]}]},
                "fields": {
                    "culture_result": {"code": "culture_result", "label": "Culture Result", "type": "choice", "options": ["No growth", "Growth"]},
                    "organism": {"code": "organism", "label": "Organism Isolated", "type": "text"},
                    "sensitivity": {"code": "sensitivity", "label": "Sensitivity Pattern", "type": "text"}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": []
        },
        
        # ==================== URINE CULTURE ====================
        {
            "test_name": "Urine C/S",
            "test_code": "URINECS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Urine (Midstream)",
            "description": "Urine culture and sensitivity",
            "discipline": "MICROBIOLOGY",
            "schema": {
                "meta": {"name": "Urine Culture & Sensitivity", "discipline": "MICROBIOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_culture", "title": "Culture & Sensitivity", "rows": [{"columns": [{"width": 12, "items": ["culture_result"]}, {"width": 12, "items": ["organism"]}, {"width": 12, "items": ["sensitivity"]}]}]}]},
                "fields": {
                    "culture_result": {"code": "culture_result", "label": "Culture Result", "type": "choice", "options": ["No growth", "Mixed growth", "Pure growth"]},
                    "organism": {"code": "organism", "label": "Organism Isolated", "type": "text"},
                    "sensitivity": {"code": "sensitivity", "label": "Sensitivity Pattern", "type": "text"}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": []
        },
        
        # ==================== STOOL CULTURE ====================
        {
            "test_name": "Stool C/S",
            "test_code": "STOOLCS",
            "test_category": "Microbiology",
            "test_type": "Culture",
            "specimen_type": "Stool",
            "description": "Stool culture and sensitivity",
            "discipline": "MICROBIOLOGY",
            "schema": {
                "meta": {"name": "Stool Culture & Sensitivity", "discipline": "MICROBIOLOGY", "version": 1},
                "layout": {"sections": [{"id": "sec_culture", "title": "Culture & Sensitivity", "rows": [{"columns": [{"width": 12, "items": ["culture_result"]}, {"width": 12, "items": ["organism"]}, {"width": 12, "items": ["parasite"]}]}]}]},
                "fields": {
                    "culture_result": {"code": "culture_result", "label": "Culture Result", "type": "choice", "options": ["No pathogens isolated", "Pathogens isolated"]},
                    "organism": {"code": "organism", "label": "Organism Isolated", "type": "text"},
                    "parasite": {"code": "parasite", "label": "Parasite", "type": "choice", "options": ["Not seen", "Ova", "Cyst", "Trophozoite"]}
                },
                "rules": {"visibility": [], "requiredIf": []},
                "calculated": []
            },
            "reference_ranges": []
        },
    ]


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Lab Template Regeneration Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate all templates
  python3 regenerate_lab_templates.py
  
  # Regenerate only specific templates
  python3 regenerate_lab_templates.py --test-codes FBC,LFT,RFT
  
  # Update only reference ranges
  python3 regenerate_lab_templates.py --update-ranges
  
  # Preview changes without applying
  python3 regenerate_lab_templates.py --dry-run
  
  # Export templates to JSON file
  python3 regenerate_lab_templates.py --export my_templates.json
  
  # Import templates from JSON file
  python3 regenerate_lab_templates.py --import my_templates.json
  
  # List all available template codes
  python3 regenerate_lab_templates.py --list
        """
    )
    
    parser.add_argument(
        '--test-codes',
        type=str,
        help='Comma-separated list of test codes to regenerate (e.g., FBC,LFT,RFT)'
    )
    
    parser.add_argument(
        '--update-ranges',
        action='store_true',
        help='Update only reference ranges, preserve custom fields'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them to the database'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        metavar='FILE',
        help='Export templates to JSON file'
    )
    
    parser.add_argument(
        '--import',
        type=str,
        dest='import_file',
        metavar='FILE',
        help='Import templates from JSON file'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available template codes and exit'
    )
    
    return parser.parse_args()


def list_template_codes():
    """List all available template codes."""
    templates = get_template_definitions()
    print("\nAvailable Lab Template Codes:")
    print("=" * 50)
    
    # Group by discipline
    by_discipline = {}
    for t in templates:
        disc = t.get('discipline', 'UNKNOWN')
        if disc not in by_discipline:
            by_discipline[disc] = []
        by_discipline[disc].append(t)
    
    for disc, temp_list in sorted(by_discipline.items()):
        print(f"\n{disc}:")
        for t in temp_list:
            print(f"  {t['test_code']:12} - {t['test_name']}")
    
    print(f"\nTotal: {len(templates)} templates")
    print("=" * 50)


def export_templates_to_file(templates, filepath):
    """Export templates to JSON file with human-readable format."""
    # Convert to exportable format with human-readable ages
    export_data = {
        "version": "1.0",
        "exported_at": "2024-01-01",  # Will be set properly below
        "description": "Lab Test Templates Export",
        "templates": []
    }
    
    from datetime import datetime
    export_data["exported_at"] = datetime.now().isoformat()
    
    for t in templates:
        template_export = {
            "test_name": t["test_name"],
            "test_code": t["test_code"],
            "test_category": t["test_category"],
            "test_type": t["test_type"],
            "specimen_type": t["specimen_type"],
            "description": t["description"],
            "discipline": t["discipline"],
            "schema": t["schema"],
            "reference_ranges": []
        }
        
        # Convert reference ranges to human-readable format
        for rr in t.get("reference_ranges", []):
            rr_export = {
                "field_code": rr.get("field_code"),
                "sex": rr.get("sex", "ANY"),
            }
            
            # Convert age in days to human-readable format
            age_min = rr.get("age_min_days")
            age_max = rr.get("age_max_days")
            
            if age_min is not None or age_max is not None:
                age_str = []
                if age_min is not None:
                    if age_min == 0:
                        age_str.append("0")
                    elif age_min >= 365:
                        years = age_min // 365
                        age_str.append(f"{years} years")
                    else:
                        age_str.append(f"{age_min} days")
                
                if age_max is not None:
                    if age_max >= 365:
                        years = age_max // 365
                        if years >= 70:
                            age_str.append("70+ years")
                        else:
                            age_str.append(f"{years} years")
                    else:
                        age_str.append(f"{age_max} days")
                
                if age_str:
                    rr_export["age_range"] = "-".join(age_str)
            
            # Add numeric values
            if "low" in rr:
                rr_export["low"] = float(rr["low"])
            if "high" in rr:
                rr_export["high"] = float(rr["high"])
            if "critical_low" in rr:
                rr_export["critical_low"] = float(rr["critical_low"])
            if "critical_high" in rr:
                rr_export["critical_high"] = float(rr["critical_high"])
            if "unit" in rr:
                rr_export["unit"] = rr["unit"]
            if "text_range" in rr:
                rr_export["text_range"] = rr["text_range"]
            
            template_export["reference_ranges"].append(rr_export)
        
        export_data["templates"].append(template_export)
    
    with open(filepath, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✓ Exported {len(templates)} templates to {filepath}")


def import_templates_from_file(filepath, db, admin_user_id, dry_run=False):
    """Import templates from JSON file."""
    with open(filepath, 'r') as f:
        import_data = json.load(f)
    
    templates = import_data.get("templates", [])
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Importing {len(templates)} templates from {filepath}...")
    
    templates_created = 0
    templates_updated = 0
    ranges_created = 0
    
    for template_data in templates:
        test_name = template_data["test_name"]
        test_code = template_data["test_code"]
        discipline = template_data["discipline"]
        schema = template_data["schema"]
        reference_ranges = template_data.get("reference_ranges", [])
        
        print(f"\nProcessing: {test_name} ({test_code})")
        
        # Check if template exists
        check_query = text("SELECT id FROM lab_templates WHERE name = :name")
        existing = db.execute(check_query, {"name": test_name}).fetchone()
        
        if existing:
            template_id = existing[0]
            if not dry_run:
                update_template = text("""
                    UPDATE lab_templates 
                    SET discipline = :discipline, status = 'PUBLISHED'
                    WHERE id = :id
                """)
                db.execute(update_template, {"discipline": discipline, "id": template_id})
            print(f"  -> Template exists, {'updating' if not dry_run else 'would update'}...")
            templates_updated += 1
        else:
            template_id = str(uuid4())
            if not dry_run:
                insert_template = text("""
                    INSERT INTO lab_templates (id, name, discipline, status, current_version, created_by_id, created_at)
                    VALUES (:id, :name, :discipline, 'PUBLISHED', 1, :created_by_id, NOW())
                """)
                db.execute(insert_template, {
                    "id": template_id,
                    "name": test_name,
                    "discipline": discipline,
                    "created_by_id": admin_user_id
                })
            print(f"  -> Creating new template...")
            templates_created += 1
        
        # Convert human-readable reference ranges back to database format
        db_ranges = []
        for rr in reference_ranges:
            db_rr = {"field_code": rr.get("field_code"), "sex": rr.get("sex", "ANY")}
            
            # Convert age string back to days
            age_range = rr.get("age_range", "")
            if age_range:
                # Simple parsing for common formats
                if "years" in age_range.lower():
                    # Extract years
                    parts = age_range.replace("+", "").split()
                    for i, p in enumerate(parts):
                        if p.isdigit():
                            years = int(p)
                            if i == 0:
                                db_rr["age_min_days"] = years * 365
                            if "+" in age_range or (i == len(parts) - 1 and "years" in age_range):
                                db_rr["age_max_days"] = 25550  # 70 years
                            elif i > 0 and parts[i-1] == "-":
                                db_rr["age_max_days"] = years * 365
                elif "days" in age_range.lower():
                    db_rr["age_min_days"] = int(age_range.split()[0])
            
            if "low" in rr:
                db_rr["low"] = str(rr["low"])
            if "high" in rr:
                db_rr["high"] = str(rr["high"])
            if "critical_low" in rr:
                db_rr["critical_low"] = str(rr["critical_low"])
            if "critical_high" in rr:
                db_rr["critical_high"] = str(rr["critical_high"])
            if "unit" in rr:
                db_rr["unit"] = rr["unit"]
            if "text_range" in rr:
                db_rr["text_range"] = rr["text_range"]
            
            db_ranges.append(db_rr)
        
        # Create or update template version (only if not dry-run and not ranges-only)
        if not dry_run:
            version_check = text("SELECT id FROM lab_template_versions WHERE template_id = :tid AND version = 1")
            version_exists = db.execute(version_check, {"tid": template_id}).fetchone()
            
            if version_exists:
                update_version = text("""
                    UPDATE lab_template_versions 
                    SET schema_json = :schema_json, status = 'PUBLISHED'
                    WHERE id = :id
                """)
                db.execute(update_version, {"schema_json": json.dumps(schema), "id": version_exists[0]})
            else:
                version_id = str(uuid4())
                insert_version = text("""
                    INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, created_by_id, created_at)
                    VALUES (:id, :template_id, 1, 'PUBLISHED', :schema_json, :created_by_id, NOW())
                """)
                db.execute(insert_version, {
                    "id": version_id,
                    "template_id": template_id,
                    "schema_json": json.dumps(schema),
                    "created_by_id": admin_user_id
                })
        
        # Create reference ranges
        for rr_data in db_ranges:
            field_code = rr_data.get("field_code", "")
            sex = rr_data.get("sex", "ANY")
            age_min = rr_data.get("age_min_days")
            
            if not field_code:
                continue
            
            if dry_run:
                print(f"  -> Would create reference range: {field_code} ({sex})")
                ranges_created += 1
                continue
            
            rr_check = text("""
                SELECT id FROM lab_reference_ranges 
                WHERE field_code = :fc AND (sex = :sex OR (sex IS NULL AND :sex IS NULL))
                AND (age_min_days = :age_min OR (age_min_days IS NULL AND :age_min IS NULL))
            """)
            rr_exists = db.execute(rr_check, {
                "fc": field_code, 
                "sex": sex, 
                "age_min": age_min
            }).fetchone()
            
            if not rr_exists:
                rr_id = str(uuid4())
                insert_rr = text("""
                    INSERT INTO lab_reference_ranges 
                    (id, field_code, sex, age_min_days, age_max_days, low, high, critical_low, critical_high, unit, text_range, created_at)
                    VALUES (:id, :field_code, :sex, :age_min_days, :age_max_days, :low, :high, :critical_low, :critical_high, :unit, :text_range, NOW())
                """)
                
                db.execute(insert_rr, {
                    "id": rr_id,
                    "field_code": field_code,
                    "sex": sex,
                    "age_min_days": age_min,
                    "age_max_days": rr_data.get("age_max_days"),
                    "low": rr_data.get("low"),
                    "high": rr_data.get("high"),
                    "critical_low": rr_data.get("critical_low"),
                    "critical_high": rr_data.get("critical_high"),
                    "unit": rr_data.get("unit"),
                    "text_range": rr_data.get("text_range")
                })
                ranges_created += 1
    
    if not dry_run:
        db.commit()
    
    return {
        "templates_created": templates_created,
        "templates_updated": templates_updated,
        "ranges_created": ranges_created
    }


def regenerate_all_templates(test_codes=None, update_ranges_only=False, dry_run=False):
    """Main function to regenerate all templates and reference ranges.
    
    Args:
        test_codes: List of test codes to regenerate (None = all)
        update_ranges_only: If True, only update reference ranges
        dry_run: If True, preview changes without applying
    """
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("LAB TEMPLATE REGENERATION")
        print("="*60)
        
        if dry_run:
            print("[DRY RUN MODE - No changes will be applied]")
        
        if test_codes:
            print(f"[FILTERED: Only processing: {', '.join(test_codes)}]")
        
        if update_ranges_only:
            print("[RANGES ONLY MODE - Only updating reference ranges]")
        
        print()
        
        # Get admin user ID
        user_query = text("SELECT id FROM users ORDER BY id LIMIT 1")
        user_result = db.execute(user_query).fetchone()
        admin_user_id = user_result[0] if user_result else 1
        
        templates = get_template_definitions()
        
        # Filter by test codes if specified
        if test_codes:
            test_codes_upper = [c.upper().strip() for c in test_codes]
            templates = [t for t in templates if t["test_code"].upper() in test_codes_upper]
            if not templates:
                print(f"ERROR: No templates found matching codes: {test_codes}")
                return False
        
        templates_created = 0
        versions_created = 0
        ranges_created = 0
        
        for template_data in templates:
            test_name = template_data["test_name"]
            test_code = template_data["test_code"]
            discipline = template_data["discipline"]
            schema = template_data["schema"]
            reference_ranges = template_data["reference_ranges"]
            
            print(f"\nProcessing: {test_name} ({test_code})")
            
            # Check if template exists
            check_query = text("SELECT id FROM lab_templates WHERE name = :name")
            existing = db.execute(check_query, {"name": test_name}).fetchone()
            
            if existing:
                template_id = existing[0]
                print(f"  -> Template exists, {'updating' if not dry_run else 'would update'}...")
                
                if not dry_run and not update_ranges_only:
                    # Update template
                    update_template = text("""
                        UPDATE lab_templates 
                        SET discipline = :discipline, status = 'PUBLISHED'
                        WHERE id = :id
                    """)
                    db.execute(update_template, {"discipline": discipline, "id": template_id})
            else:
                template_id = str(uuid4())
                print(f"  -> Creating new template...")
                
                if not dry_run and not update_ranges_only:
                    # Create template
                    insert_template = text("""
                        INSERT INTO lab_templates (id, name, discipline, status, current_version, created_by_id, created_at)
                        VALUES (:id, :name, :discipline, 'PUBLISHED', 1, :created_by_id, NOW())
                    """)
                    db.execute(insert_template, {
                        "id": template_id,
                        "name": test_name,
                        "discipline": discipline,
                        "created_by_id": admin_user_id
                    })
                    templates_created += 1
                elif dry_run and not update_ranges_only:
                    templates_created += 1
            
            # Create or update template version (skip if ranges-only mode)
            if not update_ranges_only:
                if dry_run:
                    print(f"  -> Would create/update template version 1")
                    versions_created += 1
                else:
                    version_check = text("SELECT id FROM lab_template_versions WHERE template_id = :tid AND version = 1")
                    version_exists = db.execute(version_check, {"tid": template_id}).fetchone()
                    
                    if version_exists:
                        # Update version
                        update_version = text("""
                            UPDATE lab_template_versions 
                            SET schema_json = :schema_json, status = 'PUBLISHED'
                            WHERE id = :id
                        """)
                        db.execute(update_version, {"schema_json": json.dumps(schema), "id": version_exists[0]})
                        print(f"  -> Updated template version 1")
                    else:
                        version_id = str(uuid4())
                        insert_version = text("""
                            INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, created_by_id, created_at)
                            VALUES (:id, :template_id, 1, 'PUBLISHED', :schema_json, :created_by_id, NOW())
                        """)
                        db.execute(insert_version, {
                            "id": version_id,
                            "template_id": template_id,
                            "schema_json": json.dumps(schema),
                            "created_by_id": admin_user_id
                        })
                        versions_created += 1
                        print(f"  -> Created template version 1")
            else:
                print(f"  -> Skipping template version (ranges-only mode)")
            
            # Create reference ranges
            for rr_data in reference_ranges:
                field_code = rr_data.get("field_code", "")
                sex = rr_data.get("sex", "ANY")
                age_min = rr_data.get("age_min_days")
                
                if not field_code:
                    continue
                
                if dry_run:
                    print(f"  -> Would create reference range: {field_code} ({sex})")
                    ranges_created += 1
                    continue
                    
                rr_check = text("""
                    SELECT id FROM lab_reference_ranges 
                    WHERE field_code = :fc AND (sex = :sex OR (sex IS NULL AND :sex IS NULL))
                    AND (age_min_days = :age_min OR (age_min_days IS NULL AND :age_min IS NULL))
                """)
                rr_exists = db.execute(rr_check, {
                    "fc": field_code, 
                    "sex": sex, 
                    "age_min": age_min
                }).fetchone()
                
                if not rr_exists:
                    rr_id = str(uuid4())
                    insert_rr = text("""
                        INSERT INTO lab_reference_ranges 
                        (id, field_code, sex, age_min_days, age_max_days, low, high, critical_low, critical_high, unit, text_range, created_at)
                        VALUES (:id, :field_code, :sex, :age_min_days, :age_max_days, :low, :high, :critical_low, :critical_high, :unit, :text_range, NOW())
                    """)
                    
                    db.execute(insert_rr, {
                        "id": rr_id,
                        "field_code": field_code,
                        "sex": sex,
                        "age_min_days": age_min,
                        "age_max_days": rr_data.get("age_max_days"),
                        "low": str(rr_data["low"]) if "low" in rr_data else None,
                        "high": str(rr_data["high"]) if "high" in rr_data else None,
                        "critical_low": str(rr_data["critical_low"]) if "critical_low" in rr_data else None,
                        "critical_high": str(rr_data["critical_high"]) if "critical_high" in rr_data else None,
                        "unit": rr_data.get("unit"),
                        "text_range": rr_data.get("text_range")
                    })
                    ranges_created += 1
        
        if not dry_run:
            db.commit()
        
        print("\n" + "="*60)
        print("REGENERATION COMPLETE")
        print("="*60)
        print(f"  Templates created: {templates_created}")
        print(f"  Template versions: {versions_created}")
        print(f"  Reference ranges: {ranges_created}")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        if not dry_run:
            db.rollback()
        raise
    finally:
        db.close()


def main():
    """Entry point with argument parsing."""
    args = parse_arguments()
    
    # Handle --list first
    if args.list:
        list_template_codes()
        return
    
    # Handle export
    if args.export:
        templates = get_template_definitions()
        export_templates_to_file(templates, args.export)
        return
    
    # Handle import
    if args.import_file:
        db = SessionLocal()
        try:
            user_query = text("SELECT id FROM users ORDER BY id LIMIT 1")
            user_result = db.execute(user_query).fetchone()
            admin_user_id = user_result[0] if user_result else 1
            
            result = import_templates_from_file(args.import_file, db, admin_user_id, dry_run=args.dry_run)
            
            print("\n" + "="*60)
            print("IMPORT COMPLETE")
            print("="*60)
            print(f"  Templates created: {result['templates_created']}")
            print(f"  Templates updated: {result['templates_updated']}")
            print(f"  Reference ranges: {result['ranges_created']}")
            print("="*60 + "\n")
            
            if args.dry_run:
                print("✓ Dry run complete - no changes were applied")
            else:
                print("✓ Import completed successfully!")
        except Exception as e:
            print(f"\n✗ Import failed: {str(e)}")
            sys.exit(1)
        finally:
            db.close()
        return
    
    # Handle regeneration
    test_codes = None
    if args.test_codes:
        test_codes = [c.strip() for c in args.test_codes.split(',')]
    
    print("\nStarting Lab Template Regeneration...")
    
    if args.dry_run:
        print("[DRY RUN MODE - Preview only, no changes will be applied]")
    
    if test_codes:
        print(f"[FILTERED: Only processing: {', '.join(test_codes)}]")
    
    if args.update_ranges:
        print("[RANGES ONLY MODE - Only updating reference ranges]\n")
    else:
        print("This will create/update all lab templates with proper schema and reference ranges.\n")
    
    try:
        regenerate_all_templates(
            test_codes=test_codes,
            update_ranges_only=args.update_ranges,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            print("✓ Dry run complete - no changes were applied")
        else:
            print("✓ Regeneration completed successfully!")
    except Exception as e:
        print(f"\n✗ Failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
