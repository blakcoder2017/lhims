#!/usr/bin/env python3
"""
Ghana Laboratory Test Catalog Seeder - Direct SQL Version

This script populates the database with Ghana-standard laboratory tests,
parameter templates, and reference ranges using direct SQL.

⚠️ IDEMPOTENT: Safe to run multiple times - only inserts missing records
⚠️ MERGE-SAFE: Does NOT overwrite existing data

Usage:
    python3 seed_ghana_lab_catalog.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

# Database connection
DATABASE_URL = "postgresql+psycopg2://postgres:password123@localhost:5433/lhims"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def create_option_sets(db):
    """Create Ghana-specific option sets (idempotent)."""
    print("Creating option sets...")
    
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
    
    created_count = 0
    for code, options_json in option_sets:
        result = db.execute(text("SELECT id FROM lab_option_sets WHERE code = :code"), {"code": code})
        if not result.fetchone():
            db.execute(text("INSERT INTO lab_option_sets (code, options_json) VALUES (:code, :options_json)"), 
                     {"code": code, "options_json": options_json})
            created_count += 1
    
    db.commit()
    print(f"  Created {created_count} new option sets")
    return len(option_sets)


def create_lab_tests(db):
    """Create lab test catalog records (idempotent)."""
    print("Creating lab test catalog records...")
    
    tests = [
        # HAEMATOLOGY (10)
        ("FBC", "Full Blood Count (FBC)", "Haematology", "HEMATOLOGY", "EDTA Blood", True, "Panel", "Complete blood count with differential.", 4, 1, 25.00),
        ("HB", "Haemoglobin (Hb)", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Quantitative", None, 2, 1, 5.00),
        ("ESR", "Erythrocyte Sedimentation Rate (ESR)", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Quantitative", None, 4, 2, 10.00),
        ("RETIC", "Reticulocyte Count", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Quantitative", None, 4, 1, 12.00),
        ("SICKLING", "Sickling Test", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Qualitative", None, 2, 1, 5.00),
        ("BF_MP", "Blood Film for Malaria Parasite", "Parasitology", "PARASITOLOGY", "EDTA Blood", False, "Qualitative", None, 2, 1, 8.00),
        ("HB_ELECTRO", "Haemoglobin Electrophoresis", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Qualitative", None, 24, 8, 35.00),
        ("G6PD", "G6PD Screening", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Qualitative", None, 4, 2, 15.00),
        ("COOMBS", "Coombs Test", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Qualitative", None, 8, 4, 20.00),
        ("BLOOD_GROUP", "Blood Grouping (ABO + Rh)", "Haematology", "HEMATOLOGY", "EDTA Blood", False, "Qualitative", None, 2, 1, 8.00),
        
        # MICROSCOPY / ROUTINE (4)
        ("URINE_RE", "Urine Routine Examination", "Clinical Pathology", "CLINICAL_PATHOLOGY", "Urine", True, "Panel", None, 4, 1, 15.00),
        ("STOOL_RE", "Stool Routine Examination", "Clinical Pathology", "CLINICAL_PATHOLOGY", "Stool", True, "Panel", None, 4, 2, 15.00),
        ("HVS_RE", "High Vaginal Swab (HVS) R/E", "Microbiology", "MICROBIOLOGY", "Swab", True, "Panel", None, 4, 2, 15.00),
        ("SKIN_SNIP", "Skin Snip for Microfilaria", "Parasitology", "PARASITOLOGY", "Skin Snip", False, "Qualitative", None, 8, 4, 20.00),
        
        # HORMONAL / ENDOCRINE (16)
        ("TSH", "Thyroid Stimulating Hormone (TSH)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 24, 8, 35.00),
        ("FT3", "Free T3 (Triiodothyronine)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 40.00),
        ("FT4", "Free T4 (Thyroxine)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 40.00),
        ("TESTOSTERONE", "Testosterone", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 50.00),
        ("FSH", "Follicle Stimulating Hormone (FSH)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 45.00),
        ("LH", "Luteinizing Hormone (LH)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 45.00),
        ("PROGESTERONE", "Progesterone", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 45.00),
        ("ESTRADIOL", "Estradiol (E2)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 50.00),
        ("PROLACTIN", "Prolactin", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 40.00),
        ("CORTISOL", "Cortisol", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 45.00),
        ("DHEA", "DHEA-Sulphate (DHEA-S)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 45.00),
        ("GH", "Growth Hormone (GH)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 48, 24, 50.00),
        ("PSA", "Prostate Specific Antigen (PSA)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 24, 8, 35.00),
        ("FEMALE_INFERTILITY", "Female Infertility Profile", "Hormonal", "ENDOCRINOLOGY", "Serum", True, "Panel", "FSH, LH, Prolactin, Progesterone, Estradiol", 48, 24, 80.00),
        ("THYROID_PROFILE", "Thyroid Profile", "Hormonal", "ENDOCRINOLOGY", "Serum", True, "Panel", "TSH, FT3, FT4", 48, 24, 90.00),
        ("ANTI_MULLERIAN", "Anti-Mullerian Hormone (AMH)", "Hormonal", "ENDOCRINOLOGY", "Serum", False, "Quantitative", None, 72, 48, 65.00),
        
        # SEROLOGY / INFECTIOUS DISEASES (20)
        ("HIV_SCREEN", "HIV Screening (1 & 2)", "Serology", "SEROLOGY", "Serum/Plasma", False, "Qualitative", None, 2, 1, 10.00),
        ("HBSAG", "Hepatitis B Surface Antigen (HBsAg)", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 4, 2, 15.00),
        ("HBSAB", "Hepatitis B Surface Antibody (Anti-HBs)", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 4, 2, 15.00),
        ("HBcAB_Total", "Hepatitis B Core Antibody (Total)", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 4, 2, 15.00),
        ("HBcAB_IgM", "Hepatitis B Core Antibody IgM", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 4, 2, 18.00),
        ("HBV_PROFILE", "Hepatitis B Viral Profile", "Serology", "SEROLOGY", "Serum", True, "Panel", None, 24, 8, 60.00),
        ("HCV", "Hepatitis C Antibody", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 24, 8, 25.00),
        ("HAV_IgM", "Hepatitis A Virus IgM", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 24, 8, 20.00),
        ("HAV_Total", "Hepatitis A Virus Total Antibody", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 24, 8, 20.00),
        ("HEV_IgM", "Hepatitis E Virus IgM", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 48, 24, 25.00),
        ("VDRL", "VDRL (Syphilis Test)", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 4, 2, 12.00),
        ("TPHA", "TPHA (Syphilis Confirmation)", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 24, 8, 18.00),
        ("WIDAL", "Widal Test", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 4, 2, 15.00),
        ("TYPHOID", "Typhoid IgM/IgG", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 24, 8, 20.00),
        ("GONORRHOEA", "Gonorrhoea (NGAL)", "Serology", "SEROLOGY", "Serum/Urine", False, "Qualitative", None, 24, 8, 25.00),
        ("CHLAMYDIA", "Chlamydia trachomatis IgG", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 48, 24, 30.00),
        ("HPYLORI", "H. pylori Antibody", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 24, 8, 25.00),
        ("RUBELLA", "Rubella IgG/IgM", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 48, 24, 30.00),
        ("TOXOPLASMA", "Toxoplasma IgG/IgM", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 48, 24, 35.00),
        ("CMV", "Cytomegalovirus (CMV) IgG/IgM", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 48, 24, 35.00),
        ("HSV_1_2", "Herpes Simplex Virus (HSV) 1&2", "Serology", "SEROLOGY", "Serum", False, "Qualitative", None, 48, 24, 40.00),
        ("PREGNANCY_TEST", "Pregnancy Test (Serum β-HCG)", "Serology", "SEROLOGY", "Serum", False, "Qualitative/Quantitative", None, 4, 1, 15.00),
        ("BHCG_QUANT", "Quantitative β-HCG", "Serology", "SEROLOGY", "Serum", False, "Quantitative", None, 24, 8, 35.00),
        ("AFP", "Alpha Fetoprotein (AFP)", "Tumor Marker", "ONCOLOGY", "Serum", False, "Quantitative", None, 48, 24, 40.00),
        ("CEA", "Carcinoembryonic Antigen (CEA)", "Tumor Marker", "ONCOLOGY", "Serum", False, "Quantitative", None, 48, 24, 45.00),
        ("PSA_FREE", "Free PSA", "Tumor Marker", "ONCOLOGY", "Serum", False, "Quantitative", None, 48, 24, 40.00),
        
        # BIOCHEMISTRY (22)
        ("LFT", "Liver Function Test (LFT)", "Biochemistry", "BIOCHEMISTRY", "Serum", True, "Panel", None, 8, 4, 40.00),
        ("RFT", "Renal Function Test (RFT)", "Biochemistry", "BIOCHEMISTRY", "Serum", True, "Panel", None, 8, 4, 35.00),
        ("ELECTROLYTES", "Serum Electrolytes", "Biochemistry", "BIOCHEMISTRY", "Serum", True, "Panel", None, 4, 1, 25.00),
        ("FBS", "Fasting Blood Sugar (FBS)", "Biochemistry", "BIOCHEMISTRY", "Fluoride Plasma", False, "Quantitative", None, 4, 1, 8.00),
        ("RBS", "Random Blood Sugar (RBS)", "Biochemistry", "BIOCHEMISTRY", "Fluoride Plasma", False, "Quantitative", None, 2, 1, 8.00),
        ("OGTT", "Oral Glucose Tolerance Test (OGTT)", "Biochemistry", "BIOCHEMISTRY", "Fluoride Plasma", True, "Panel", None, 8, 4, 20.00),
        ("HbA1c", "Glycated Haemoglobin (HbA1c)", "Biochemistry", "BIOCHEMISTRY", "EDTA Blood", False, "Quantitative", None, 24, 8, 45.00),
        ("LIPID_PROFILE", "Lipid Profile", "Biochemistry", "BIOCHEMISTRY", "Serum", True, "Panel", None, 8, 4, 35.00),
        ("CALCIUM", "Serum Calcium", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 4, 2, 12.00),
        ("MAGNESIUM", "Serum Magnesium", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 15.00),
        ("PHOSPHATE", "Serum Phosphate", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 12.00),
        ("IRON_STUDIES", "Iron Studies", "Biochemistry", "BIOCHEMISTRY", "Serum", True, "Panel", None, 24, 8, 55.00),
        ("FERRITIN", "Ferritin", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 24, 8, 30.00),
        ("TIBC", "Total Iron Binding Capacity (TIBC)", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 24, 8, 25.00),
        ("URIC_ACID", "Uric Acid", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 4, 2, 12.00),
        ("AMYLASE", "Serum Amylase", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 18.00),
        ("LIPASE", "Serum Lipase", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 20.00),
        ("CK", "Creatine Kinase (CK)", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 20.00),
        ("CK_MB", "CK-MB", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 25.00),
        ("LDH", "Lactate Dehydrogenase (LDH)", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 8, 4, 18.00),
        ("TROPONIN", "Troponin I/T", "Cardiac Marker", "CARDIOLOGY", "Serum", False, "Qualitative/Quantitative", None, 4, 1, 35.00),
        ("BNP", "B-type Natriuretic Peptide (BNP)", "Cardiac Marker", "CARDIOLOGY", "Serum", False, "Quantitative", None, 24, 8, 55.00),
        ("GFR", "Glomerular Filtration Rate (GFR)", "Biochemistry", "BIOCHEMISTRY", "Serum", False, "Quantitative", None, 4, 2, 15.00),
        
        # INFLAMMATORY MARKERS (5)
        ("CRP", "C-Reactive Protein (CRP)", "Inflammatory", "IMMUNOLOGY", "Serum", False, "Quantitative", None, 24, 8, 20.00),
        ("ASO", "Antistreptolysin O (ASO) Titer", "Inflammatory", "IMMUNOLOGY", "Serum", False, "Quantitative", None, 24, 8, 20.00),
        ("RA_FACTOR", "Rheumatoid Factor (RA)", "Inflammatory", "IMMUNOLOGY", "Serum", False, "Qualitative/Quantitative", None, 24, 8, 20.00),
        ("ANA", "Antinuclear Antibody (ANA)", "Inflammatory", "IMMUNOLOGY", "Serum", False, "Qualitative", None, 72, 48, 40.00),
        ("ANTI_CCP", "Anti-CCP Antibody", "Inflammatory", "IMMUNOLOGY", "Serum", False, "Quantitative", None, 72, 48, 45.00),
        
        # BODY FLUIDS (3)
        ("CSF_BIOCHEM", "CSF Biochemistry", "Biochemistry", "BIOCHEMISTRY", "CSF", True, "Panel", None, 8, 4, 30.00),
        ("ASCITIC_FLUID", "Ascitic Fluid Analysis", "Biochemistry", "BIOCHEMISTRY", "Ascitic Fluid", True, "Panel", None, 8, 4, 35.00),
        ("PLEURAL_FLUID", "Pleural Fluid Analysis", "Biochemistry", "BIOCHEMISTRY", "Pleural Fluid", True, "Panel", None, 8, 4, 35.00),
        
        # CULTURE & SENSITIVITY (5)
        ("CS_BLOOD", "Blood Culture & Sensitivity", "Microbiology", "MICROBIOLOGY", "Blood", True, "Panel", None, 72, 48, 45.00),
        ("CS_URINE", "Urine Culture & Sensitivity", "Microbiology", "MICROBIOLOGY", "Urine", True, "Panel", None, 48, 24, 30.00),
        ("CS_STOOL", "Stool Culture & Sensitivity", "Microbiology", "MICROBIOLOGY", "Stool", True, "Panel", None, 72, 48, 35.00),
        ("CS_SPUTUM", "Sputum Culture & Sensitivity", "Microbiology", "MICROBIOLOGY", "Sputum", True, "Panel", None, 72, 48, 35.00),
        ("CS_WOUND", "Wound Swab Culture & Sensitivity", "Microbiology", "MICROBIOLOGY", "Swab", True, "Panel", None, 72, 48, 30.00),
        
        # VIROLOGY (4)
        ("HIV_VL", "HIV Viral Load", "Virology", "VIROLOGY", "EDTA Plasma", False, "Quantitative", None, 72, 48, 85.00),
        ("HBV_VL", "Hepatitis B Viral Load", "Virology", "VIROLOGY", "Serum", False, "Quantitative", None, 72, 48, 90.00),
        ("HCV_VL", "Hepatitis C Viral Load", "Virology", "VIROLOGY", "Serum", False, "Quantitative", None, 72, 48, 100.00),
        ("CD4", "CD4 Count", "Immunology", "IMMUNOLOGY", "EDTA Blood", False, "Quantitative", None, 24, 8, 55.00),
    ]
    
    created_count = 0
    for test in tests:
        result = db.execute(text("SELECT id FROM lab_tests WHERE test_code = :code"), {"code": test[0]})
        if not result.fetchone():
            db.execute(text("""
                INSERT INTO lab_tests (test_code, test_name, test_category, test_type, specimen_type, 
                is_active, is_specialized, description, routine_tat, urgent_tat, cost)
                VALUES (:code, :name, :category, :type, :specimen, true, false, :desc, :routine, :urgent, :cost)
            """), {"code": test[0], "name": test[1], "category": test[2], "type": test[6], 
                  "specimen": test[4], "desc": test[7], "routine": test[8], "urgent": test[9], "cost": test[10]})
            created_count += 1
    
    db.commit()
    print(f"  Created {created_count} new lab test records")
    return len(tests)


def create_lab_templates(db):
    """Create lab template schemas (idempotent)."""
    print("Creating lab templates...")
    
    # FBC Template
    result = db.execute(text("SELECT id FROM lab_templates WHERE name = 'Full Blood Count (FBC)'"))
    if not result.fetchone():
        import uuid
        template_id = str(uuid.uuid4())
        fbc_schema = {
            "meta": {"name": "Full Blood Count (FBC)", "discipline": "HEMATOLOGY", "version": 1},
            "layout": {"sections": [
                {"id": "sec_rbc", "title": "Red Blood Cells", "rows": [
                    {"columns": [{"items": ["hb"], "width": 3}, {"items": ["hct"], "width": 3}, {"items": ["rbc_count"], "width": 3}, {"items": ["mcv"], "width": 3}]},
                    {"columns": [{"items": ["mch"], "width": 4}, {"items": ["mchc"], "width": 4}, {"items": ["retic"], "width": 4}]}
                ]},
                {"id": "sec_wbc", "title": "White Blood Cells", "rows": [
                    {"columns": [{"items": ["wbc_count"], "width": 12}]}
                ]},
                {"id": "sec_diff", "title": "Differential Count", "rows": [
                    {"columns": [{"items": ["neutrophils"], "width": 4}, {"items": ["lymphocytes"], "width": 4}, {"items": ["monocytes"], "width": 4}]},
                    {"columns": [{"items": ["eosinophils"], "width": 4}, {"items": ["basophils"], "width": 4}, {"items": ["blasts"], "width": 4}]}
                ]},
                {"id": "sec_plt", "title": "Platelets", "rows": [
                    {"columns": [{"items": ["platelet_count"], "width": 12}]}
                ]}
            ]},
            "fields": {
                "hb": {"code": "hb", "type": "numeric", "label": "Haemoglobin (Hb)", "unit": "g/dL", "decimals": 1, "critical": {"low": 7.0, "high": 20.0}},
                "hct": {"code": "hct", "type": "numeric", "label": "Hematocrit (Hct)", "unit": "%", "decimals": 1, "critical": {"low": 20.0, "high": 60.0}},
                "rbc_count": {"code": "rbc_count", "type": "numeric", "label": "RBC Count", "unit": "x10^12/L", "decimals": 2},
                "mcv": {"code": "mcv", "type": "numeric", "label": "MCV", "unit": "fL", "decimals": 1},
                "mch": {"code": "mch", "type": "numeric", "label": "MCH", "unit": "pg", "decimals": 1},
                "mchc": {"code": "mchc", "type": "numeric", "label": "MCHC", "unit": "g/dL", "decimals": 1},
                "retic": {"code": "retic", "type": "numeric", "label": "Reticulocytes", "unit": "%", "decimals": 1},
                "wbc_count": {"code": "wbc_count", "type": "numeric", "label": "WBC Count", "unit": "x10^9/L", "decimals": 2, "critical": {"low": 2.0, "high": 30.0}},
                "neutrophils": {"code": "neutrophils", "type": "numeric", "label": "Neutrophils", "unit": "%", "decimals": 1},
                "lymphocytes": {"code": "lymphocytes", "type": "numeric", "label": "Lymphocytes", "unit": "%", "decimals": 1},
                "monocytes": {"code": "monocytes", "type": "numeric", "label": "Monocytes", "unit": "%", "decimals": 1},
                "eosinophils": {"code": "eosinophils", "type": "numeric", "label": "Eosinophils", "unit": "%", "decimals": 1},
                "basophils": {"code": "basophils", "type": "numeric", "label": "Basophils", "unit": "%", "decimals": 1},
                "blasts": {"code": "blasts", "type": "numeric", "label": "Blasts", "unit": "%", "decimals": 0},
                "platelet_count": {"code": "platelet_count", "type": "numeric", "label": "Platelet Count", "unit": "x10^9/L", "decimals": 0, "critical": {"low": 20.0, "high": 1000.0}},
            }
        }
        
        db.execute(text("""
            INSERT INTO lab_templates (id, name, discipline, status, current_version)
            VALUES (:id, 'Full Blood Count (FBC)', 'HEMATOLOGY', 'PUBLISHED', 1)
        """), {"id": template_id})
        
        db.execute(text("""
            INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, change_note)
            VALUES (:vid, :tid, 1, 'PUBLISHED', :schema, 'Initial Ghana-standard FBC template')
        """), {"vid": str(uuid.uuid4()), "tid": template_id, "schema": str(fbc_schema).replace("'", '"')})
    
    # Urine R/E Template
    result = db.execute(text("SELECT id FROM lab_templates WHERE name = 'Urine Routine Examination'"))
    if not result.fetchone():
        import uuid
        template_id = str(uuid.uuid4())
        urine_schema = {
            "meta": {"name": "Urine Routine Examination", "discipline": "CLINICAL_PATHOLOGY", "version": 1},
            "layout": {"sections": [
                {"id": "sec_physical", "title": "Physical", "rows": [
                    {"columns": [{"items": ["urine_colour"], "width": 6}, {"items": ["urine_appearance"], "width": 6}]}
                ]},
                {"id": "sec_chemical", "title": "Chemical", "rows": [
                    {"columns": [{"items": ["urine_protein"], "width": 4}, {"items": ["urine_glucose"], "width": 4}, {"items": ["urine_ketones"], "width": 4}]},
                    {"columns": [{"items": ["urine_blood"], "width": 4}, {"items": ["urine_ph"], "width": 4}, {"items": ["urine_sg"], "width": 4}]}
                ]},
                {"id": "sec_microscopic", "title": "Microscopic", "rows": [
                    {"columns": [{"items": ["urine_wbc"], "width": 4}, {"items": ["urine_rbc"], "width": 4}, {"items": ["urine_epithelial"], "width": 4}]},
                    {"columns": [{"items": ["urine_casts"], "width": 4}, {"items": ["urine_crystals"], "width": 4}, {"items": ["urine_bacteria"], "width": 4}]}
                ]}
            ]},
            "fields": {
                "urine_colour": {"code": "urine_colour", "type": "select", "label": "Colour", "options": ["Straw", "Yellow", "Amber", "Red", "Brown", "Other"]},
                "urine_appearance": {"code": "urine_appearance", "type": "select", "label": "Appearance", "options": ["Clear", "Slightly turbid", "Turbid"]},
                "urine_protein": {"code": "urine_protein", "type": "select", "label": "Protein", "options": ["Negative", "Trace", "+", "++", "+++"]},
                "urine_glucose": {"code": "urine_glucose", "type": "select", "label": "Glucose", "options": ["Negative", "Trace", "+", "++", "+++"]},
                "urine_ketones": {"code": "urine_ketones", "type": "select", "label": "Ketones", "options": ["Negative", "Trace", "+", "++", "+++"]},
                "urine_blood": {"code": "urine_blood", "type": "select", "label": "Blood", "options": ["Negative", "Trace", "+", "++", "+++"]},
                "urine_ph": {"code": "urine_ph", "type": "numeric", "label": "pH", "unit": "", "decimals": 1},
                "urine_sg": {"code": "urine_sg", "type": "numeric", "label": "Specific Gravity", "unit": "", "decimals": 3},
                "urine_wbc": {"code": "urine_wbc", "type": "text", "label": "WBC/HPF"},
                "urine_rbc": {"code": "urine_rbc", "type": "text", "label": "RBC/HPF"},
                "urine_epithelial": {"code": "urine_epithelial", "type": "text", "label": "Epithelial Cells"},
                "urine_casts": {"code": "urine_casts", "type": "text", "label": "Casts"},
                "urine_crystals": {"code": "urine_crystals", "type": "text", "label": "Crystals"},
                "urine_bacteria": {"code": "urine_bacteria", "type": "text", "label": "Bacteria"},
            }
        }
        
        db.execute(text("""
            INSERT INTO lab_templates (id, name, discipline, status, current_version)
            VALUES (:id, 'Urine Routine Examination', 'CLINICAL_PATHOLOGY', 'PUBLISHED', 1)
        """), {"id": template_id})
        
        db.execute(text("""
            INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, change_note)
            VALUES (:vid, :tid, 1, 'PUBLISHED', :schema, 'Initial Ghana-standard Urine R/E template')
        """), {"vid": str(uuid.uuid4()), "tid": template_id, "schema": str(urine_schema).replace("'", '"')})
    
    db.commit()
    print(f"  Created lab templates")
    return 2


def create_reference_ranges(db):
    """Create Ghana-standard reference ranges (idempotent)."""
    print("Creating reference ranges...")
    
    ranges = [
        # Haemoglobin
        ("hb", "M", 6570, 25550, 12.5, 17.5, 7.0, 20.0, "g/dL"),
        ("hb", "F", 6570, 25550, 11.5, 15.5, 7.0, 20.0, "g/dL"),
        ("hb", "ANY", 4745, 6570, 12.0, 16.0, 7.0, 20.0, "g/dL"),
        ("hb", "ANY", 2190, 4745, 11.5, 15.5, 7.0, 20.0, "g/dL"),
        ("hb", "ANY", 0, 28, 14.5, 22.5, 10.0, 25.0, "g/dL"),
        
        # Hematocrit
        ("hct", "M", 6570, 25550, 36, 50, 20, 60, "%"),
        ("hct", "F", 6570, 25550, 34, 46, 20, 60, "%"),
        ("hct", "ANY", 0, 6570, 32, 50, 20, 60, "%"),
        
        # RBC, WBC, Platelets
        ("rbc_count", "M", 6570, None, 4.5, 6.5, None, None, "x10^12/L"),
        ("rbc_count", "F", 6570, None, 3.8, 5.8, None, None, "x10^12/L"),
        ("wbc_count", "ANY", 0, 25550, 4.0, 11.0, 2.0, 30.0, "x10^9/L"),
        ("platelet_count", "ANY", 0, 25550, 150, 400, 20, 1000, "x10^9/L"),
        
        # RBC Indices
        ("mcv", "ANY", 0, None, 80, 100, None, None, "fL"),
        ("mch", "ANY", 0, None, 27, 34, None, None, "pg"),
        ("mchc", "ANY", 0, None, 32, 36, None, None, "g/dL"),
        
        # Differential
        ("neutrophils", "ANY", 0, None, 40, 75, None, None, "%"),
        ("lymphocytes", "ANY", 0, None, 20, 45, None, None, "%"),
        ("monocytes", "ANY", 0, None, 2, 10, None, None, "%"),
        ("eosinophils", "ANY", 0, None, 1, 6, None, None, "%"),
        ("basophils", "ANY", 0, None, 0, 2, None, None, "%"),
        
        # Reticulocytes & ESR
        ("retic", "ANY", 0, None, 0.5, 2.5, None, None, "%"),
        ("esr", "M", 6570, None, 0, 15, None, None, "mm/hr"),
        ("esr", "F", 6570, None, 0, 20, None, None, "mm/hr"),
        
        # Liver Function
        ("alt", "M", 6570, None, 0, 40, None, 500, "U/L"),
        ("alt", "F", 6570, None, 0, 35, None, 500, "U/L"),
        ("ast", "M", 6570, None, 0, 40, None, 500, "U/L"),
        ("ast", "F", 6570, None, 0, 35, None, 500, "U/L"),
        ("alp", "ANY", 6570, None, 44, 147, None, None, "U/L"),
        ("total_bilirubin", "ANY", 6570, None, 3.4, 20.5, None, 171.0, "µmol/L"),
        ("albumin", "ANY", 0, None, 35, 50, 20, None, "g/L"),
        ("total_protein", "ANY", 0, None, 60, 80, None, None, "g/L"),
        
        # Renal Function
        ("urea", "ANY", 6570, None, 2.9, 8.2, None, 35.0, "mmol/L"),
        ("creatinine", "M", 6570, None, 62, 124, None, 707.0, "µmol/L"),
        ("creatinine", "F", 6570, None, 44, 107, None, 707.0, "µmol/L"),
        
        # Electrolytes
        ("sodium", "ANY", 0, None, 136, 145, 120.0, 160.0, "mmol/L"),
        ("potassium", "ANY", 0, None, 3.5, 5.0, 2.5, 6.5, "mmol/L"),
        ("chloride", "ANY", 0, None, 98, 106, None, None, "mmol/L"),
        ("bicarbonate", "ANY", 0, None, 22, 29, None, None, "mmol/L"),
        
        # Glucose
        ("fbs", "ANY", 0, None, 3.9, 6.1, 2.2, 27.8, "mmol/L"),
        ("rbs", "ANY", 0, None, 3.9, 7.8, 2.2, 27.8, "mmol/L"),
        ("hba1c", "ANY", 0, None, 4.0, 5.6, None, 10.0, "%"),
        
        # Lipid Profile
        ("total_cholesterol", "ANY", 6570, None, 0, 5.2, None, None, "mmol/L"),
        ("ldl_cholesterol", "ANY", 6570, None, 0, 3.3, None, None, "mmol/L"),
        ("hdl_cholesterol", "M", 6570, None, 1.0, 2.1, None, None, "mmol/L"),
        ("hdl_cholesterol", "F", 6570, None, 1.2, 2.7, None, None, "mmol/L"),
        ("triglycerides", "ANY", 6570, None, 0.4, 1.7, None, None, "mmol/L"),
        
        # Minerals
        ("calcium", "ANY", 0, None, 2.10, 2.55, 1.5, 3.0, "mmol/L"),
        ("magnesium", "ANY", 0, None, 0.66, 1.07, None, None, "mmol/L"),
        ("phosphate", "ANY", 6570, None, 0.81, 1.45, None, None, "mmol/L"),
        ("uric_acid", "M", 6570, None, 210, 430, None, None, "µmol/L"),
        ("uric_acid", "F", 6570, None, 140, 360, None, None, "µmol/L"),
        
        # Hormonal
        ("tsh", "ANY", 6570, None, 0.4, 4.0, None, None, "mIU/L"),
        ("ft3", "ANY", 6570, None, 3.1, 6.8, None, None, "pmol/L"),
        ("ft4", "ANY", 6570, None, 12, 22, None, None, "pmol/L"),
        ("testosterone", "M", 6570, 25550, 8.64, 29.0, None, None, "nmol/L"),
        ("testosterone", "F", 6570, 25550, 0.29, 1.67, None, None, "nmol/L"),
    ]
    
    created_count = 0
    for r in ranges:
        result = db.execute(text("""
            SELECT id FROM lab_reference_ranges 
            WHERE field_code = :code AND sex = :sex AND age_min_days = :age_min
        """), {"code": r[0], "sex": r[1], "age_min": r[2]})
        
        if not result.fetchone():
            db.execute(text("""
                INSERT INTO lab_reference_ranges (field_code, sex, age_min_days, age_max_days, 
                low, high, critical_low, critical_high, unit)
                VALUES (:code, :sex, :age_min, :age_max, :low, :high, :crit_low, :crit_high, :unit)
            """), {"code": r[0], "sex": r[1], "age_min": r[2], "age_max": r[3], 
                  "low": r[4], "high": r[5], "crit_low": r[6], "crit_high": r[7], "unit": r[8]})
            created_count += 1
    
    db.commit()
    print(f"  Created {created_count} new reference range records")
    return len(ranges)


def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("Ghana Laboratory Test Catalog Seeder")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        create_option_sets(db)
        create_lab_tests(db)
        create_lab_templates(db)
        create_reference_ranges(db)
        
        print("\n" + "=" * 60)
        print("Seeding completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
