#!/usr/bin/env python3
"""
HVS R/E Template Configuration Seed Script

This script updates the High Vaginal Swab (HVS) R/E laboratory test template
to reflect standard microscopy reporting used in Ghana hospital laboratories.

Parameters configured:
- Epith. Cells (Numeric, /HPF)
- Pus Cells (Numeric, /HPF)
- RBCs (Numeric, /HPF)
- T. vaginalis (Qualitative, -, dropdown: Present, Absent, Seen, Not Seen)
- Yeast-like cells (Qualitative, -, dropdown: Present, Absent, Seen, Not Seen)
- Clue Cells (Qualitative, -, dropdown: Present, Absent, Seen, Not Seen)
- Spermatozoa (Qualitative, -, dropdown: Present, Absent, Seen, Not Seen)

All parameters have:
- reference_range = "-"
- flag_enabled = false

Usage:
    python seed_hvs_re_template.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.crud.lab_template_crud import (
    get_template, 
    create_template, 
    save_draft, 
    publish_version,
    upsert_option_set,
    get_option_set
)
from app.models.lab_template_models import LabTemplate, LabTemplateVersion
from sqlalchemy.orm import Session


def create_hvs_option_sets(db: Session):
    """Create option sets for HVS R/E test parameters."""
    
    # Option set for organism detection (T. vaginalis, Yeast-like cells, Clue Cells, Spermatozoa)
    # Note: Epith. Cells, Pus Cells, RBCs are text fields for manual input, not dropdowns
    organism_detection_options = ["Absent", "Present", "Seen", "Not Seen"]
    
    # Create or update option sets
    upsert_option_set(db, "HVS_ORGANISM_DETECTION", organism_detection_options)
    print("Created option set: HVS_ORGANISM_DETECTION")
    
    return True


def create_hvs_re_template(db: Session, created_by_id: int = 1):
    """
    Create or update the HVS R/E template with Ghana laboratory standard parameters.
    
    Template fields:
    1. Epith. Cells - Text/Choice with /HPF unit
    2. Pus Cells - Text/Choice with /HPF unit
    3. RBCs - Text/Choice with /HPF unit
    4. T. vaginalis - Qualitative (no unit)
    5. Yeast-like cells - Qualitative (no unit)
    6. Clue Cells - Qualitative (no unit)
    7. Spermatozoa - Qualitative (no unit)
    """
    
    template_name = "High Vaginal Swab (HVS) R/E"
    discipline = "MICROBIOLOGY"
    
    # Check if template already exists
    existing_templates = db.query(LabTemplate).filter(
        LabTemplate.name == template_name,
        LabTemplate.discipline == discipline,
        LabTemplate.is_deleted != True
    ).all()
    
    if existing_templates:
        template = existing_templates[0]
        print(f"Found existing template: {template_name} (ID: {template.id})")
    else:
        # Create new template
        template = create_template(
            db=db,
            name=template_name,
            discipline=discipline,
            created_by_id=created_by_id,
            schema_json={
                "meta": {
                    "name": template_name,
                    "discipline": discipline,
                    "version": 1,
                    "test_type": "Microscopy",
                    "short_name": "HVS R/E",
                    "department": "Microbiology"
                },
                "layout": {
                    "sections": [
                        {
                            "id": "sec_microscopy",
                            "title": "Microscopy Results",
                            "rows": [
                                {
                                    "columns": [
                                        {
                                            "width": 12,
                                            "items": [
                                                "epith_cells",
                                                "pus_cells",
                                                "rbcs"
                                            ]
                                        }
                                    ]
                                },
                                {
                                    "columns": [
                                        {
                                            "width": 12,
                                            "items": [
                                                "t_vaginalis",
                                                "yeast_like_cells",
                                                "clue_cells",
                                                "spermatozoa"
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "fields": {
                    "epith_cells": {
                        "code": "epith_cells",
                        "label": "Epith. Cells",
                        "type": "numeric",
                        "unit": "/HPF",
                        "decimals": 0,
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    },
                    "pus_cells": {
                        "code": "pus_cells",
                        "label": "Pus Cells",
                        "type": "numeric",
                        "unit": "/HPF",
                        "decimals": 0,
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    },
                    "rbcs": {
                        "code": "rbcs",
                        "label": "RBCs",
                        "type": "numeric",
                        "unit": "/HPF",
                        "decimals": 0,
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    },
                    "t_vaginalis": {
                        "code": "t_vaginalis",
                        "label": "T. vaginalis",
                        "type": "choice",
                        "optionSet": "HVS_ORGANISM_DETECTION",
                        "unit": "-",
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    },
                    "yeast_like_cells": {
                        "code": "yeast_like_cells",
                        "label": "Yeast-like cells",
                        "type": "choice",
                        "optionSet": "HVS_ORGANISM_DETECTION",
                        "unit": "-",
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    },
                    "clue_cells": {
                        "code": "clue_cells",
                        "label": "Clue Cells",
                        "type": "choice",
                        "optionSet": "HVS_ORGANISM_DETECTION",
                        "unit": "-",
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    },
                    "spermatozoa": {
                        "code": "spermatozoa",
                        "label": "Spermatozoa",
                        "type": "choice",
                        "optionSet": "HVS_ORGANISM_DETECTION",
                        "unit": "-",
                        "required": False,
                        "flag_enabled": False,
                        "reference_range": "-"
                    }
                },
                "rules": {
                    "visibility": [],
                    "requiredIf": []
                },
                "calculated": []
            }
        )
        print(f"Created new template: {template_name} (ID: {template.id})")
    
    # Save draft with the proper schema
    schema_json = {
        "meta": {
            "name": template_name,
            "discipline": discipline,
            "version": 1,
            "test_type": "Microscopy",
            "short_name": "HVS R/E",
            "department": "Microbiology"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_microscopy",
                    "title": "Microscopy Results",
                    "rows": [
                        {
                            "columns": [
                                {
                                    "width": 12,
                                    "items": [
                                        "epith_cells",
                                        "pus_cells",
                                        "rbcs"
                                    ]
                                }
                            ]
                        },
                        {
                            "columns": [
                                {
                                    "width": 12,
                                    "items": [
                                        "t_vaginalis",
                                        "yeast_like_cells",
                                        "clue_cells",
                                        "spermatozoa"
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "fields": {
            "epith_cells": {
                "code": "epith_cells",
                "label": "Epith. Cells",
                "type": "numeric",
                "unit": "/HPF",
                "decimals": 0,
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            },
            "pus_cells": {
                "code": "pus_cells",
                "label": "Pus Cells",
                "type": "numeric",
                "unit": "/HPF",
                "decimals": 0,
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            },
            "rbcs": {
                "code": "rbcs",
                "label": "RBCs",
                "type": "numeric",
                "unit": "/HPF",
                "decimals": 0,
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            },
            "t_vaginalis": {
                "code": "t_vaginalis",
                "label": "T. vaginalis",
                "type": "choice",
                "optionSet": "HVS_ORGANISM_DETECTION",
                "unit": "-",
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            },
            "yeast_like_cells": {
                "code": "yeast_like_cells",
                "label": "Yeast-like cells",
                "type": "choice",
                "optionSet": "HVS_ORGANISM_DETECTION",
                "unit": "-",
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            },
            "clue_cells": {
                "code": "clue_cells",
                "label": "Clue Cells",
                "type": "choice",
                "optionSet": "HVS_ORGANISM_DETECTION",
                "unit": "-",
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            },
            "spermatozoa": {
                "code": "spermatozoa",
                "label": "Spermatozoa",
                "type": "choice",
                "optionSet": "HVS_ORGANISM_DETECTION",
                "unit": "-",
                "required": False,
                "flag_enabled": False,
                "reference_range": "-"
            }
        },
        "rules": {
            "visibility": [],
            "requiredIf": []
        },
        "calculated": []
    }
    
    # Save as draft
    save_draft(db, template.id, schema_json, created_by_id)
    print(f"Saved draft for template: {template_name}")
    
    # Get current published version to determine next version number
    from app.crud.lab_template_crud import get_published_version, get_draft_version
    current_published = get_published_version(db, template.id)
    current_draft = get_draft_version(db, template.id)
    
    # If there's no published version yet and draft exists with version 1, we need to publish as version 2
    # to avoid the unique constraint violation on (template_id, version)
    if current_published is None and current_draft and current_draft.version == 1:
        # Need to publish as version 2 since version 1 already exists as DRAFT
        from uuid import uuid4
        from app.crud.lab_template_crud import _compute_checksum
        
        checksum = _compute_checksum(schema_json)
        new_published = LabTemplateVersion(
            id=uuid4(),
            template_id=template.id,
            version=2,
            status="PUBLISHED",
            schema_json=schema_json,
            change_note="Updated HVS R/E template to Ghana laboratory standard - microscopy parameters",
            created_by_id=created_by_id,
            checksum=checksum
        )
        db.add(new_published)
        template.current_version = 2
        template.status = "PUBLISHED"
        db.commit()
        print(f"Published template: {template_name} (version 2)")
    else:
        # Normal case - use the publish_version function
        next_version = (current_published.version + 1) if current_published else 1
        publish_version(
            db, 
            template.id, 
            change_note=f"Updated HVS R/E template to Ghana laboratory standard - microscopy parameters (v{next_version})", 
            created_by_id=created_by_id
        )
        print(f"Published template: {template_name} (version {next_version})")
    
    return template


def update_hvs_re_test_catalog(db: Session):
    """
    Update all HVS R/E tests in the lab catalog to link to the new template.
    This includes:
    - HVS_RE (ID 13) - High Vaginal Swab (HVS) R/E
    - HVS-RE (ID 95) - HVS R/E (alternate code)
    """
    from app.models.lab_catalog_models import LabTest
    
    # Get the template
    template = db.query(LabTemplate).filter(
        LabTemplate.name == "High Vaginal Swab (HVS) R/E",
        LabTemplate.discipline == "MICROBIOLOGY",
        LabTemplate.is_deleted != True
    ).first()
    
    if not template:
        print("Template not found, skipping test catalog update")
        return
    
    # Find all HVS R/E tests (by test code pattern)
    hvs_tests = db.query(LabTest).filter(
        LabTest.test_code.in_(['HVS_RE', 'HVS-RE'])
    ).all()
    
    for hvs_test in hvs_tests:
        hvs_test.template_id = template.id
        hvs_test.template_version = template.current_version
        print(f"Updated {hvs_test.test_name} (ID: {hvs_test.id}, Code: {hvs_test.test_code}) to use template (ID: {template.id})")
    
    db.commit()
    print(f"Updated {len(hvs_tests)} HVS R/E tests in catalog")


def create_hvs_reference_ranges(db: Session):
    """
    Create reference range entries for HVS R/E template fields.
    These are observational findings, so they don't have numeric reference ranges.
    We set text_range to "-" to indicate no reference range is applicable.
    """
    from app.crud.lab_catalog_crud import create_template_reference_range
    
    # Parameters that use /HPF unit (cell counts)
    hpf_fields = [
        "epith_cells",
        "pus_cells",
        "rbcs"
    ]
    
    # Parameters with no unit (organism detection)
    no_unit_fields = [
        "t_vaginalis",
        "yeast_like_cells",
        "clue_cells",
        "spermatozoa"
    ]
    
    # Create reference ranges for HPF fields
    for field_code in hpf_fields:
        try:
            create_template_reference_range(
                db=db,
                field_code=field_code,
                sex="ANY",
                age_min_days=None,
                age_max_days=None,
                low=None,
                high=None,
                critical_low=None,
                critical_high=None,
                text_range="-",
                unit="/HPF"
            )
            print(f"Created reference range for {field_code}")
        except Exception as e:
            # Reference range might already exist
            print(f"Reference range for {field_code}: {e}")
    
    # Create reference ranges for organism fields
    for field_code in no_unit_fields:
        try:
            create_template_reference_range(
                db=db,
                field_code=field_code,
                sex="ANY",
                age_min_days=None,
                age_max_days=None,
                low=None,
                high=None,
                critical_low=None,
                critical_high=None,
                text_range="-",
                unit="-"
            )
            print(f"Created reference range for {field_code}")
        except Exception as e:
            print(f"Reference range for {field_code}: {e}")
    
    return True


def main():
    """Main function to run the seed script."""
    print("=" * 60)
    print("HVS R/E Template Configuration")
    print("Ghana Laboratory Standard")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Create option sets
        print("\n1. Creating option sets...")
        create_hvs_option_sets(db)
        
        # Create/update template
        print("\n2. Creating/updating HVS R/E template...")
        create_hvs_re_template(db, created_by_id=1)
        
        # Create reference ranges
        print("\n3. Creating reference ranges for HVS parameters...")
        create_hvs_reference_ranges(db)
        
        # Update test catalog
        print("\n4. Updating lab test catalog...")
        update_hvs_re_test_catalog(db)
        
        print("\n" + "=" * 60)
        print("HVS R/E Template Configuration Complete!")
        print("=" * 60)
        
        # Print summary of configured parameters
        print("\nConfigured Parameters:")
        print("-" * 40)
        print("Parameter        | Type        | Unit   | Range")
        print("-" * 40)
        print("Epith. Cells     | Numeric     | /HPF   | -")
        print("Pus Cells        | Numeric     | /HPF   | -")
        print("RBCs             | Numeric     | /HPF   | -")
        print("T. vaginalis     | Choice      | -      | -")
        print("Yeast-like cells | Choice      | -      | -")
        print("Clue Cells       | Choice      | -      | -")
        print("Spermatozoa      | Choice      | -      | -")
        print("-" * 40)
        
        print("\nOption Sets:")
        print("-" * 40)
        print("HVS_ORGANISM_DETECTION: ['Absent', 'Present', 'Seen', 'Not Seen']")
        print("-" * 40)
        print("\nNote: Epith. Cells, Pus Cells, RBCs are numeric fields")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
