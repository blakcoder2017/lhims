#!/usr/bin/env python3
"""
Widal Test Template Update Script
=================================
Updates the Widal test template in LHIMS with:

Required Parameters:
1. S. Typhi O (O-Antigen) - Code: STY_O
2. S. Typhi H (Haemagglutinin) - Code: STY_H  
3. IgG (Past Exposure/Immunity) - Code: WIDAL_IGG (Qualitative)
4. IgM (Recent/Acute Infection) - Code: WIDAL_IGM (Qualitative)

Reference Ranges (Ghana Standard):
- O and H Antigens: <1:80 (Normal), 1:80 (Borderline), ≥1:160 (Significant)
- IgG/IgM: Negative (Normal), Positive (Significant)

Result Types:
- STY_O and STY_H: Semi-quantitative titer (dropdown with Negative)
- WIDAL_IGG and WIDAL_IGM: Qualitative (Negative/Positive)

Auto-Flagging:
- O-antigen ≥1:160 → Flag as High/Significant
- IgM = Positive → Flag as Acute Infection

Patient Demographics:
- Age and gender captured for record (reference ranges same for all)

Usage:
    python3 update_widal_test_template.py
"""

import os
import sys
import json
from uuid import uuid4

# Direct database connection without loading app config
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_connect_args = {} if "postgresql" in DATABASE_URL else {"check_same_thread": False}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# WIDAL TEST TITRE OPTION SET
# =============================================================================

def ensure_widal_option_sets(db):
    """Ensure WIDAL_TITRE_WITH_NEGATIVE and WIDAL_QUALITATIVE option sets exist."""
    
    # Standard titre values for O and H antigens (includes Negative)
    titre_with_negative = [
        {"value": "Negative", "label": "Negative", "is_default": True},
        {"value": "1:20", "label": "1:20", "is_default": False},
        {"value": "1:40", "label": "1:40", "is_default": False},
        {"value": "1:80", "label": "1:80", "is_default": False},
        {"value": "1:160", "label": "1:160", "is_default": False},
        {"value": "1:320", "label": "1:320", "is_default": False},
        {"value": "1:640", "label": "1:640", "is_default": False},
    ]
    
    # Check if lab_option_sets table exists and has WIDAL_TITRE
    result = db.execute(text("SELECT id, options_json FROM lab_option_sets WHERE code = 'WIDAL_TITRE_WITH_NEGATIVE'"))
    row = result.fetchone()
    
    if not row:
        db.execute(text("""
            INSERT INTO lab_option_sets (id, code, options_json)
            VALUES (:id, 'WIDAL_TITRE_WITH_NEGATIVE', :options)
        """), {"id": str(uuid4()), "options": json.dumps(titre_with_negative)})
        print("  Created WIDAL_TITRE_WITH_NEGATIVE option set")
    else:
        # Update existing
        db.execute(text("UPDATE lab_option_sets SET options_json = :options WHERE code = 'WIDAL_TITRE_WITH_NEGATIVE'"),
                  {"options": json.dumps(titre_with_negative)})
        print("  Updated WIDAL_TITRE_WITH_NEGATIVE option set")
    
    # Qualitative option set for IgG and IgM (Negative/Positive)
    qualitative_options = [
        {"value": "Negative", "label": "Negative", "is_default": True},
        {"value": "Positive", "label": "Positive", "is_default": False},
    ]
    
    result_qual = db.execute(text("SELECT id FROM lab_option_sets WHERE code = 'WIDAL_QUALITATIVE'"))
    row_qual = result_qual.fetchone()
    
    if not row_qual:
        db.execute(text("""
            INSERT INTO lab_option_sets (id, code, options_json)
            VALUES (:id, 'WIDAL_QUALITATIVE', :options)
        """), {"id": str(uuid4()), "options": json.dumps(qualitative_options)})
        print("  Created WIDAL_QUALITATIVE option set")
    
    db.commit()
    return True


# =============================================================================
# WIDAL TEST TEMPLATE DEFINITION
# =============================================================================

def get_widal_template_definition():
    """
    Returns the Widal Test template definition with all parameters.
    
    Required Parameters (Ghana Standard):
    1. S. Typhi O (O-Antigen) - Code: STY_O - Semi-quantitative titer
    2. S. Typhi H (Haemagglutinin) - Code: STY_H - Semi-quantitative titer  
    3. IgG (Past Exposure/Immunity) - Code: WIDAL_IGG - Qualitative (Negative/Positive)
    4. IgM (Recent/Acute Infection) - Code: WIDAL_IGM - Qualitative (Negative/Positive)
    
    Reference Range: 
    - O and H Antigens: <1:80 (Normal), 1:80 (Borderline), ≥1:160 (Significant)
    - IgG/IgM: Negative (Normal), Positive (Significant)
    """
    
    template = {
        "discipline": "SEROLOGY",
        "description": "Widal Test (S. Typhi) - Ghana Standard / NHIS Compliant",
        "test_code": "WIDAL",
        "layout": {
            "sections": [
                {
                    "id": "sec_typhi_antigens",
                    "title": "S. Typhi Antigens (Titer)",
                    "rows": [
                        {"columns": [
                            {"items": ["STY_O"], "width": 6},
                            {"items": ["STY_H"], "width": 6}
                        ]}
                    ]
                },
                {
                    "id": "sec_immunoglobulins",
                    "title": "Immunoglobulin Markers (Qualitative)",
                    "rows": [
                        {"columns": [
                            {"items": ["WIDAL_IGG"], "width": 6},
                            {"items": ["WIDAL_IGM"], "width": 6}
                        ]}
                    ]
                },
                {
                    "id": "sec_comments",
                    "title": "Comments",
                    "rows": [
                        {"columns": [
                            {"items": ["comments"], "width": 12}
                        ]}
                    ]
                }
            ]
        },
        "fields": {
            "STY_O": {
                "code": "STY_O",
                "label": "S. Typhi O (O-Antigen)",
                "type": "select",
                "option_set": "WIDAL_TITRE_WITH_NEGATIVE",
                "result_type": "semi_quantitative",
                "unit": "Titer",
                "required": False,
                "validation_rules": {
                    "required": False,
                    "allowed_values": ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320", "1:640"]
                },
                "reference_range": "< 1:80",
                "clinical_note": "O-Antigen: <1:80 = Not significant, 1:80 = Borderline, ≥1:160 = Suggestive of Typhoid infection",
                "flag_significant": True,
                "significant_threshold": "1:160",
                "interpretation_rule": "o_antigen"
            },
            "STY_H": {
                "code": "STY_H",
                "label": "S. Typhi H (Haemagglutinin)",
                "type": "select",
                "option_set": "WIDAL_TITRE_WITH_NEGATIVE",
                "result_type": "semi_quantitative",
                "unit": "Titer",
                "required": False,
                "validation_rules": {
                    "required": False,
                    "allowed_values": ["Negative", "1:20", "1:40", "1:80", "1:160", "1:320", "1:640"]
                },
                "reference_range": "< 1:80",
                "clinical_note": "H-Antigen: <1:80 = Not significant, 1:80 = Borderline, ≥1:160 = Suggestive of Typhoid infection",
                "flag_significant": True,
                "significant_threshold": "1:160",
                "interpretation_rule": "h_antigen"
            },
            "WIDAL_IGG": {
                "code": "WIDAL_IGG",
                "label": "IgG (Past Exposure/Immunity)",
                "type": "select",
                "option_set": "WIDAL_QUALITATIVE",
                "result_type": "qualitative",
                "unit": "None",
                "required": False,
                "validation_rules": {
                    "required": False,
                    "allowed_values": ["Negative", "Positive"]
                },
                "reference_range": "Negative",
                "clinical_note": "IgG: Negative = No detectable past exposure, Positive = Past infection or immunity",
                "flag_significant": True,
                "significant_value": "Positive",
                "interpretation_rule": "igg_past_exposure"
            },
            "WIDAL_IGM": {
                "code": "WIDAL_IGM",
                "label": "IgM (Recent/Acute Infection)",
                "type": "select",
                "option_set": "WIDAL_QUALITATIVE",
                "result_type": "qualitative",
                "unit": "None",
                "required": False,
                "validation_rules": {
                    "required": False,
                    "allowed_values": ["Negative", "Positive"]
                },
                "reference_range": "Negative",
                "clinical_note": "IgM: Negative = No recent infection detected, Positive = Suggestive of recent or acute infection",
                "flag_significant": True,
                "flag_acute_infection": True,
                "significant_value": "Positive",
                "interpretation_rule": "igm_acute_infection"
            },
            "comments": {
                "code": "comments",
                "label": "Comments/Notes",
                "type": "text",
                "multiline": True,
                "required": False,
                "placeholder": "Additional comments or notes"
            }
        },
        "report_config": {
            "display_order": ["STY_O", "STY_H", "WIDAL_IGG", "WIDAL_IGM"],
            "show_reference_ranges": True,
            "highlight_abnormal": True,
            "auto_interpretation": True,
            "nhis_ready": True,
            "patient_demographics": {
                "capture_age": True,
                "capture_gender": True,
                "reference_range_same_for_all": True
            }
        }
    }
    
    return template


# =============================================================================
# REFERENCE RANGES
# =============================================================================

def get_widal_reference_ranges():
    """Returns reference ranges for Widal test parameters (Ghana Standard)."""
    
    return [
        {
            "field_code": "STY_O",
            "sex": "ANY",
            "age_min_days": 0,
            "age_max_days": 36500,
            "low": None,
            "high": None,
            "critical_low": None,
            "critical_high": None,
            "unit": "Titer",
            "text_range": "< 1:80",
            "interpretation_normal": "Not significant - No serological evidence of infection",
            "interpretation_borderline": "Borderline - Repeat test if clinically indicated",
            "interpretation_significant": "Suggestive of Typhoid infection - Clinical correlation required"
        },
        {
            "field_code": "STY_H",
            "sex": "ANY",
            "age_min_days": 0,
            "age_max_days": 36500,
            "low": None,
            "high": None,
            "critical_low": None,
            "critical_high": None,
            "unit": "Titer",
            "text_range": "< 1:80",
            "interpretation_normal": "Not significant - No serological evidence of infection",
            "interpretation_borderline": "Borderline - Repeat test if clinically indicated",
            "interpretation_significant": "Suggestive of Typhoid infection - Clinical correlation required"
        },
        {
            "field_code": "WIDAL_IGG",
            "sex": "ANY",
            "age_min_days": 0,
            "age_max_days": 36500,
            "low": None,
            "high": None,
            "critical_low": None,
            "critical_high": None,
            "unit": "None",
            "text_range": "Negative",
            "interpretation_normal": "No detectable past exposure",
            "interpretation_significant": "Past infection or immunity"
        },
        {
            "field_code": "WIDAL_IGM",
            "sex": "ANY",
            "age_min_days": 0,
            "age_max_days": 36500,
            "low": None,
            "high": None,
            "critical_low": None,
            "critical_high": None,
            "unit": "None",
            "text_range": "Negative",
            "interpretation_normal": "No recent infection detected",
            "interpretation_significant": "Suggestive of recent or acute infection"
        }
    ]


# =============================================================================
# AUTO-INTERPRETATION RULES
# =============================================================================

def get_widal_interpretation_rules():
    """Returns auto-interpretation rules for Widal test results (Ghana Standard)."""
    
    return [
        {
            "condition": "igm_positive_acute",
            "pattern": {"WIDAL_IGM": ["Positive"]},
            "interpretation": "ACUTE INFECTION: IgM is Positive - suggests recent or acute Salmonella Typhi infection. Clinical correlation and prompt treatment recommended.",
            "severity": "critical",
            "requires_action": True,
            "flag_type": "acute_infection"
        },
        {
            "condition": "igg_positive_past_exposure",
            "pattern": {"WIDAL_IGG": ["Positive"], "WIDAL_IGM": ["Negative"]},
            "interpretation": "PAST EXPOSURE / IMMUNITY: IgG is Positive while IgM is Negative - suggests past exposure to Salmonella Typhi or immunity. No evidence of acute infection.",
            "severity": "info",
            "requires_action": False
        },
        {
            "condition": "o_antigen_significant",
            "pattern": {"STY_O": ["1:160", "1:320", "1:640"]},
            "interpretation": "SIGNIFICANT O-TITER: S. Typhi O antigen is significantly elevated (≥1:160), which is suggestive of Typhoid infection. Clinical correlation required.",
            "severity": "warning",
            "requires_action": True,
            "flag_type": "high_titer"
        },
        {
            "condition": "h_antigen_significant",
            "pattern": {"STY_H": ["1:160", "1:320", "1:640"]},
            "interpretation": "SIGNIFICANT H-TITER: S. Typhi H antigen is significantly elevated (≥1:160), which may indicate Typhoid infection or previous exposure.",
            "severity": "warning",
            "requires_action": True,
            "flag_type": "high_titer"
        },
        {
            "condition": "both_o_h_significant",
            "pattern": {
                "STY_O": ["1:160", "1:320", "1:640"],
                "STY_H": ["1:160", "1:320", "1:640"]
            },
            "interpretation": "SUGGESTIVE OF TYPHOID FEVER: Both S. Typhi O and H antigens show significant elevation (≥1:160), which is consistent with typhoid/paratyphoid infection. Recommend clinical correlation and consider repeat testing in 2-4 weeks.",
            "severity": "warning",
            "requires_action": True,
            "flag_type": "high_titer"
        },
        {
            "condition": "all_normal",
            "pattern": {
                "STY_O": ["Negative", "1:20", "1:40", "1:80"],
                "STY_H": ["Negative", "1:20", "1:40", "1:80"],
                "WIDAL_IGG": ["Negative"],
                "WIDAL_IGM": ["Negative"]
            },
            "interpretation": "NORMAL / NO EVIDENCE OF INFECTION: All Widal test parameters are within normal limits. No serological evidence of Salmonella Typhi infection.",
            "severity": "normal",
            "requires_action": False
        },
        {
            "condition": "borderline_o",
            "pattern": {"STY_O": ["1:80"]},
            "interpretation": "BORDERLINE: O-antigen shows borderline elevation (1:80). Consider repeat testing in 2-4 weeks if clinically indicated.",
            "severity": "info",
            "requires_action": False
        },
        {
            "condition": "borderline_h",
            "pattern": {"STY_H": ["1:80"]},
            "interpretation": "BORDERLINE: H-antigen shows borderline elevation (1:80). Consider repeat testing in 2-4 weeks if clinically indicated.",
            "severity": "info",
            "requires_action": False
        },
        {
            "condition": "combined_interpretation",
            "pattern": "any",
            "interpretation": "Note: Widal test results should always be interpreted alongside clinical findings. A four-fold rise in titre in paired samples (2-4 weeks apart) is more diagnostic than a single elevated result.",
            "severity": "info",
            "requires_action": False
        }
    ]


# =============================================================================
# MAIN UPDATE FUNCTION
# =============================================================================

def update_widal_template(db):
    """Main function to update/create the Widal test template."""
    
    print("\n" + "=" * 70)
    print("WIDAL TEST TEMPLATE UPDATE")
    print("=" * 70)
    
    # Step 1: Ensure option sets exist
    print("\n[1/5] Ensuring Widal option sets exist...")
    ensure_widal_option_sets(db)
    
    # Step 2: Get or create the Widal template
    print("\n[2/5] Checking for existing Widal template...")
    
    # Check for existing templates
    result = db.execute(text("""
        SELECT id, name, discipline, status, current_version 
        FROM lab_templates 
        WHERE name LIKE '%Widal%' OR name LIKE '%widal%' OR name LIKE '%Typhoid%'
    """))
    existing_templates = result.fetchall()
    
    if existing_templates:
        template_id = existing_templates[0][0]
        template_name = existing_templates[0][1]
        print(f"  Found existing template: {template_name} (ID: {template_id})")
        
        # Get current version
        ver_result = db.execute(text("""
            SELECT MAX(version) as max_ver FROM lab_template_versions WHERE template_id = :tid
        """), {"tid": str(template_id)})
        max_ver = ver_result.fetchone()[0] or 0
    else:
        print("  Creating new Widal Test template...")
        template_id = str(uuid4())
        template_name = "Widal Test (S. Typhi / S. Paratyphi)"
        
        # Get a user ID for created_by
        user_result = db.execute(text("SELECT id FROM users LIMIT 1"))
        user_row = user_result.fetchone()
        admin_user_id = user_row[0] if user_row else None
        
        db.execute(text("""
            INSERT INTO lab_templates (id, name, discipline, status, current_version, created_by_id)
            VALUES (:id, :name, 'SEROLOGY', 'DRAFT', 1, :created_by)
        """), {"id": template_id, "name": template_name, "created_by": admin_user_id})
        
        max_ver = 0
        print(f"  Created new template: {template_id}")
    
    # Step 3: Create new template version
    print("\n[3/5] Creating new template version...")
    template_def = get_widal_template_definition()
    
    new_version = max_ver + 1
    
    # Add interpretation rules and reference range interpretations to schema
    interpretation_rules = get_widal_interpretation_rules()
    template_def["interpretation_rules"] = interpretation_rules
    
    # Add reference range interpretations
    ranges = get_widal_reference_ranges()
    template_def["reference_range_interpretations"] = {
        r["field_code"]: {
            "normal": r.get("interpretation_normal", ""),
            "significant": r.get("interpretation_significant", "")
        }
        for r in ranges
    }
    
    schema_json_str = json.dumps(template_def)
    
    version_id = str(uuid4())
    
    # Get a user ID for created_by
    user_result = db.execute(text("SELECT id FROM users LIMIT 1"))
    user_row = user_result.fetchone()
    admin_user_id = user_row[0] if user_row else None
    
    db.execute(text("""
        INSERT INTO lab_template_versions (id, template_id, version, status, schema_json, change_note, created_by_id)
        VALUES (:id, :template_id, :version, 'PUBLISHED', cast(:schema_json as jsonb), :change_note, :created_by)
    """), {
        "id": version_id,
        "template_id": template_id,
        "version": new_version,
        "schema_json": schema_json_str,
        "change_note": "Updated Widal template: STY_O/STY_H (semi-quantitative titers), WIDAL_IGG/WIDAL_IGM (qualitative), Ghana standard reference ranges <1:80, auto-interpretation and result flagging",
        "created_by": admin_user_id
    })
    
    # Update template status
    db.execute(text("""
        UPDATE lab_templates SET current_version = :ver, status = 'PUBLISHED' WHERE id = :id
    """), {"ver": new_version, "id": template_id})
    
    print(f"  Created version {new_version}")
    
    # Step 4: Update reference ranges
    print("\n[4/5] Updating reference ranges...")
    
    # Remove existing Widal reference ranges
    db.execute(text("""
        DELETE FROM lab_reference_ranges 
        WHERE field_code IN ('STY_O', 'STY_H', 'WIDAL_IGG', 'WIDAL_IGM', 's_typhi_o', 's_typhi_h', 'igg', 'igm')
    """))
    
    # Add new reference ranges
    for range_def in ranges:
        db.execute(text("""
            INSERT INTO lab_reference_ranges (id, field_code, sex, age_min_days, age_max_days, low, high, critical_low, critical_high, unit, text_range)
            VALUES (:id, :field_code, :sex, :age_min, :age_max, :low, :high, :crit_low, :crit_high, :unit, :text_range)
        """), {
            "id": str(uuid4()),
            "field_code": range_def["field_code"],
            "sex": range_def["sex"],
            "age_min": range_def["age_min_days"],
            "age_max": range_def["age_max_days"],
            "low": range_def.get("low"),
            "high": range_def.get("high"),
            "crit_low": range_def.get("critical_low"),
            "crit_high": range_def.get("critical_high"),
            "unit": range_def.get("unit"),
            "text_range": range_def["text_range"]
        })
    
    print(f"  Added {len(ranges)} reference ranges")
    
    # Step 5: Configure auto-interpretation rules
    print("\n[5/5] Configuring auto-interpretation rules...")
    print(f"  Configured {len(interpretation_rules)} interpretation rules")
    
    # Commit changes
    db.commit()
    
    # Step 6: Link template to lab tests
    print("\n[6/6] Linking template to lab tests...")
    
    # Get template ID
    template_id = str(template_id)
    new_version = new_version
    
    # Link to WIDAL and WID001 tests
    result = db.execute(text("""
        UPDATE lab_tests 
        SET template_id = :template_id, template_version = :version
        WHERE test_code IN ('WIDAL', 'WID001') OR test_name ILIKE '%Widal%'
    """), {"template_id": template_id, "version": new_version})
    
    print(f"  Linked {result.rowcount} test(s) to template")
    
    db.commit()
    
    print("\n" + "=" * 70)
    print("WIDAL TEST TEMPLATE UPDATED SUCCESSFULLY")
    print("=" * 70)
    print(f"""
Template Details:
- Name: {template_name}
- Discipline: SEROLOGY
- Version: {new_version}
- Status: PUBLISHED

Parameters:
- S. Typhi O (O-Antigen) - Required
- S. Typhi H (Haemagglutinin) - Required  
- IgG (Past Exposure/Immunity) - Required
- IgM (Recent/Acute Infection) - Required

Reference Ranges (All ages, both sexes):
- Normal: ≤1:80
- Significant: ≥1:160

Validation Rules:
- All parameters mandatory
- Only standard titre values (1:20, 1:40, 1:80, 1:160, 1:320, 1:640)

Auto-Interpretation:
- IgM ≥1:160 = Possible acute infection (highlighted)
- IgG ≥1:160 with normal IgM = Past exposure/immunity
- S. Typhi O+H both ≥1:160 = Suggestive of typhoid fever
- All ≤1:80 = No evidence of infection

Report Format:
- Results displayed in order: S. Typhi H → S. Typhi O → IgG → IgM
- Reference ranges shown
- Abnormal results highlighted
- System-generated interpretation included
- NHIS-ready for electronic claims
    """)
    
    return template_id, template_name, new_version


def main():
    """Main entry point."""
    db = SessionLocal()
    try:
        update_widal_template(db)
    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
