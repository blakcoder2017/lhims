#!/usr/bin/env python3
"""
Ghana Hospital EMR - Comprehensive Laboratory Test Seeder

This script creates/merges laboratory tests into the Test Catalog with:
- Test definitions in the lab_tests table
- Parameter templates for results entry
- Ghana-standard reference ranges with age and sex logic
- Idempotent operations (safe to re-run)

Usage:
    python3 seed_ghana_lab_catalog_v2.py

Requirements:
    - Database must be initialized
    - Run from the project root directory
"""

import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection - use environment variable or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:password123@localhost:5433/lhims")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


# =============================================================================
# TEST CATALOG DEFINITIONS
# =============================================================================

def get_lab_tests_definition():
    """Return all lab test definitions for the Ghana EMR."""
    return [
        # HAEMATOLOGY & PARASITOLOGY
        {
            "test_code": "FBC",
            "test_name": "Full Blood Count (FBC)",
            "test_category": "Haematology",
            "test_type": "Panel",
            "specimen_type": "EDTA Blood",
            "description": "Complete blood count with differential - Hb, PCV, RBC, WBC, Platelets, Indices",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("25.00"),
            "is_panel": True,
        },
        {
            "test_code": "HB",
            "test_name": "Haemoglobin (Hb)",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Haemoglobin measurement",
            "routine_tat": 2,
            "urgent_tat": 1,
            "cost": Decimal("5.00"),
            "is_panel": False,
        },
        {
            "test_code": "ESR",
            "test_name": "Erythrocyte Sedimentation Rate (ESR)",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Erythrocyte sedimentation rate",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("10.00"),
            "is_panel": False,
        },
        {
            "test_code": "RETIC",
            "test_name": "Reticulocyte Count",
            "test_category": "Haematology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "Reticulocyte count percentage",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("12.00"),
            "is_panel": False,
        },
        {
            "test_code": "SICKLING",
            "test_name": "Sickling Test",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Sickling test for sickle cell disease screening",
            "routine_tat": 2,
            "urgent_tat": 1,
            "cost": Decimal("5.00"),
            "is_panel": False,
        },
        {
            "test_code": "BF_MP",
            "test_name": "Blood Film for Malaria Parasite",
            "test_category": "Parasitology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Blood film examination for malaria parasites",
            "routine_tat": 2,
            "urgent_tat": 1,
            "cost": Decimal("8.00"),
            "is_panel": False,
        },
        {
            "test_code": "HB_ELECTRO",
            "test_name": "Haemoglobin Electrophoresis (Hb Phenotype)",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Haemoglobin electrophoresis for phenotype determination (AA, AS, SS, SC)",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("35.00"),
            "is_panel": False,
        },
        {
            "test_code": "G6PD",
            "test_name": "G6PD Screening",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Glucose-6-Phosphate Dehydrogenase deficiency screening",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "COOMBS",
            "test_name": "Coombs Test",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "Direct and Indirect Coombs test",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        {
            "test_code": "BLOOD_GROUP",
            "test_name": "Blood Grouping (ABO + Rh)",
            "test_category": "Haematology",
            "test_type": "Qualitative",
            "specimen_type": "EDTA Blood",
            "description": "ABO blood group and Rhesus factor typing",
            "routine_tat": 2,
            "urgent_tat": 1,
            "cost": Decimal("8.00"),
            "is_panel": False,
        },
        
        # MICROSCOPY / ROUTINE EXAMS
        {
            "test_code": "URINE_RE",
            "test_name": "Urine Routine Examination",
            "test_category": "Clinical Pathology",
            "test_type": "Panel",
            "specimen_type": "Urine",
            "description": "Urinalysis - physical, chemical and microscopic examination",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("15.00"),
            "is_panel": True,
        },
        {
            "test_code": "STOOL_RE",
            "test_name": "Stool Routine Examination",
            "test_category": "Clinical Pathology",
            "test_type": "Panel",
            "specimen_type": "Stool",
            "description": "Stool analysis - physical, microscopic and occult blood",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": True,
        },
        {
            "test_code": "HVS_RE",
            "test_name": "High Vaginal Swab (HVS) R/E",
            "test_category": "Microbiology",
            "test_type": "Panel",
            "specimen_type": "Swab",
            "description": "High vaginal swab microscopy and culture",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": True,
        },
        {
            "test_code": "SKIN_SNIP",
            "test_name": "Skin Snip for Microfilaria",
            "test_category": "Parasitology",
            "test_type": "Qualitative",
            "specimen_type": "Skin Snip",
            "description": "Skin snip examination for microfilaria",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        
        # HORMONAL / ENDOCRINE
        {
            "test_code": "TSH",
            "test_name": "Thyroid Stimulating Hormone (TSH)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "TSH measurement for thyroid function",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("35.00"),
            "is_panel": False,
        },
        {
            "test_code": "FT3",
            "test_name": "Free T3 (Triiodothyronine)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Free T3 measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("40.00"),
            "is_panel": False,
        },
        {
            "test_code": "FT4",
            "test_name": "Free T4 (Thyroxine)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Free T4 measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("40.00"),
            "is_panel": False,
        },
        {
            "test_code": "TESTOSTERONE",
            "test_name": "Testosterone",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Total testosterone measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("50.00"),
            "is_panel": False,
            "sex_restriction": "both",
        },
        {
            "test_code": "FSH",
            "test_name": "Follicle Stimulating Hormone (FSH)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "FSH measurement for fertility assessment",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("45.00"),
            "is_panel": False,
        },
        {
            "test_code": "LH",
            "test_name": "Luteinizing Hormone (LH)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "LH measurement for fertility assessment",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("45.00"),
            "is_panel": False,
        },
        {
            "test_code": "PROGESTERONE",
            "test_name": "Progesterone",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum progesterone measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("45.00"),
            "is_panel": False,
        },
        {
            "test_code": "ESTRADIOL",
            "test_name": "Estradiol (E2)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Estradiol measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("50.00"),
            "is_panel": False,
        },
        {
            "test_code": "PROLACTIN",
            "test_name": "Prolactin",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum prolactin measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("40.00"),
            "is_panel": False,
        },
        {
            "test_code": "CORTISOL",
            "test_name": "Cortisol",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum cortisol measurement (morning sample preferred)",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("45.00"),
            "is_panel": False,
        },
        {
            "test_code": "DHEA",
            "test_name": "DHEA-Sulphate (DHEA-S)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "DHEA-Sulphate measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("45.00"),
            "is_panel": False,
        },
        {
            "test_code": "GH",
            "test_name": "Growth Hormone (GH)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Growth hormone measurement",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("50.00"),
            "is_panel": False,
        },
        {
            "test_code": "PSA",
            "test_name": "Prostate Specific Antigen (PSA)",
            "test_category": "Hormonal",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Total PSA for prostate cancer screening",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("35.00"),
            "is_panel": False,
            "sex_restriction": "male",
        },
        {
            "test_code": "THYROID_PROFILE",
            "test_name": "Thyroid Profile",
            "test_category": "Hormonal",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Complete thyroid panel - TSH, FT3, FT4",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("90.00"),
            "is_panel": True,
        },
        {
            "test_code": "FEMALE_INFERTILITY",
            "test_name": "Female Infertility Profile",
            "test_category": "Hormonal",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Female infertility workup - FSH, LH, Prolactin, Progesterone, Estradiol",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("80.00"),
            "is_panel": True,
            "sex_restriction": "female",
        },
        
        # SEROLOGY / INFECTIOUS DISEASES
        {
            "test_code": "HIV_SCREEN",
            "test_name": "HIV Screening (1 & 2)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum/Plasma",
            "description": "HIV 1&2 antibody screening",
            "routine_tat": 2,
            "urgent_tat": 1,
            "cost": Decimal("10.00"),
            "is_panel": False,
        },
        {
            "test_code": "HBSAG",
            "test_name": "Hepatitis B Surface Antigen (HBsAg)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Hepatitis B surface antigen detection",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "HBSAB",
            "test_name": "Hepatitis B Surface Antibody (Anti-HBs)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Hepatitis B immunity status",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "HBcAB_Total",
            "test_name": "Hepatitis B Core Antibody (Total)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "HBc antibody (total) for past or present infection",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "HBV_PROFILE",
            "test_name": "Hepatitis B Viral Profile",
            "test_category": "Serology",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Complete HBV profile - HBsAg, HBsAb, HBcAb, HBeAg, HBeAb",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("60.00"),
            "is_panel": True,
        },
        {
            "test_code": "HCV",
            "test_name": "Hepatitis C Antibody",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Hepatitis C antibody screening",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("25.00"),
            "is_panel": False,
        },
        {
            "test_code": "VDRL",
            "test_name": "VDRL (Syphilis Test)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Venereal Disease Research Laboratory test for syphilis",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("12.00"),
            "is_panel": False,
        },
        {
            "test_code": "TPHA",
            "test_name": "TPHA (Syphilis Confirmation)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Treponema pallidum haemagglutination assay",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("18.00"),
            "is_panel": False,
        },
        {
            "test_code": "WIDAL",
            "test_name": "Widal Test",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Widal test for typhoid fever",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "GONORRHOEA",
            "test_name": "Gonorrhoea (NGAL)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum/Urine",
            "description": "Neisseria gonorrhoeae antigen detection",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("25.00"),
            "is_panel": False,
        },
        {
            "test_code": "CHLAMYDIA",
            "test_name": "Chlamydia trachomatis IgG",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Chlamydia trachomatis IgG antibody",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("30.00"),
            "is_panel": False,
        },
        {
            "test_code": "HPYLORI",
            "test_name": "H. pylori Antibody",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Helicobacter pylori antibody (blood/stool)",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("25.00"),
            "is_panel": False,
        },
        {
            "test_code": "PREGNANCY_TEST",
            "test_name": "Pregnancy Test (Serum β-HCG)",
            "test_category": "Serology",
            "test_type": "Qualitative",
            "specimen_type": "Serum",
            "description": "Pregnancy test using serum β-HCG",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "BHCG_QUANT",
            "test_name": "Quantitative β-HCG",
            "test_category": "Serology",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Quantitative β-HCG for pregnancy monitoring",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("35.00"),
            "is_panel": False,
        },
        {
            "test_code": "AFP",
            "test_name": "Alpha Fetoprotein (AFP)",
            "test_category": "Tumor Marker",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "AFP tumor marker",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("40.00"),
            "is_panel": False,
        },
        
        # BIOCHEMISTRY
        {
            "test_code": "LFT",
            "test_name": "Liver Function Test (LFT)",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Liver function panel - Bilirubin, ALT, AST, ALP, GGT, Protein, Albumin",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("40.00"),
            "is_panel": True,
        },
        {
            "test_code": "RFT",
            "test_name": "Renal Function Test (RFT)",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Renal function panel - Urea, Creatinine, Uric Acid",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("35.00"),
            "is_panel": True,
        },
        {
            "test_code": "ELECTROLYTES",
            "test_name": "Serum Electrolytes",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Electrolyte panel - Na, K, Cl, Bicarbonate",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("25.00"),
            "is_panel": True,
        },
        {
            "test_code": "FBS",
            "test_name": "Fasting Blood Sugar (FBS)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Fluoride Plasma",
            "description": "Fasting blood glucose measurement",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("8.00"),
            "is_panel": False,
        },
        {
            "test_code": "RBS",
            "test_name": "Random Blood Sugar (RBS)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Fluoride Plasma",
            "description": "Random blood glucose measurement",
            "routine_tat": 2,
            "urgent_tat": 1,
            "cost": Decimal("8.00"),
            "is_panel": False,
        },
        {
            "test_code": "OGTT",
            "test_name": "Oral Glucose Tolerance Test (OGTT)",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Fluoride Plasma",
            "description": "Glucose tolerance test - Fasting, 1hr, 2hr",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("20.00"),
            "is_panel": True,
        },
        {
            "test_code": "HbA1c",
            "test_name": "Glycated Haemoglobin (HbA1c)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "HbA1c for diabetes monitoring",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("45.00"),
            "is_panel": False,
        },
        {
            "test_code": "LIPID_PROFILE",
            "test_name": "Lipid Profile",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Lipid panel - Total Cholesterol, HDL, LDL, Triglycerides",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("35.00"),
            "is_panel": True,
        },
        {
            "test_code": "CALCIUM",
            "test_name": "Serum Calcium",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Total serum calcium",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("12.00"),
            "is_panel": False,
        },
        {
            "test_code": "MAGNESIUM",
            "test_name": "Serum Magnesium",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum magnesium measurement",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        {
            "test_code": "PHOSPHATE",
            "test_name": "Serum Phosphate",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum inorganic phosphate",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("12.00"),
            "is_panel": False,
        },
        {
            "test_code": "IRON_STUDIES",
            "test_name": "Iron Studies",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Serum",
            "description": "Iron studies - Serum Iron, TIBC, Ferritin, Transferrin Saturation",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("55.00"),
            "is_panel": True,
        },
        {
            "test_code": "FERRITIN",
            "test_name": "Ferritin",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum ferritin measurement",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("30.00"),
            "is_panel": False,
        },
        {
            "test_code": "TIBC",
            "test_name": "Total Iron Binding Capacity (TIBC)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Total iron binding capacity",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("25.00"),
            "is_panel": False,
        },
        {
            "test_code": "URIC_ACID",
            "test_name": "Uric Acid",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Serum uric acid measurement",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("12.00"),
            "is_panel": False,
        },
        {
            "test_code": "AMYLASE",
            "test_name": "Serum Amylase",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Pancreatic amylase measurement",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("18.00"),
            "is_panel": False,
        },
        {
            "test_code": "LIPASE",
            "test_name": "Serum Lipase",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Pancreatic lipase measurement",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        {
            "test_code": "CK",
            "test_name": "Creatine Kinase (CK)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Total CK for muscle damage",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        {
            "test_code": "CK_MB",
            "test_name": "CK-MB",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "CK-MB isoform for cardiac injury",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("25.00"),
            "is_panel": False,
        },
        {
            "test_code": "LDH",
            "test_name": "Lactate Dehydrogenase (LDH)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "LDH for tissue damage",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("18.00"),
            "is_panel": False,
        },
        {
            "test_code": "TROPONIN",
            "test_name": "Troponin I/T",
            "test_category": "Cardiac Marker",
            "test_type": "Qualitative/Quantitative",
            "specimen_type": "Serum",
            "description": "Cardiac troponin for myocardial infarction",
            "routine_tat": 4,
            "urgent_tat": 1,
            "cost": Decimal("35.00"),
            "is_panel": False,
        },
        {
            "test_code": "BNP",
            "test_name": "B-type Natriuretic Peptide (BNP)",
            "test_category": "Cardiac Marker",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "BNP for heart failure assessment",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("55.00"),
            "is_panel": False,
        },
        {
            "test_code": "GFR",
            "test_name": "Glomerular Filtration Rate (GFR)",
            "test_category": "Biochemistry",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "Estimated GFR calculation",
            "routine_tat": 4,
            "urgent_tat": 2,
            "cost": Decimal("15.00"),
            "is_panel": False,
        },
        
        # INFLAMMATORY MARKERS
        {
            "test_code": "CRP",
            "test_name": "C-Reactive Protein (CRP)",
            "test_category": "Inflammatory",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "CRP for inflammation",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        {
            "test_code": "ASO",
            "test_name": "Antistreptolysin O (ASO) Titer",
            "test_category": "Inflammatory",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "ASO titer for streptococcal infection",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        {
            "test_code": "RA_FACTOR",
            "test_name": "Rheumatoid Factor (RA)",
            "test_category": "Inflammatory",
            "test_type": "Qualitative/Quantitative",
            "specimen_type": "Serum",
            "description": "Rheumatoid factor",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("20.00"),
            "is_panel": False,
        },
        
        # BODY FLUIDS
        {
            "test_code": "CSF_BIOCHEM",
            "test_name": "CSF Biochemistry",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "CSF",
            "description": "CSF analysis - Glucose, Protein, Cell count",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("30.00"),
            "is_panel": True,
        },
        {
            "test_code": "ASCITIC_FLUID",
            "test_name": "Ascitic Fluid Analysis",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Ascitic Fluid",
            "description": "Ascitic fluid biochemistry and cell count",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("35.00"),
            "is_panel": True,
        },
        {
            "test_code": "PLEURAL_FLUID",
            "test_name": "Pleural Fluid Analysis",
            "test_category": "Biochemistry",
            "test_type": "Panel",
            "specimen_type": "Pleural Fluid",
            "description": "Pleural fluid biochemistry and cell count",
            "routine_tat": 8,
            "urgent_tat": 4,
            "cost": Decimal("35.00"),
            "is_panel": True,
        },
        
        # CULTURE & SENSITIVITY
        {
            "test_code": "CS_BLOOD",
            "test_name": "Blood Culture & Sensitivity",
            "test_category": "Microbiology",
            "test_type": "Panel",
            "specimen_type": "Blood",
            "description": "Blood culture for bacteremia detection",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("45.00"),
            "is_panel": True,
        },
        {
            "test_code": "CS_URINE",
            "test_name": "Urine Culture & Sensitivity",
            "test_category": "Microbiology",
            "test_type": "Panel",
            "specimen_type": "Urine",
            "description": "Urine culture and sensitivity",
            "routine_tat": 48,
            "urgent_tat": 24,
            "cost": Decimal("30.00"),
            "is_panel": True,
        },
        {
            "test_code": "CS_STOOL",
            "test_name": "Stool Culture & Sensitivity",
            "test_category": "Microbiology",
            "test_type": "Panel",
            "specimen_type": "Stool",
            "description": "Stool culture for enteric pathogens",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("35.00"),
            "is_panel": True,
        },
        {
            "test_code": "CS_SPUTUM",
            "test_name": "Sputum Culture & Sensitivity",
            "test_category": "Microbiology",
            "test_type": "Panel",
            "specimen_type": "Sputum",
            "description": "Sputum culture for respiratory pathogens",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("35.00"),
            "is_panel": True,
        },
        {
            "test_code": "CS_WOUND",
            "test_name": "Wound Swab Culture & Sensitivity",
            "test_category": "Microbiology",
            "test_type": "Panel",
            "specimen_type": "Swab",
            "description": "Wound swab culture",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("30.00"),
            "is_panel": True,
        },
        
        # VIROLOGY
        {
            "test_code": "HIV_VL",
            "test_name": "HIV Viral Load",
            "test_category": "Virology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Plasma",
            "description": "HIV RNA viral load measurement",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("85.00"),
            "is_panel": False,
        },
        {
            "test_code": "HBV_VL",
            "test_name": "Hepatitis B Viral Load",
            "test_category": "Virology",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "HBV DNA viral load",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("90.00"),
            "is_panel": False,
        },
        {
            "test_code": "HCV_VL",
            "test_name": "Hepatitis C Viral Load",
            "test_category": "Virology",
            "test_type": "Quantitative",
            "specimen_type": "Serum",
            "description": "HCV RNA viral load",
            "routine_tat": 72,
            "urgent_tat": 48,
            "cost": Decimal("100.00"),
            "is_panel": False,
        },
        {
            "test_code": "CD4",
            "test_name": "CD4 Count",
            "test_category": "Immunology",
            "test_type": "Quantitative",
            "specimen_type": "EDTA Blood",
            "description": "CD4+ T lymphocyte count",
            "routine_tat": 24,
            "urgent_tat": 8,
            "cost": Decimal("55.00"),
            "is_panel": False,
        },
    ]


# =============================================================================
# PARAMETER TEMPLATE DEFINITIONS
# =============================================================================

def get_template_definitions():
    """Return template definitions with parameters for each test."""
    return {
        # HAEMATOLOGY
        "FBC": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "hb": {"label": "Haemoglobin (Hb)", "type": "numeric", "unit": "g/dL", "decimals": 1},
                "hct": {"label": "Packed Cell Volume (PCV)", "type": "numeric", "unit": "%", "decimals": 1},
                "rbc_count": {"label": "RBC Count", "type": "numeric", "unit": "x10^12/L", "decimals": 2},
                "wbc_count": {"label": "WBC Count", "type": "numeric", "unit": "x10^9/L", "decimals": 2},
                "platelet_count": {"label": "Platelet Count", "type": "numeric", "unit": "x10^9/L", "decimals": 0},
                "mcv": {"label": "MCV", "type": "numeric", "unit": "fL", "decimals": 1},
                "mch": {"label": "MCH", "type": "numeric", "unit": "pg", "decimals": 1},
                "mchc": {"label": "MCHC", "type": "numeric", "unit": "g/dL", "decimals": 1},
                "neutrophils": {"label": "Neutrophils", "type": "numeric", "unit": "%", "decimals": 1},
                "lymphocytes": {"label": "Lymphocytes", "type": "numeric", "unit": "%", "decimals": 1},
                "monocytes": {"label": "Monocytes", "type": "numeric", "unit": "%", "decimals": 1},
                "eosinophils": {"label": "Eosinophils", "type": "numeric", "unit": "%", "decimals": 1},
                "basophils": {"label": "Basophils", "type": "numeric", "unit": "%", "decimals": 1},
                "retic": {"label": "Reticulocytes", "type": "numeric", "unit": "%", "decimals": 1},
                "rbcmorph": {"label": "RBC Morphology", "type": "text", "multiline": True},
                "remarks": {"label": "Remarks", "type": "text", "multiline": True},
            }
        },
        "HB": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "hb_value": {"label": "Haemoglobin (Hb)", "type": "numeric", "unit": "g/dL", "decimals": 1},
            }
        },
        "ESR": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "esr_value": {"label": "ESR", "type": "numeric", "unit": "mm/hr", "decimals": 0},
            }
        },
        "RETIC": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "retic_count": {"label": "Reticulocyte Count", "type": "numeric", "unit": "%", "decimals": 1},
            }
        },
        "SICKLING": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "sickling_result": {"label": "Sickling Test", "type": "choice", 
                    "options": ["Positive", "Negative"]},
            }
        },
        "BF_MP": {
            "discipline": "PARASITOLOGY",
            "fields": {
                "mp_result": {"label": "Malaria Parasite", "type": "choice",
                    "options": ["Negative", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"]},
                "parasite_density": {"label": "Parasite Density", "type": "text"},
            }
        },
        "HB_ELECTRO": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "hb_phenotype": {"label": "Hb Phenotype", "type": "choice",
                    "options": ["AA", "AS", "SS", "SC", "AC", "CC", "Other"]},
            }
        },
        "G6PD": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "g6pd_result": {"label": "G6PD Status", "type": "choice",
                    "options": ["Normal", "Deficient", "Intermediate"]},
            }
        },
        "COOMBS": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "direct_coombs": {"label": "Direct Coombs", "type": "choice",
                    "options": ["Positive", "Negative"]},
                "indirect_coombs": {"label": "Indirect Coombs", "type": "choice",
                    "options": ["Positive", "Negative"]},
            }
        },
        "BLOOD_GROUP": {
            "discipline": "HEMATOLOGY",
            "fields": {
                "abo_group": {"label": "ABO Group", "type": "choice",
                    "options": ["A", "B", "AB", "O"]},
                "rh_factor": {"label": "Rhesus Factor", "type": "choice",
                    "options": ["Positive", "Negative"]},
            }
        },
        
        # URINE R/E
        "URINE_RE": {
            "discipline": "CLINICAL_PATHOLOGY",
            "fields": {
                "appearance": {"label": "Appearance", "type": "choice",
                    "options": ["Clear", "Slightly turbid", "Turbid"]},
                "colour": {"label": "Colour", "type": "choice",
                    "options": ["Straw", "Yellow", "Amber", "Red", "Brown", "Other"]},
                "ph": {"label": "pH", "type": "numeric", "unit": "", "decimals": 1},
                "specific_gravity": {"label": "Specific Gravity", "type": "numeric", "unit": "", "decimals": 3},
                "protein": {"label": "Protein", "type": "choice",
                    "options": ["Negative", "Trace", "+", "++", "+++"]},
                "glucose": {"label": "Glucose", "type": "choice",
                    "options": ["Negative", "Trace", "+", "++", "+++"]},
                "ketones": {"label": "Ketones", "type": "choice",
                    "options": ["Negative", "Trace", "+", "++", "+++"]},
                "blood": {"label": "Blood", "type": "choice",
                    "options": ["Negative", "Trace", "+", "++", "+++"]},
                "nitrite": {"label": "Nitrite", "type": "choice",
                    "options": ["Negative", "Positive"]},
                "urobilinogen": {"label": "Urobilinogen", "type": "choice",
                    "options": ["Normal", "Elevated"]},
                "bilirubin": {"label": "Bilirubin", "type": "choice",
                    "options": ["Negative", "Positive"]},
                "rbchpf": {"label": "RBC/HPF", "type": "choice",
                    "options": ["0-1", "1-5", "5-10", "10-20", ">20"]},
                "wbchpf": {"label": "WBC/HPF", "type": "choice",
                    "options": ["0-1", "1-5", "5-10", "10-20", ">20"]},
                "casts": {"label": "Casts", "type": "text"},
                "crystals": {"label": "Crystals", "type": "text"},
                "bacteria": {"label": "Bacteria", "type": "text"},
                "yeast": {"label": "Yeast", "type": "text"},
            }
        },
        
        # STOOL R/E
        "STOOL_RE": {
            "discipline": "CLINICAL_PATHOLOGY",
            "fields": {
                "colour": {"label": "Colour", "type": "choice",
                    "options": ["Brown", "Green", "Black", "Red", "Pale", "Other"]},
                "consistency": {"label": "Consistency", "type": "choice",
                    "options": ["Formed", "Semi-formed", "Watery", "Mucoid"]},
                "occult_blood": {"label": "Occult Blood", "type": "choice",
                    "options": ["Negative", "Positive"]},
                "mucus": {"label": "Mucus", "type": "choice",
                    "options": ["Absent", "Present"]},
                "ova": {"label": "Ova", "type": "text"},
                "parasites": {"label": "Parasites", "type": "text"},
                "rbchpf": {"label": "RBC/HPF", "type": "text"},
                "wbchpf": {"label": "WBC/HPF", "type": "text"},
            }
        },
        
        # HVS R/E
        "HVS_RE": {
            "discipline": "MICROBIOLOGY",
            "fields": {
                "appearance": {"label": "Appearance", "type": "text"},
                "epithelial": {"label": "Epithelial Cells", "type": "choice",
                    "options": ["Few", "Moderate", "Many"]},
                "wbchpf": {"label": "WBCs", "type": "choice",
                    "options": ["0-5", "5-10", "10-20", ">20"]},
                "organisms": {"label": "Organisms", "type": "choice",
                    "options": ["None", "Trichomonas", "Yeast", "Bacteria", "Mixed"]},
                "yeast": {"label": "Yeast Cells", "type": "choice",
                    "options": ["Not Seen", "Seen"]},
                "culture": {"label": "Culture Result", "type": "text"},
            }
        },
        
        # SKIN SNIP
        "SKIN_SNIP": {
            "discipline": "PARASITOLOGY",
            "fields": {
                "microfilaria": {"label": "Microfilaria", "type": "choice",
                    "options": ["Not Seen", "Seen"]},
                "remarks": {"label": "Remarks", "type": "text", "multiline": True},
            }
        },
        
        # THYROID PROFILE
        "THYROID_PROFILE": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "tsh": {"label": "TSH", "type": "numeric", "unit": "mIU/L", "decimals": 2},
                "ft3": {"label": "Free T3", "type": "numeric", "unit": "pmol/L", "decimals": 2},
                "ft4": {"label": "Free T4", "type": "numeric", "unit": "pmol/L", "decimals": 2},
            }
        },
        
        # LFT
        "LFT": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "total_bilirubin": {"label": "Total Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1},
                "direct_bilirubin": {"label": "Direct Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1},
                "indirect_bilirubin": {"label": "Indirect Bilirubin", "type": "numeric", "unit": "μmol/L", "decimals": 1},
                "alt": {"label": "ALT (SGPT)", "type": "numeric", "unit": "U/L", "decimals": 0},
                "ast": {"label": "AST (SGOT)", "type": "numeric", "unit": "U/L", "decimals": 0},
                "alp": {"label": "ALP", "type": "numeric", "unit": "U/L", "decimals": 0},
                "ggt": {"label": "GGT", "type": "numeric", "unit": "U/L", "decimals": 0},
                "total_protein": {"label": "Total Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
                "albumin": {"label": "Albumin", "type": "numeric", "unit": "g/L", "decimals": 1},
                "globulin": {"label": "Globulin", "type": "numeric", "unit": "g/L", "decimals": 1},
            }
        },
        
        # RFT
        "RFT": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "urea": {"label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "creatinine": {"label": "Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0},
                "uric_acid": {"label": "Uric Acid", "type": "numeric", "unit": "μmol/L", "decimals": 0},
                "egfr": {"label": "eGFR", "type": "numeric", "unit": "mL/min/1.73m²", "decimals": 0},
            }
        },
        
        # ELECTROLYTES
        "ELECTROLYTES": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "sodium": {"label": "Sodium (Na+)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
                "potassium": {"label": "Potassium (K+)", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "chloride": {"label": "Chloride (Cl-)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
                "bicarbonate": {"label": "Bicarbonate (HCO3-)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
            }
        },
        
        # LIPID PROFILE
        "LIPID_PROFILE": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "total_cholesterol": {"label": "Total Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "hdl_cholesterol": {"label": "HDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "ldl_cholesterol": {"label": "LDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "triglycerides": {"label": "Triglycerides", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            }
        },
        
        # OGTT
        "OGTT": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "fasting_glucose": {"label": "Fasting Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "1hr_glucose": {"label": "1 Hour Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "2hr_glucose": {"label": "2 Hour Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
            }
        },
        
        # FBS/RBS
        "FBS": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "glucose_value": {"label": "Fasting Blood Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
            }
        },
        "RBS": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "glucose_value": {"label": "Random Blood Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
            }
        },
        
        # HbA1c
        "HbA1c": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "hba1c_value": {"label": "HbA1c", "type": "numeric", "unit": "%", "decimals": 1},
            }
        },
        
        # IRON STUDIES
        "IRON_STUDIES": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "serum_iron": {"label": "Serum Iron", "type": "numeric", "unit": "μmol/L", "decimals": 1},
                "tibc": {"label": "TIBC", "type": "numeric", "unit": "μmol/L", "decimals": 0},
                "ferritin": {"label": "Ferritin", "type": "numeric", "unit": "ng/mL", "decimals": 0},
                "transferrin_sat": {"label": "Transferrin Saturation", "type": "numeric", "unit": "%", "decimals": 0},
            }
        },
        
        # CALCIUM
        "CALCIUM": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "calcium_value": {"label": "Serum Calcium", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            }
        },
        
        # MAGNESIUM
        "MAGNESIUM": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "magnesium_value": {"label": "Serum Magnesium", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            }
        },
        
        # PHOSPHATE
        "PHOSPHATE": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "phosphate_value": {"label": "Serum Phosphate", "type": "numeric", "unit": "mmol/L", "decimals": 2},
            }
        },
        
        # URIC ACID
        "URIC_ACID": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "uric_acid_value": {"label": "Uric Acid", "type": "numeric", "unit": "μmol/L", "decimals": 0},
            }
        },
        
        # AMYLASE
        "AMYLASE": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "amylase_value": {"label": "Serum Amylase", "type": "numeric", "unit": "U/L", "decimals": 0},
            }
        },
        
        # LIPASE
        "LIPASE": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "lipase_value": {"label": "Serum Lipase", "type": "numeric", "unit": "U/L", "decimals": 0},
            }
        },
        
        # CK / CK-MB
        "CK": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "ck_value": {"label": "Creatine Kinase (CK)", "type": "numeric", "unit": "U/L", "decimals": 0},
            }
        },
        "CK_MB": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "ckmb_value": {"label": "CK-MB", "type": "numeric", "unit": "U/L", "decimals": 0},
            }
        },
        
        # LDH
        "LDH": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "ldh_value": {"label": "LDH", "type": "numeric", "unit": "U/L", "decimals": 0},
            }
        },
        
        # TROPONIN
        "TROPONIN": {
            "discipline": "CARDIOLOGY",
            "fields": {
                "troponin_qual": {"label": "Troponin (Qualitative)", "type": "choice",
                    "options": ["Negative", "Positive"]},
                "troponin_quant": {"label": "Troponin I/T (Quantitative)", "type": "numeric", "unit": "ng/mL", "decimals": 3},
            }
        },
        
        # BNP
        "BNP": {
            "discipline": "CARDIOLOGY",
            "fields": {
                "bnp_value": {"label": "BNP", "type": "numeric", "unit": "pg/mL", "decimals": 0},
            }
        },
        
        # GFR
        "GFR": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "gfr_value": {"label": "eGFR", "type": "numeric", "unit": "mL/min/1.73m²", "decimals": 0},
                "creatinine_value": {"label": "Serum Creatinine", "type": "numeric", "unit": "μmol/L", "decimals": 0},
            }
        },
        
        # HORMONES
        "TSH": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "tsh_value": {"label": "TSH", "type": "numeric", "unit": "mIU/L", "decimals": 2},
            }
        },
        "FT3": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "ft3_value": {"label": "Free T3", "type": "numeric", "unit": "pmol/L", "decimals": 2},
            }
        },
        "FT4": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "ft4_value": {"label": "Free T4", "type": "numeric", "unit": "pmol/L", "decimals": 2},
            }
        },
        "TESTOSTERONE": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "testosterone_value": {"label": "Testosterone", "type": "numeric", "unit": "nmol/L", "decimals": 1},
            }
        },
        "FSH": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "fsh_value": {"label": "FSH", "type": "numeric", "unit": "IU/L", "decimals": 1},
            }
        },
        "LH": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "lh_value": {"label": "LH", "type": "numeric", "unit": "IU/L", "decimals": 1},
            }
        },
        "PROGESTERONE": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "progesterone_value": {"label": "Progesterone", "type": "numeric", "unit": "nmol/L", "decimals": 1},
            }
        },
        "ESTRADIOL": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "estradiol_value": {"label": "Estradiol (E2)", "type": "numeric", "unit": "pmol/L", "decimals": 0},
            }
        },
        "PROLACTIN": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "prolactin_value": {"label": "Prolactin", "type": "numeric", "unit": "mIU/L", "decimals": 0},
            }
        },
        "CORTISOL": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "cortisol_value": {"label": "Cortisol", "type": "numeric", "unit": "nmol/L", "decimals": 0},
            }
        },
        "DHEA": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "dhea_value": {"label": "DHEA-S", "type": "numeric", "unit": "μmol/L", "decimals": 1},
            }
        },
        "GH": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "gh_value": {"label": "Growth Hormone", "type": "numeric", "unit": "mIU/L", "decimals": 1},
            }
        },
        "PSA": {
            "discipline": "ENDOCRINOLOGY",
            "fields": {
                "psa_value": {"label": "PSA", "type": "numeric", "unit": "ng/mL", "decimals": 2},
            }
        },
        
        # SEROLOGY - INFECTIOUS
        "HIV_SCREEN": {
            "discipline": "SEROLOGY",
            "fields": {
                "hiv_result": {"label": "HIV Result", "type": "choice",
                    "options": ["Non-Reactive", "Reactive", "Indeterminate"]},
                "kit_name": {"label": "Kit Name", "type": "text"},
            }
        },
        "HBSAG": {
            "discipline": "SEROLOGY",
            "fields": {
                "hbsag_result": {"label": "HBsAg", "type": "choice",
                    "options": ["Negative", "Positive", "Indeterminate"]},
            }
        },
        "HBSAB": {
            "discipline": "SEROLOGY",
            "fields": {
                "hbsab_result": {"label": "Anti-HBs", "type": "choice",
                    "options": ["Negative", "Positive", "Indeterminate"]},
            }
        },
        "HBcAB_Total": {
            "discipline": "SEROLOGY",
            "fields": {
                "hbcab_result": {"label": "HBcAb (Total)", "type": "choice",
                    "options": ["Negative", "Positive"]},
            }
        },
        "HCV": {
            "discipline": "SEROLOGY",
            "fields": {
                "hcv_result": {"label": "HCV Antibody", "type": "choice",
                    "options": ["Negative", "Positive", "Indeterminate"]},
            }
        },
        "VDRL": {
            "discipline": "SEROLOGY",
            "fields": {
                "vdrl_result": {"label": "VDRL", "type": "choice",
                    "options": ["Non-Reactive", "Reactive", "Weakly Reactive"]},
                "vdrl_titer": {"label": "VDRL Titer", "type": "text"},
            }
        },
        "TPHA": {
            "discipline": "SEROLOGY",
            "fields": {
                "tpha_result": {"label": "TPHA", "type": "choice",
                    "options": ["Negative", "Positive"]},
            }
        },
        "WIDAL": {
            "discipline": "SEROLOGY",
            "fields": {
                "widal_to": {"label": "Widal TO", "type": "choice",
                    "options": ["<1:20", "1:20", "1:40", "1:80", "1:160", "1:320", ">1:320"]},
                "widal_th": {"label": "Widal TH", "type": "choice",
                    "options": ["<1:20", "1:20", "1:40", "1:80", "1:160", "1:320", ">1:320"]},
                "widal_po": {"label": "Widal PO", "type": "choice",
                    "options": ["<1:20", "1:20", "1:40", "1:80", "1:160", "1:320", ">1:320"]},
                "widal_ph": {"label": "Widal PH", "type": "choice",
                    "options": ["<1:20", "1:20", "1:40", "1:80", "1:160", "1:320", ">1:320"]},
            }
        },
        "GONORRHOEA": {
            "discipline": "SEROLOGY",
            "fields": {
                "gonorrhoea_result": {"label": "Gonorrhoea", "type": "choice",
                    "options": ["Negative", "Positive"]},
            }
        },
        "CHLAMYDIA": {
            "discipline": "SEROLOGY",
            "fields": {
                "chlamydia_result": {"label": "Chlamydia IgG", "type": "choice",
                    "options": ["Negative", "Positive"]},
            }
        },
        "HPYLORI": {
            "discipline": "SEROLOGY",
            "fields": {
                "hpylori_result": {"label": "H. pylori", "type": "choice",
                    "options": ["Negative", "Positive"]},
            }
        },
        "PREGNANCY_TEST": {
            "discipline": "SEROLOGY",
            "fields": {
                "pregnancy_result": {"label": "Pregnancy Test", "type": "choice",
                    "options": ["Negative", "Positive"]},
            }
        },
        "BHCG_QUANT": {
            "discipline": "SEROLOGY",
            "fields": {
                "bhcg_value": {"label": "β-HCG", "type": "numeric", "unit": "IU/L", "decimals": 0},
            }
        },
        "AFP": {
            "discipline": "ONCOLOGY",
            "fields": {
                "afp_result": {"label": "AFP", "type": "choice",
                    "options": ["Normal", "Elevated"]},
                "afp_value": {"label": "AFP Value", "type": "numeric", "unit": "ng/mL", "decimals": 1},
            }
        },
        
        # VIROLOGY
        "HIV_VL": {
            "discipline": "VIROLOGY",
            "fields": {
                "hiv_vl_value": {"label": "HIV Viral Load", "type": "numeric", "unit": "copies/mL", "decimals": 0},
                "hiv_vl_log": {"label": "HIV VL (log)", "type": "numeric", "unit": "log10", "decimals": 2},
            }
        },
        "HBV_VL": {
            "discipline": "VIROLOGY",
            "fields": {
                "hbv_vl_value": {"label": "HBV Viral Load", "type": "numeric", "unit": "IU/mL", "decimals": 0},
            }
        },
        "HCV_VL": {
            "discipline": "VIROLOGY",
            "fields": {
                "hcv_vl_value": {"label": "HCV Viral Load", "type": "numeric", "unit": "IU/mL", "decimals": 0},
            }
        },
        "CD4": {
            "discipline": "IMMUNOLOGY",
            "fields": {
                "cd4_count": {"label": "CD4 Count", "type": "numeric", "unit": "cells/μL", "decimals": 0},
                "cd4_percentage": {"label": "CD4 %", "type": "numeric", "unit": "%", "decimals": 1},
            }
        },
        
        # INFLAMMATORY MARKERS
        "CRP": {
            "discipline": "IMMUNOLOGY",
            "fields": {
                "crp_value": {"label": "CRP", "type": "numeric", "unit": "mg/L", "decimals": 1},
            }
        },
        "ASO": {
            "discipline": "IMMUNOLOGY",
            "fields": {
                "aso_value": {"label": "ASO Titer", "type": "numeric", "unit": "IU/mL", "decimals": 0},
            }
        },
        "RA_FACTOR": {
            "discipline": "IMMUNOLOGY",
            "fields": {
                "ra_result": {"label": "Rheumatoid Factor", "type": "choice",
                    "options": ["Negative", "Positive"]},
                "ra_titer": {"label": "RA Titer", "type": "numeric", "unit": "IU/mL", "decimals": 0},
            }
        },
        
        # BODY FLUIDS
        "CSF_BIOCHEM": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "csf_appearance": {"label": "Appearance", "type": "text"},
                "csf_glucose": {"label": "CSF Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "csf_protein": {"label": "CSF Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
                "csf_rbc": {"label": "RBC Count", "type": "numeric", "unit": "/μL", "decimals": 0},
                "csf_wbc": {"label": "WBC Count", "type": "numeric", "unit": "/μL", "decimals": 0},
                "csf_lymphocytes": {"label": "Lymphocytes", "type": "numeric", "unit": "%", "decimals": 0},
                "csf_neutrophils": {"label": "Neutrophils", "type": "numeric", "unit": "%", "decimals": 0},
            }
        },
        "ASCITIC_FLUID": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "ascitic_appearance": {"label": "Appearance", "type": "text"},
                "ascitic_glucose": {"label": "Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "ascitic_protein": {"label": "Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
                "ascitic_rbc": {"label": "RBC Count", "type": "numeric", "unit": "/μL", "decimals": 0},
                "ascitic_wbc": {"label": "WBC Count", "type": "numeric", "unit": "/μL", "decimals": 0},
                "ascitic_lymphocytes": {"label": "Lymphocytes", "type": "numeric", "unit": "%", "decimals": 0},
            }
        },
        "PLEURAL_FLUID": {
            "discipline": "BIOCHEMISTRY",
            "fields": {
                "pleural_appearance": {"label": "Appearance", "type": "text"},
                "pleural_glucose": {"label": "Glucose", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "pleural_protein": {"label": "Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
                "pleural_rbc": {"label": "RBC Count", "type": "numeric", "unit": "/μL", "decimals": 0},
                "pleural_wbc": {"label": "WBC Count", "type": "numeric", "unit": "/μL", "decimals": 0},
            }
        },
        
        # CULTURE & SENSITIVITY (Generic template for all C/S)
        "CS_BLOOD": {
            "discipline": "MICROBIOLOGY",
            "fields": {
                "organism": {"label": "Organism Isolated", "type": "text"},
                "gram_stain": {"label": "Gram Stain", "type": "text"},
                "sensitivity_1": {"label": "Sensitivity 1", "type": "choice",
                    "options": ["Sensitive", "Resistant", "Intermediate"]},
                "sensitivity_2": {"label": "Sensitivity 2", "type": "choice",
                    "options": ["Sensitive", "Resistant", "Intermediate"]},
                "sensitivity_3": {"label": "Sensitivity 3", "type": "choice",
                    "options": ["Sensitive", "Resistant", "Intermediate"]},
                "micrologist_comment": {"label": "Microbiologist Comment", "type": "text", "multiline": True},
            }
        },
    }


# =============================================================================
# REFERENCE RANGES - Ghana Standards
# =============================================================================

def get_reference_ranges_definition():
    """Return Ghana-standard reference ranges with age and sex logic."""
    ranges = []
    
    # Age group conversions (days)
    NEONATE_MAX = 28       # 0-28 days
    INFANT_MAX = 365       # 1-12 months
    TODDLER_MAX = 1095     # 1-3 years
    CHILD_MAX = 4745       # 3-12 years  
    ADOLESCENT_MAX = 6570  # 12-18 years
    ADULT_MAX = 25550      # 18-70 years
    ELDERLY_MAX = 36500    # 70-100 years
    
    # Helper to convert years to days
    def years_to_days(years):
        return years * 365
    
    # ========== HAEMATOLOGY ==========
    
    # Haemoglobin (Hb) - g/dL
    ranges.extend([
        # Adult Male (18-70)
        {"field_code": "hb", "test_code": "HB", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("13.0"), "normal_max": Decimal("17.0"), 
         "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Adult Female (18-70)
        {"field_code": "hb", "test_code": "HB", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("12.0"), "normal_max": Decimal("15.0"), 
         "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Adolescent (12-18)
        {"field_code": "hb", "test_code": "HB", "sex": "ANY", "age_min": 12, "age_max": 18,
         "normal_min": Decimal("12.0"), "normal_max": Decimal("16.0"), 
         "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Child (5-12)
        {"field_code": "hb", "test_code": "HB", "sex": "ANY", "age_min": 5, "age_max": 12,
         "normal_min": Decimal("11.5"), "normal_max": Decimal("14.5"), 
         "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Toddler (1-5)
        {"field_code": "hb", "test_code": "HB", "sex": "ANY", "age_min": 1, "age_max": 5,
         "normal_min": Decimal("11.0"), "normal_max": Decimal("14.0"), 
         "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Infant (1-12 months)
        {"field_code": "hb", "test_code": "HB", "sex": "ANY", "age_min": 0, "age_max": 1,
         "normal_min": Decimal("9.5"), "normal_max": Decimal("13.0"), 
         "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        # Neonate (0-28 days)
        {"field_code": "hb", "test_code": "HB", "sex": "ANY", "age_min": 0, "age_max": 0,
         "normal_min": Decimal("14.5"), "normal_max": Decimal("22.5"), 
         "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"},
    ])
    
    # PCV/HCT - %
    ranges.extend([
        {"field_code": "hct", "test_code": "FBC", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("36"), "normal_max": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct", "test_code": "FBC", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("34"), "normal_max": Decimal("46"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("32"), "normal_max": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
    ])
    
    # RBC Count - x10^12/L
    ranges.extend([
        {"field_code": "rbc_count", "test_code": "FBC", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("4.5"), "normal_max": Decimal("6.5"), "unit": "x10^12/L"},
        {"field_code": "rbc_count", "test_code": "FBC", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("3.8"), "normal_max": Decimal("5.8"), "unit": "x10^12/L"},
        {"field_code": "rbc_count", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("3.8"), "normal_max": Decimal("6.0"), "unit": "x10^12/L"},
    ])
    
    # WBC Count - x10^9/L
    ranges.extend([
        {"field_code": "wbc_count", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("4.0"), "normal_max": Decimal("11.0"), 
         "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10^9/L"},
    ])
    
    # Platelet Count - x10^9/L
    ranges.extend([
        {"field_code": "platelet_count", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("150"), "normal_max": Decimal("450"), 
         "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "x10^9/L"},
    ])
    
    # MCV - fL
    ranges.extend([
        {"field_code": "mcv", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("80"), "normal_max": Decimal("100"), "unit": "fL"},
    ])
    
    # MCH - pg
    ranges.extend([
        {"field_code": "mch", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("27"), "normal_max": Decimal("34"), "unit": "pg"},
    ])
    
    # MCHC - g/dL
    ranges.extend([
        {"field_code": "mchc", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("32"), "normal_max": Decimal("36"), "unit": "g/dL"},
    ])
    
    # Neutrophils - %
    ranges.extend([
        {"field_code": "neutrophils", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("40"), "normal_max": Decimal("75"), "unit": "%"},
    ])
    
    # Lymphocytes - %
    ranges.extend([
        {"field_code": "lymphocytes", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("20"), "normal_max": Decimal("50"), "unit": "%"},
    ])
    
    # Monocytes - %
    ranges.extend([
        {"field_code": "monocytes", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("2"), "normal_max": Decimal("10"), "unit": "%"},
    ])
    
    # Eosinophils - %
    ranges.extend([
        {"field_code": "eosinophils", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("1"), "normal_max": Decimal("6"), "unit": "%"},
    ])
    
    # Basophils - %
    ranges.extend([
        {"field_code": "basophils", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("2"), "unit": "%"},
    ])
    
    # Reticulocytes - %
    ranges.extend([
        {"field_code": "retic", "test_code": "FBC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0.5"), "normal_max": Decimal("2.5"), "unit": "%"},
    ])
    
    # ESR - mm/hr
    ranges.extend([
        {"field_code": "esr_value", "test_code": "ESR", "sex": "M", "age_min": 18, "age_max": 50,
         "normal_min": Decimal("0"), "normal_max": Decimal("15"), "unit": "mm/hr"},
        {"field_code": "esr_value", "test_code": "ESR", "sex": "M", "age_min": 50, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("20"), "unit": "mm/hr"},
        {"field_code": "esr_value", "test_code": "ESR", "sex": "F", "age_min": 18, "age_max": 50,
         "normal_min": Decimal("0"), "normal_max": Decimal("20"), "unit": "mm/hr"},
        {"field_code": "esr_value", "test_code": "ESR", "sex": "F", "age_min": 50, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("30"), "unit": "mm/hr"},
        {"field_code": "esr_value", "test_code": "ESR", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("0"), "normal_max": Decimal("10"), "unit": "mm/hr"},
    ])
    
    # Reticulocyte Count - %
    ranges.extend([
        {"field_code": "retic_count", "test_code": "RETIC", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0.5"), "normal_max": Decimal("2.5"), "unit": "%"},
    ])
    
    # ========== BIOCHEMISTRY ==========
    
    # Fasting Blood Sugar - mmol/L
    ranges.extend([
        {"field_code": "glucose_value", "test_code": "FBS", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("3.9"), "normal_max": Decimal("6.1"),
         "critical_low": Decimal("2.2"), "critical_high": Decimal("27.8"), "unit": "mmol/L"},
    ])
    
    # Random Blood Sugar - mmol/L
    ranges.extend([
        {"field_code": "glucose_value", "test_code": "RBS", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("3.9"), "normal_max": Decimal("7.8"),
         "critical_low": Decimal("2.2"), "critical_high": Decimal("27.8"), "unit": "mmol/L"},
    ])
    
    # OGTT - mmol/L
    ranges.extend([
        {"field_code": "fasting_glucose", "test_code": "OGTT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("3.9"), "normal_max": Decimal("6.1"), "unit": "mmol/L"},
        {"field_code": "1hr_glucose", "test_code": "OGTT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("10.0"), "unit": "mmol/L"},
        {"field_code": "2hr_glucose", "test_code": "OGTT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("7.8"), "unit": "mmol/L"},
    ])
    
    # HbA1c - %
    ranges.extend([
        {"field_code": "hba1c_value", "test_code": "HbA1c", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("4.0"), "normal_max": Decimal("6.0"), 
         "critical_high": Decimal("15.0"), "unit": "%"},
    ])
    
    # LFT - Various
    ranges.extend([
        # Total Bilirubin - μmol/L
        {"field_code": "total_bilirubin", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("3.4"), "normal_max": Decimal("20.5"), "unit": "μmol/L"},
        # Direct Bilirubin
        {"field_code": "direct_bilirubin", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("8.6"), "unit": "μmol/L"},
        # ALT (SGPT) - U/L
        {"field_code": "alt", "test_code": "LFT", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("10"), "normal_max": Decimal("40"), "unit": "U/L"},
        {"field_code": "alt", "test_code": "LFT", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("7"), "normal_max": Decimal("35"), "unit": "U/L"},
        {"field_code": "alt", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("5"), "normal_max": Decimal("30"), "unit": "U/L"},
        # AST (SGOT) - U/L
        {"field_code": "ast", "test_code": "LFT", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("10"), "normal_max": Decimal("40"), "unit": "U/L"},
        {"field_code": "ast", "test_code": "LFT", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("9"), "normal_max": Decimal("32"), "unit": "U/L"},
        {"field_code": "ast", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("8"), "normal_max": Decimal("35"), "unit": "U/L"},
        # ALP - U/L
        {"field_code": "alp", "test_code": "LFT", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("44"), "normal_max": Decimal("147"), "unit": "U/L"},
        {"field_code": "alp", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("100"), "normal_max": Decimal("350"), "unit": "U/L"},
        # GGT - U/L
        {"field_code": "ggt", "test_code": "LFT", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("9"), "normal_max": Decimal("48"), "unit": "U/L"},
        {"field_code": "ggt", "test_code": "LFT", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("4"), "normal_max": Decimal("32"), "unit": "U/L"},
        # Total Protein - g/L
        {"field_code": "total_protein", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("60"), "normal_max": Decimal("80"), "unit": "g/L"},
        # Albumin - g/L
        {"field_code": "albumin", "test_code": "LFT", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("35"), "normal_max": Decimal("50"), "unit": "g/L"},
    ])
    
    # RFT - mmol/L, μmol/L
    ranges.extend([
        # Urea - mmol/L
        {"field_code": "urea", "test_code": "RFT", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("2.9"), "normal_max": Decimal("8.2"), "unit": "mmol/L"},
        {"field_code": "urea", "test_code": "RFT", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("1.8"), "normal_max": Decimal("6.5"), "unit": "mmol/L"},
        # Creatinine - μmol/L
        {"field_code": "creatinine", "test_code": "RFT", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("62"), "normal_max": Decimal("106"), "unit": "μmol/L"},
        {"field_code": "creatinine", "test_code": "RFT", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("44"), "normal_max": Decimal("80"), "unit": "μmol/L"},
        {"field_code": "creatinine", "test_code": "RFT", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("20"), "normal_max": Decimal("70"), "unit": "μmol/L"},
        # Uric Acid - μmol/L
        {"field_code": "uric_acid", "test_code": "RFT", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("200"), "normal_max": Decimal("430"), "unit": "μmol/L"},
        {"field_code": "uric_acid", "test_code": "RFT", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("140"), "normal_max": Decimal("360"), "unit": "μmol/L"},
        # eGFR - mL/min/1.73m²
        {"field_code": "egfr", "test_code": "RFT", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("90"), "normal_max": Decimal("120"), "unit": "mL/min/1.73m²"},
    ])
    
    # Electrolytes - mmol/L
    ranges.extend([
        {"field_code": "sodium", "test_code": "ELECTROLYTES", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("136"), "normal_max": Decimal("145"), 
         "critical_low": Decimal("120"), "critical_high": Decimal("160"), "unit": "mmol/L"},
        {"field_code": "potassium", "test_code": "ELECTROLYTES", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("3.5"), "normal_max": Decimal("5.0"), 
         "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mmol/L"},
        {"field_code": "chloride", "test_code": "ELECTROLYTES", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("98"), "normal_max": Decimal("106"), "unit": "mmol/L"},
        {"field_code": "bicarbonate", "test_code": "ELECTROLYTES", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("22"), "normal_max": Decimal("29"), "unit": "mmol/L"},
    ])
    
    # Lipid Profile - mmol/L
    ranges.extend([
        {"field_code": "total_cholesterol", "test_code": "LIPID_PROFILE", "sex": "ANY", "age_min": 18, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("5.2"), "unit": "mmol/L"},
        {"field_code": "hdl_cholesterol", "test_code": "LIPID_PROFILE", "sex": "M", "age_min": 18, "age_max": 100,
         "normal_min": Decimal("1.0"), "normal_max": Decimal("2.2"), "unit": "mmol/L"},
        {"field_code": "hdl_cholesterol", "test_code": "LIPID_PROFILE", "sex": "F", "age_min": 18, "age_max": 100,
         "normal_min": Decimal("1.2"), "normal_max": Decimal("2.7"), "unit": "mmol/L"},
        {"field_code": "ldl_cholesterol", "test_code": "LIPID_PROFILE", "sex": "ANY", "age_min": 18, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("3.4"), "unit": "mmol/L"},
        {"field_code": "triglycerides", "test_code": "LIPID_PROFILE", "sex": "ANY", "age_min": 18, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("1.7"), "unit": "mmol/L"},
    ])
    
    # Calcium - mmol/L
    ranges.extend([
        {"field_code": "calcium_value", "test_code": "CALCIUM", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("2.10"), "normal_max": Decimal("2.55"),
         "critical_low": Decimal("1.5"), "critical_high": Decimal("3.0"), "unit": "mmol/L"},
    ])
    
    # Magnesium - mmol/L
    ranges.extend([
        {"field_code": "magnesium_value", "test_code": "MAGNESIUM", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0.70"), "normal_max": Decimal("1.10"), "unit": "mmol/L"},
    ])
    
    # Phosphate - mmol/L
    ranges.extend([
        {"field_code": "phosphate_value", "test_code": "PHOSPHATE", "sex": "ANY", "age_min": 18, "age_max": 100,
         "normal_min": Decimal("0.81"), "normal_max": Decimal("1.45"), "unit": "mmol/L"},
        {"field_code": "phosphate_value", "test_code": "PHOSPHATE", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("1.10"), "normal_max": Decimal("2.0"), "unit": "mmol/L"},
    ])
    
    # Uric Acid standalone - μmol/L
    ranges.extend([
        {"field_code": "uric_acid_value", "test_code": "URIC_ACID", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("200"), "normal_max": Decimal("430"), "unit": "μmol/L"},
        {"field_code": "uric_acid_value", "test_code": "URIC_ACID", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("140"), "normal_max": Decimal("360"), "unit": "μmol/L"},
    ])
    
    # Amylase - U/L
    ranges.extend([
        {"field_code": "amylase_value", "test_code": "AMYLASE", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("28"), "normal_max": Decimal("100"), "unit": "U/L"},
    ])
    
    # Lipase - U/L
    ranges.extend([
        {"field_code": "lipase_value", "test_code": "LIPASE", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("13"), "normal_max": Decimal("60"), "unit": "U/L"},
    ])
    
    # CK - U/L
    ranges.extend([
        {"field_code": "ck_value", "test_code": "CK", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("38"), "normal_max": Decimal("174"), "unit": "U/L"},
        {"field_code": "ck_value", "test_code": "CK", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("26"), "normal_max": Decimal("140"), "unit": "U/L"},
    ])
    
    # CK-MB - U/L
    ranges.extend([
        {"field_code": "ckmb_value", "test_code": "CK_MB", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("25"), "unit": "U/L"},
    ])
    
    # LDH - U/L
    ranges.extend([
        {"field_code": "ldh_value", "test_code": "LDH", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("140"), "normal_max": Decimal("280"), "unit": "U/L"},
    ])
    
    # ========== ENDOCRINE / HORMONES ==========
    
    # TSH - mIU/L
    ranges.extend([
        {"field_code": "tsh_value", "test_code": "TSH", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("0.4"), "normal_max": Decimal("4.0"), "unit": "mIU/L"},
        {"field_code": "tsh_value", "test_code": "TSH", "sex": "ANY", "age_min": 0, "age_max": 18,
         "normal_min": Decimal("0.7"), "normal_max": Decimal("6.0"), "unit": "mIU/L"},
    ])
    
    # Free T3 - pmol/L
    ranges.extend([
        {"field_code": "ft3_value", "test_code": "FT3", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("3.1"), "normal_max": Decimal("6.8"), "unit": "pmol/L"},
    ])
    
    # Free T4 - pmol/L
    ranges.extend([
        {"field_code": "ft4_value", "test_code": "FT4", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("12"), "normal_max": Decimal("22"), "unit": "pmol/L"},
    ])
    
    # Testosterone - nmol/L
    ranges.extend([
        {"field_code": "testosterone_value", "test_code": "TESTOSTERONE", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("8.6"), "normal_max": Decimal("29.0"), "unit": "nmol/L"},
        {"field_code": "testosterone_value", "test_code": "TESTOSTERONE", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("0.5"), "normal_max": Decimal("2.6"), "unit": "nmol/L"},
    ])
    
    # FSH - IU/L
    ranges.extend([
        {"field_code": "fsh_value", "test_code": "FSH", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("1.5"), "normal_max": Decimal("12.4"), "unit": "IU/L"},
        {"field_code": "fsh_value", "test_code": "FSH", "sex": "F", "age_min": 18, "age_max": 50,
         "normal_min": Decimal("3.5"), "normal_max": Decimal("12.5"), "unit": "IU/L"},
        {"field_code": "fsh_value", "test_code": "FSH", "sex": "F", "age_min": 50, "age_max": 70,
         "normal_min": Decimal("25.8"), "normal_max": Decimal("134.8"), "unit": "IU/L"},
    ])
    
    # LH - IU/L
    ranges.extend([
        {"field_code": "lh_value", "test_code": "LH", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("1.7"), "normal_max": Decimal("8.6"), "unit": "IU/L"},
        {"field_code": "lh_value", "test_code": "LH", "sex": "F", "age_min": 18, "age_max": 50,
         "normal_min": Decimal("2.4"), "normal_max": Decimal("12.6"), "unit": "IU/L"},
        {"field_code": "lh_value", "test_code": "LH", "sex": "F", "age_min": 50, "age_max": 70,
         "normal_min": Decimal("14.2"), "normal_max": Decimal("52.3"), "unit": "IU/L"},
    ])
    
    # Progesterone - nmol/L
    ranges.extend([
        {"field_code": "progesterone_value", "test_code": "PROGESTERONE", "sex": "F", "age_min": 18, "age_max": 50,
         "normal_min": Decimal("0.3"), "normal_max": Decimal("25.6"), "unit": "nmol/L"},
    ])
    
    # Estradiol - pmol/L
    ranges.extend([
        {"field_code": "estradiol_value", "test_code": "ESTRADIOL", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("50"), "normal_max": Decimal("200"), "unit": "pmol/L"},
        {"field_code": "estradiol_value", "test_code": "ESTRADIOL", "sex": "F", "age_min": 18, "age_max": 50,
         "normal_min": Decimal("70"), "normal_max": Decimal("600"), "unit": "pmol/L"},
    ])
    
    # Prolactin - mIU/L
    ranges.extend([
        {"field_code": "prolactin_value", "test_code": "PROLACTIN", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("86"), "normal_max": Decimal("324"), "unit": "mIU/L"},
        {"field_code": "prolactin_value", "test_code": "PROLACTIN", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("102"), "normal_max": Decimal("496"), "unit": "mIU/L"},
    ])
    
    # Cortisol - nmol/L (morning sample)
    ranges.extend([
        {"field_code": "cortisol_value", "test_code": "CORTISOL", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("171"), "normal_max": Decimal("536"), "unit": "nmol/L"},
    ])
    
    # PSA - ng/mL
    ranges.extend([
        {"field_code": "psa_value", "test_code": "PSA", "sex": "M", "age_min": 40, "age_max": 50,
         "normal_min": Decimal("0"), "normal_max": Decimal("2.5"), "unit": "ng/mL"},
        {"field_code": "psa_value", "test_code": "PSA", "sex": "M", "age_min": 50, "age_max": 60,
         "normal_min": Decimal("0"), "normal_max": Decimal("3.5"), "unit": "ng/mL"},
        {"field_code": "psa_value", "test_code": "PSA", "sex": "M", "age_min": 60, "age_max": 70,
         "normal_min": Decimal("0"), "normal_max": Decimal("4.5"), "unit": "ng/mL"},
        {"field_code": "psa_value", "test_code": "PSA", "sex": "M", "age_min": 70, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("6.5"), "unit": "ng/mL"},
    ])
    
    # ========== IRON STUDIES ==========
    
    # Serum Iron - μmol/L
    ranges.extend([
        {"field_code": "serum_iron", "test_code": "IRON_STUDIES", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("11.6"), "normal_max": Decimal("31.3"), "unit": "μmol/L"},
        {"field_code": "serum_iron", "test_code": "IRON_STUDIES", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("9.0"), "normal_max": Decimal("30.4"), "unit": "μmol/L"},
    ])
    
    # TIBC - μmol/L
    ranges.extend([
        {"field_code": "tibc", "test_code": "IRON_STUDIES", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("44.8"), "normal_max": Decimal("73.4"), "unit": "μmol/L"},
    ])
    
    # Ferritin - ng/mL
    ranges.extend([
        {"field_code": "ferritin", "test_code": "IRON_STUDIES", "sex": "M", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("30"), "normal_max": Decimal("400"), "unit": "ng/mL"},
        {"field_code": "ferritin", "test_code": "IRON_STUDIES", "sex": "F", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("13"), "normal_max": Decimal("150"), "unit": "ng/mL"},
    ])
    
    # ========== INFLAMMATORY MARKERS ==========
    
    # CRP - mg/L
    ranges.extend([
        {"field_code": "crp_value", "test_code": "CRP", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("5.0"), "unit": "mg/L"},
    ])
    
    # ASO - IU/mL
    ranges.extend([
        {"field_code": "aso_value", "test_code": "ASO", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0"), "normal_max": Decimal("200"), "unit": "IU/mL"},
    ])
    
    # ========== VIROLOGY ==========
    
    # CD4 Count - cells/μL
    ranges.extend([
        {"field_code": "cd4_count", "test_code": "CD4", "sex": "ANY", "age_min": 18, "age_max": 70,
         "normal_min": Decimal("500"), "normal_max": Decimal("1500"), "unit": "cells/μL"},
    ])
    
    # ========== URINE ==========
    
    # Urine pH
    ranges.extend([
        {"field_code": "ph", "test_code": "URINE_RE", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("4.5"), "normal_max": Decimal("8.0"), "unit": ""},
    ])
    
    # Urine Specific Gravity
    ranges.extend([
        {"field_code": "specific_gravity", "test_code": "URINE_RE", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("1.005"), "normal_max": Decimal("1.030"), "unit": ""},
    ])
    
    # ========== CSF ==========
    
    # CSF Glucose - mmol/L
    ranges.extend([
        {"field_code": "csf_glucose", "test_code": "CSF_BIOCHEM", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("2.2"), "normal_max": Decimal("3.9"), "unit": "mmol/L"},
    ])
    
    # CSF Protein - g/L
    ranges.extend([
        {"field_code": "csf_protein", "test_code": "CSF_BIOCHEM", "sex": "ANY", "age_min": 0, "age_max": 100,
         "normal_min": Decimal("0.15"), "normal_max": Decimal("0.45"), "unit": "g/L"},
    ])
    
    return ranges


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def create_lab_tests(db):
    """Create or update lab test catalog records (idempotent)."""
    print("\n=== Creating Lab Test Catalog Records ===")
    
    tests = get_lab_tests_definition()
    created = 0
    skipped = 0
    
    for test_def in tests:
        # Check if test already exists
        result = db.execute(
            text("SELECT id FROM lab_tests WHERE test_code = :code AND is_active = true"),
            {"code": test_def["test_code"]}
        )
        existing = result.fetchone()
        
        if existing:
            # Update existing test but don't overwrite
            skipped += 1
            continue
        
        # Insert new test
        db.execute(text("""
            INSERT INTO lab_tests (
                test_code, test_name, test_category, test_type, specimen_type,
                description, routine_tat, urgent_tat, cost, is_active,
                is_specialized
            ) VALUES (
                :code, :name, :category, :type, :specimen,
                :description, :routine_tat, :urgent_tat, :cost, true,
                :is_specialized
            )
        """), {
            "code": test_def["test_code"],
            "name": test_def["test_name"],
            "category": test_def["test_category"],
            "type": test_def["test_type"],
            "specimen": test_def["specimen_type"],
            "description": test_def.get("description"),
            "routine_tat": test_def.get("routine_tat"),
            "urgent_tat": test_def.get("urgent_tat"),
            "cost": test_def.get("cost"),
            "is_specialized": False,
        })
        created += 1
    
    db.commit()
    print(f"  Created: {created} new tests")
    print(f"  Skipped (existing): {skipped} tests")
    return created + skipped


def create_option_sets(db):
    """Create Ghana-specific option sets (idempotent)."""
    print("\n=== Creating Option Sets ===")
    
    option_sets = [
        ("DIPSTICK_SCALE", '["Negative", "Trace", "+", "++", "+++"]'),
        ("URINE_COLOUR", '["Straw", "Yellow", "Amber", "Red", "Brown", "Other"]'),
        ("URINE_APPEARANCE", '["Clear", "Slightly turbid", "Turbid"]'),
        ("URINE_PROTEIN", '["Negative", "Trace", "+", "++", "+++"]'),
        ("URINE_GLUCOSE", '["Negative", "Trace", "+", "++", "+++"]'),
        ("URINE_KETONES", '["Negative", "Trace", "+", "++", "+++"]'),
        ("URINE_BLOOD", '["Negative", "Trace", "+", "++", "+++"]'),
        ("STOOL_CONSISTENCY", '["Formed", "Semi-formed", "Watery", "Mucoid"]'),
        ("STOOL_COLOUR", '["Brown", "Green", "Black", "Red", "Pale", "Other"]'),
        ("STOOL_OCCULT_BLOOD", '["Negative", "Positive"]'),
        ("ORGANISM_LIST", '["Escherichia coli", "Klebsiella pneumoniae", "Pseudomonas aeruginosa", "Proteus mirabilis", "Enterococcus faecalis", "Staphylococcus aureus", "Staphylococcus epidermidis", "Streptococcus pyogenes", "Streptococcus pneumoniae", "Neisseria gonorrhoeae", "Haemophilus influenzae", "Salmonella spp.", "Shigella spp.", "Vibrio cholerae", "Candida albicans", "Other"]'),
        ("ANTIBIOTIC_LIST", '["Amoxicillin", "Ampicillin", "Azithromycin", "Cefotaxime", "Ceftriaxone", "Ciprofloxacin", "Clindamycin", "Doxycycline", "Erythromycin", "Gentamicin", "Meropenem", "Metronidazole", "Nitrofurantoin", "Penicillin G", "Piperacillin", "Tetracycline", "Trimethoprim-Sulfamethoxazole", "Vancomycin", "Cefuroxime", "Amoxicillin-Clavulanate", "Levofloxacin", "Norfloxacin", "Ofloxacin", "Other"]'),
        ("HIV_KIT_NAMES", '["Determine", "Unigold", "Stat-Pak", "Oral Quick", "First Response", "Other"]'),
        ("BLOOD_GROUP", '["A", "B", "AB", "O"]'),
        ("RH_FACTOR", '["Positive", "Negative"]'),
        ("SICKLING_RESULT", '["Positive", "Negative"]'),
        ("HB_PHENOTYPE", '["AA", "AS", "SS", "SC", "AC", "CC", "Other"]'),
        ("G6PD_RESULT", '["Normal", "Deficient", "Intermediate"]'),
        ("COOMBS_RESULT", '["Positive", "Negative"]'),
        ("MICROSCOPY_HPF", '["0-1", "1-5", "5-10", "10-20", ">20"]'),
        ("MICROSCOPY_LPF", '["0-1", "1-5", "5-10", "10-20", ">20"]'),
        ("MALARIA_RDT", '["Negative", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"]'),
        ("MALARIA_PARASITE", '["None seen", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"]'),
        ("MALARIA_DENSITY", '["<100", "100-500", "500-1000", "1000-5000", ">5000"]'),
        ("HIV_RESULT", '["Non-Reactive", "Reactive", "Indeterminate"]'),
        ("HBSAG_RESULT", '["Negative", "Positive", "Indeterminate"]'),
        ("HCV_RESULT", '["Negative", "Positive", "Indeterminate"]'),
        ("VDRL_RESULT", '["Non-Reactive", "Reactive", "Weakly Reactive"]'),
        ("WIDAL_TITER", '["<1:20", "1:20", "1:40", "1:80", "1:160", "1:320", ">1:320"]'),
        ("HPYLORI_RESULT", '["Negative", "Positive"]'),
        ("PREGNANCY_RESULT", '["Negative", "Positive"]'),
        ("BHCG_RESULT", '["Negative", "Positive", "Equivocal"]'),
        ("AFP_RESULT", '["Normal", "Elevated"]'),
        ("MICROFILARIA_RESULT", '["Not Seen", "Seen"]'),
        ("HVS_EPITHELIAL", '["Few", "Moderate", "Many"]'),
        ("HVS_WBC", '["0-5", "5-10", "10-20", ">20"]'),
        ("HVS_ORGANISMS", '["None", "Trichomonas", "Yeast", "Bacteria", "Mixed"]'),
        ("HVS_YEAST", '["Not Seen", "Seen"]'),
        ("CULTURE_RESULT", '["No Growth", "Mixed Growth", "Contaminated"]'),
        ("SENSITIVITY_RESULT", '["Sensitive", "Resistant", "Intermediate"]'),
    ]
    
    created = 0
    for code, options_json in option_sets:
        result = db.execute(text("SELECT id FROM lab_option_sets WHERE code = :code"), {"code": code})
        if not result.fetchone():
            db.execute(text("INSERT INTO lab_option_sets (code, options_json) VALUES (:code, :options_json)"), 
                     {"code": code, "options_json": options_json})
            created += 1
    
    db.commit()
    print(f"  Created: {created} new option sets")
    return len(option_sets)


def create_lab_templates(db):
    """Create lab template schemas (idempotent)."""
    print("\n=== Creating Lab Templates ===")
    
    templates = get_template_definitions()
    created = 0
    
    for test_code, template_def in templates.items():
        # Check if template already exists
        result = db.execute(
            text("SELECT id FROM lab_templates WHERE name = :name"),
            {"name": f"Lab Test - {test_code}"}
        )
        existing_template = result.fetchone()
        
        # Get test ID
        test_result = db.execute(
            text("SELECT id FROM lab_tests WHERE test_code = :code"),
            {"code": test_code}
        )
        test_row = test_result.fetchone()
        
        if not test_row:
            print(f"  Warning: No test found for {test_code}")
            continue
        
        test_id = test_row[0]
        
        # Build schema JSON
        fields = template_def.get("fields", {})
        schema = {
            "meta": {
                "name": f"Lab Test - {test_code}",
                "discipline": template_def.get("discipline", "HEMATOLOGY"),
                "version": 1,
                "test_code": test_code
            },
            "layout": {
                "sections": [
                    {
                        "id": "main",
                        "title": test_code,
                        "rows": [
                            {
                                "columns": [
                                    {"items": [field_code], "width": 12 // min(len(fields), 3) if fields else 12}
                                    for field_code in list(fields.keys())[:12]
                                ]
                            }
                        ]
                    }
                ]
            },
            "fields": template_def.get("fields", {})
        }
        
        import json
        
        if existing_template:
            # Update existing template schema
            template_id = existing_template[0]
            # Get the latest version
            ver_result = db.execute(
                text("SELECT id, version FROM lab_template_versions WHERE template_id = :tid ORDER BY version DESC LIMIT 1"),
                {"tid": template_id}
            )
            ver_row = ver_result.fetchone()
            if ver_row:
                new_version = ver_row[1] + 1
                version_id = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO lab_template_versions (id, template_id, version, status, schema_json)
                    VALUES (:id, :template_id, :version, 'PUBLISHED', :schema_json)
                """), {"id": version_id, "template_id": template_id, "version": new_version, "schema_json": json.dumps(schema)})
                db.execute(text("""
                    UPDATE lab_templates SET current_version = :version WHERE id = :tid
                """), {"version": new_version, "tid": template_id})
            created += 1
            continue
        
        # Get test ID
        test_result = db.execute(
            text("SELECT id FROM lab_tests WHERE test_code = :code"),
            {"code": test_code}
        )
        test_row = test_result.fetchone()
        
        if not test_row:
            print(f"  Warning: No test found for {test_code}")
            continue
        
        test_id = test_row[0]
        
        # Create template
        template_id = str(uuid.uuid4())
        discipline = template_def.get("discipline", "HEMATOLOGY")
        fields = template_def.get("fields", {})
        
        # Build schema JSON
        schema = {
            "meta": {
                "name": f"Lab Test - {test_code}",
                "discipline": discipline,
                "version": 1,
                "test_code": test_code
            },
            "layout": {
                "sections": [
                    {
                        "id": "main",
                        "title": test_code,
                        "rows": [
                            {
                                "columns": [
                                    {"items": [field_code], "width": 12 // min(len(fields), 3) if fields else 12}
                                    for field_code in list(fields.keys())[:12]
                                ]
                            }
                        ]
                    }
                ]
            },
            "fields": fields
        }
        
        db.execute(text("""
            INSERT INTO lab_templates (id, name, discipline, status, current_version)
            VALUES (:id, :name, :discipline, 'PUBLISHED', 1)
        """), {"id": template_id, "name": f"Lab Test - {test_code}", "discipline": discipline})
        
        # Create version
        version_id = str(uuid.uuid4())
        import json
        db.execute(text("""
            INSERT INTO lab_template_versions (id, template_id, version, status, schema_json)
            VALUES (:id, :template_id, 1, 'PUBLISHED', :schema_json)
        """), {"id": version_id, "template_id": template_id, "schema_json": json.dumps(schema)})
        
        # Link template to test
        db.execute(text("""
            UPDATE lab_tests SET template_id = :template_id WHERE id = :test_id
        """), {"template_id": template_id, "test_id": test_id})
        
        created += 1
    
    db.commit()
    print(f"  Created: {created} templates")
    return created


def create_reference_ranges(db):
    """Create reference ranges with age and sex logic (idempotent)."""
    print("\n=== Creating Reference Ranges ===")
    
    ranges = get_reference_ranges_definition()
    created = 0
    skipped = 0
    
    for range_def in ranges:
        test_code = range_def["test_code"]
        sex = range_def.get("sex", "ANY")
        age_min = range_def.get("age_min", 0)
        age_max = range_def.get("age_max", 100)
        
        # Check if range already exists (using test_code, gender, age)
        gender_val = sex if sex != "ANY" else None
        result = db.execute(text("""
            SELECT id FROM reference_ranges 
            WHERE test_code = :test_code 
            AND (gender = :gender OR (gender IS NULL AND :gender IS NULL))
            AND age_min = :age_min 
            AND age_max = :age_max
            AND is_active = true
        """), {
            "test_code": test_code,
            "gender": gender_val,
            "age_min": age_min,
            "age_max": age_max
        })
        
        if result.fetchone():
            skipped += 1
            continue
        
        # Get test_id
        test_result = db.execute(
            text("SELECT id FROM lab_tests WHERE test_code = :code"),
            {"code": test_code}
        )
        test_row = test_result.fetchone()
        
        if test_row:
            test_id = test_row[0]
        else:
            test_id = None
        
        # Insert range
        db.execute(text("""
            INSERT INTO reference_ranges (
                test_id, test_name, test_code, gender,
                age_min, age_max, normal_min, normal_max,
                critical_low, critical_high, unit, is_active
            ) VALUES (
                :test_id, :test_name, :test_code, :gender,
                :age_min, :age_max, :normal_min, :normal_max,
                :critical_low, :critical_high, :unit, true
            )
        """), {
            "test_id": test_id,
            "test_name": f"Lab Test - {test_code}",
            "test_code": test_code,
            "gender": gender_val,
            "age_min": age_min,
            "age_max": age_max,
            "normal_min": range_def.get("normal_min"),
            "normal_max": range_def.get("normal_max"),
            "critical_low": range_def.get("critical_low"),
            "critical_high": range_def.get("critical_high"),
            "unit": range_def.get("unit"),
        })
        created += 1
    
    db.commit()
    print(f"  Created: {created} reference ranges")
    print(f"  Skipped (existing): {skipped} ranges")
    return created + skipped


def create_lab_reference_ranges(db):
    """Create lab_reference_ranges for template fields (for UI display)."""
    print("\n=== Creating Lab Reference Ranges for Templates ===")
    
    # Define field_code based reference ranges for template fields
    # This maps the template field codes to reference ranges
    field_ranges = [
        # FBC fields
        {"field_code": "hb", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("13.0"), "high": Decimal("17.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("12.0"), "high": Decimal("15.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb", "sex": "ANY", "age_min_days": 0, "age_max_days": 28,
         "low": Decimal("14.5"), "high": Decimal("22.5"), "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"},
        {"field_code": "hct", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("36"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("34"), "high": Decimal("46"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "hct", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570,
         "low": Decimal("32"), "high": Decimal("50"), "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"},
        {"field_code": "rbc_count", "sex": "M", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("4.5"), "high": Decimal("6.5"), "unit": "x10^12/L"},
        {"field_code": "rbc_count", "sex": "F", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("3.8"), "high": Decimal("5.8"), "unit": "x10^12/L"},
        {"field_code": "wbc_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("4.0"), "high": Decimal("11.0"), "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10^9/L"},
        {"field_code": "platelet_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("150"), "high": Decimal("450"), "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "x10^9/L"},
        {"field_code": "mcv", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("80"), "high": Decimal("100"), "unit": "fL"},
        {"field_code": "mch", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("27"), "high": Decimal("34"), "unit": "pg"},
        {"field_code": "mchc", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("32"), "high": Decimal("36"), "unit": "g/dL"},
        {"field_code": "neutrophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("40"), "high": Decimal("75"), "unit": "%"},
        {"field_code": "lymphocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("20"), "high": Decimal("50"), "unit": "%"},
        {"field_code": "monocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("2"), "high": Decimal("10"), "unit": "%"},
        {"field_code": "eosinophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("1"), "high": Decimal("6"), "unit": "%"},
        {"field_code": "basophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("2"), "unit": "%"},
        {"field_code": "retic", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0.5"), "high": Decimal("2.5"), "unit": "%"},
        
        # Biochemistry fields
        {"field_code": "glucose_value", "test_code": "FBS", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("3.9"), "high": Decimal("6.1"), "critical_low": Decimal("2.2"), "critical_high": Decimal("27.8"), "unit": "mmol/L"},
        {"field_code": "glucose_value", "test_code": "RBS", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("3.9"), "high": Decimal("7.8"), "critical_low": Decimal("2.2"), "critical_high": Decimal("27.8"), "unit": "mmol/L"},
        
        # LFT fields
        {"field_code": "total_bilirubin", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("3.4"), "high": Decimal("20.5"), "unit": "μmol/L"},
        {"field_code": "direct_bilirubin", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("8.6"), "unit": "μmol/L"},
        {"field_code": "alt", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("10"), "high": Decimal("40"), "unit": "U/L"},
        {"field_code": "alt", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("7"), "high": Decimal("35"), "unit": "U/L"},
        {"field_code": "ast", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("10"), "high": Decimal("40"), "unit": "U/L"},
        {"field_code": "ast", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("9"), "high": Decimal("32"), "unit": "U/L"},
        {"field_code": "alp", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("44"), "high": Decimal("147"), "unit": "U/L"},
        {"field_code": "ggt", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("9"), "high": Decimal("48"), "unit": "U/L"},
        {"field_code": "ggt", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("4"), "high": Decimal("32"), "unit": "U/L"},
        {"field_code": "total_protein", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("60"), "high": Decimal("80"), "unit": "g/L"},
        {"field_code": "albumin", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("35"), "high": Decimal("50"), "unit": "g/L"},
        
        # RFT fields
        {"field_code": "urea", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("2.9"), "high": Decimal("8.2"), "unit": "mmol/L"},
        {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("62"), "high": Decimal("106"), "unit": "μmol/L"},
        {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("44"), "high": Decimal("80"), "unit": "μmol/L"},
        
        # Electrolytes
        {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("136"), "high": Decimal("145"), "critical_low": Decimal("120"), "critical_high": Decimal("160"), "unit": "mmol/L"},
        {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("3.5"), "high": Decimal("5.0"), "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mmol/L"},
        {"field_code": "chloride", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("98"), "high": Decimal("106"), "unit": "mmol/L"},
        {"field_code": "bicarbonate", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("22"), "high": Decimal("29"), "unit": "mmol/L"},
        
        # Lipid Profile
        {"field_code": "total_cholesterol", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("5.2"), "unit": "mmol/L"},
        {"field_code": "hdl_cholesterol", "sex": "M", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("1.0"), "high": Decimal("2.2"), "unit": "mmol/L"},
        {"field_code": "hdl_cholesterol", "sex": "F", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("1.2"), "high": Decimal("2.7"), "unit": "mmol/L"},
        {"field_code": "ldl_cholesterol", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("3.4"), "unit": "mmol/L"},
        {"field_code": "triglycerides", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("1.7"), "unit": "mmol/L"},
        
        # Thyroid
        {"field_code": "tsh", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("0.4"), "high": Decimal("4.0"), "unit": "mIU/L"},
        {"field_code": "ft3", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("3.1"), "high": Decimal("6.8"), "unit": "pmol/L"},
        {"field_code": "ft4", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("12"), "high": Decimal("22"), "unit": "pmol/L"},
        
        # Hormones
        {"field_code": "testosterone_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("8.6"), "high": Decimal("29.0"), "unit": "nmol/L"},
        {"field_code": "testosterone_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("0.5"), "high": Decimal("2.6"), "unit": "nmol/L"},
        {"field_code": "psa_value", "sex": "M", "age_min_days": 14600, "age_max_days": 18250,
         "low": Decimal("0"), "high": Decimal("2.5"), "unit": "ng/mL"},
        {"field_code": "psa_value", "sex": "M", "age_min_days": 18250, "age_max_days": 21900,
         "low": Decimal("0"), "high": Decimal("3.5"), "unit": "ng/mL"},
        {"field_code": "psa_value", "sex": "M", "age_min_days": 21900, "age_max_days": 25550,
         "low": Decimal("0"), "high": Decimal("4.5"), "unit": "ng/mL"},
        {"field_code": "psa_value", "sex": "M", "age_min_days": 25550, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("6.5"), "unit": "ng/mL"},
        
        # CD4
        {"field_code": "cd4_count", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("500"), "high": Decimal("1500"), "unit": "cells/μL"},
        
        # Urine
        {"field_code": "ph", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("4.5"), "high": Decimal("8.0"), "unit": ""},
        {"field_code": "specific_gravity", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("1.005"), "high": Decimal("1.030"), "unit": ""},
        
        # ===== ADDITIONAL FIELD CODES TO MATCH TEMPLATES =====
        # The templates use different field codes (e.g., hb_value instead of hb)
        
        # Hb (HB test uses hb_value)
        {"field_code": "hb_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("13.0"), "high": Decimal("17.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("12.0"), "high": Decimal("15.0"), "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"},
        {"field_code": "hb_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 28,
         "low": Decimal("14.5"), "high": Decimal("22.5"), "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"},
        
        # ESR
        {"field_code": "esr_value", "sex": "M", "age_min_days": 6570, "age_max_days": 18250,
         "low": Decimal("0"), "high": Decimal("15"), "unit": "mm/hr"},
        {"field_code": "esr_value", "sex": "F", "age_min_days": 6570, "age_max_days": 18250,
         "low": Decimal("0"), "high": Decimal("20"), "unit": "mm/hr"},
        
        # Retic count
        {"field_code": "retic_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0.5"), "high": Decimal("2.5"), "unit": "%"},
        
        # TSH (uses tsh_value in templates)
        {"field_code": "tsh_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("0.4"), "high": Decimal("4.0"), "critical_low": Decimal("0.1"), "critical_high": Decimal("10.0"), "unit": "mIU/L"},
        
        # FT3, FT4
        {"field_code": "ft3_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("3.1"), "high": Decimal("6.8"), "unit": "pmol/L"},
        {"field_code": "ft4_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("12"), "high": Decimal("22"), "unit": "pmol/L"},
        
        # Testosterone
        {"field_code": "testosterone_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("8.6"), "high": Decimal("29.0"), "unit": "nmol/L"},
        {"field_code": "testosterone_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("0.5"), "high": Decimal("2.6"), "unit": "nmol/L"},
        
        # FSH, LH
        {"field_code": "fsh_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("1.5"), "high": Decimal("12.4"), "unit": "IU/L"},
        {"field_code": "fsh_value", "sex": "F", "age_min_days": 6570, "age_max_days": 18250,
         "low": Decimal("3.5"), "high": Decimal("12.5"), "unit": "IU/L"},
        {"field_code": "lh_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("1.7"), "high": Decimal("8.6"), "unit": "IU/L"},
        {"field_code": "lh_value", "sex": "F", "age_min_days": 6570, "age_max_days": 18250,
         "low": Decimal("2.4"), "high": Decimal("12.6"), "unit": "IU/L"},
        
        # Progesterone
        {"field_code": "progesterone_value", "sex": "F", "age_min_days": 6570, "age_max_days": 18250,
         "low": Decimal("0.3"), "high": Decimal("25.6"), "unit": "nmol/L"},
        
        # Estradiol
        {"field_code": "estradiol_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("50"), "high": Decimal("200"), "unit": "pmol/L"},
        {"field_code": "estradiol_value", "sex": "F", "age_min_days": 6570, "age_max_days": 18250,
         "low": Decimal("70"), "high": Decimal("600"), "unit": "pmol/L"},
        
        # Prolactin
        {"field_code": "prolactin_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("86"), "high": Decimal("324"), "unit": "mIU/L"},
        {"field_code": "prolactin_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("102"), "high": Decimal("496"), "unit": "mIU/L"},
        
        # Cortisol
        {"field_code": "cortisol_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("171"), "high": Decimal("536"), "unit": "nmol/L"},
        
        # Amylase
        {"field_code": "amylase_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("28"), "high": Decimal("100"), "unit": "U/L"},
        
        # Lipase
        {"field_code": "lipase_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("13"), "high": Decimal("60"), "unit": "U/L"},
        
        # CK
        {"field_code": "ck_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("38"), "high": Decimal("174"), "unit": "U/L"},
        {"field_code": "ck_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("26"), "high": Decimal("140"), "unit": "U/L"},
        
        # CK-MB
        {"field_code": "ckmb_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("25"), "unit": "U/L"},
        
        # LDH
        {"field_code": "ldh_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("140"), "high": Decimal("280"), "unit": "U/L"},
        
        # HbA1c
        {"field_code": "hba1c_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("4.0"), "high": Decimal("6.0"), "critical_high": Decimal("15.0"), "unit": "%"},
        
        # Ferritin
        {"field_code": "ferritin", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("30"), "high": Decimal("400"), "unit": "ng/mL"},
        {"field_code": "ferritin", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("13"), "high": Decimal("150"), "unit": "ng/mL"},
        
        # TIBC
        {"field_code": "tibc", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("44.8"), "high": Decimal("73.4"), "unit": "μmol/L"},
        
        # Serum Iron
        {"field_code": "serum_iron", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("11.6"), "high": Decimal("31.3"), "unit": "μmol/L"},
        {"field_code": "serum_iron", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("9.0"), "high": Decimal("30.4"), "unit": "μmol/L"},
        
        # Calcium
        {"field_code": "calcium_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("2.10"), "high": Decimal("2.55"), "critical_low": Decimal("1.5"), "critical_high": Decimal("3.0"), "unit": "mmol/L"},
        
        # Magnesium
        {"field_code": "magnesium_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0.70"), "high": Decimal("1.10"), "unit": "mmol/L"},
        
        # Phosphate
        {"field_code": "phosphate_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 36500,
         "low": Decimal("0.81"), "high": Decimal("1.45"), "unit": "mmol/L"},
        
        # Uric Acid
        {"field_code": "uric_acid_value", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("200"), "high": Decimal("430"), "unit": "μmol/L"},
        {"field_code": "uric_acid_value", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("140"), "high": Decimal("360"), "unit": "μmol/L"},
        
        # GFR / eGFR
        {"field_code": "gfr_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("90"), "high": Decimal("120"), "unit": "mL/min/1.73m²"},
        
        # BNP
        {"field_code": "bnp_value", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
         "low": Decimal("0"), "high": Decimal("100"), "unit": "pg/mL"},
        
        # CRP
        {"field_code": "crp_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("5.0"), "unit": "mg/L"},
        
        # ASO
        {"field_code": "aso_value", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("200"), "unit": "IU/mL"},
        
        # OGTT fields
        {"field_code": "fasting_glucose", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("3.9"), "high": Decimal("6.1"), "unit": "mmol/L"},
        {"field_code": "1hr_glucose", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("10.0"), "unit": "mmol/L"},
        {"field_code": "2hr_glucose", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500,
         "low": Decimal("0"), "high": Decimal("7.8"), "unit": "mmol/L"},
    ]
    
    created = 0
    skipped = 0
    
    for range_def in field_ranges:
        field_code = range_def["field_code"]
        sex = range_def.get("sex", "ANY")
        age_min_days = range_def.get("age_min_days", 0)
        age_max_days = range_def.get("age_max_days", 36500)
        
        # Check if range already exists
        result = db.execute(text("""
            SELECT id FROM lab_reference_ranges 
            WHERE field_code = :field_code
            AND (sex = :sex OR (sex IS NULL AND :sex = 'ANY'))
            AND age_min_days = :age_min_days 
            AND age_max_days = :age_max_days
        """), {
            "field_code": field_code,
            "sex": sex,
            "age_min_days": age_min_days,
            "age_max_days": age_max_days
        })
        
        if result.fetchone():
            skipped += 1
            continue
        
        # Insert range
        db.execute(text("""
            INSERT INTO lab_reference_ranges (
                field_code, sex, age_min_days, age_max_days,
                low, high, critical_low, critical_high, unit
            ) VALUES (
                :field_code, :sex, :age_min_days, :age_max_days,
                :low, :high, :critical_low, :critical_high, :unit
            )
        """), {
            "field_code": field_code,
            "sex": sex if sex != "ANY" else None,
            "age_min_days": age_min_days,
            "age_max_days": age_max_days,
            "low": range_def.get("low"),
            "high": range_def.get("high"),
            "critical_low": range_def.get("critical_low"),
            "critical_high": range_def.get("critical_high"),
            "unit": range_def.get("unit"),
        })
        created += 1
    
    db.commit()
    print(f"  Created: {created} lab reference ranges")
    print(f"  Skipped (existing): {skipped} ranges")
    return created + skipped


def main():
    """Main execution function."""
    print("=" * 60)
    print("Ghana Hospital EMR - Laboratory Test Seeder")
    print("=" * 60)
    print(f"Database: {DATABASE_URL}")
    
    try:
        db = SessionLocal()
        
        # Run all seed operations
        total_tests = create_lab_tests(db)
        total_options = create_option_sets(db)
        total_templates = create_lab_templates(db)
        total_ranges = create_reference_ranges(db)
        total_lab_ranges = create_lab_reference_ranges(db)
        
        print("\n" + "=" * 60)
        print("SEEDING COMPLETE")
        print("=" * 60)
        print(f"  Total Tests: {total_tests}")
        print(f"  Total Option Sets: {total_options}")
        print(f"  Total Templates: {total_templates}")
        print(f"  Total Reference Ranges: {total_ranges}")
        print(f"  Total Lab Reference Ranges (UI): {total_lab_ranges}")
        print("\n✓ All laboratory tests have been seeded successfully!")
        print("✓ Tests are ready for lab staff to use in the EMR")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
