#!/usr/bin/env python3
"""
Seed All Swab Culture Templates
================================
This script creates comprehensive templates for all swab culture tests:
- Wound Swab Culture & Sensitivity (already created)
- Throat Swab Culture
- Ear Swab Culture
- Eye Swab Culture
- Vaginal Swab Culture (HVS)
- Urethral Swab Culture

Each template includes specimen-specific options, culture results,
organism identification, and antibiotic sensitivity panels.

Run with: python3 seed_swab_culture_templates.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import json
import uuid
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')


# Base swab culture template structure
def create_swab_template(name, specimen_options, test_codes):
    """Create a swab culture template with specimen-specific options."""
    return {
        "meta": {
            "name": name,
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
                                {"width": 6, "items": ["specimen_type"]},
                                {"width": 6, "items": ["collection_date"]}
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
                                {"width": 6, "items": ["gram_stain"]},
                                {"width": 6, "items": ["wbc_grams"]}
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
                                {"width": 12, "items": ["culture_result"]}
                            ]
                        },
                        {
                            "columns": [
                                {"width": 12, "items": ["organism"]}
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
                                {"width": 4, "items": ["abs_sensitive"]},
                                {"width": 4, "items": ["cipro_sensitive"]},
                                {"width": 4, "items": ["ceftri_sensitive"]}
                            ]
                        },
                        {
                            "columns": [
                                {"width": 4, "items": ["clinda_sensitive"]},
                                {"width": 4, "items": ["metro_sensitive"]},
                                {"width": 4, "items": ["azith_sensitive"]}
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
                                {"width": 12, "items": ["swab_comment"]}
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
                "options": specimen_options,
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
                "options": ["None", "Few", "Moderate", "Many"],
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
                    "Contaminant"
                ],
                "required": True
            },
            "organism": {
                "code": "organism",
                "label": "Organism Isolated",
                "type": "text",
                "required": False
            },
            "abs_sensitive": {
                "code": "abs_sensitive",
                "label": "Amoxicillin/Clavulanate",
                "type": "choice",
                "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                "required": False
            },
            "cipro_sensitive": {
                "code": "cipro_sensitive",
                "label": "Ciprofloxacin",
                "type": "choice",
                "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                "required": False
            },
            "ceftri_sensitive": {
                "code": "ceftri_sensitive",
                "label": "Ceftriaxone",
                "type": "choice",
                "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                "required": False
            },
            "clinda_sensitive": {
                "code": "clinda_sensitive",
                "label": "Clindamycin",
                "type": "choice",
                "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                "required": False
            },
            "metro_sensitive": {
                "code": "metro_sensitive",
                "label": "Metronidazole",
                "type": "choice",
                "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                "required": False
            },
            "azith_sensitive": {
                "code": "azith_sensitive",
                "label": "Azithromycin",
                "type": "choice",
                "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                "required": False
            },
            "swab_comment": {
                "code": "swab_comment",
                "label": "Microbiologist Comment",
                "type": "text",
                "required": False
            }
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }


# All swab culture templates to create
SWAB_TEMPLATES = [
    {
        "name": "Throat Swab Culture",
        "template_name": "Lab Test - THROAT_SWAB_CULTURE",
        "specimen_options": ["Throat Swab", "Tonsillar Swab", "Pharyngeal Swab"],
        "test_codes": ["TCULT", "THROATCS", "THROAT_CULTURE"]
    },
    {
        "name": "Ear Swab Culture",
        "template_name": "Lab Test - EAR_SWAB_CULTURE",
        "specimen_options": ["Ear Swab", "Ear Discharge", "Middle Ear Fluid"],
        "test_codes": ["ECULT", "EARCS", "EAR_CULTURE"]
    },
    {
        "name": "Eye Swab Culture",
        "template_name": "Lab Test - EYE_SWAB_CULTURE",
        "specimen_options": ["Conjunctival Swab", "Corneal Scrape", "Eye Discharge", "Vitreous Tap"],
        "test_codes": ["EYECULT", "EYECS", "EYE_CULTURE"]
    },
    {
        "name": "Vaginal Swab Culture (HVS)",
        "template_name": "Lab Test - HVS_CULTURE",
        "specimen_options": ["High Vaginal Swab", "Low Vaginal Swab", "Endocervical Swab"],
        "test_codes": ["VCULT", "HVS", "HVSCS", "HVS_CULTURE", "VAGINAL_CS"]
    },
    {
        "name": "Urethral Swab Culture",
        "template_name": "Lab Test - URETHRAL_SWAB_CULTURE",
        "specimen_options": ["Urethral Swab", "Urethral Discharge", "First Catch Urine"],
        "test_codes": ["UCULT", "URETHRALCS", "URETHRAL_CULTURE"]
    }
]


def create_swab_templates():
    """Create all swab culture templates."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        created_count = 0
        skipped_count = 0
        linked_count = 0
        
        for tmpl_def in SWAB_TEMPLATES:
            template = create_swab_template(tmpl_def["name"], tmpl_def["specimen_options"], tmpl_def["test_codes"])
            template_name = tmpl_def["template_name"]
            
            # Check if template exists
            check = conn.execute(text(f"""
                SELECT id FROM lab_templates WHERE name = '{template_name}'
            """))
            
            if check.fetchone():
                print(f"  Skipping: {template_name} (already exists)")
                skipped_count += 1
                continue
            
            # Create new template
            template_id = str(uuid.uuid4())
            version_id = str(uuid.uuid4())
            schema_json = json.dumps(template)
            
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
            
            print(f"  Created: {template_name}")
            created_count += 1
            
            # Try to link to test codes
            for test_code in tmpl_def["test_codes"]:
                result = conn.execute(text(f"""
                    SELECT id FROM lab_tests WHERE test_code = '{test_code}'
                """))
                test_row = result.fetchone()
                
                if test_row:
                    test_id = test_row[0]
                    conn.execute(text(f"""
                        UPDATE lab_tests 
                        SET template_id = '{template_id}', template_version = 1
                        WHERE id = {test_id}
                    """))
                    print(f"    Linked {test_code} to template")
                    linked_count += 1
        
        conn.commit()
        
        return created_count, skipped_count, linked_count


def main():
    print("=" * 70)
    print("Seeding All Swab Culture Templates")
    print("=" * 70)
    print(f"\nDatabase: {DATABASE_URL}")
    print(f"\nTemplates to create: {len(SWAB_TEMPLATES)}")
    
    created, skipped, linked = create_swab_templates()
    
    print(f"\n{'=' * 70}")
    print("COMPLETED:")
    print(f"  - Templates created: {created}")
    print(f"  - Templates skipped: {skipped}")
    print(f"  - Lab tests linked: {linked}")
    print(f"{'=' * 70}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
