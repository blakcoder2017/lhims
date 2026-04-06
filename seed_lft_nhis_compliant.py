#!/usr/bin/env python3
"""
NHIS-Compliant Liver Function Test (LFT) Template Seeder
==========================================================

This script creates/updates the LFT template with:
- All 10 required parameters with proper units
- Age and gender-based reference ranges
- Decimal numeric input validation
- Low/Normal/High flagging
- Critical value alerts
- Auto-calculation for Globulin (Total Protein - Albumin)
- Pattern interpretation (Hepatocellular vs Cholestatic)
- NHIS-ready claim configuration

Usage:
    DATABASE_URL=postgresql://user:pass@host:port/db python seed_lft_nhis_compliant.py
"""

import sys
import os
import json
from datetime import datetime
from decimal import Decimal

# Use environment variable or default
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost/lhims')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()


def get_admin_user():
    """Get admin user ID."""
    result = db.execute(text("SELECT id FROM users WHERE username = 'admin' LIMIT 1"))
    row = result.fetchone()
    if row:
        return row[0]
    
    # Try to get first user
    result = db.execute(text("SELECT id FROM users LIMIT 1"))
    row = result.fetchone()
    if row:
        return row[0]
    
    return 1  # Default fallback


def create_lft_nhis_template(admin_user_id: int):
    """Create NHIS-compliant Liver Function Test template with all 10 parameters."""
    
    print("=" * 70)
    print("CREATING NHIS-COMPLIANT LFT TEMPLATE")
    print("=" * 70)
    
    # Check for existing LFT template
    result = db.execute(text(
        "SELECT id, name FROM lab_templates WHERE name ILIKE '%Liver Function Test%' LIMIT 1"
    ))
    row = result.fetchone()
    
    if row:
        existing_id = row[0]
        print(f"Found existing LFT template: {existing_id}")
        
        # Get latest version
        result = db.execute(text("""
            SELECT version FROM lab_template_versions 
            WHERE template_id = :tid 
            ORDER BY version DESC LIMIT 1
        """), {"tid": existing_id})
        vrow = result.fetchone()
        current_version = vrow[0] if vrow else 1
    else:
        existing_id = None
        current_version = 0
    
    # Complete LFT Schema
    lft_schema = {
        "meta": {
            "name": "Liver Function Test (LFT)",
            "discipline": "CHEMISTRY",
            "description": "NHIS-compliant Liver Function Test panel with comprehensive liver health assessment",
            "version": current_version + 1,
            "nhis_compliant": True,
            "test_code": "LFT",
            "category": "Biochemistry",
            "specimen_type": "Serum",
            "panel_type": "BUNDLED",
            "claim_flags": {
                "diagnosis_required": True,
                "result_required": True,
                "specimen_required": True
            },
            "tat_hours": 6,
            "instructions": "Fast for 8-12 hours before sample collection. Avoid alcohol and fatty meals."
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_proteins",
                    "title": "Protein Profile",
                    "order": 1,
                    "rows": [
                        {
                            "columns": [
                                {"width": 4, "items": ["total_protein"]},
                                {"width": 4, "items": ["albumin"]},
                                {"width": 4, "items": ["globulin"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_enzymes",
                    "title": "Liver Enzymes",
                    "order": 2,
                    "rows": [
                        {
                            "columns": [
                                {"width": 3, "items": ["alt"]},
                                {"width": 3, "items": ["ast"]},
                                {"width": 3, "items": ["ggt"]},
                                {"width": 3, "items": ["alp"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_bilirubin",
                    "title": "Bilirubin Profile",
                    "order": 3,
                    "rows": [
                        {
                            "columns": [
                                {"width": 4, "items": ["total_bilirubin"]},
                                {"width": 4, "items": ["direct_bilirubin"]},
                                {"width": 4, "items": ["indirect_bilirubin"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_interpretation",
                    "title": "Clinical Interpretation",
                    "order": 4,
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["interpretation"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Additional Notes",
                    "order": 5,
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["comment"]}
                            ]
                        }
                    ]
                }
            ]
        },
        "fields": {
            "total_protein": {
                "code": "total_protein",
                "label": "Total Protein",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "g/L",
                "decimals": 1,
                "min_value": 0,
                "max_value": 150,
                "required": True,
                "critical": {"low": 30.0, "high": 100.0},
                "default_range": {"adult": {"low": 60.0, "high": 80.0}, "child": {"low": 55.0, "high": 75.0}}
            },
            "albumin": {
                "code": "albumin",
                "label": "Albumin",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "g/L",
                "decimals": 1,
                "min_value": 0,
                "max_value": 80,
                "required": True,
                "critical": {"low": 20.0, "high": 60.0},
                "default_range": {"adult": {"low": 35.0, "high": 50.0}, "child": {"low": 30.0, "high": 50.0}}
            },
            "globulin": {
                "code": "globulin",
                "label": "Globulin",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "g/L",
                "decimals": 1,
                "required": False,
                "calculated": True,
                "formula": "total_protein - albumin",
                "editable": True,
                "default_range": {"adult": {"low": 20.0, "high": 35.0}, "child": {"low": 20.0, "high": 30.0}}
            },
            "alt": {
                "code": "alt",
                "label": "ALT (SGPT)",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "U/L",
                "decimals": 0,
                "required": True,
                "critical": {"high": 500.0},
                "gender_specific": True,
                "default_range": {"adult_male": {"low": 0.0, "high": 41.0}, "adult_female": {"low": 0.0, "high": 31.0}, "child": {"low": 0.0, "high": 45.0}}
            },
            "ast": {
                "code": "ast",
                "label": "SGOT (AST)",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "U/L",
                "decimals": 0,
                "required": True,
                "critical": {"high": 500.0},
                "gender_specific": True,
                "default_range": {"adult_male": {"low": 0.0, "high": 40.0}, "adult_female": {"low": 0.0, "high": 35.0}, "child": {"low": 0.0, "high": 45.0}}
            },
            "ggt": {
                "code": "ggt",
                "label": "Gamma-GT (GGT)",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "U/L",
                "decimals": 0,
                "required": True,
                "critical": {"high": 200.0},
                "gender_specific": True,
                "default_range": {"adult_male": {"low": 10.0, "high": 71.0}, "adult_female": {"low": 6.0, "high": 42.0}, "child": {"low": 5.0, "high": 32.0}}
            },
            "alp": {
                "code": "alp",
                "label": "Alkaline Phosphatase",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "U/L",
                "decimals": 0,
                "required": True,
                "critical": {"high": 400.0},
                "age_specific": True,
                "default_range": {"adult": {"low": 44.0, "high": 147.0}, "child": {"low": 100.0, "high": 320.0}}
            },
            "total_bilirubin": {
                "code": "total_bilirubin",
                "label": "Total Bilirubin",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "µmol/L",
                "decimals": 1,
                "required": True,
                "critical": {"high": 171.0},
                "default_range": {"adult": {"low": 5.0, "high": 21.0}, "child": {"low": 5.0, "high": 17.0}}
            },
            "direct_bilirubin": {
                "code": "direct_bilirubin",
                "label": "Direct (Conjugated) Bilirubin",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "µmol/L",
                "decimals": 1,
                "required": True,
                "critical": {"high": 85.0},
                "default_range": {"all": {"low": 0.0, "high": 7.0}}
            },
            "indirect_bilirubin": {
                "code": "indirect_bilirubin",
                "label": "Indirect (Unconjugated) Bilirubin",
                "type": "numeric",
                "data_type": "decimal",
                "unit": "µmol/L",
                "decimals": 1,
                "required": False,
                "calculated": True,
                "formula": "total_bilirubin - direct_bilirubin",
                "editable": True,
                "default_range": {"all": {"low": 3.0, "high": 14.0}}
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Clinical Interpretation",
                "type": "select",
                "optionSet": "LFT_INTERPRETATION",
                "required": False
            },
            "comment": {
                "code": "comment",
                "label": "Additional Notes",
                "type": "text",
                "required": False
            }
        },
        "optionSets": {
            "LFT_INTERPRETATION": [
                {"value": "normal", "label": "Normal Liver Function"},
                {"value": "hepatocellular", "label": "Hepatocellular Injury Pattern"},
                {"value": "cholestatic", "label": "Cholestatic Pattern"},
                {"value": "mixed", "label": "Mixed Pattern"},
                {"value": "jaundice", "label": "Jaundice - Elevated Bilirubin"},
                {"value": "hemolysis", "label": "Suspected Hemolysis"},
                {"value": "alcoholic", "label": "Alcoholic Liver Disease"},
                {"value": "viral", "label": "Viral Hepatitis Pattern"},
                {"value": "drug_induced", "label": "Drug-Induced Liver Injury"}
            ]
        },
        "rules": {
            "autoCalculate": [
                {"target": "globulin", "formula": "total_protein - albumin", "trigger": ["total_protein", "albumin"]},
                {"target": "indirect_bilirubin", "formula": "total_bilirubin - direct_bilirubin", "trigger": ["total_bilirubin", "direct_bilirubin"]}
            ],
            "patternRecognition": [
                {
                    "name": "Hepatocellular Injury",
                    "description": "ALT and AST elevated, often ALT > AST",
                    "conditions": [
                        {"field": "alt", "operator": ">", "threshold": "upper_limit", "weight": 2},
                        {"field": "ast", "operator": ">", "threshold": "upper_limit", "weight": 2}
                    ],
                    "pattern_code": "hepatocellular"
                },
                {
                    "name": "Cholestatic Pattern",
                    "description": "ALP and GGT elevated",
                    "conditions": [
                        {"field": "alp", "operator": ">", "threshold": "upper_limit", "weight": 2},
                        {"field": "ggt", "operator": ">", "threshold": "upper_limit", "weight": 2}
                    ],
                    "pattern_code": "cholestatic"
                },
                {
                    "name": "Jaundice",
                    "description": "Elevated bilirubin levels",
                    "conditions": [{"field": "total_bilirubin", "operator": ">", "threshold": 30, "weight": 1}],
                    "pattern_code": "jaundice"
                }
            ],
            "criticalAlerts": [
                {"field": "total_bilirubin", "condition": ">171", "message": "CRITICAL: Severe hyperbilirubinemia"},
                {"field": "alt", "condition": ">500", "message": "CRITICAL: Severely elevated ALT"},
                {"field": "ast", "condition": ">500", "message": "CRITICAL: Severely elevated AST"},
                {"field": "albumin", "condition": "<20", "message": "CRITICAL: Severely low albumin"}
            ]
        },
        "validation": {
            "decimal_precision": {
                "total_protein": 1, "albumin": 1, "globulin": 1, "alt": 0, "ast": 0, "ggt": 0, "alp": 0,
                "total_bilirubin": 1, "direct_bilirubin": 1, "indirect_bilirubin": 1
            },
            "flagging": {"enabled": True}
        },
        "reporting": {
            "display_order": ["total_protein", "albumin", "globulin", "alt", "ast", "ggt", "alp",
                            "total_bilirubin", "direct_bilirubin", "indirect_bilirubin"],
            "include_units": True,
            "include_reference_ranges": True,
            "include_flag": True,
            "nhis_export_format": True,
            "structured_export": {"api": True, "csv": True, "nhis_claims": True}
        }
    }
    
    schema_json_str = json.dumps(lft_schema)
    
    if existing_id:
        # Update existing template
        db.execute(text("""
            UPDATE lab_templates 
            SET name = :name, discipline = :discipline, status = 'DRAFT', updated_at = NOW()
            WHERE id = :id
        """), {"name": "Liver Function Test (LFT)", "discipline": "CHEMISTRY", "id": existing_id})
        
        # Create new version
        db.execute(text("""
            INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, change_note, created_by_id, created_at)
            VALUES (gen_random_uuid(), :template_id, :version, 'DRAFT', :schema_json, :change_note, :created_by_id, NOW())
        """), {
            "template_id": existing_id,
            "version": current_version + 1,
            "schema_json": schema_json_str,
            "change_note": "NHIS-compliant update - Added Indirect Bilirubin, improved reference ranges, pattern recognition",
            "created_by_id": admin_user_id
        })
        
        print(f"Updated LFT template and created new draft version {current_version + 1}")
        template_id = existing_id
    else:
        # Create new template
        template_id = None
        db.execute(text("""
            INSERT INTO lab_templates (id, name, discipline, status, created_by_id, created_at)
            VALUES (gen_random_uuid(), :name, :discipline, 'DRAFT', :created_by_id, NOW())
        """), {"name": "Liver Function Test (LFT)", "discipline": "CHEMISTRY", "created_by_id": admin_user_id})
        
        # Get the new template ID
        result = db.execute(text("SELECT id FROM lab_templates WHERE name = 'Liver Function Test (LFT)'"))
        row = result.fetchone()
        template_id = row[0]
        
        # Create first version
        db.execute(text("""
            INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, change_note, created_by_id, created_at)
            VALUES (gen_random_uuid(), :template_id, 1, 'DRAFT', :schema_json, :change_note, :created_by_id, NOW())
        """), {
            "template_id": template_id,
            "schema_json": schema_json_str,
            "change_note": "Initial NHIS-compliant LFT template",
            "created_by_id": admin_user_id
        })
        
        print(f"Created new LFT template")
    
    db.commit()
    
    print(f"\nLFT Template ID: {template_id}")
    print(f"Template Name: Liver Function Test (LFT)")
    print(f"Discipline: CHEMISTRY")
    
    return template_id


def create_lft_reference_ranges():
    """Create comprehensive reference ranges for LFT."""
    
    print("\n" + "=" * 70)
    print("CREATING LFT REFERENCE RANGES")
    print("=" * 70)
    
    # Reference ranges: field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_high
    lft_ranges = [
        # Total Protein
        ("total_protein", "ANY", 6570, 30000, 60.0, 80.0, "g/L", "60 - 80 g/L", None),
        ("total_protein", "ANY", 0, 6569, 55.0, 75.0, "g/L", "55 - 75 g/L", None),
        
        # Albumin
        ("albumin", "ANY", 6570, 30000, 35.0, 50.0, "g/L", "35 - 50 g/L", None),
        ("albumin", "ANY", 0, 6569, 30.0, 50.0, "g/L", "30 - 50 g/L", None),
        
        # Globulin
        ("globulin", "ANY", 6570, 30000, 20.0, 35.0, "g/L", "20 - 35 g/L", None),
        ("globulin", "ANY", 0, 6569, 20.0, 30.0, "g/L", "20 - 30 g/L", None),
        
        # AST (SGOT)
        ("ast", "M", 6570, 30000, 0.0, 40.0, "U/L", "≤ 40 U/L", 500.0),
        ("ast", "F", 6570, 30000, 0.0, 35.0, "U/L", "≤ 35 U/L", 500.0),
        ("ast", "ANY", 0, 6569, 0.0, 45.0, "U/L", "≤ 45 U/L", None),
        
        # ALT (SGPT)
        ("alt", "M", 6570, 30000, 0.0, 41.0, "U/L", "≤ 41 U/L", 500.0),
        ("alt", "F", 6570, 30000, 0.0, 31.0, "U/L", "≤ 31 U/L", 500.0),
        ("alt", "ANY", 0, 6569, 0.0, 45.0, "U/L", "≤ 45 U/L", None),
        
        # GGT
        ("ggt", "M", 6570, 30000, 10.0, 71.0, "U/L", "10 - 71 U/L", 200.0),
        ("ggt", "F", 6570, 30000, 6.0, 42.0, "U/L", "6 - 42 U/L", 200.0),
        ("ggt", "ANY", 0, 6569, 5.0, 32.0, "U/L", "5 - 32 U/L", None),
        
        # ALP
        ("alp", "ANY", 6570, 30000, 44.0, 147.0, "U/L", "44 - 147 U/L", 400.0),
        ("alp", "ANY", 0, 6569, 100.0, 320.0, "U/L", "100 - 320 U/L", None),
        
        # Total Bilirubin
        ("total_bilirubin", "ANY", 6570, 30000, 5.0, 21.0, "µmol/L", "5 - 21 µmol/L", 171.0),
        ("total_bilirubin", "ANY", 0, 6569, 5.0, 17.0, "µmol/L", "5 - 17 µmol/L", None),
        
        # Direct Bilirubin
        ("direct_bilirubin", "ANY", 0, 30000, 0.0, 7.0, "µmol/L", "0 - 7 µmol/L", 85.0),
        
        # Indirect Bilirubin
        ("indirect_bilirubin", "ANY", 0, 30000, 3.0, 14.0, "µmol/L", "3 - 14 µmol/L", None),
    ]
    
    field_codes = ["total_protein", "albumin", "globulin", "ast", "alt", "ggt",
                   "alp", "total_bilirubin", "direct_bilirubin", "indirect_bilirubin"]
    
    # Delete existing ranges
    db.execute(text("DELETE FROM lab_reference_ranges WHERE field_code IN :codes"), {"codes": tuple(field_codes)})
    print(f"Deleted existing LFT reference ranges")
    
    # Insert new ranges
    inserted = 0
    for rr in lft_ranges:
        field_code, sex, age_min, age_max, low, high, unit, text_range, critical_high = rr
        
        db.execute(text("""
            INSERT INTO lab_reference_ranges 
            (id, field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_high, created_at)
            VALUES (gen_random_uuid(), :field_code, :sex, :age_min, :age_max, :low, :high, :unit, :text_range, :critical_high, NOW())
        """), {
            "field_code": field_code,
            "sex": sex,
            "age_min": age_min,
            "age_max": age_max,
            "low": low,
            "high": high,
            "unit": unit,
            "text_range": text_range,
            "critical_high": critical_high
        })
        inserted += 1
    
    db.commit()
    print(f"Inserted {inserted} reference ranges")
    return inserted


def create_option_sets():
    """Create option sets for LFT interpretation."""
    
    print("\n" + "=" * 70)
    print("CREATING LFT OPTION SETS")
    print("=" * 70)
    
    interpretation_options = json.dumps([
        {"value": "normal", "label": "Normal Liver Function"},
        {"value": "hepatocellular", "label": "Hepatocellular Injury Pattern"},
        {"value": "cholestatic", "label": "Cholestatic Pattern"},
        {"value": "mixed", "label": "Mixed Pattern"},
        {"value": "jaundice", "label": "Jaundice - Elevated Bilirubin"},
        {"value": "hemolysis", "label": "Suspected Hemolysis"},
        {"value": "alcoholic", "label": "Alcoholic Liver Disease"},
        {"value": "viral", "label": "Viral Hepatitis Pattern"},
        {"value": "drug_induced", "label": "Drug-Induced Liver Injury"}
    ])
    
    # Upsert option set
    db.execute(text("""
        INSERT INTO lab_option_sets (id, code, options_json, created_at)
        VALUES (gen_random_uuid(), 'LFT_INTERPRETATION', :options, NOW())
        ON CONFLICT (code) DO UPDATE SET options_json = :options
    """), {"options": interpretation_options})
    
    db.commit()
    print("Created/updated LFT_INTERPRETATION option set")
    return True


def seed_lft_nhis():
    """Main function to seed NHIS-compliant LFT template."""
    
    print("\n" + "=" * 70)
    print("NHIS-COMPLIANT LFT TEMPLATE SEEDER")
    print("=" * 70)
    print(f"Database: {DATABASE_URL}")
    print(f"Started at: {datetime.now().isoformat()}")
    
    try:
        # Get admin user
        admin_user_id = get_admin_user()
        print(f"Using admin user ID: {admin_user_id}")
        
        # Step 1: Create LFT template
        template_id = create_lft_nhis_template(admin_user_id)
        
        # Step 2: Create option sets
        create_option_sets()
        
        # Step 3: Create reference ranges
        create_lft_reference_ranges()
        
        print("\n" + "=" * 70)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nThe LFT template is now ready with:")
        print("  ✓ 10 parameters with decimal numeric input")
        print("  ✓ Age-based reference ranges (Adult vs Child)")
        print("  ✓ Gender-specific reference ranges (AST, ALT, GGT)")
        print("  ✓ Critical value alerts")
        print("  ✓ Auto-calculation for Globulin and Indirect Bilirubin")
        print("  ✓ Pattern recognition (Hepatocellular, Cholestatic)")
        print("  ✓ NHIS-ready claim flags (diagnosis, result, specimen required)")
        print("  ✓ Structured export capability (API, CSV, NHIS claims)")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_lft_nhis()
    sys.exit(0 if success else 1)
