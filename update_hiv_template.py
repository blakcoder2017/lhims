"""
HIV 1 & 2 Screening Template Update

This script updates the HIV test template in LHIMS to include:
- Retroscreening (First Response)
- Confirmation Test
- Rapid Test Kit Used (Bio Line, OraQuick, Determine, Wondfo)
- Interpretation Logic
- Validation Rules
- NHIS Claim Alignment

Run this script to update the template in the database.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import SessionLocal


def create_hiv_option_sets():
    """Create new option sets for HIV 1 & 2 Screening"""
    db = SessionLocal()
    
    try:
        option_sets_data = {
            # First Response (Retroscreening) - uses Reactive/Non-Reactive/Invalid
            "HIV_FIRST_RESPONSE": ["Reactive", "Non-Reactive", "Invalid"],
            
            # Confirmation Test results
            "HIV_CONFIRMATION_RESULT": ["Positive", "Negative", "Indeterminate"],
            
            # Rapid Test Kit Results (includes Not Used option)
            "RAPID_KIT_RESULT": ["Reactive", "Non-Reactive", "Not Used"],
            
            # Final Interpretation (auto-calculated but included for reference)
            "HIV_FINAL_INTERPRETATION": [
                "HIV 1 & 2: Negative",
                "HIV 1 & 2: Positive",
                "Indeterminate – Repeat testing recommended"
            ]
        }
        
        print("Creating HIV-specific option sets...")
        
        for code, options in option_sets_data.items():
            # Check if exists
            check_query = text("SELECT id FROM lab_option_sets WHERE code = :code")
            existing = db.execute(check_query, {"code": code}).fetchone()
            
            if existing:
                # Update existing
                update_query = text("""
                    UPDATE lab_option_sets 
                    SET options_json = :options_json, updated_at = NOW()
                    WHERE code = :code
                """)
                db.execute(update_query, {
                    "code": code,
                    "options_json": json.dumps(options)
                })
                print(f"  Updated option set: {code}")
            else:
                # Insert new
                from uuid import uuid4
                insert_query = text("""
                    INSERT INTO lab_option_sets (id, code, options_json, created_at)
                    VALUES (:id, :code, :options_json, NOW())
                """)
                db.execute(insert_query, {
                    "id": str(uuid4()),
                    "code": code,
                    "options_json": json.dumps(options)
                })
                print(f"  Created option set: {code}")
        
        db.commit()
        print(f"Completed HIV option sets\n")
        
    except Exception as e:
        print(f"ERROR creating option sets: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_hiv_template_schema():
    """
    Create the comprehensive HIV 1 & 2 Screening template schema
    
    Structure:
    A. RETROSCREENING
       - First Response (Reactive/Non-Reactive/Invalid)
    B. CONFIRMATION TEST
       - Confirmation Result (Positive/Negative/Indeterminate)
       - Only enabled if First Response = Reactive
    C. RAPID TEST KITS USED
       - Bio Line
       - OraQuick
       - Determine
       - Wondfo
    D. FINAL INTERPRETATION (Auto-calculated)
    """
    
    return {
        "meta": {
            "name": "HIV 1 & 2 Screening",
            "discipline": "SEROLOGY",
            "version": 2,
            "nhis_code": "HIV001",
            "description": "HIV 1 & 2 Screening with Confirmation - NHIS Compliant",
            "nhis_claimable": True,
            "specimen_type": "Serum/Plasma"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_retroscreening",
                    "title": "A. RETROSCREENING (First Response)",
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["first_response"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_confirmation",
                    "title": "B. CONFIRMATION TEST",
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["confirmation_result"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_rapid_kits",
                    "title": "C. RAPID TEST KITS USED",
                    "description": "Record which kit was used during testing for traceability and audit",
                    "rows": [
                        {
                            "columns": [
                                {"width": 6, "items": ["bio_line"]},
                                {"width": 6, "items": ["oraquick"]}
                            ]
                        },
                        {
                            "columns": [
                                {"width": 6, "items": ["determine"]},
                                {"width": 6, "items": ["wondfo"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_interpretation",
                    "title": "D. FINAL INTERPRETATION",
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["final_interpretation"]}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_comments",
                    "title": "E. COMMENTS",
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["comments"]}
                            ]
                        }
                    ]
                }
            ]
        },
        "fields": {
            "first_response": {
                "code": "first_response",
                "label": "First Response (Retroscreening)",
                "type": "choice",
                "optionSet": "HIV_FIRST_RESPONSE",
                "required": True,
                "reference_range": {
                    "normal": "Non-Reactive",
                    "text": "Non-Reactive = Negative, Reactive = Proceed to Confirmation"
                },
                "validation": {
                    "on_change": "reactive_requires_confirmation"
                }
            },
            "confirmation_result": {
                "code": "confirmation_result",
                "label": "Confirmation Result",
                "type": "choice",
                "optionSet": "HIV_CONFIRMATION_RESULT",
                "required": False,  # Only required when first_response is Reactive
                "enabled": {
                    "when": "first_response",
                    "equals": "Reactive"
                },
                "validation": {
                    "required_if": {
                        "field": "first_response",
                        "value": "Reactive"
                    }
                }
            },
            "bio_line": {
                "code": "bio_line",
                "label": "Bio Line",
                "type": "choice",
                "optionSet": "RAPID_KIT_RESULT",
                "required": False,
                "description": "Rapid test kit used"
            },
            "oraquick": {
                "code": "oraquick",
                "label": "OraQuick",
                "type": "choice",
                "optionSet": "RAPID_KIT_RESULT",
                "required": False,
                "description": "Rapid test kit used"
            },
            "determine": {
                "code": "determine",
                "label": "Determine",
                "type": "choice",
                "optionSet": "RAPID_KIT_RESULT",
                "required": False,
                "description": "Rapid test kit used"
            },
            "wondfo": {
                "code": "wondfo",
                "label": "Wondfo",
                "type": "choice",
                "optionSet": "RAPID_KIT_RESULT",
                "required": False,
                "description": "Rapid test kit used"
            },
            "final_interpretation": {
                "code": "final_interpretation",
                "label": "Final Interpretation",
                "type": "choice",
                "optionSet": "HIV_FINAL_INTERPRETATION",
                "required": True,
                "calculated": True,
                "read_only": True,
                "description": "Auto-calculated based on First Response and Confirmation Result"
            },
            "comments": {
                "code": "comments",
                "label": "Comments",
                "type": "text",
                "required": False,
                "multiline": True
            }
        },
        "rules": {
            "visibility": [
                {
                    "field": "confirmation_result",
                    "condition": {
                        "field": "first_response",
                        "operator": "equals",
                        "value": "Reactive"
                    }
                }
            ],
            "requiredIf": [
                {
                    "field": "confirmation_result",
                    "condition": {
                        "field": "first_response",
                        "value": "Reactive"
                    },
                    "message": "Confirmation result is required when First Response is Reactive"
                },
                {
                    "field": "rapid_kit_used",
                    "condition": {
                        "field": "first_response",
                        "value": "Reactive"
                    },
                    "message": "At least one rapid kit must be recorded"
                }
            ],
            "validation": [
                {
                    "field": "first_response",
                    "rule": "invalid_flag",
                    "message": "Invalid test result detected. Please repeat the test.",
                    "condition": {
                        "field": "first_response",
                        "value": "Invalid"
                    }
                },
                {
                    "field": "first_response",
                    "rule": "negative_no_confirmation",
                    "message": "No confirmation needed for Non-Reactive results",
                    "condition": {
                        "field": "first_response",
                        "value": "Non-Reactive"
                    },
                    "action": "auto_finalize"
                }
            ],
            "calculation": {
                "final_interpretation": {
                    "formula": "interpret_hiv_result",
                    "inputs": ["first_response", "confirmation_result"]
                }
            }
        },
        "calculated": [
            {
                "field": "final_interpretation",
                "logic": {
                    "if": [
                        {"eq": ["first_response", "Non-Reactive"]},
                        "HIV 1 & 2: Negative",
                        {
                            "if": [
                                {"eq": ["first_response", "Reactive"]},
                                {
                                    "if": [
                                        {"eq": ["confirmation_result", "Positive"]},
                                        "HIV 1 & 2: Positive",
                                        {
                                            "if": [
                                                {"eq": ["confirmation_result", "Indeterminate"]},
                                                "Indeterminate – Repeat testing recommended",
                                                "HIV 1 & 2: Positive"
                                            ]
                                        }
                                    ]
                                },
                                "HIV 1 & 2: Positive"
                            ]
                        }
                    ]
                }
            }
        ],
        "nhis_requirements": {
            "claimable": True,
            "nhis_code": "HIV001",
            "required_for_claim": [
                "first_response",
                "final_interpretation",
                "specimen_date"
            ],
            "diagnosis_required": True,
            "final_result_required": True,
            "prevent_claim_if_not_finalized": True
        },
        "audit_trail": {
            "enabled": True,
            "track_changes": True,
            "track_result_edits": True,
            "track_user": True
        },
        "historical_data": {
            "preserve_results": True,
            "exportable": True,
            "api_available": True
        }
    }


def update_hiv_template():
    """Update the HIV template with the new comprehensive schema"""
    db = SessionLocal()
    
    try:
        # Get the existing HIV template
        check_query = text("SELECT id, name FROM lab_templates WHERE name LIKE '%HIV%' LIMIT 1")
        existing = db.execute(check_query).fetchone()
        
        if existing:
            template_id = existing[0]
            print(f"Found existing HIV template: {existing[1]} (ID: {template_id})")
            
            # Get current version
            version_query = text("""
                SELECT id, version FROM lab_template_versions 
                WHERE template_id = :template_id 
                ORDER BY version DESC LIMIT 1
            """)
            current_ver = db.execute(version_query, {"template_id": template_id}).fetchone()
            new_version = (current_ver[1] + 1) if current_ver else 1
            
            print(f"  Current version: {current_ver[1] if current_ver else 'N/A'}")
            print(f"  New version: {new_version}")
            
            # Create new version with updated schema
            schema_json = create_hiv_template_schema()
            
            insert_version = text("""
                INSERT INTO lab_template_versions 
                (id, template_id, version, status, schema_json, change_note, created_by_id, created_at)
                VALUES (:id, :template_id, :version, :status, :schema_json, :change_note, :created_by_id, NOW())
            """)
            
            from uuid import uuid4
            db.execute(insert_version, {
                "id": str(uuid4()),
                "template_id": template_id,
                "version": new_version,
                "status": "PUBLISHED",
                "schema_json": json.dumps(schema_json),
                "change_note": f"Updated HIV 1 & 2 Screening template - v{new_version} with NHIS-compliant fields and validation rules",
                "created_by_id": 1  # System admin
            })
            
            # Update template to point to new version
            update_template = text("""
                UPDATE lab_templates 
                SET current_version = :version, updated_at = NOW()
                WHERE id = :template_id
            """)
            db.execute(update_template, {
                "version": new_version,
                "template_id": template_id
            })
            
            print(f"\n  Updated template to version {new_version}")
            
        else:
            print("No existing HIV template found. Creating new template...")
            
            # Create new template
            from uuid import uuid4
            template_id = str(uuid4())
            version_id = str(uuid4())
            
            schema_json = create_hiv_template_schema()
            
            # Get admin user
            user_query = text("SELECT id FROM users ORDER BY id LIMIT 1")
            user_result = db.execute(user_query).fetchone()
            admin_user_id = user_result[0] if user_result else 1
            
            # Insert template
            insert_template = text("""
                INSERT INTO lab_templates 
                (id, name, discipline, status, current_version, created_by_id, created_at)
                VALUES (:id, :name, :discipline, :status, :current_version, :created_by_id, NOW())
            """)
            db.execute(insert_template, {
                "id": template_id,
                "name": "HIV 1 & 2 Screening",
                "discipline": "SEROLOGY",
                "status": "PUBLISHED",
                "current_version": 1,
                "created_by_id": admin_user_id
            })
            
            # Insert version
            insert_version = text("""
                INSERT INTO lab_template_versions 
                (id, template_id, version, status, schema_json, change_note, created_by_id, created_at)
                VALUES (:id, :template_id, :version, :status, :schema_json, :change_note, :created_by_id, NOW())
            """)
            db.execute(insert_version, {
                "id": version_id,
                "template_id": template_id,
                "version": 1,
                "status": "PUBLISHED",
                "schema_json": json.dumps(schema_json),
                "change_note": "Initial HIV 1 & 2 Screening template - NHIS Compliant",
                "created_by_id": admin_user_id
            })
            
            print(f"  Created new template: HIV 1 & 2 Screening (ID: {template_id})")
        
        db.commit()
        print("\nHIV template update completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR updating HIV template: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_lab_test_entry():
    """Create or update the lab test catalog entry for HIV 1 & 2 Screening"""
    db = SessionLocal()
    
    try:
        # Check if test exists
        check_query = text("SELECT id FROM lab_tests WHERE test_name LIKE '%HIV%' AND test_name LIKE '%Screening%' LIMIT 1")
        existing = db.execute(check_query).fetchone()
        
        if existing:
            test_id = existing[0]
            print(f"Found existing HIV lab test (ID: {test_id}), updating...")
            
            # Get template ID
            template_query = text("SELECT id FROM lab_templates WHERE name = 'HIV 1 & 2 Screening' LIMIT 1")
            template_result = db.execute(template_query).fetchone()
            
            if template_result:
                update_query = text("""
                    UPDATE lab_tests 
                    SET test_name = :name, 
                        test_code = :code, 
                        test_category = :category,
                        description = :description,
                        specimen_type = :specimen,
                        nhis_covered = :nhis_covered,
                        nhis_code = :nhis_code,
                        template_id = :template_id,
                        updated_at = NOW()
                    WHERE id = :test_id
                """)
                db.execute(update_query, {
                    "name": "HIV 1 & 2 Screening",
                    "code": "HIV",
                    "category": "Serology",
                    "description": "HIV 1 & 2 Screening with Confirmation - NHIS Compliant. Includes retroscreening, confirmation test, and rapid kit traceability.",
                    "specimen": "Serum/Plasma",
                    "nhis_covered": True,
                    "nhis_code": "HIV001",
                    "template_id": template_result[0],
                    "test_id": test_id
                })
                print(f"  Updated lab test entry")
        else:
            print("Creating new lab test entry for HIV 1 & 2 Screening...")
            
            # Get template ID
            template_query = text("SELECT id FROM lab_templates WHERE name = 'HIV 1 & 2 Screening' LIMIT 1")
            template_result = db.execute(template_query).fetchone()
            
            if not template_result:
                print("  ERROR: Template not found. Please run update_hiv_template first.")
                return False
            
            # Get admin user
            user_query = text("SELECT id FROM users ORDER BY id LIMIT 1")
            user_result = db.execute(user_query).fetchone()
            admin_user_id = user_result[0] if user_result else 1
            
            insert_query = text("""
                INSERT INTO lab_tests 
                (test_name, test_code, test_category, test_type, description, specimen_type, 
                 routine_tat, cost, nhis_covered, nhis_code, template_id, is_active, created_at)
                VALUES (:name, :code, :category, :type, :description, :specimen, 
                        :tat, :cost, :nhis_covered, :nhis_code, :template_id, True, NOW())
            """)
            db.execute(insert_query, {
                "name": "HIV 1 & 2 Screening",
                "code": "HIV",
                "category": "Serology",
                "type": "Qualitative",
                "description": "HIV 1 & 2 Screening with Confirmation - NHIS Compliant. Includes retroscreening, confirmation test, and rapid kit traceability.",
                "specimen": "Serum/Plasma",
                "tat": 24,
                "cost": 0.00,  # NHIS covered
                "nhis_covered": True,
                "nhis_code": "HIV001",
                "template_id": template_result[0]
            })
            print("  Created new lab test entry")
        
        db.commit()
        print("Lab test entry update completed!")
        return True
        
    except Exception as e:
        print(f"ERROR creating lab test entry: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def print_template_summary():
    """Print a summary of the template configuration"""
    print("\n" + "="*70)
    print("HIV 1 & 2 SCREENING TEMPLATE SUMMARY")
    print("="*70)
    print("\nTEMPLATE STRUCTURE:")
    print("-" * 50)
    print("A. RETROSCREENING (First Response)")
    print("   - Field: first_response")
    print("   - Type: Choice (Reactive/Non-Reactive/Invalid)")
    print("   - Required: Yes")
    print("   - Reference: Non-Reactive = Negative")
    print("")
    print("B. CONFIRMATION TEST")
    print("   - Field: confirmation_result")
    print("   - Type: Choice (Positive/Negative/Indeterminate)")
    print("   - Enabled: Only when First Response = Reactive")
    print("   - Required: Conditional")
    print("")
    print("C. RAPID TEST KITS USED")
    print("   - bio_line: Bio Line test kit")
    print("   - oraquick: OraQuick test kit")
    print("   - determine: Determine test kit")
    print("   - wondfo: Wondfo test kit")
    print("   - Values: Reactive/Non-Reactive/Not Used")
    print("")
    print("D. FINAL INTERPRETATION")
    print("   - Field: final_interpretation")
    print("   - Auto-calculated based on results")
    print("")
    print("INTERPRETATION LOGIC:")
    print("-" * 50)
    print("• Non-Reactive → HIV 1 & 2: Negative")
    print("• Reactive + Positive → HIV 1 & 2: Positive")
    print("• Reactive + Indeterminate → Indeterminate – Repeat testing recommended")
    print("• Reactive + Negative → HIV 1 & 2: Positive (default)")
    print("")
    print("VALIDATION RULES:")
    print("-" * 50)
    print("• Confirmation disabled unless First Response = Reactive")
    print("• At least one rapid kit must be recorded")
    print("• Invalid results flagged for repeat testing")
    print("• Prevent claim submission if result not finalized")
    print("")
    print("NHIS REQUIREMENTS:")
    print("-" * 50)
    print("• Claimable: Yes")
    print("• NHIS Code: HIV001")
    print("• Required for claim:")
    print("  - First Response")
    print("  - Final Interpretation")
    print("  - Specimen Date")
    print("  - Diagnosis")
    print("• Historical data preserved")
    print("• Audit trail maintained")
    print("• API/CSV export available")
    print("="*70)


def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("HIV 1 & 2 SCREENING TEMPLATE UPDATE")
    print("="*70 + "\n")
    
    try:
        # Step 1: Create option sets
        print("Step 1: Creating HIV-specific option sets...")
        create_hiv_option_sets()
        
        # Step 2: Update/create template
        print("\nStep 2: Updating HIV template schema...")
        update_hiv_template()
        
        # Step 3: Create lab test entry
        print("\nStep 3: Creating lab test catalog entry...")
        create_lab_test_entry()
        
        # Step 4: Print summary
        print_template_summary()
        
        print("\n✓ HIV 1 & 2 Screening template update completed successfully!")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
