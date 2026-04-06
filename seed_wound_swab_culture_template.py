#!/usr/bin/env python3
"""
Seed Wound Swab Culture & Sensitivity Template
==============================================
This script creates a complete template for Wound Swab Culture & Sensitivity test
with all required parameters, layout, and reference ranges.

The template includes:
- Specimen information section
- Gram stain results
- Culture results
- Organism identification
- Sensitivity testing for multiple antibiotics
- Microbiologist comments

Age/Sex considerations: Microbiology culture tests are qualitative (not quantitative),
so the "normal" result is consistently "No growth" regardless of age or sex.
Reference ranges use 'ANY' for sex and cover all ages (0-100 years).

Run with: python seed_wound_swab_template.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import json
import uuid
from datetime import datetime

# Database connection - update as needed
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')


# Complete Wound Swab Culture & Sensitivity Template
# This is a comprehensive template with full layout and all fields
WOUND_SWAB_TEMPLATE = {
    "meta": {
        "name": "Wound Swab Culture & Sensitivity",
        "discipline": "MICROBIOLOGY",
        "version": 1
    },
    "layout": {
        "sections": [
            {
                "id": "sec_specimen",
                "title": "Specimen Information",
                "rows": [
                    {
                        "columns": [
                            {
                                "width": 6,
                                "items": ["specimen_type"]
                            },
                            {
                                "width": 6,
                                "items": ["collection_date"]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sec_gram_stain",
                "title": "Gram Stain Results",
                "rows": [
                    {
                        "columns": [
                            {
                                "width": 6,
                                "items": ["gram_stain"]
                            },
                            {
                                "width": 6,
                                "items": ["wbc_grams"]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sec_culture",
                "title": "Culture & Sensitivity",
                "rows": [
                    {
                        "columns": [
                            {
                                "width": 12,
                                "items": ["culture_result"]
                            }
                        ]
                    },
                    {
                        "columns": [
                            {
                                "width": 12,
                                "items": ["organism"]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sec_sensitivity",
                "title": "Antibiotic Sensitivity",
                "rows": [
                    {
                        "columns": [
                            {
                                "width": 4,
                                "items": ["abs_sensitive"]
                            },
                            {
                                "width": 4,
                                "items": ["cipro_sensitive"]
                            },
                            {
                                "width": 4,
                                "items": ["ceftri_sensitive"]
                            }
                        ]
                    },
                    {
                        "columns": [
                            {
                                "width": 4,
                                "items": ["clinda_sensitive"]
                            },
                            {
                                "width": 4,
                                "items": ["metro_sensitive"]
                            },
                            {
                                "width": 4,
                                "items": ["gent_sensitive"]
                            }
                        ]
                    },
                    {
                        "columns": [
                            {
                                "width": 4,
                                "items": ["azith_sensitive"]
                            },
                            {
                                "width": 4,
                                "items": ["cefuro_sensitive"]
                            },
                            {
                                "width": 4,
                                "items": ["doxy_sensitive"]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sec_comments",
                "title": "Additional Comments",
                "rows": [
                    {
                        "columns": [
                            {
                                "width": 12,
                                "items": ["wound_comment"]
                            }
                        ]
                    }
                ]
            }
        ]
    },
    "fields": {
        "specimen_type": {
            "code": "specimen_type",
            "label": "Specimen Type",
            "type": "choice",
            "options": [
                "Wound Swab",
                "Pus Swab",
                "Abscess Aspirate",
                "Ulcer Swab",
                "Surgical Wound",
                "Burn Wound",
                "Other"
            ],
            "required": True
        },
        "collection_date": {
            "code": "collection_date",
            "label": "Collection Date",
            "type": "date",
            "required": True
        },
        "gram_stain": {
            "code": "gram_stain",
            "label": "Gram Stain",
            "type": "choice",
            "options": [
                "No Organisms Seen",
                "Gram Positive Cocci",
                "Gram Negative Bacilli",
                "Gram Positive Bacilli",
                "Gram Negative Cocci",
                "Mixed Flora",
                "Yeast Seen"
            ],
            "required": False
        },
        "wbc_grams": {
            "code": "wbc_grams",
            "label": "WBC on Gram Stain",
            "type": "choice",
            "options": [
                "None",
                "Few",
                "Moderate",
                "Many"
            ],
            "required": False
        },
        "culture_result": {
            "code": "culture_result",
            "label": "Culture Result",
            "type": "choice",
            "options": [
                "No Growth",
                "Mixed Growth",
                "Significant Growth",
                "Contaminant",
                "Heavy Growth",
                "Moderate Growth",
                "Light Growth"
            ],
            "required": True
        },
        "organism": {
            "code": "organism",
            "label": "Organism Isolated",
            "type": "text",
            "required": False,
            "placeholder": "e.g., Staphylococcus aureus, Pseudomonas aeruginosa"
        },
        "abs_sensitive": {
            "code": "abs_sensitive",
            "label": "Amoxicillin/Clavulanate",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "cipro_sensitive": {
            "code": "cipro_sensitive",
            "label": "Ciprofloxacin",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "ceftri_sensitive": {
            "code": "ceftri_sensitive",
            "label": "Ceftriaxone",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "clinda_sensitive": {
            "code": "clinda_sensitive",
            "label": "Clindamycin",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "metro_sensitive": {
            "code": "metro_sensitive",
            "label": "Metronidazole",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "gent_sensitive": {
            "code": "gent_sensitive",
            "label": "Gentamicin",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "azith_sensitive": {
            "code": "azith_sensitive",
            "label": "Azithromycin",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "cefuro_sensitive": {
            "code": "cefuro_sensitive",
            "label": "Cefuroxime",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "doxy_sensitive": {
            "code": "doxy_sensitive",
            "label": "Doxycycline",
            "type": "choice",
            "options": [
                "Sensitive",
                "Resistant",
                "Intermediate",
                "Not Tested"
            ],
            "required": False
        },
        "wound_comment": {
            "code": "wound_comment",
            "label": "Microbiologist Comment",
            "type": "text",
            "required": False,
            "placeholder": "Additional observations or recommendations..."
        }
    },
    "rules": {
        "visibility": [],
        "requiredIf": [
            {
                "field": "organism",
                "condition": "equals",
                "value": "",
                "dependentOn": "culture_result",
                "action": "hide",
                "when": "No Growth"
            },
            {
                "field": "organism",
                "condition": "notEquals",
                "value": "",
                "dependentOn": "culture_result",
                "action": "show",
                "when": "Significant Growth"
            }
        ]
    },
    "calculated": []
}

# Reference ranges for Wound Swab C&S
# For Microbiology tests, these are qualitative (text-based) with options
# Age and Sex don't apply to culture results - "No growth" is normal for all
# Tuple order: (field_code, sex, age_min, age_max, low, high, unit, text_range, critical_low, critical_high)
REFERENCE_RANGES = [
    # Specimen type options
    ("specimen_type", "ANY", 0, 36500, None, None, None, "Wound Swab,Pus Swab,Abscess Aspirate,Ulcer Swab,Surgical Wound,Burn Wound,Other", None, None),
    
    # Gram stain results
    ("gram_stain", "ANY", 0, 36500, None, None, None, "No Organisms Seen,Gram Positive Cocci,Gram Negative Bacilli,Gram Positive Bacilli,Gram Negative Cocci,Mixed Flora,Yeast Seen", None, None),
    
    # WBC on Gram stain
    ("wbc_grams", "ANY", 0, 36500, None, None, None, "None,Few,Moderate,Many", None, None),
    
    # Culture results
    ("culture_result", "ANY", 0, 36500, None, None, None, "No Growth,Mixed Growth,Significant Growth,Contaminant,Heavy Growth,Moderate Growth,Light Growth", None, None),
    
    # All antibiotic sensitivity options (S/R/I/Not Tested)
    ("abs_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("cipro_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("ceftri_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("clinda_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("metro_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("gent_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("azith_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("cefuro_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
    ("doxy_sensitive", "ANY", 0, 36500, None, None, None, "Sensitive,Resistant,Intermediate,Not Tested", None, None),
]

# Lab test catalog codes to link with this template
LAB_TEST_CODES = ["CS_WOUND", "WOUNDCS", "WCULT", "WOUND_CULTURE"]


def create_wound_swab_template():
    """Create the Wound Swab Culture & Sensitivity template."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        created_count = 0
        skipped_count = 0
        
        template_name = "Lab Test - WOUND_SWAB_CULTURE_SENSITIVITY"
        
        # Check if template already exists
        check = conn.execute(text(f"""
            SELECT id FROM lab_templates WHERE name = '{template_name}'
        """))
        
        if check.fetchone():
            print(f"  Template already exists: {template_name}")
            print("  Updating existing template...")
            
            # Get existing template ID
            result = conn.execute(text(f"""
                SELECT id FROM lab_templates WHERE name = '{template_name}'
            """))
            row = result.fetchone()
            if row:
                template_id = row[0]
                
                # Update schema - create new version
                version_result = conn.execute(text(f"""
                    SELECT MAX(version) FROM lab_template_versions 
                    WHERE template_id = '{template_id}'
                """))
                max_version = version_result.fetchone()[0] or 0
                new_version = max_version + 1
                version_id = str(uuid.uuid4())
                schema_json = json.dumps(WOUND_SWAB_TEMPLATE)
                
                # Insert new version
                conn.execute(text(f"""
                    INSERT INTO lab_template_versions 
                    (id, template_id, version, status, schema_json, created_at)
                    VALUES 
                    ('{version_id}', '{template_id}', {new_version}, 'DRAFT', :schema_json, NOW())
                """), {"schema_json": schema_json})
                
                # Update template to point to new version
                conn.execute(text(f"""
                    UPDATE lab_templates 
                    SET current_version = {new_version}, updated_at = NOW()
                    WHERE id = '{template_id}'
                """))
                
                print(f"  Updated template to version {new_version}")
        else:
            # Create new template
            template_id = str(uuid.uuid4())
            version_id = str(uuid.uuid4())
            schema_json = json.dumps(WOUND_SWAB_TEMPLATE)
            
            conn.execute(text(f"""
                INSERT INTO lab_templates 
                (id, name, discipline, status, current_version, created_at, updated_at)
                VALUES 
                ('{template_id}', '{template_name}', 'MICROBIOLOGY', 'active', 1, NOW(), NOW())
            """))
            
            conn.execute(text(f"""
                INSERT INTO lab_template_versions 
                (id, template_id, version, status, schema_json, created_at)
                VALUES 
                ('{version_id}', '{template_id}', 1, 'DRAFT', :schema_json, NOW())
            """), {"schema_json": schema_json})
            
            print(f"  Created new template: {template_name}")
            created_count += 1
        
        # Add reference ranges
        print("\n  Adding reference ranges...")
        ranges_added = 0
        
        for (field_code, sex, age_min, age_max, low, high, unit, text_range, critical_low, critical_high) in REFERENCE_RANGES:
            # Check if reference range already exists
            check_rr = conn.execute(text(f"""
                SELECT id FROM lab_reference_ranges 
                WHERE field_code = '{field_code}' 
                AND sex = '{sex}'
                AND age_min_days = {age_min}
                AND age_max_days = {age_max}
            """))
            
            if not check_rr.fetchone():
                conn.execute(text(f"""
                    INSERT INTO lab_reference_ranges 
                    (id, field_code, sex, age_min_days, age_max_days, low, high, unit, text_range, critical_low, critical_high, created_at)
                    VALUES 
                    (:id, :field_code, :sex, :age_min_days, :age_max_days, :low, :high, :unit, :text_range, :critical_low, :critical_high, NOW())
                """), {
                    "id": str(uuid.uuid4()),
                    "field_code": field_code,
                    "sex": sex,
                    "age_min_days": age_min,
                    "age_max_days": age_max,
                    "low": low,
                    "high": high,
                    "unit": unit,
                    "text_range": text_range,
                    "critical_low": critical_low,
                    "critical_high": critical_high
                })
                ranges_added += 1
            else:
                print(f"    Skipping existing range for: {field_code}")
        
        print(f"  Added {ranges_added} reference ranges")
        
        # Link template to lab test catalog
        print("\n  Linking template to lab test catalog...")
        linked_tests = 0
        
        for test_code in LAB_TEST_CODES:
            # Find the lab test
            test_result = conn.execute(text(f"""
                SELECT id FROM lab_tests WHERE test_code = '{test_code}'
            """))
            test_row = test_result.fetchone()
            
            if test_row:
                test_id = test_row[0]
                
                # Update the lab test to link to this template
                conn.execute(text(f"""
                    UPDATE lab_tests 
                    SET template_id = '{template_id}', template_version = 1
                    WHERE id = {test_id}
                """))
                print(f"    Linked {test_code} to template")
                linked_tests += 1
            else:
                print(f"    Test code {test_code} not found in catalog (may need to be added first)")
        
        conn.commit()
        
        return created_count, skipped_count, ranges_added, linked_tests


def main():
    print("=" * 70)
    print("Seeding Wound Swab Culture & Sensitivity Template")
    print("=" * 70)
    print(f"\nDatabase: {DATABASE_URL}")
    print(f"\nTemplate: Wound Swab Culture & Sensitivity")
    print(f"Fields: {len(WOUND_SWAB_TEMPLATE['fields'])}")
    print(f"Sections: {len(WOUND_SWAB_TEMPLATE['layout']['sections'])}")
    print(f"Reference Ranges: {len(REFERENCE_RANGES)}")
    print(f"Lab Tests to Link: {len(LAB_TEST_CODES)}")
    
    created, skipped, ranges, linked = create_wound_swab_template()
    
    print(f"\n{'=' * 70}")
    print("COMPLETED:")
    print(f"  - Templates created: {created}")
    print(f"  - Templates skipped: {skipped}")
    print(f"  - Reference ranges added: {ranges}")
    print(f"  - Lab tests linked: {linked}")
    print(f"{'=' * 70}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
