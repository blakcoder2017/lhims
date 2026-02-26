#!/usr/bin/env python3
"""
Seed Ghana-focused lab template pack.
Run: python3 scripts/seed_lab_templates_ghana.py

Creates:
- lab_option_sets (DIPSTICK_SCALE, URINE_COLOUR, etc.)
- lab_templates + lab_template_version v1 (PUBLISHED)
- lab_reference_ranges for common numeric fields
- Updates lab_tests to map to templates where test codes match
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.lab_template_models import LabTemplate, LabTemplateVersion, LabOptionSet, LabReferenceRange
from app.models.lab_catalog_models import LabTest
from app.models.user_models import User, Role


OPTION_SETS = [
    ("DIPSTICK_SCALE", ["Negative", "Trace", "+", "++", "+++"]),
    ("URINE_COLOUR", ["Straw", "Yellow", "Amber", "Red", "Brown", "Other"]),
    ("URINE_APPEARANCE", ["Clear", "Slightly turbid", "Turbid"]),
    ("STOOL_CONSISTENCY", ["Formed", "Semi-formed", "Watery"]),
    ("STOOL_COLOUR", ["Brown", "Green", "Black", "Red", "Other"]),
    ("ORGANISM_LIST", [
        "E. coli", "Klebsiella spp.", "Staphylococcus aureus", "Pseudomonas aeruginosa",
        "Proteus spp.", "Streptococcus spp.", "Candida spp.", "Salmonella spp.", "Shigella spp.", "Other"
    ]),
    ("ANTIBIOTIC_LIST", [
        "Ampicillin", "Amoxicillin-clavulanate", "Ceftriaxone", "Ceftazidime", "Ciprofloxacin",
        "Gentamicin", "Amikacin", "Erythromycin", "Azithromycin", "Tetracycline", "Co-trimoxazole",
        "Nitrofurantoin", "Imipenem", "Meropenem", "Vancomycin"
    ]),
    ("HIV_KIT_NAMES", ["Determine", "First Response", "OraQuick", "Uni-Gold", "Other"]),
]


def fbc_template():
    """Full Blood Count (FBC/CBC) - HEMATOLOGY"""
    return {
        "meta": {"name": "Full Blood Count (FBC)", "discipline": "HEMATOLOGY", "version": 1},
        "layout": {
            "sections": [
                {
                    "id": "sec_core",
                    "title": "Core Indices",
                    "rows": [{
                        "columns": [
                            {"width": 6, "items": ["fld_wbc", "fld_rbc", "fld_hb", "fld_hct_pcv", "fld_mcv"]},
                            {"width": 6, "items": ["fld_mch", "fld_mchc", "fld_rdw", "fld_platelets"]}
                        ]
                    }]
                },
                {
                    "id": "sec_diff",
                    "title": "Differential",
                    "rows": [{
                        "columns": [
                            {"width": 6, "items": ["fld_neut_pct", "fld_lymph_pct", "fld_mono_pct", "fld_eos_pct", "fld_baso_pct"]},
                            {"width": 6, "items": ["fld_neut_abs", "fld_lymph_abs"]}
                        ]
                    }]
                },
                {
                    "id": "sec_morph",
                    "title": "Morphology/Comments",
                    "rows": [{
                        "columns": [
                            {"width": 12, "items": ["fld_film_comment_tags", "fld_film_comment_free"]}
                        ]
                    }]
                }
            ]
        },
        "fields": {
            "fld_wbc": {"type": "numeric", "code": "wbc", "label": "WBC", "unit": "x10^9/L", "decimals": 1, "required": True},
            "fld_rbc": {"type": "numeric", "code": "rbc", "label": "RBC", "unit": "x10^12/L", "decimals": 2, "required": True},
            "fld_hb": {"type": "numeric", "code": "hb", "label": "Haemoglobin", "unit": "g/dL", "decimals": 1, "required": True,
                       "critical": {"low": 5.0, "high": 20.0}},
            "fld_hct_pcv": {"type": "numeric", "code": "hct_pcv", "label": "HCT/PCV", "unit": "%", "decimals": 1, "required": True},
            "fld_mcv": {"type": "numeric", "code": "mcv", "label": "MCV", "unit": "fL", "decimals": 1},
            "fld_mch": {"type": "numeric", "code": "mch", "label": "MCH", "unit": "pg", "decimals": 1},
            "fld_mchc": {"type": "numeric", "code": "mchc", "label": "MCHC", "unit": "g/dL", "decimals": 1},
            "fld_rdw": {"type": "numeric", "code": "rdw", "label": "RDW", "unit": "%", "decimals": 1},
            "fld_platelets": {"type": "numeric", "code": "platelets", "label": "Platelets", "unit": "x10^9/L", "decimals": 0, "required": True},
            "fld_neut_pct": {"type": "numeric", "code": "neut_pct", "label": "Neutrophils %", "unit": "%", "decimals": 1},
            "fld_lymph_pct": {"type": "numeric", "code": "lymph_pct", "label": "Lymphocytes %", "unit": "%", "decimals": 1},
            "fld_mono_pct": {"type": "numeric", "code": "mono_pct", "label": "Monocytes %", "unit": "%", "decimals": 1},
            "fld_eos_pct": {"type": "numeric", "code": "eos_pct", "label": "Eosinophils %", "unit": "%", "decimals": 1},
            "fld_baso_pct": {"type": "numeric", "code": "baso_pct", "label": "Basophils %", "unit": "%", "decimals": 1},
            "fld_neut_abs": {"type": "numeric", "code": "neut_abs", "label": "Neutrophils (abs)", "unit": "x10^9/L", "decimals": 2},
            "fld_lymph_abs": {"type": "numeric", "code": "lymph_abs", "label": "Lymphocytes (abs)", "unit": "x10^9/L", "decimals": 2},
            "fld_film_comment_tags": {"type": "multichoice", "code": "film_comment_tags", "label": "Film morphology",
                "options": ["Microcytosis", "Macrocytosis", "Hypochromia", "Anisocytosis", "Poikilocytosis", "Target cells",
                           "Sickle cells seen", "Schistocytes", "Polychromasia", "Atypical lymphocytes", "Blasts suspected", "Platelet clumping"]},
            "fld_film_comment_free": {"type": "text", "code": "film_comment_free", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def malaria_rdt_template():
    """Malaria RDT - PARASITOLOGY"""
    return {
        "meta": {"name": "Malaria RDT", "discipline": "PARASITOLOGY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": ["fld_rdt_result", "fld_species_hint", "fld_comment"]}]}]}]},
        "fields": {
            "fld_rdt_result": {"type": "choice", "code": "rdt_result", "label": "RDT Result", "options": ["Positive", "Negative", "Invalid"], "required": True},
            "fld_species_hint": {"type": "choice", "code": "species_hint", "label": "Species hint", "options": ["Pf", "Pan", "Mixed", "Unknown"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def ue_template():
    """Urea & Electrolytes (U&E) - CHEMISTRY"""
    return {
        "meta": {"name": "Urea & Electrolytes (U&E)", "discipline": "CHEMISTRY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Electrolytes & Renal", "rows": [{"columns": [{"width": 12, "items": [
            "fld_sodium", "fld_potassium", "fld_chloride", "fld_bicarb", "fld_urea", "fld_creatinine", "fld_anion_gap"
        ]}]}]}]},
        "fields": {
            "fld_sodium": {"type": "numeric", "code": "sodium", "label": "Sodium", "unit": "mmol/L", "decimals": 1, "required": True},
            "fld_potassium": {"type": "numeric", "code": "potassium", "label": "Potassium", "unit": "mmol/L", "decimals": 1, "required": True},
            "fld_chloride": {"type": "numeric", "code": "chloride", "label": "Chloride", "unit": "mmol/L", "decimals": 1, "required": True},
            "fld_bicarb": {"type": "numeric", "code": "bicarb", "label": "Bicarbonate", "unit": "mmol/L", "decimals": 1, "required": True},
            "fld_urea": {"type": "numeric", "code": "urea", "label": "Urea", "unit": "mmol/L", "decimals": 1, "required": True},
            "fld_creatinine": {"type": "numeric", "code": "creatinine", "label": "Creatinine", "unit": "µmol/L", "decimals": 0, "required": True},
            "fld_anion_gap": {"type": "calculated", "code": "anion_gap", "label": "Anion Gap", "unit": "mmol/L", "formula": "sodium - (chloride + bicarb)", "decimals": 1},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [
            {"target_code": "anion_gap", "formula": "sodium - (chloride + bicarb)", "deps": ["sodium", "chloride", "bicarb"], "decimals": 1, "unit": "mmol/L"}
        ],
    }


def blood_group_template():
    """Blood Grouping ABO/RhD - BLOODBANK"""
    return {
        "meta": {"name": "Blood Grouping (ABO/RhD)", "discipline": "BLOODBANK", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": ["fld_abo_group", "fld_rhd", "fld_weak_d", "fld_comment"]}]}]}]},
        "fields": {
            "fld_abo_group": {"type": "choice", "code": "abo_group", "label": "ABO Group", "options": ["A", "B", "AB", "O"], "required": True},
            "fld_rhd": {"type": "choice", "code": "rhd", "label": "RhD", "options": ["Positive", "Negative"], "required": True},
            "fld_weak_d": {"type": "choice", "code": "weak_d", "label": "Weak D", "options": ["Not performed", "Positive", "Negative"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def blood_film_mp_template():
    """Blood Film for Malaria Parasites - PARASITOLOGY"""
    return {
        "meta": {"name": "Blood Film for Malaria Parasites", "discipline": "PARASITOLOGY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": ["fld_mp_result", "fld_species", "fld_density_grade", "fld_comment"]}]}]}]},
        "fields": {
            "fld_mp_result": {"type": "choice", "code": "mp_result", "label": "Result", "options": ["Positive", "Negative"], "required": True},
            "fld_species": {"type": "choice", "code": "species", "label": "Species", "options": ["Pf", "Pv", "Mixed", "Unknown"]},
            "fld_density_grade": {"type": "choice", "code": "density_grade", "label": "Density grade", "options": ["Negative", "+", "++", "+++", "++++"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [{"target": "fld_density_grade", "showIf": {"field": "mp_result", "op": "==", "value": "Positive"}}],
                  "requiredIf": [{"target": "fld_density_grade", "if": {"field": "mp_result", "op": "==", "value": "Positive"}}]},
        "calculated": [],
    }


def urinalysis_template():
    """Urinalysis (Dipstick + Microscopy) - CHEMISTRY"""
    return {
        "meta": {"name": "Urinalysis", "discipline": "CHEMISTRY", "version": 1},
        "layout": {"sections": [
            {"id": "sec_phys", "title": "Physical", "rows": [{"columns": [{"width": 12, "items": ["fld_colour", "fld_appearance", "fld_sg", "fld_ph"]}]}]},
            {"id": "sec_dipstick", "title": "Dipstick", "rows": [{"columns": [{"width": 12, "items": [
                "fld_protein", "fld_glucose", "fld_ketones", "fld_blood", "fld_nitrite", "fld_leukocytes", "fld_bilirubin", "fld_urobilinogen"
            ]}]}]},
            {"id": "sec_micro", "title": "Microscopy", "rows": [{"columns": [{"width": 12, "items": [
                "fld_wbc_hpf", "fld_rbc_hpf", "fld_epithelial", "fld_bacteria", "fld_yeast", "fld_schisto_ova", "fld_comment"
            ]}]}]}
        ]},
        "fields": {
            "fld_colour": {"type": "choice", "code": "colour", "label": "Colour", "optionSet": "URINE_COLOUR"},
            "fld_appearance": {"type": "choice", "code": "appearance", "label": "Appearance", "optionSet": "URINE_APPEARANCE"},
            "fld_sg": {"type": "numeric", "code": "sg", "label": "Specific Gravity", "decimals": 2},
            "fld_ph": {"type": "numeric", "code": "ph", "label": "pH", "decimals": 1},
            "fld_protein": {"type": "choice", "code": "protein", "label": "Protein", "optionSet": "DIPSTICK_SCALE"},
            "fld_glucose": {"type": "choice", "code": "glucose", "label": "Glucose", "optionSet": "DIPSTICK_SCALE"},
            "fld_ketones": {"type": "choice", "code": "ketones", "label": "Ketones", "optionSet": "DIPSTICK_SCALE"},
            "fld_blood": {"type": "choice", "code": "blood", "label": "Blood", "optionSet": "DIPSTICK_SCALE"},
            "fld_nitrite": {"type": "choice", "code": "nitrite", "label": "Nitrite", "optionSet": "DIPSTICK_SCALE"},
            "fld_leukocytes": {"type": "choice", "code": "leukocytes", "label": "Leukocytes", "optionSet": "DIPSTICK_SCALE"},
            "fld_bilirubin": {"type": "choice", "code": "bilirubin", "label": "Bilirubin", "optionSet": "DIPSTICK_SCALE"},
            "fld_urobilinogen": {"type": "choice", "code": "urobilinogen", "label": "Urobilinogen", "optionSet": "DIPSTICK_SCALE"},
            "fld_wbc_hpf": {"type": "numeric", "code": "wbc_hpf", "label": "WBC/HPF", "decimals": 0},
            "fld_rbc_hpf": {"type": "numeric", "code": "rbc_hpf", "label": "RBC/HPF", "decimals": 0},
            "fld_epithelial": {"type": "choice", "code": "epithelial", "label": "Epithelial cells", "options": ["None", "Few", "Moderate", "Many"]},
            "fld_bacteria": {"type": "choice", "code": "bacteria", "label": "Bacteria", "options": ["None", "Few", "Moderate", "Many"]},
            "fld_yeast": {"type": "choice", "code": "yeast", "label": "Yeast", "options": ["Present", "Absent"]},
            "fld_schisto_ova": {"type": "choice", "code": "schisto_ova", "label": "Schistosoma ova (Ghana)", "options": ["Present", "Absent"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def stool_re_template():
    """Stool Routine Examination - PARASITOLOGY"""
    return {
        "meta": {"name": "Stool R/E", "discipline": "PARASITOLOGY", "version": 1},
        "layout": {"sections": [
            {"id": "sec_macro", "title": "Macroscopy", "rows": [{"columns": [{"width": 12, "items": ["fld_consistency", "fld_colour", "fld_blood", "fld_mucus"]}]}]},
            {"id": "sec_micro", "title": "Microscopy", "rows": [{"columns": [{"width": 12, "items": ["fld_wbc", "fld_rbc", "fld_ova_cysts", "fld_ova_cysts_other", "fld_comment"]}]}]}
        ]},
        "fields": {
            "fld_consistency": {"type": "choice", "code": "consistency", "label": "Consistency", "optionSet": "STOOL_CONSISTENCY"},
            "fld_colour": {"type": "choice", "code": "colour", "label": "Colour", "optionSet": "STOOL_COLOUR"},
            "fld_blood": {"type": "choice", "code": "blood", "label": "Blood", "options": ["Present", "Absent"]},
            "fld_mucus": {"type": "choice", "code": "mucus", "label": "Mucus", "options": ["Present", "Absent"]},
            "fld_wbc": {"type": "choice", "code": "wbc", "label": "WBC", "options": ["None", "Few", "Moderate", "Many"]},
            "fld_rbc": {"type": "choice", "code": "rbc", "label": "RBC", "options": ["None", "Few", "Moderate", "Many"]},
            "fld_ova_cysts": {"type": "multichoice", "code": "ova_cysts", "label": "Ova/Cysts", "options": [
                "Ascaris", "Hookworm", "Trichuris", "Strongyloides", "Taenia", "Schistosoma mansoni",
                "Giardia", "Entamoeba histolytica/dispar", "Other"
            ]},
            "fld_ova_cysts_other": {"type": "text", "code": "ova_cysts_other", "label": "Other (specify)"},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def lft_template():
    """Liver Function Test - CHEMISTRY"""
    return {
        "meta": {"name": "Liver Function Test (LFT)", "discipline": "CHEMISTRY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Results", "rows": [{"columns": [{"width": 12, "items": [
            "fld_ast", "fld_alt", "fld_alp", "fld_ggt", "fld_bilirubin_total", "fld_bilirubin_direct",
            "fld_albumin", "fld_total_protein", "fld_comment"
        ]}]}]}]},
        "fields": {
            "fld_ast": {"type": "numeric", "code": "ast", "label": "AST", "unit": "U/L", "decimals": 0, "required": True},
            "fld_alt": {"type": "numeric", "code": "alt", "label": "ALT", "unit": "U/L", "decimals": 0, "required": True},
            "fld_alp": {"type": "numeric", "code": "alp", "label": "ALP", "unit": "U/L", "decimals": 0, "required": True},
            "fld_ggt": {"type": "numeric", "code": "ggt", "label": "GGT", "unit": "U/L", "decimals": 0},
            "fld_bilirubin_total": {"type": "numeric", "code": "bilirubin_total", "label": "Total Bilirubin", "unit": "µmol/L", "decimals": 1, "required": True},
            "fld_bilirubin_direct": {"type": "numeric", "code": "bilirubin_direct", "label": "Direct Bilirubin", "unit": "µmol/L", "decimals": 1},
            "fld_albumin": {"type": "numeric", "code": "albumin", "label": "Albumin", "unit": "g/L", "decimals": 1},
            "fld_total_protein": {"type": "numeric", "code": "total_protein", "label": "Total Protein", "unit": "g/L", "decimals": 1},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def glucose_template():
    """Glucose (Random/Fasting) - CHEMISTRY"""
    return {
        "meta": {"name": "Glucose", "discipline": "CHEMISTRY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": ["fld_state", "fld_glucose", "fld_comment"]}]}]}]},
        "fields": {
            "fld_state": {"type": "choice", "code": "state", "label": "State", "options": ["Random", "Fasting"], "required": True},
            "fld_glucose": {"type": "numeric", "code": "glucose", "label": "Glucose", "unit": "mmol/L", "decimals": 1, "required": True},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def ogtt_template():
    """OGTT - CHEMISTRY"""
    return {
        "meta": {"name": "OGTT", "discipline": "CHEMISTRY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Oral Glucose Tolerance Test", "rows": [{"columns": [{"width": 12, "items": ["fld_ogtt_0h", "fld_ogtt_1h", "fld_ogtt_2h"]}]}]}]},
        "fields": {
            "fld_ogtt_0h": {"type": "numeric", "code": "ogtt_0h", "label": "Fasting (0h)", "unit": "mmol/L", "decimals": 1},
            "fld_ogtt_1h": {"type": "numeric", "code": "ogtt_1h", "label": "1 hour", "unit": "mmol/L", "decimals": 1},
            "fld_ogtt_2h": {"type": "numeric", "code": "ogtt_2h", "label": "2 hours", "unit": "mmol/L", "decimals": 1},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def hiv_algorithm_template():
    """HIV Testing Algorithm (Rapid tests) - SEROLOGY"""
    return {
        "meta": {"name": "HIV Algorithm", "discipline": "SEROLOGY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "HIV Rapid Test Algorithm", "rows": [{"columns": [{"width": 12, "items": [
            "fld_test1_name", "fld_test1_result", "fld_test2_name", "fld_test2_result",
            "fld_tiebreaker_name", "fld_tiebreaker_result", "fld_comment"
        ]}]}]}]},
        "fields": {
            "fld_test1_name": {"type": "choice", "code": "test1_name", "label": "Test 1 (name)", "optionSet": "HIV_KIT_NAMES"},
            "fld_test1_result": {"type": "choice", "code": "test1_result", "label": "Test 1 result", "options": ["Reactive", "Non-reactive", "Invalid"], "required": True},
            "fld_test2_name": {"type": "choice", "code": "test2_name", "label": "Test 2 (name)", "optionSet": "HIV_KIT_NAMES"},
            "fld_test2_result": {"type": "choice", "code": "test2_result", "label": "Test 2 result", "options": ["Reactive", "Non-reactive", "Invalid"]},
            "fld_tiebreaker_name": {"type": "choice", "code": "tiebreaker_name", "label": "Tiebreaker (name)", "optionSet": "HIV_KIT_NAMES"},
            "fld_tiebreaker_result": {"type": "choice", "code": "tiebreaker_result", "label": "Tiebreaker result", "options": ["Reactive", "Non-reactive", "Invalid"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [
            {"target": "fld_test2_name", "showIf": {"field": "test1_result", "op": "==", "value": "Reactive"}},
            {"target": "fld_test2_result", "showIf": {"field": "test1_result", "op": "==", "value": "Reactive"}},
        ], "requiredIf": []},
        "calculated": [],
    }


def hepatitis_template():
    """Hepatitis B/C - SEROLOGY"""
    return {
        "meta": {"name": "Hepatitis B/C", "discipline": "SEROLOGY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": ["fld_hbsag", "fld_anti_hcv", "fld_comment"]}]}]}]},
        "fields": {
            "fld_hbsag": {"type": "choice", "code": "hbsag", "label": "HBsAg", "options": ["Positive", "Negative", "Invalid"]},
            "fld_anti_hcv": {"type": "choice", "code": "anti_hcv", "label": "Anti-HCV", "options": ["Positive", "Negative", "Invalid"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [],
    }


def syphilis_template():
    """Syphilis - SEROLOGY"""
    return {
        "meta": {"name": "Syphilis", "discipline": "SEROLOGY", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": ["fld_rpr_vdrl", "fld_rpr_titre", "fld_tpha", "fld_comment"]}]}]}]},
        "fields": {
            "fld_rpr_vdrl": {"type": "choice", "code": "rpr_vdrl", "label": "RPR/VDRL", "options": ["Reactive", "Non-reactive"]},
            "fld_rpr_titre": {"type": "text", "code": "rpr_titre", "label": "Titre (if reactive)"},
            "fld_tpha": {"type": "choice", "code": "tpha", "label": "TPHA", "options": ["Reactive", "Non-reactive"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [{"target": "fld_rpr_titre", "showIf": {"field": "rpr_vdrl", "op": "==", "value": "Reactive"}}], "requiredIf": []},
        "calculated": [],
    }


def crossmatch_template():
    """Crossmatch - BLOODBANK"""
    return {
        "meta": {"name": "Crossmatch", "discipline": "BLOODBANK", "version": 1},
        "layout": {"sections": [{"id": "sec_main", "title": "Result", "rows": [{"columns": [{"width": 12, "items": [
            "fld_recipient_group", "fld_donor_unit_id", "fld_donor_group", "fld_method",
            "fld_result", "fld_comment"
        ]}]}]}]},
        "fields": {
            "fld_recipient_group": {"type": "text", "code": "recipient_group", "label": "Recipient group"},
            "fld_donor_unit_id": {"type": "text", "code": "donor_unit_id", "label": "Donor unit ID", "required": True},
            "fld_donor_group": {"type": "choice", "code": "donor_group", "label": "Donor group", "options": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]},
            "fld_method": {"type": "choice", "code": "method", "label": "Method", "options": ["Immediate spin", "AHG", "Other"]},
            "fld_result": {"type": "choice", "code": "result", "label": "Result", "options": ["Compatible", "Incompatible"], "required": True},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment (required if Incompatible)"},
        },
        "rules": {"visibility": [], "requiredIf": [{"target": "fld_comment", "if": {"field": "result", "op": "==", "value": "Incompatible"}}]},
        "calculated": [],
    }


def culture_sensitivity_template():
    """Culture & Sensitivity - MICROBIOLOGY (simplified)"""
    return {
        "meta": {"name": "Culture & Sensitivity (C&S)", "discipline": "MICROBIOLOGY", "version": 1},
        "layout": {"sections": [
            {"id": "sec_spec", "title": "Specimen", "rows": [{"columns": [{"width": 12, "items": ["fld_specimen_type", "fld_culture_result", "fld_organisms", "fld_ast", "fld_comment"]}]}]},
        ]},
        "fields": {
            "fld_specimen_type": {"type": "choice", "code": "specimen_type", "label": "Specimen type",
                "options": ["Urine", "Wound swab", "HVS", "Sputum", "Blood", "CSF", "Other"], "required": True},
            "fld_culture_result": {"type": "choice", "code": "culture_result", "label": "Culture result",
                "options": ["No growth", "Mixed growth", "Growth"], "required": True},
            "fld_organisms": {"type": "repeat_group", "code": "organisms", "label": "Organisms (when growth)",
                "childFields": [
                    {"code": "organism_name", "label": "Organism", "type": "choice", "optionSet": "ORGANISM_LIST"},
                    {"code": "quantity", "label": "Quantity", "type": "choice", "options": ["Scanty", "Moderate", "Heavy"]},
                ]},
            "fld_ast": {"type": "table", "code": "ast", "label": "Antibiotic susceptibility (S/I/R)",
                "rowOptionSet": "ORGANISM_LIST", "colOptionSet": "ANTIBIOTIC_LIST", "cellOptions": ["S", "I", "R"]},
            "fld_comment": {"type": "text", "code": "comment", "label": "Comment"},
        },
        "rules": {"visibility": [
            {"target": "fld_organisms", "showIf": {"field": "culture_result", "op": "!=", "value": "No growth"}},
            {"target": "fld_ast", "showIf": {"field": "culture_result", "op": "!=", "value": "No growth"}},
        ], "requiredIf": []},
        "calculated": [],
    }


TEMPLATES = [
    ("Full Blood Count (FBC)", "HEMATOLOGY", "FBC", fbc_template),
    ("Malaria RDT", "PARASITOLOGY", "MALARIA_RDT", malaria_rdt_template),
    ("Blood Film for Malaria Parasites", "PARASITOLOGY", "BLOOD_FILM_MP", blood_film_mp_template),
    ("Urea & Electrolytes", "CHEMISTRY", "UE", ue_template),
    ("Urinalysis", "CHEMISTRY", "URINALYSIS", urinalysis_template),
    ("Stool R/E", "PARASITOLOGY", "STOOL_RE", stool_re_template),
    ("Liver Function Test (LFT)", "CHEMISTRY", "LFT", lft_template),
    ("Glucose", "CHEMISTRY", "GLUCOSE", glucose_template),
    ("OGTT", "CHEMISTRY", "OGTT", ogtt_template),
    ("HIV Algorithm", "SEROLOGY", "HIV", hiv_algorithm_template),
    ("Hepatitis B/C", "SEROLOGY", "HEPATITIS", hepatitis_template),
    ("Syphilis", "SEROLOGY", "SYPHILIS", syphilis_template),
    ("Blood Grouping (ABO/RhD)", "BLOODBANK", "BLOOD_GROUP", blood_group_template),
    ("Crossmatch", "BLOODBANK", "CROSSMATCH", crossmatch_template),
    ("Culture & Sensitivity (C&S)", "MICROBIOLOGY", "C&S", culture_sensitivity_template),
]

REFERENCE_RANGES = [
    ("hb", "ANY", None, None, 12.0, 17.0, None, "g/dL"),
    ("hb", "F", None, None, 11.0, 15.0, None, "g/dL"),
    ("wbc", "ANY", None, None, 4.0, 11.0, None, "x10^9/L"),
    ("platelets", "ANY", None, None, 150, 400, None, "x10^9/L"),
    ("sodium", "ANY", None, None, 135, 145, None, "mmol/L"),
    ("potassium", "ANY", None, None, 3.5, 5.0, None, "mmol/L"),
    ("creatinine", "ANY", None, None, 60, 120, None, "µmol/L"),
]


def main():
    db = SessionLocal()
    try:
        admin = db.query(User).join(Role, User.role_id == Role.id).filter(Role.name == "Admin").first()
        if not admin:
            admin = db.query(User).first()
        created_by_id = admin.id if admin else 1

        # 1. Option sets
        print("Seeding option sets...")
        for code, options in OPTION_SETS:
            existing = db.query(LabOptionSet).filter(LabOptionSet.code == code).first()
            if not existing:
                db.add(LabOptionSet(code=code, options_json=options))
                print(f"  + {code}")
        db.commit()

        # 2. Reference ranges
        print("Seeding reference ranges...")
        for fc, sex, amin, amax, low, high, tr, unit in REFERENCE_RANGES:
            existing = db.query(LabReferenceRange).filter(
                LabReferenceRange.field_code == fc,
                LabReferenceRange.sex == sex
            ).first()
            if not existing:
                db.add(LabReferenceRange(
                    field_code=fc, sex=sex or "ANY",
                    age_min_days=amin, age_max_days=amax,
                    low=low, high=high, text_range=tr, unit=unit
                ))
                print(f"  + {fc} ({sex})")
        db.commit()

        # 3. Templates
        print("Seeding templates...")
        template_by_code = {}
        for name, discipline, code, fn in TEMPLATES:
            existing = db.query(LabTemplate).filter(LabTemplate.name == name).first()
            if existing:
                print(f"  ~ {name} (exists)")
                template_by_code[code] = existing.id
                continue
            schema = fn()
            tmpl = LabTemplate(name=name, discipline=discipline, status="DRAFT", created_by_id=created_by_id)
            db.add(tmpl)
            db.flush()
            ver = LabTemplateVersion(
                template_id=tmpl.id, version=1, status="PUBLISHED",
                schema_json=schema, created_by_id=created_by_id
            )
            db.add(ver)
            tmpl.current_version = 1
            tmpl.status = "PUBLISHED"
            template_by_code[code] = tmpl.id
            print(f"  + {name}")
        db.commit()

        # 4. Map lab_tests to templates
        print("Mapping lab_tests to templates...")
        mappings = [
            (["FBC", "CBC", "FULL BLOOD COUNT", "FULL BLOOD"], "FBC"),
            (["MALARIA", "RDT"], "MALARIA_RDT"),
            (["BLOOD FILM", "MP", "MALARIA PARASITE", "FILM"], "BLOOD_FILM_MP"),
            (["U&E", "UREA", "ELECTROLYTES", "U&E"], "UE"),
            (["URINALYSIS", "URINE", "DIPSTICK"], "URINALYSIS"),
            (["STOOL", "R/E", "O&P", "FECES"], "STOOL_RE"),
            (["LFT", "LIVER", "LIVER FUNCTION"], "LFT"),
            (["GLUCOSE", "FBS", "RBS", "RANDOM GLUCOSE"], "GLUCOSE"),
            (["OGTT", "GTT", "GLUCOSE TOLERANCE"], "OGTT"),
            (["HIV", "HIV TEST"], "HIV"),
            (["HEPATITIS", "HBSAG", "HCV"], "HEPATITIS"),
            (["SYPHILIS", "RPR", "VDRL", "TPHA"], "SYPHILIS"),
            (["BLOOD GROUP", "ABO", "RHD"], "BLOOD_GROUP"),
            (["CROSSMATCH", "CROSS MATCH", "XM"], "CROSSMATCH"),
            (["C&S", "CULTURE", "SENSITIVITY", "MICROBIOLOGY"], "C&S"),
        ]
        for keywords, tcode in mappings:
            tid = template_by_code.get(tcode)
            if not tid:
                continue
            tname = next((n for n, d, c, _ in TEMPLATES if c == tcode), tcode)
            seen = set()
            for kw in keywords:
                tests = db.query(LabTest).filter(LabTest.test_name.ilike(f"%{kw}%")).all()
                for t in tests:
                    if t.id in seen:
                        continue
                    seen.add(t.id)
                    t.template_id = tid
                    t.template_version = 1
                    print(f"  Mapped {t.test_name} -> {tname}")
        db.commit()

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    update_cs = "--update-cs" in sys.argv
    if update_cs:
        db = SessionLocal()
        try:
            cs = db.query(LabTemplate).filter(LabTemplate.name == "Culture & Sensitivity (C&S)").first()
            if cs:
                from app.crud import lab_template_crud
                admin = db.query(User).join(Role, User.role_id == Role.id).filter(Role.name == "Admin").first() or db.query(User).first()
                cby = admin.id if admin else 1
                schema = culture_sensitivity_template()
                lab_template_crud.save_draft(db, cs.id, schema, created_by_id=cby)
                lab_template_crud.publish_version(db, cs.id, change_note="Add repeat_group and AST table", created_by_id=cby)
                print("Updated C&S template with repeat_group and AST table")
            else:
                print("C&S template not found; run full seed first")
        finally:
            db.close()
        sys.exit(0)
    main()
