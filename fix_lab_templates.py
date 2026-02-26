#!/usr/bin/env python3
"""
Fix Lab Templates Script - Using direct SQL to avoid model relationship issues

This script regenerates all lab test templates with the proper schema format:
- layout.sections with title, rows, columns, items
- fields as a dict with field_id keys
- rules.visibility
- calculated

Run this script to fix templates causing errors like 'list object has no attribute layout'.

Usage:
    python3 fix_lab_templates.py
"""
import os
import sys
import json

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from uuid import UUID

from app.core.config import settings

# Database setup
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def convert_to_proper_schema(schema_json, template_name="Unknown"):
    """
    Convert any schema format to the proper format with:
    - layout.sections
    - fields as dict
    - rules.visibility
    - calculated
    """
    # Handle None
    if schema_json is None:
        return _create_empty_schema(template_name)
    
    # Handle list format (old format)
    if isinstance(schema_json, list):
        print(f"  -> Converting list format to dict for {template_name}")
        fields_dict = {}
        for fld in schema_json:
            if isinstance(fld, dict):
                field_id = fld.get('field_name') or fld.get('code') or fld.get('id')
                if field_id:
                    fields_dict[field_id] = fld
        
        return {
            "meta": {"name": template_name, "version": 1},
            "layout": {
                "sections": [{
                    "id": "sec_results",
                    "title": "Results",
                    "rows": [{
                        "columns": [{
                            "width": 12,
                            "items": list(fields_dict.keys())
                        }]
                    }]
                }]
            },
            "fields": fields_dict,
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    
    # Handle dict format (proper format but may be incomplete)
    if isinstance(schema_json, dict):
        result = schema_json.copy()
        
        # Ensure meta
        if "meta" not in result:
            result["meta"] = {"name": template_name, "version": 1}
        
        # Ensure layout.sections
        if "layout" not in result:
            result["layout"] = {"sections": []}
        elif isinstance(result["layout"], list):
            # Convert list to dict format
            print(f"  -> Converting layout from list to dict for {template_name}")
            sections = result["layout"]
            result["layout"] = {
                "sections": sections if sections else []
            }
        
        # Ensure layout has sections key
        if isinstance(result.get("layout"), dict) and "sections" not in result["layout"]:
            result["layout"]["sections"] = []
        
        # Ensure fields is a dict
        if "fields" not in result:
            result["fields"] = {}
        elif isinstance(result["fields"], list):
            print(f"  -> Converting fields from list to dict for {template_name}")
            fields_dict = {}
            for fld in result["fields"]:
                if isinstance(fld, dict):
                    field_id = fld.get('field_name') or fld.get('code') or fld.get('id')
                    if field_id:
                        fields_dict[field_id] = fld
            result["fields"] = fields_dict
        
        # Ensure rules
        if "rules" not in result:
            result["rules"] = {"visibility": [], "requiredIf": []}
        elif isinstance(result["rules"], list):
            # Convert list to dict format
            print(f"  -> Converting rules from list to dict for {template_name}")
            result["rules"] = {"visibility": result["rules"], "requiredIf": []}
        
        # Ensure rules has visibility
        if isinstance(result.get("rules"), dict) and "visibility" not in result["rules"]:
            result["rules"]["visibility"] = []
        
        # Ensure calculated
        if "calculated" not in result:
            result["calculated"] = []
        
        return result
    
    # Unknown format, return empty schema
    print(f"  -> Unknown schema format for {template_name}, creating empty schema")
    return _create_empty_schema(template_name)


def _create_empty_schema(name):
    """Create an empty proper schema"""
    return {
        "meta": {"name": name, "version": 1},
        "layout": {"sections": []},
        "fields": {},
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }


def fix_templates():
    """Fix all lab templates in the database using direct SQL"""
    db = SessionLocal()
    
    try:
        # Get all templates with their versions using raw SQL
        query = text("""
            SELECT t.id::text as template_id, t.name, t.discipline, t.status, t.current_version,
                   v.id::text as version_id, v.version, v.status as version_status, v.schema_json
            FROM lab_templates t
            LEFT JOIN lab_template_versions v ON t.id::text = v.template_id::text
            ORDER BY t.name, v.version
        """)
        
        result = db.execute(query)
        rows = result.fetchall()
        
        print(f"\nFound {len(rows)} template versions to process\n")
        
        fixed_count = 0
        template_count = 0
        
        current_template_id = None
        
        for row in rows:
            template_id = row[0]  # Keep as string
            template_name = row[1]
            version_id = row[5]  # Keep as string - it's the actual ID
            schema_json = row[8]  # Already a dict
            
            if template_id != current_template_id:
                current_template_id = template_id
                template_count += 1
                print(f"Processing: {template_name}")
            
            # Convert schema
            new_schema = convert_to_proper_schema(schema_json, template_name)
            
            # Check if schema changed
            if schema_json != new_schema:
                print(f"  -> Fixed version {row[7]}")
                
                # Update the database
                update_query = text("""
                    UPDATE lab_template_versions 
                    SET schema_json = :schema_json
                    WHERE id = :version_id
                """)
                db.execute(update_query, {"schema_json": json.dumps(new_schema), "version_id": version_id})
                fixed_count += 1
            else:
                print(f"  -> Version {row[7]} already proper")
        
        db.commit()
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Templates processed: {template_count}")
        print(f"  Schema versions fixed: {fixed_count}")
        print(f"{'='*60}\n")
        
        return fixed_count
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_option_sets():
    """Create option sets using direct SQL"""
    db = SessionLocal()
    from uuid import UUID  # Import here
    
    try:
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
            "HEPATITIS_B_SURFACE": ["Non-reactive", "Reactive"],
            "HEPATITIS_C_RESULT": ["Non-reactive", "Reactive"],
            "HIV_RESULT": ["Negative", "Positive", "Indeterminate"],
            "SYPHILIS_RESULT": ["Non-reactive", "Reactive"],
            "URINE_COLOR": ["Pale Yellow", "Yellow", "Dark Yellow", "Amber", "Brown", "Red"],
            "URINE_CLARITY": ["Clear", "Slightly Cloudy", "Cloudy", "Turbid"],
            "STOOL_APPEARANCE": ["Formed", "Soft", "Watery", "Mucoid", "Bloody"],
            "STOOL_OCCULT_BLOOD": ["Negative", "Positive"],
            "GRAM_STAIN_RESULT": ["No organisms seen", "Gram positive cocci", "Gram negative cocci", 
                                   "Gram positive rods", "Gram negative rods", "Mixed flora"],
        }
        
        print("Creating option sets...")
        
        for code, options in option_sets_data.items():
            # Check if exists
            check_query = text("SELECT id FROM lab_option_sets WHERE code = :code")
            existing = db.execute(check_query, {"code": code}).fetchone()
            
            if not existing:
                insert_query = text("""
                    INSERT INTO lab_option_sets (id, code, options_json, created_at)
                    VALUES (:id, :code, :options_json, NOW())
                """)
                db.execute(insert_query, {
                    "id": str(UUID()),
                    "code": code,
                    "options_json": json.dumps(options)
                })
        
        db.commit()
        print(f"Created {len(option_sets_data)} option sets\n")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_comprehensive_templates():
    """Create comprehensive lab test templates using direct SQL"""
    db = SessionLocal()
    
    try:
        # Get admin user ID
        user_query = text("SELECT id FROM users ORDER BY id LIMIT 1")
        user_result = db.execute(user_query).fetchone()
        admin_user_id = user_result[0] if user_result else 1
        
        # Define templates
        templates_to_create = [
            _create_cbc_schema(),
            _create_lft_schema(),
            _create_rft_schema(),
            _create_lipid_profile_schema(),
            _create_urinalysis_schema(),
            _create_stool_exam_schema(),
            _create_hiv_schema(),
            _create_hepatitis_schema(),
            _create_syphilis_schema(),
            _create_malaria_schema(),
            _create_sickling_schema(),
            _create_pt_inr_schema(),
            _create_blood_group_schema(),
        ]
        
        created_count = 0
        
        for template_data in templates_to_create:
            # Check if template already exists
            check_query = text("SELECT id FROM lab_templates WHERE name = :name")
            existing = db.execute(check_query, {"name": template_data["name"]}).fetchone()
            
            if existing:
                print(f"Template '{template_data['name']}' already exists, skipping")
                continue
            
            template_id = str(UUID())
            version_id = str(UUID())
            
            # Create template
            insert_template = text("""
                INSERT INTO lab_templates (id, name, discipline, status, current_version, created_by_id, created_at)
                VALUES (:id, :name, :discipline, :status, :current_version, :created_by_id, NOW())
            """)
            db.execute(insert_template, {
                "id": template_id,
                "name": template_data["name"],
                "discipline": template_data["discipline"],
                "status": "PUBLISHED",
                "current_version": 1,
                "created_by_id": admin_user_id
            })
            
            # Create version
            insert_version = text("""
                INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, change_note, created_by_id, created_at)
                VALUES (:id, :template_id, :version, :status, :schema_json, :change_note, :created_by_id, NOW())
            """)
            db.execute(insert_version, {
                "id": version_id,
                "template_id": template_id,
                "version": 1,
                "status": "PUBLISHED",
                "schema_json": json.dumps(template_data["schema"]),
                "change_note": f"Initial {template_data['name']} template",
                "created_by_id": admin_user_id
            })
            
            print(f"Created template: {template_data['name']} ({template_data['discipline']})")
            created_count += 1
        
        db.commit()
        print(f"\nCreated {created_count} new templates\n")
        return created_count
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def _create_cbc_schema():
    """Complete Blood Count schema"""
    return {
        "name": "Complete Blood Count (CBC)",
        "discipline": "HEMATOLOGY",
        "schema": {
            "meta": {"name": "Complete Blood Count (CBC)", "discipline": "HEMATOLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_hemoglobin", "title": "Hemoglobin & Hematocrit", "rows": [{"columns": [{"width": 6, "items": ["hb", "hct"]}]}]},
                    {"id": "sec_rbc", "title": "Red Blood Cell Indices", "rows": [{"columns": [{"width": 6, "items": ["rbc_count", "mcv", "mch", "mchc"]}]}]},
                    {"id": "sec_wbc", "title": "White Blood Cell Count", "rows": [{"columns": [{"width": 12, "items": ["wbc_count"]}]}]},
                    {"id": "sec_differential", "title": "Differential Count", "rows": [{"columns": [{"width": 6, "items": ["neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]}]}]},
                    {"id": "sec_platelets", "title": "Platelets", "rows": [{"columns": [{"width": 12, "items": ["platelet_count"]}]}]},
                    {"id": "sec_morphology", "title": "Morphology", "rows": [{"columns": [{"width": 12, "items": ["rbcmorph", "wbc_morph", "platelet_morph"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "hb": {"code": "hb", "label": "Hemoglobin (Hb)", "type": "numeric", "unit": "g/dL", "decimals": 1, "critical": True, "critical_low": 7.0, "critical_high": 20.0},
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
                "rbcmorph": {"code": "rbcmorph", "label": "RBC Morphology", "type": "multichoice", "optionSet": "RBC_MORPHOLOGY"},
                "wbc_morph": {"code": "wbc_morph", "label": "WBC Morphology", "type": "multichoice", "optionSet": "WBC_MORPHOLOGY"},
                "platelet_morph": {"code": "platelet_morph", "label": "Platelet Morphology", "type": "choice", "optionSet": "PLATELET_MORPHOLOGY"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_lft_schema():
    """Liver Function Tests schema"""
    return {
        "name": "Liver Function Tests (LFT)",
        "discipline": "CHEMISTRY",
        "schema": {
            "meta": {"name": "Liver Function Tests (LFT)", "discipline": "CHEMISTRY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_bilirubin", "title": "Bilirubin", "rows": [{"columns": [{"width": 6, "items": ["total_bili", "direct_bili"]}]}]},
                    {"id": "sec_enzymes", "title": "Liver Enzymes", "rows": [{"columns": [{"width": 6, "items": ["alt", "ast", "alp", "ggt"]}]}]},
                    {"id": "sec_proteins", "title": "Proteins", "rows": [{"columns": [{"width": 6, "items": ["total_protein", "albumin", "globulin"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "total_bili": {"code": "total_bili", "label": "Total Bilirubin", "type": "numeric", "unit": "µmol/L", "decimals": 1},
                "direct_bili": {"code": "direct_bili", "label": "Direct Bilirubin", "type": "numeric", "unit": "µmol/L", "decimals": 1},
                "alt": {"code": "alt", "label": "ALT (SGPT)", "type": "numeric", "unit": "U/L", "decimals": 0},
                "ast": {"code": "ast", "label": "AST (SGOT)", "type": "numeric", "unit": "U/L", "decimals": 0},
                "alp": {"code": "alp", "label": "ALP", "type": "numeric", "unit": "U/L", "decimals": 0},
                "ggt": {"code": "ggt", "label": "GGT", "type": "numeric", "unit": "U/L", "decimals": 0},
                "total_protein": {"code": "total_protein", "label": "Total Protein", "type": "numeric", "unit": "g/L", "decimals": 1},
                "albumin": {"code": "albumin", "label": "Albumin", "type": "numeric", "unit": "g/L", "decimals": 1},
                "globulin": {"code": "globulin", "label": "Globulin", "type": "numeric", "unit": "g/L", "decimals": 1},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_rft_schema():
    """Renal Function Tests schema"""
    return {
        "name": "Renal Function Tests (RFT)",
        "discipline": "CHEMISTRY",
        "schema": {
            "meta": {"name": "Renal Function Tests (RFT)", "discipline": "CHEMISTRY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_renal", "title": "Renal Function", "rows": [{"columns": [{"width": 6, "items": ["creatinine", "urea", "uric_acid"]}]}]},
                    {"id": "sec_electrolytes", "title": "Electrolytes", "rows": [{"columns": [{"width": 6, "items": ["sodium", "potassium", "chloride", "bicarbonate"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "creatinine": {"code": "creatinine", "label": "Creatinine", "type": "numeric", "unit": "µmol/L", "decimals": 0},
                "urea": {"code": "urea", "label": "Urea", "type": "numeric", "unit": "mmol/L", "decimals": 1},
                "uric_acid": {"code": "uric_acid", "label": "Uric Acid", "type": "numeric", "unit": "µmol/L", "decimals": 0},
                "sodium": {"code": "sodium", "label": "Sodium (Na)", "type": "numeric", "unit": "mmol/L", "decimals": 0, "critical": True, "critical_low": 120, "critical_high": 160},
                "potassium": {"code": "potassium", "label": "Potassium (K)", "type": "numeric", "unit": "mmol/L", "decimals": 1, "critical": True, "critical_low": 2.5, "critical_high": 6.5},
                "chloride": {"code": "chloride", "label": "Chloride (Cl)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
                "bicarbonate": {"code": "bicarbonate", "label": "Bicarbonate (HCO3)", "type": "numeric", "unit": "mmol/L", "decimals": 0},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_lipid_profile_schema():
    """Lipid Profile schema"""
    return {
        "name": "Lipid Profile",
        "discipline": "CHEMISTRY",
        "schema": {
            "meta": {"name": "Lipid Profile", "discipline": "CHEMISTRY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_lipids", "title": "Lipid Profile", "rows": [{"columns": [{"width": 6, "items": ["total_cholesterol", "triglycerides", "hdl", "ldl", "vldl"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "total_cholesterol": {"code": "total_cholesterol", "label": "Total Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "triglycerides": {"code": "triglycerides", "label": "Triglycerides", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "hdl": {"code": "hdl", "label": "HDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "ldl": {"code": "ldl", "label": "LDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "vldl": {"code": "vldl", "label": "VLDL Cholesterol", "type": "numeric", "unit": "mmol/L", "decimals": 2},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_urinalysis_schema():
    """Urinalysis schema"""
    return {
        "name": "Urinalysis",
        "discipline": "URINALYSIS",
        "schema": {
            "meta": {"name": "Urinalysis", "discipline": "URINALYSIS", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_physical", "title": "Physical Examination", "rows": [{"columns": [{"width": 6, "items": ["urine_color", "urine_clarity"]}]}]},
                    {"id": "sec_dipstick", "title": "Dipstick Results", "rows": [{"columns": [{"width": 4, "items": ["dipstick_ph", "dipstick_sg"]}, {"width": 4, "items": ["dipstick_protein", "dipstick_glucose"]}, {"width": 4, "items": ["dipstick_ketones", "dipstick_blood"]}]}]},
                    {"id": "sec_dipstick2", "title": "Dipstick Continued", "rows": [{"columns": [{"width": 4, "items": ["dipstick_bilirubin", "dipstick_urobilinogen"]}, {"width": 4, "items": ["dipstick_nitrite", "dipstick_leukocytes"]}]}]},
                    {"id": "sec_microscopy", "title": "Microscopy", "rows": [{"columns": [{"width": 6, "items": ["wbc_hpf", "rbc_hpf"]}, {"width": 6, "items": ["epithelial_cells", "casts", "crystals", "bacteria"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "urine_color": {"code": "urine_color", "label": "Color", "type": "choice", "optionSet": "URINE_COLOR"},
                "urine_clarity": {"code": "urine_clarity", "label": "Clarity", "type": "choice", "optionSet": "URINE_CLARITY"},
                "dipstick_ph": {"code": "dipstick_ph", "label": "pH", "type": "numeric", "unit": "", "decimals": 1},
                "dipstick_sg": {"code": "dipstick_sg", "label": "Specific Gravity", "type": "numeric", "unit": "", "decimals": 3},
                "dipstick_protein": {"code": "dipstick_protein", "label": "Protein", "type": "choice", "optionSet": "DIPSTICK_PROTEIN"},
                "dipstick_glucose": {"code": "dipstick_glucose", "label": "Glucose", "type": "choice", "optionSet": "DIPSTICK_GLUCOSE"},
                "dipstick_ketones": {"code": "dipstick_ketones", "label": "Ketones", "type": "choice", "optionSet": "DIPSTICK_KETONES"},
                "dipstick_blood": {"code": "dipstick_blood", "label": "Blood", "type": "choice", "optionSet": "DIPSTICK_BLOOD"},
                "dipstick_bilirubin": {"code": "dipstick_bilirubin", "label": "Bilirubin", "type": "choice", "optionSet": "DIPSTICK_BILIRUBIN"},
                "dipstick_urobilinogen": {"code": "dipstick_urobilinogen", "label": "Urobilinogen", "type": "choice", "optionSet": "DIPSTICK_UROBILINOGEN"},
                "dipstick_nitrite": {"code": "dipstick_nitrite", "label": "Nitrite", "type": "choice", "optionSet": "DIPSTICK_NITRITE"},
                "dipstick_leukocytes": {"code": "dipstick_leukocytes", "label": "Leukocytes", "type": "choice", "optionSet": "DIPSTICK_LEUKOCYTES"},
                "wbc_hpf": {"code": "wbc_hpf", "label": "WBC/HPF", "type": "choice", "optionSet": "MICROSCOPY_HPF"},
                "rbc_hpf": {"code": "rbc_hpf", "label": "RBC/HPF", "type": "choice", "optionSet": "MICROSCOPY_HPF"},
                "epithelial_cells": {"code": "epithelial_cells", "label": "Epithelial Cells", "type": "text"},
                "casts": {"code": "casts", "label": "Casts", "type": "text"},
                "crystals": {"code": "crystals", "label": "Crystals", "type": "text"},
                "bacteria": {"code": "bacteria", "label": "Bacteria", "type": "text"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_stool_exam_schema():
    """Stool Examination schema"""
    return {
        "name": "Stool Examination",
        "discipline": "PARASITOLOGY",
        "schema": {
            "meta": {"name": "Stool Examination", "discipline": "PARASITOLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_physical", "title": "Physical Examination", "rows": [{"columns": [{"width": 6, "items": ["stool_color", "stool_consistency"]}]}]},
                    {"id": "sec_microscopy", "title": "Microscopy", "rows": [{"columns": [{"width": 12, "items": ["wet_mount", "gram_stain"]}]}]},
                    {"id": "sec_occult", "title": "Occult Blood", "rows": [{"columns": [{"width": 12, "items": ["occult_blood"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "stool_color": {"code": "stool_color", "label": "Color", "type": "choice", "optionSet": "STOOL_APPEARANCE"},
                "stool_consistency": {"code": "stool_consistency", "label": "Consistency", "type": "choice", "optionSet": "STOOL_APPEARANCE"},
                "wet_mount": {"code": "wet_mount", "label": "Wet Mount", "type": "text"},
                "gram_stain": {"code": "gram_stain", "label": "Gram Stain", "type": "choice", "optionSet": "GRAM_STAIN_RESULT"},
                "occult_blood": {"code": "occult_blood", "label": "Occult Blood", "type": "choice", "optionSet": "STOOL_OCCULT_BLOOD"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_hiv_schema():
    """HIV Test schema"""
    return {
        "name": "HIV Test",
        "discipline": "SEROLOGY",
        "schema": {
            "meta": {"name": "HIV Test", "discipline": "SEROLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_screening", "title": "Screening", "rows": [{"columns": [{"width": 6, "items": ["hiv_screening"]}]}]},
                    {"id": "sec_confirmatory", "title": "Confirmatory", "rows": [{"columns": [{"width": 6, "items": ["hiv_confirmatory"]}]}]},
                    {"id": "sec_result", "title": "Final Result", "rows": [{"columns": [{"width": 6, "items": ["hiv_final"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "hiv_screening": {"code": "hiv_screening", "label": "Screening Test", "type": "choice", "optionSet": "HIV_RESULT"},
                "hiv_confirmatory": {"code": "hiv_confirmatory", "label": "Confirmatory Test", "type": "choice", "optionSet": "HIV_RESULT"},
                "hiv_final": {"code": "hiv_final", "label": "Final Result", "type": "choice", "optionSet": "HIV_RESULT"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_hepatitis_schema():
    """Hepatitis Test schema"""
    return {
        "name": "Hepatitis B & C",
        "discipline": "SEROLOGY",
        "schema": {
            "meta": {"name": "Hepatitis B & C", "discipline": "SEROLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_hepb", "title": "Hepatitis B", "rows": [{"columns": [{"width": 6, "items": ["hepb_surface_ag", "hepb_surface_ab", "hepb_core_ab"]}]}]},
                    {"id": "sec_hepc", "title": "Hepatitis C", "rows": [{"columns": [{"width": 6, "items": ["hepc_ab"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "hepb_surface_ag": {"code": "hepb_surface_ag", "label": "HBsAg", "type": "choice", "optionSet": "HEPATITIS_B_SURFACE"},
                "hepb_surface_ab": {"code": "hepb_surface_ab", "label": "HBsAb", "type": "choice", "optionSet": "HEPATITIS_B_SURFACE"},
                "hepb_core_ab": {"code": "hepb_core_ab", "label": "HBcAb", "type": "choice", "optionSet": "HEPATITIS_B_SURFACE"},
                "hepc_ab": {"code": "hepc_ab", "label": "HCV Antibody", "type": "choice", "optionSet": "HEPATITIS_C_RESULT"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_syphilis_schema():
    """Syphilis Test schema"""
    return {
        "name": "Syphilis Test",
        "discipline": "SEROLOGY",
        "schema": {
            "meta": {"name": "Syphilis Test", "discipline": "SEROLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_screening", "title": "Screening", "rows": [{"columns": [{"width": 6, "items": ["rpr_screening"]}]}]},
                    {"id": "sec_confirmatory", "title": "Confirmatory", "rows": [{"columns": [{"width": 6, "items": ["tpha_confirmatory"]}]}]},
                    {"id": "sec_result", "title": "Final Result", "rows": [{"columns": [{"width": 6, "items": ["syphilis_final"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "rpr_screening": {"code": "rpr_screening", "label": "RPR Screening", "type": "choice", "optionSet": "SYPHILIS_RESULT"},
                "tpha_confirmatory": {"code": "tpha_confirmatory", "label": "TPHA Confirmatory", "type": "choice", "optionSet": "SYPHILIS_RESULT"},
                "syphilis_final": {"code": "syphilis_final", "label": "Final Result", "type": "choice", "optionSet": "SYPHILIS_RESULT"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_malaria_schema():
    """Malaria Test schema"""
    return {
        "name": "Malaria Test (RDT)",
        "discipline": "PARASITOLOGY",
        "schema": {
            "meta": {"name": "Malaria Test (RDT)", "discipline": "PARASITOLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_rdt", "title": "Rapid Diagnostic Test", "rows": [{"columns": [{"width": 6, "items": ["malaria_rdt"]}]}]},
                    {"id": "sec_microscopy", "title": "Microscopy", "rows": [{"columns": [{"width": 6, "items": ["malaria_microscopy"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "malaria_rdt": {"code": "malaria_rdt", "label": "Malaria RDT", "type": "choice", "optionSet": "MALARIA_RDT"},
                "malaria_microscopy": {"code": "malaria_microscopy", "label": "Malaria Microscopy", "type": "choice", "optionSet": "MALARIA_RDT"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_sickling_schema():
    """Sickling Test schema"""
    return {
        "name": "Sickling Test",
        "discipline": "HEMATOLOGY",
        "schema": {
            "meta": {"name": "Sickling Test", "discipline": "HEMATOLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_sickling", "title": "Sickling Test", "rows": [{"columns": [{"width": 6, "items": ["sickling_test"]}]}]},
                    {"id": "sec_hb_electrophoresis", "title": "Hb Electrophoresis", "rows": [{"columns": [{"width": 6, "items": ["hb_electrophoresis"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "sickling_test": {"code": "sickling_test", "label": "Sickling Test", "type": "choice", "optionSet": "SICKLING_TEST"},
                "hb_electrophoresis": {"code": "hb_electrophoresis", "label": "Hb Electrophoresis", "type": "text"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_pt_inr_schema():
    """PT/INR Test schema"""
    return {
        "name": "PT/INR",
        "discipline": "HEMATOLOGY",
        "schema": {
            "meta": {"name": "PT/INR", "discipline": "HEMATOLOGY", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_coagulation", "title": "Coagulation", "rows": [{"columns": [{"width": 6, "items": ["pt_seconds", "pt_inr"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "pt_seconds": {"code": "pt_seconds", "label": "PT (Seconds)", "type": "numeric", "unit": "sec", "decimals": 1},
                "pt_inr": {"code": "pt_inr", "label": "INR", "type": "numeric", "unit": "", "decimals": 2},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


def _create_blood_group_schema():
    """Blood Group schema"""
    return {
        "name": "Blood Grouping",
        "discipline": "BLOODBANK",
        "schema": {
            "meta": {"name": "Blood Grouping", "discipline": "BLOODBANK", "version": 1},
            "layout": {
                "sections": [
                    {"id": "sec_blood_group", "title": "Blood Group", "rows": [{"columns": [{"width": 6, "items": ["abo_group", "rh_factor"]}]}]},
                    {"id": "sec_antibody", "title": "Antibody Screen", "rows": [{"columns": [{"width": 6, "items": ["antibody_screen"]}]}]},
                    {"id": "sec_comment", "title": "Comments", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]},
                ]
            },
            "fields": {
                "abo_group": {"code": "abo_group", "label": "ABO Group", "type": "choice", "optionSet": "BLOOD_GROUP_OPTIONS"},
                "rh_factor": {"code": "rh_factor", "label": "Rh Factor", "type": "choice", "optionSet": "RH_FACTOR"},
                "antibody_screen": {"code": "antibody_screen", "label": "Antibody Screen", "type": "choice", "optionSet": "RH_FACTOR"},
                "comment": {"code": "comment", "label": "Comments", "type": "text"}
            },
            "rules": {"visibility": [], "requiredIf": []},
            "calculated": []
        }
    }


if __name__ == "__main__":
    print("="*60)
    print("Lab Template Fix Script")
    print("="*60)
    
    # Step 1: Fix existing templates
    print("\n[Step 1] Fixing existing templates...")
    fixed = fix_templates()
    
    # Step 2: Create option sets
    print("\n[Step 2] Creating option sets...")
    create_option_sets()
    
    # Step 3: Create comprehensive templates if needed
    print("\n[Step 3] Creating comprehensive templates...")
    created = create_comprehensive_templates()
    
    print("\n" + "="*60)
    print("Done!")
    print(f"  Fixed: {fixed} template versions")
    print(f"  Created: {created} new templates")
    print("="*60)
