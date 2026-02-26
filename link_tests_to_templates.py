#!/usr/bin/env python3
"""
Link Lab Tests to Templates

This script links existing lab tests to their corresponding templates
based on name matching and code matching.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import LabTemplate, LabTemplateVersion

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Mapping of test codes to template names
TEST_CODE_TO_TEMPLATE = {
    "CBC": "Complete Blood Count (CBC)",
    "FBG": "Fasting Blood Glucose",
    "PBS": "Peripheral Blood Smear",
    "HB": "Haemoglobin (Hb)",
    "FBC": "Full Blood Count (FBC)",
    "PPBG": "Random Blood Glucose",
    "LFT": "Liver Function Tests (LFT)",
    "RFT": "Renal Function Tests (RFT)",
    "ELECT": "Serum Electrolytes (Na, K, Cl, HCO3)",
    "LIPID": "Lipid Profile",
    "MAL": "Malaria Rapid Diagnostic Test (RDT)",
    "INR": "Coagulation Profile (PT, APTT, INR)",
    "DATBB": "Direct Coombs Test (DAT) - Blood Bank",
    "IAT": "Indirect Coombs Test (IAT)",
    "PLT": "Platelet Count",
    "FE": "Iron Studies (Iron, Ferritin, TIBC)",
    "TIBC": "Iron Studies (Iron, Ferritin, TIBC)",
    "IBIL": "Indirect Bilirubin",
    "GLOB": "Total Protein",
    "AGRATIO": "Total Protein",
    "EGFR": "Creatinine",
    "HSCRP": "C-Reactive Protein (CRP)",
    "TT4": "Free T4 (fT4)",
    "TT3": "Free T3 (fT3)",
    "UPCR": "Urinalysis",
    "UACR": "Urinalysis",
    "24UP": "Urinalysis",
    "ABSCR": "Blood Grouping (ABO & Rh)",
    "DAT": "Direct Coombs Test (DAT) - Blood Bank",
    "FOBT": "Stool Microscopy (Ova & Cysts)",
    "UCULT": "Urine Culture & Sensitivity",
    "SPCULT": "Sputum for AFB",
    "WCULT": "Wound Swab Culture",
    "TCULT": "Throat Swab Culture",
    "ECULT": "Ear Swab Culture",
    "EYECULT": "Eye Swab Culture",
    "VCULT": "Vaginal Swab Culture",
    "CSF": "CSF Analysis",
    "PLEURAL": "Pleural Fluid Analysis",
}


def normalize_name(name):
    """Normalize name for matching."""
    return name.lower().strip().replace("(", "").replace(")", "").replace("  ", " ")


def link_tests_to_templates(db: Session):
    """Link lab tests to their templates."""
    
    # Get all tests without templates
    tests = db.query(LabTest).filter(LabTest.template_id == None).all()
    
    # Get all templates
    all_templates = db.query(LabTemplate).all()
    templates_by_name = {normalize_name(t.name): t for t in all_templates}
    templates_by_code = {t.name.lower(): t for t in all_templates}
    
    linked_count = 0
    
    for test in tests:
        matched = False
        
        # Try by test code
        if test.test_code in TEST_CODE_TO_TEMPLATE:
            template_name = TEST_CODE_TO_TEMPLATE[test.test_code]
            template = templates_by_name.get(normalize_name(template_name))
            if template:
                test.template_id = template.id
                test.template_version = 1
                linked_count += 1
                print(f"  [{test.test_code}] {test.test_name} -> {template.name} (by code)")
                matched = True
        
        # Try by test name
        if not matched:
            test_name_norm = normalize_name(test.test_name)
            for tmpl_name, template in templates_by_name.items():
                # Check if test name is in template name or vice versa
                if test_name_norm in tmpl_name or tmpl_name in test_name_norm:
                    test.template_id = template.id
                    test.template_version = 1
                    linked_count += 1
                    print(f"  [{test.test_code}] {test.test_name} -> {template.name} (by name)")
                    matched = True
                    break
        
        if not matched:
            print(f"  [{test.test_code}] {test.test_name} -> NOT MATCHED")
    
    db.commit()
    return linked_count


def main():
    print("Linking Lab Tests to Templates...")
    
    db = SessionLocal()
    try:
        linked = link_tests_to_templates(db)
        print(f"\n✓ Linked {linked} tests to templates")
        
        # Verify remaining
        remaining = db.query(LabTest).filter(LabTest.template_id == None).count()
        print(f"  Remaining tests without templates: {remaining}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
