#!/usr/bin/env python3
"""
Seed script for Ghana lab test templates.
Creates option sets, templates, and maps to lab_test_catalog.

Usage:
    python3 seed_ghana_lab_templates.py
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
    """Create Ghana-specific option sets."""
    print("Creating option sets...")
    
    option_sets_data = {
        # Dipstick scales
        "DIPSTICK_SCALE": ["Negative", "Trace", "+", "++", "+++"],
        
        # Urine characteristics
        "URINE_COLOUR": ["Straw", "Yellow", "Amber", "Red", "Brown", "Other"],
        "URINE_APPEARANCE": ["Clear", "Slightly turbid", "Turbid"],
        
        # Stool characteristics  
        "STOOL_CONSISTENCY": ["Formed", "Semi-formed", "Watery"],
        "STOOL_COLOUR": ["Brown", "Green", "Black", "Red", "Other"],
        
        # Microbiology
        "ORGANISM_LIST": [
            "Escherichia coli", "Klebsiella pneumoniae", "Pseudomonas aeruginosa",
            "Proteus mirabilis", "Enterococcus faecalis", "Staphylococcus aureus",
            "Staphylococcus epidermidis", "Streptococcus pyogenes", "Streptococcus pneumoniae",
            "Neisseria gonorrhoeae", "Haemophilus influenzae", "Salmonella spp.",
            "Shigella spp.", "Vibrio cholerae", "Candida albicans", "Other"
        ],
        
        # Antibiotics
        "ANTIBIOTIC_LIST": [
            "Amoxicillin", "Ampicillin", "Azithromycin", "Cefotaxime", "Ceftriaxone",
            "Ciprofloxacin", "Clindamycin", "Doxycycline", "Erythromycin", "Gentamicin",
            "Meropenem", "Metronidazole", "Nitrofurantoin", "Penicillin G", "Piperacillin",
            "Tetracycline", "Trimethoprim-Sulfamethoxazole", "Vancomycin", "Other"
        ],
        
        # HIV Kit names
        "HIV_KIT_NAMES": [
            "Determine", "Unigold", "Stat-Pak", "Oral Quick", "First Response", "Other"
        ],
        
        # Blood group
        "BLOOD_GROUP": ["A", "B", "AB", "O"],
        "RH_FACTOR": ["Positive", "Negative"],
        
        # Microscopy
        "MICROSCOPY_HPF": ["0-1", "1-5", "5-10", "10-20", ">20"],
        "MICROSCOPY_LPF": ["0-1", "1-5", "5-10", "10-20", ">20"],
        
        # Malaria
        "MALARIA_RDT": ["Negative", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"],
        "MALARIA_PARASITE": ["None seen", "P. falciparum", "P. vivax", "P. malariae", "P. ovale", "Mixed"],
        "MALARIA_DENSITY": ["<100", "100-500", "500-1000", "1000-5000", ">5000"],
    }
    
    for code, options in option_sets_data.items():
        existing = db.query(LabOptionSet).filter(LabOptionSet.code == code).first()
        if not existing:
            obj = LabOptionSet(code=code, options_json=options)
            db.add(obj)
    
    db.commit()
    print(f"Created {len(option_sets_data)} option sets")
    return option_sets_data


def create_cbc_template(db: Session, admin_user_id: int):
    """Create Complete Blood Count (CBC) template."""
    print("Creating CBC template...")
    
    # Check if exists
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Complete Blood Count (CBC)").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
    schema = {
        "meta": {"name": "Complete Blood Count (CBC)", "discipline": "HEMATOLOGY"},
        "layout": {
            "sections": [
                {"id": "sec_hb", "title": "Hemoglobin & Hematocrit", "rows": [
                    {"columns": [{"items": ["hb"], "width": 6}, {"items": ["hct"], "width": 6}]}
                ]},
                {"id": "sec_rbc", "title": "Red Cell Indices", "rows": [
                    {"columns": [{"items": ["rbc"], "width": 3}, {"items": ["mcv"], "width": 3}, {"items": ["mch"], "width": 3}, {"items": ["mchc"], "width": 3}]}
                ]},
                {"id": "sec_wbc", "title": "White Cell Count", "rows": [
                    {"columns": [{"items": ["twbc"], "width": 4}, {"items": ["neutrophils"], "width": 4}, {"items": ["lymphocytes"], "width": 4}]}
                ]},
                {"id": "sec_platelet", "title": "Platelets", "rows": [
                    {"columns": [{"items": ["platelets"], "width": 12}]}
                ]},
            ]
        },
        "fields": {
            "hb": {"type": "numeric", "label": "Hemoglobin", "code": "hb", "unit": "g/dL", "decimals": 1},
            "hct": {"type": "numeric", "label": "Hematocrit", "code": "hct", "unit": "%", "decimals": 1},
            "rbc": {"type": "numeric", "label": "RBC Count", "code": "rbc", "unit": "x10^12/L", "decimals": 2},
            "mcv": {"type": "numeric", "label": "MCV", "code": "mcv", "unit": "fL", "decimals": 1},
            "mch": {"type": "numeric", "label": "MCH", "code": "mch", "unit": "pg", "decimals": 1},
            "mchc": {"type": "numeric", "label": "MCHC", "code": "mchc", "unit": "g/dL", "decimals": 1},
            "twbc": {"type": "numeric", "label": "Total WBC", "code": "twbc", "unit": "x10^9/L", "decimals": 2},
            "neutrophils": {"type": "numeric", "label": "Neutrophils", "code": "neutrophils", "unit": "x10^9/L", "decimals": 2},
            "lymphocytes": {"type": "numeric", "label": "Lymphocytes", "code": "lymphocytes", "unit": "x10^9/L", "decimals": 2},
            "platelets": {"type": "numeric", "label": "Platelet Count", "code": "platelets", "unit": "x10^9/L", "decimals": 0},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }
    
    tmpl = LabTemplate(name="Complete Blood Count (CBC)", discipline="HEMATOLOGY", status="DRAFT", created_by_id=admin_user_id)
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id, version=1, status="PUBLISHED", schema_json=schema,
        change_note="Initial CBC template", created_by_id=admin_user_id
    )
    db.add(version)
    tmpl.current_version = 1
    tmpl.status = "PUBLISHED"
    
    db.commit()
    print(f"Created CBC template (v1)")
    return tmpl


def create_malaria_rdt_template(db: Session, admin_user_id: int):
    """Create Malaria RDT template."""
    print("Creating Malaria RDT template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Malaria RDT").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
    schema = {
        "meta": {"name": "Malaria RDT", "discipline": "PARASITOLOGY"},
        "layout": {
            "sections": [
                {"id": "sec_result", "title": "Result", "rows": [
                    {"columns": [{"items": ["kit_name", "result"], "width": 6}]}
                ]},
                {"id": "sec_control", "title": "Quality Control", "rows": [
                    {"columns": [{"items": ["control_line"], "width": 12}]}
                ]},
            ]
        },
        "fields": {
            "kit_name": {"type": "choice", "label": "Kit Name", "code": "kit_name", "optionSet": "HIV_KIT_NAMES"},
            "result": {"type": "choice", "label": "Result", "code": "result", "optionSet": "MALARIA_RDT"},
            "control_line": {"type": "choice", "label": "Control Line", "code": "control_line", "options": ["Valid", "Invalid"]},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }
    
    tmpl = LabTemplate(name="Malaria RDT", discipline="PARASITOLOGY", status="DRAFT", created_by_id=admin_user_id)
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id, version=1, status="PUBLISHED", schema_json=schema,
        change_note="Initial Malaria RDT template", created_by_id=admin_user_id
    )
    db.add(version)
    tmpl.current_version = 1
    tmpl.status = "PUBLISHED"
    db.commit()
    print(f"Created Malaria RDT template (v1)")
    return tmpl


def create_urinalysis_template(db: Session, admin_user_id: int):
    """Create Urinalysis template (dipstick + microscopy)."""
    print("Creating Urinalysis template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Urinalysis").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
    schema = {
        "meta": {"name": "Urinalysis", "discipline": "CHEMISTRY"},
        "layout": {
            "sections": [
                {"id": "sec_physical", "title": "Physical Examination", "rows": [
                    {"columns": [{"items": ["colour", "appearance"], "width": 6}]}
                ]},
                {"id": "sec_dipstick", "title": "Dipstick Results", "rows": [
                    {"columns": [{"items": ["ph", "protein", "glucose", "ketones", "blood"], "width": 4}]}
                ]},
                {"id": "sec_microscopy", "title": "Microscopy", "rows": [
                    {"columns": [{"items": ["wbc_hpf", "rbc_hpf", "epithelial", "casts", "crystals", "bacteria"], "width": 4}]}
                ]},
            ]
        },
        "fields": {
            "colour": {"type": "choice", "label": "Colour", "code": "colour", "optionSet": "URINE_COLOUR"},
            "appearance": {"type": "choice", "label": "Appearance", "code": "appearance", "optionSet": "URINE_APPEARANCE"},
            "ph": {"type": "numeric", "label": "pH", "code": "ph", "decimals": 1},
            "protein": {"type": "choice", "label": "Protein", "code": "protein", "optionSet": "DIPSTICK_SCALE"},
            "glucose": {"type": "choice", "label": "Glucose", "code": "glucose", "optionSet": "DIPSTICK_SCALE"},
            "ketones": {"type": "choice", "label": "Ketones", "code": "ketones", "optionSet": "DIPSTICK_SCALE"},
            "blood": {"type": "choice", "label": "Blood", "code": "blood", "optionSet": "DIPSTICK_SCALE"},
            "wbc_hpf": {"type": "choice", "label": "WBC/HPF", "code": "wbc_hpf", "optionSet": "MICROSCOPY_HPF"},
            "rbc_hpf": {"type": "choice", "label": "RBC/HPF", "code": "rbc_hpf", "optionSet": "MICROSCOPY_HPF"},
            "epithelial": {"type": "text", "label": "Epithelial Cells", "code": "epithelial"},
            "casts": {"type": "text", "label": "Casts", "code": "casts"},
            "crystals": {"type": "text", "label": "Crystals", "code": "crystals"},
            "bacteria": {"type": "text", "label": "Bacteria", "code": "bacteria"},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }
    
    tmpl = LabTemplate(name="Urinalysis", discipline="CHEMISTRY", status="DRAFT", created_by_id=admin_user_id)
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id, version=1, status="PUBLISHED", schema_json=schema,
        change_note="Initial Urinalysis template", created_by_id=admin_user_id
    )
    db.add(version)
    tmpl.current_version = 1
    tmpl.status = "PUBLISHED"
    db.commit()
    print(f"Created Urinalysis template (v1)")
    return tmpl


def create_ue_template(db: Session, admin_user_id: int):
    """Create U&E (Urea & Electrolytes) template with anion gap calculation."""
    print("Creating U&E template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Urea & Electrolytes").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
    schema = {
        "meta": {"name": "Urea & Electrolytes (U&E)", "discipline": "CHEMISTRY"},
        "layout": {
            "sections": [
                {"id": "sec_renal", "title": "Renal Function", "rows": [
                    {"columns": [{"items": ["urea", "creatinine"], "width": 6}]}
                ]},
                {"id": "sec_electrolytes", "title": "Electrolytes", "rows": [
                    {"columns": [{"items": ["sodium", "potassium", "chloride", "bicarbonate"], "width": 3}]}
                ]},
                {"id": "sec_calculated", "title": "Calculated", "rows": [
                    {"columns": [{"items": ["anion_gap"], "width": 12}]}
                ]},
            ]
        },
        "fields": {
            "urea": {"type": "numeric", "label": "Urea", "code": "urea", "unit": "mmol/L", "decimals": 1},
            "creatinine": {"type": "numeric", "label": "Creatinine", "code": "creatinine", "unit": "µmol/L", "decimals": 0},
            "sodium": {"type": "numeric", "label": "Sodium (Na+)", "code": "sodium", "unit": "mmol/L", "decimals": 0},
            "potassium": {"type": "numeric", "label": "Potassium (K+)", "code": "potassium", "unit": "mmol/L", "decimals": 1},
            "chloride": {"type": "numeric", "label": "Chloride (Cl-)", "code": "chloride", "unit": "mmol/L", "decimals": 0},
            "bicarbonate": {"type": "numeric", "label": "Bicarbonate (HCO3-)", "code": "bicarbonate", "unit": "mmol/L", "decimals": 0},
            "anion_gap": {"type": "calculated", "label": "Anion Gap", "code": "anion_gap", "unit": "mmol/L", "decimals": 1},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": [
            {"target_code": "anion_gap", "formula": "sodium + potassium - chloride - bicarbonate", "deps": ["sodium", "potassium", "chloride", "bicarbonate"], "decimals": 1}
        ]
    }
    
    tmpl = LabTemplate(name="Urea & Electrolytes", discipline="CHEMISTRY", status="DRAFT", created_by_id=admin_user_id)
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id, version=1, status="PUBLISHED", schema_json=schema,
        change_note="Initial U&E template with anion gap", created_by_id=admin_user_id
    )
    db.add(version)
    tmpl.current_version = 1
    tmpl.status = "PUBLISHED"
    db.commit()
    print(f"Created U&E template (v1)")
    return tmpl


def create_blood_group_template(db: Session, admin_user_id: int):
    """Create Blood Grouping template."""
    print("Creating Blood Group template...")
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Blood Grouping").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
    
    schema = {
        "meta": {"name": "Blood Grouping", "discipline": "BLOODBANK"},
        "layout": {
            "sections": [
                {"id": "sec_abg", "title": "ABO & Rh", "rows": [
                    {"columns": [{"items": ["abo_group", "rh_type"], "width": 6}]}
                ]},
                {"id": "sec_screen", "title": "Screening", "rows": [
                    {"columns": [{"items": ["antibody_screen"], "width": 12}]}
                ]},
            ]
        },
        "fields": {
            "abo_group": {"type": "choice", "label": "ABO Group", "code": "abo_group", "optionSet": "BLOOD_GROUP"},
            "rh_type": {"type": "choice", "label": "Rh Type", "code": "rh_type", "optionSet": "RH_FACTOR"},
            "antibody_screen": {"type": "choice", "label": "Antibody Screen", "code": "antibody_screen", "options": ["Negative", "Positive"]},
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }
    
    tmpl = LabTemplate(name="Blood Grouping", discipline="BLOODBANK", status="DRAFT", created_by_id=admin_user_id)
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id, version=1, status="PUBLISHED", schema_json=schema,
        change_note="Initial Blood Group template", created_by_id=admin_user_id
    )
    db.add(version)
    tmpl.current_version = 1
    tmpl.status = "PUBLISHED"
    db.commit()
    print(f"Created Blood Group template (v1)")
    return tmpl


def map_templates_to_catalog(db: Session):
    """Map templates to lab_test_catalog."""
    print("Mapping templates to catalog...")
    
    # Get templates
    cbc = db.query(LabTemplate).filter(LabTemplate.name == "Complete Blood Count (CBC)").first()
    malaria = db.query(LabTemplate).filter(LabTemplate.name == "Malaria RDT").first()
    urinalysis = db.query(LabTemplate).filter(LabTemplate.name == "Urinalysis").first()
    ue = db.query(LabTemplate).filter(LabTemplate.name == "Urea & Electrolytes").first()
    blood_group = db.query(LabTemplate).filter(LabTemplate.name == "Blood Grouping").first()
    
    # Common test names in Ghana
    test_mappings = [
        # CBC
        ("Complete Blood Count", "CBC", cbc),
        ("Full Blood Count", "FBC", cbc),
        ("Hemoglobin", "Hb", cbc),
        
        # Malaria
        ("Malaria RDT", "MRDT", malaria),
        ("Malaria Rapid Test", "MRDT", malaria),
        ("Malaria Parasite", "MP", malaria),
        
        # Urinalysis
        ("Urinalysis", "U&E", urinalysis),
        ("Urine R/E", "U&R/E", urinalysis),
        
        # U&E
        ("Urea & Electrolytes", "U&E", ue),
        ("Renal Function Test", "RFT", ue),
        ("Electrolytes", "ELECT", ue),
        
        # Blood Group
        ("Blood Group", "BG", blood_group),
        ("ABO & Rh", "ABO", blood_group),
        ("Blood Typing", "BT", blood_group),
    ]
    
    mapped = 0
    for test_name, test_code, template in test_mappings:
        if not template:
            continue
        test = db.query(LabTest).filter(
            (LabTest.test_name.ilike(f"%{test_name}%")) | (LabTest.test_code == test_code)
        ).first()
        
        if test:
            test.template_id = template.id
            test.template_version = 1
            mapped += 1
            print(f"  Mapped: {test.test_name} -> {template.name}")
        else:
            # Create test if not exists
            test = LabTest(
                test_name=test_name,
                test_code=test_code,
                test_category="Ghana Standard",
                template_id=template.id,
                template_version=1,
                is_active=True
            )
            db.add(test)
            mapped += 1
            print(f"  Created & Mapped: {test_name} -> {template.name}")
    
    db.commit()
    print(f"Mapped {mapped} tests to templates")
    return mapped


def create_reference_ranges(db: Session):
    """Create reference ranges for common tests."""
    print("Creating reference ranges...")
    
    ranges_data = [
        # CBC - Adult male
        {"field_code": "hb", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": 13.0, "high": 17.5, "unit": "g/dL"},
        # CBC - Adult female
        {"field_code": "hb", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": 11.5, "high": 16.0, "unit": "g/dL"},
        # CBC - Child
        {"field_code": "hb", "sex": "ANY", "age_min_days": 365, "age_max_days": 6570, "low": 11.0, "high": 14.0, "unit": "g/dL"},
        
        # Platelets
        {"field_code": "platelets", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": 150, "high": 400, "unit": "x10^9/L"},
        
        # WBC
        {"field_code": "twbc", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 4.0, "high": 11.0, "unit": "x10^9/L"},
        
        # Glucose
        {"field_code": "glucose_val", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 3.9, "high": 6.1, "unit": "mmol/L"},
        
        # Urea
        {"field_code": "urea", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": 2.5, "high": 7.0, "unit": "mmol/L"},
        
        # Creatinine
        {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": 62, "high": 115, "unit": "µmol/L"},
        {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": 44, "high": 97, "unit": "µmol/L"},
        
        # Sodium
        {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500, "low": 136, "high": 145, "unit": "mmol/L"},
        
        # Potassium
        {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "age_max_days": 36500, "low": 3.5, "high": 5.0, "unit": "mmol/L"},
    ]
    
    for r in ranges_data:
        existing = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == r["field_code"],
            LabReferenceRange.sex == r["sex"]
        ).first()
        if not existing:
            rr = LabReferenceRange(**r)
            db.add(rr)
    
    db.commit()
    print(f"Created {len(ranges_data)} reference ranges")
    return len(ranges_data)


def main():
    db = SessionLocal()
    try:
        # Get admin user
        admin = db.query(User).filter(User.role_id == 1).first()
        if not admin:
            print("No admin user found. Creating with user_id=1")
            admin_id = 1
        else:
            admin_id = admin.id
        
        # Create option sets
        create_option_sets(db)
        
        # Create templates
        create_cbc_template(db, admin_id)
        create_malaria_rdt_template(db, admin_id)
        create_urinalysis_template(db, admin_id)
        create_ue_template(db, admin_id)
        create_blood_group_template(db, admin_id)
        
        # Map to catalog
        map_templates_to_catalog(db)
        
        # Create reference ranges
        create_reference_ranges(db)
        
        print("\n=== Ghana Lab Templates Seed Complete ===")
        print("Templates created: CBC, Malaria RDT, Urinalysis, U&E, Blood Group")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
