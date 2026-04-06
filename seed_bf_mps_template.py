#!/usr/bin/env python3
"""
Seed script for BF (Blood Film) for MPS (Malaria Parasites) laboratory test template.

This template follows standard malaria microscopy reporting used in Ghanaian laboratories
and supports age and gender metadata for epidemiological tracking.

Required Parameters:
1. Malaria Parasites (BF) - Code: MP_BF - Qualitative (Negative/Positive)
2. Specie - Code: MAL_SPECIE - Dropdown
3. Gametocytes Seen - Code: GAM_SEEN - Yes/No (Seen/Not Seen)
4. Trophozoites Count - Code: TROPH_COUNT - Numeric or +/++/+++/++++

Usage:
    python3 seed_bf_mps_template.py
"""
import os
import sys

# Set DATABASE_URL directly before any imports
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')
os.environ['DATABASE_URL'] = DATABASE_URL
# Set DEBUG as boolean
os.environ['DEBUG'] = 'False'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.lab_catalog_models import LabTest
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabOptionSet, LabReferenceRange
)
from app.models.user_models import User

SQLALCHEMY_DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_or_create_admin_user(db: Session):
    """Get or create admin user for audit purposes."""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        # Try to get first available user
        admin = db.query(User).first()
    return admin


def create_malaria_option_sets(db: Session):
    """Create option sets for malaria testing."""
    print("\n" + "="*60)
    print("CREATING MALARIA OPTION SETS")
    print("="*60)
    
    option_sets = {
        # Malaria Parasite Result - Qualitative
        "MP_BF_RESULT": ["Negative", "Positive", "Other"],
        
        # Malaria Species (most common in Ghana is P. falciparum)
        "MALARIA_SPECIES": [
            "Plasmodium falciparum",
            "Plasmodium malariae", 
            "Plasmodium ovale",
            "Plasmodium vivax",
            "Mixed Infection",
            "Not Identified",
            "Other"
        ],
        
        # Yes/No for gametocytes
        "GAM_SEEN": ["Seen", "Not Seen"],
        
        # Semi-quantitative parasite grading
        "PARASITE_GRADING": ["+", "++", "+++", "++++"],
        
        # Parasite density per uL (optional numeric entry)
        "PARASITE_DENSITY": ["<100", "100-500", "500-1000", "1000-5000", ">5000"],
    }
    
    created = 0
    updated = 0
    
    for code, options in option_sets.items():
        existing = db.query(LabOptionSet).filter(LabOptionSet.code == code).first()
        if existing:
            existing.options_json = options
            updated += 1
            print(f"  + Updated: {code}")
        else:
            obj = LabOptionSet(code=code, options_json=options)
            db.add(obj)
            created += 1
            print(f"  + Created: {code}")
    
    db.commit()
    print(f"\nOption Sets: {created} created, {updated} updated")
    return created, updated


def create_bf_mps_template(db: Session, admin_user):
    """Create or update BF for MPS (Malaria Parasites) template."""
    print("\n" + "="*60)
    print("CREATING BF FOR MPS TEMPLATE")
    print("="*60)
    
    template_name = "BF for MPS (Malaria Parasite)"
    
    # Check if template exists
    existing = db.query(LabTemplate).filter(
        LabTemplate.name == template_name
    ).first()
    
    # Build the template schema
    schema_json = {
        "meta": {
            "name": "BF for MPS (Malaria Parasite)",
            "discipline": "PARASITOLOGY",
            "description": "Blood Film Examination for Malaria Parasites - Ghana NHIS Compliant",
            "test_code": "MPS001",
            "specimen_type": "Thick & Thin Blood Film",
            "nhis_compliant": True,
            "version": "2.0",
            "updated_date": datetime.utcnow().isoformat()
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_parasite",
                    "title": "Parasite Detection",
                    "rows": [
                        {"columns": [{"items": ["MP_BF", "MP_BF_OTHER"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_species",
                    "title": "Species Identification",
                    "rows": [
                        {"columns": [{"items": ["MAL_SPECIE", "MAL_SPECIE_OTHER"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_gametocytes",
                    "title": "Gametocytes",
                    "rows": [
                        {"columns": [{"items": ["GAM_SEEN"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_count",
                    "title": "Parasite Count",
                    "rows": [
                        {"columns": [{"items": ["TROPH_COUNT"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_notes",
                    "title": "Notes",
                    "rows": [
                        {"columns": [{"items": ["NOTES"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "MP_BF": {
                "type": "choice",
                "label": "Malaria Parasites (BF)",
                "code": "MP_BF",
                "optionSet": "MP_BF_RESULT",
                "required": True,
                "unit": None,
                "description": "Primary malaria parasite detection result",
                "result_type": "qualitative"
            },
            "MP_BF_OTHER": {
                "type": "text",
                "label": "Specify Other Parasite",
                "code": "MP_BF_OTHER",
                "required": False,
                "unit": None,
                "placeholder": "Enter other parasite detected...",
                "description": "Text field for specifying other parasites when 'Other' is selected",
                "result_type": "qualitative",
                "dependency": {
                    "field": "MP_BF",
                    "value": "Other",
                    "action": "show"
                }
            },
            "MAL_SPECIE": {
                "type": "choice",
                "label": "Specie",
                "code": "MAL_SPECIE",
                "optionSet": "MALARIA_SPECIES",
                "required": False,
                "unit": None,
                "description": "Plasmodium species identification",
                "result_type": "qualitative",
                "dependency": {
                    "field": "MP_BF",
                    "value": "Positive",
                    "action": "show"
                }
            },
            "MAL_SPECIE_OTHER": {
                "type": "text",
                "label": "Specify Other Species",
                "code": "MAL_SPECIE_OTHER",
                "required": False,
                "unit": None,
                "placeholder": "Enter other Plasmodium species...",
                "description": "Text field for specifying other malaria species when 'Other' is selected",
                "result_type": "qualitative",
                "dependency": {
                    "field": "MAL_SPECIE",
                    "value": "Other",
                    "action": "show"
                }
            },
            "GAM_SEEN": {
                "type": "choice",
                "label": "Gametocytes Seen",
                "code": "GAM_SEEN",
                "optionSet": "GAM_SEEN",
                "required": False,
                "unit": None,
                "description": "Sexual stage parasites (gametocytes)",
                "result_type": "qualitative",
                "dependency": {
                    "field": "MP_BF",
                    "value": "Positive",
                    "action": "show"
                }
            },
            "TROPH_COUNT": {
                "type": "text",
                "label": "Trophozoites Count",
                "code": "TROPH_COUNT",
                "required": False,
                "unit": "Parasites/µL",
                "placeholder": "e.g., 120 parasites/µL",
                "description": "Parasite density - numeric (parasites/uL) or semi-quantitative (+/++/+++/++++)",
                "result_type": "quantitative",
                "reference_range": {
                    "text_range": "NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL"
                }
            },
            "NOTES": {
                "type": "text",
                "label": "Notes",
                "code": "NOTES",
                "required": False,
                "multiline": True,
                "placeholder": "Additional observations or comments"
            }
        },
        "rules": {
            "visibility": [
                {
                    "field": "MP_BF_OTHER",
                    "condition": "MP_BF == 'Other'",
                    "action": "show"
                },
                {
                    "field": "MAL_SPECIE",
                    "condition": "MP_BF == 'Positive'",
                    "action": "show"
                },
                {
                    "field": "MAL_SPECIE_OTHER",
                    "condition": "MAL_SPECIE == 'Other'",
                    "action": "show"
                },
                {
                    "field": "GAM_SEEN",
                    "condition": "MP_BF == 'Positive'",
                    "action": "show"
                },
                {
                    "field": "TROPH_COUNT",
                    "condition": "MP_BF == 'Positive'",
                    "action": "show"
                }
            ],
            "requiredIf": [
                {
                    "field": "MP_BF_OTHER",
                    "condition": "MP_BF == 'Other'",
                    "error_message": "Please specify the other parasite detected"
                },
                {
                    "field": "MAL_SPECIE",
                    "condition": "MP_BF == 'Positive'",
                    "error_message": "Species is required when Malaria Parasites = Positive"
                },
                {
                    "field": "MAL_SPECIE_OTHER",
                    "condition": "MAL_SPECIE == 'Other'",
                    "error_message": "Please specify the other malaria species"
                }
            ],
            "auto_clear": [
                {
                    "condition": "MP_BF == 'Negative'",
                    "actions": [
                        {"field": "MP_BF_OTHER", "value": ""},
                        {"field": "MAL_SPECIE", "value": ""},
                        {"field": "MAL_SPECIE_OTHER", "value": ""},
                        {"field": "GAM_SEEN", "value": "Not Seen"},
                        {"field": "TROPH_COUNT", "value": ""}
                    ]
                },
                {
                    "condition": "MP_BF == 'Positive'",
                    "actions": [
                        {"field": "MP_BF_OTHER", "value": ""}
                    ]
                }
            ]
        },
        "calculated": [],
        "interpretation": {
            "auto_interpret": True,
            "rules": [
                {
                    "when": "MP_BF == 'Negative'",
                    "result": "Normal",
                    "interpretation": "No malaria parasites seen"
                },
                {
                    "when": "MP_BF == 'Positive'",
                    "result": "Abnormal",
                    "interpretation": "Malaria parasites detected"
                }
            ]
        },
        "demographic_config": {
            "age_dependent": False,
            "gender_dependent": False,
            "applies_to_all_ages": True,
            "applies_to_all_genders": True,
            "record_age_for_epidemiology": True,
            "record_gender_for_epidemiology": True,
            "age_categories": ["neonate", "infant", "child", "adolescent", "adult", "elderly"]
        },
        "print_config": {
            "footer_notes": [
                "PARASITE DENSITY GRADING:",
                "NEG: 0 p/uL",
                "LOW: 1-100 p/uL",
                "MODERATE: 101-100,000 p/uL",
                "SEVERE: >100,000 p/uL OR >10,000 with Hb <=5g/dL"
            ],
            "show_footer_on_print": True
        }
    }
    
    if existing:
        # Update existing template - create new version
        next_version = (existing.current_version or 0) + 1
        
        version = LabTemplateVersion(
            template_id=existing.id,
            version=next_version,
            status="PUBLISHED",
            schema_json=schema_json,
            change_note="Updated with Ghana-standard field codes (MP_BF, MAL_SPECIE, GAM_SEEN, TROPH_COUNT)",
            created_by_id=admin_user.id if admin_user else None
        )
        db.add(version)
        
        existing.current_version = next_version
        existing.discipline = "PARASITOLOGY"
        existing.status = "PUBLISHED"
        existing.updated_at = datetime.utcnow()
        
        print(f"  + Updated: {template_name} (v{next_version})")
    else:
        # Create new template
        db_template = LabTemplate(
            name=template_name,
            discipline="PARASITOLOGY",
            status="PUBLISHED",
            current_version=1,
            created_by_id=admin_user.id if admin_user else None
        )
        db.add(db_template)
        db.flush()
        
        version = LabTemplateVersion(
            template_id=db_template.id,
            version=1,
            status="PUBLISHED",
            schema_json=schema_json,
            change_note="Initial BF for MPS template - Ghana NHIS compliant",
            created_by_id=admin_user.id if admin_user else None
        )
        db.add(version)
        
        print(f"  + Created: {template_name} (v1)")
    
    db.commit()
    return existing is not None


def create_reference_ranges(db: Session):
    """Create reference ranges for BF for MPS template."""
    print("\n" + "="*60)
    print("CREATING REFERENCE RANGES")
    print("="*60)
    
    # Reference ranges for malaria - same for all ages and genders
    reference_ranges = [
        {
            "field_code": "MP_BF",
            "sex": "ANY",
            "age_min_days": None,
            "age_max_days": None,
            "text_range": "Negative",
            "unit": None,
            "interpretation": "No malaria parasites seen"
        },
        {
            "field_code": "MAL_SPECIE",
            "sex": "ANY", 
            "age_min_days": None,
            "age_max_days": None,
            "text_range": "Not Applicable",
            "unit": None,
            "interpretation": "Species only applicable when parasites are detected"
        },
        {
            "field_code": "GAM_SEEN",
            "sex": "ANY",
            "age_min_days": None,
            "age_max_days": None,
            "text_range": "Not Seen",
            "unit": None,
            "interpretation": "No gametocytes seen (normal)"
        },
        {
            "field_code": "TROPH_COUNT",
            "sex": "ANY",
            "age_min_days": None,
            "age_max_days": None,
            "text_range": "NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL",
            "low": None,
            "high": None,
            "unit": "Parasites/µL",
            "interpretation": "Malaria parasite density interpretation scale"
        }
    ]
    
    created = 0
    updated = 0
    
    for ref in reference_ranges:
        existing = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == ref["field_code"],
            LabReferenceRange.sex == ref["sex"]
        ).first()
        
        if existing:
            existing.text_range = ref.get("text_range")
            existing.low = ref.get("low")
            existing.high = ref.get("high")
            existing.unit = ref.get("unit")
            existing.age_min_days = ref.get("age_min_days")
            existing.age_max_days = ref.get("age_max_days")
            updated += 1
            print(f"  + Updated reference range for: {ref['field_code']}")
        else:
            new_ref = LabReferenceRange(
                field_code=ref["field_code"],
                sex=ref["sex"],
                age_min_days=ref.get("age_min_days"),
                age_max_days=ref.get("age_max_days"),
                text_range=ref.get("text_range"),
                low=ref.get("low"),
                high=ref.get("high"),
                unit=ref.get("unit")
            )
            db.add(new_ref)
            created += 1
            print(f"  + Created reference range for: {ref['field_code']}")
    
    db.commit()
    print(f"\nReference Ranges: {created} created, {updated} updated")
    return created, updated


def ensure_lab_test_catalog_entry(db: Session):
    """Ensure BF for MPS exists in lab test catalog."""
    print("\n" + "="*60)
    print("CHECKING LAB TEST CATALOG")
    print("="*60)
    
    # Check if BF_MP test exists
    existing = db.query(LabTest).filter(LabTest.test_code == "MPS001").first()
    
    if existing:
        print(f"  + Test already exists: {existing.test_name} ({existing.test_code})")
        return False
    else:
        # Create the lab test entry
        new_test = LabTest(
            test_code="MPS001",
            test_name="BF for MPS (Malaria Parasite)",
            test_category="PARASITOLOGY",
            specimen_type="Thick & Thin Blood Film",
            description="Blood Film Examination for Malaria Parasites - microscopy based",
            is_active=True,
            turnaround_time_hours=2,
            price=8.00  # Ghana NHIS price
        )
        db.add(new_test)
        db.commit()
        print(f"  + Created lab test: BF for MPS (MPS001)")
        return True


def main():
    """Main seeding function."""
    print("\n" + "="*70)
    print("BF FOR MPS (MALARIA PARASITES) TEMPLATE SEEDER")
    print("="*70)
    print(f"Database: {SQLALCHEMY_DATABASE_URL[:50]}...")
    
    db = SessionLocal()
    
    try:
        # Get admin user for audit
        admin_user = get_or_create_admin_user(db)
        print(f"Using admin user: {admin_user.username if admin_user else 'None'}")
        
        # Run seeders
        opt_created, opt_updated = create_malaria_option_sets(db)
        template_updated = create_bf_mps_template(db, admin_user)
        range_created, range_updated = create_reference_ranges(db)
        test_created = ensure_lab_test_catalog_entry(db)
        
        # Summary
        print("\n" + "="*70)
        print("SEEDING COMPLETE - SUMMARY")
        print("="*70)
        print(f"  Option Sets: {opt_created} created, {opt_updated} updated")
        print(f"  Template: {'Updated' if template_updated else 'Created'}")
        print(f"  Reference Ranges: {range_created} created, {range_updated} updated")
        print(f"  Lab Test Catalog: {'Created' if test_created else 'Already exists'}")
        
        print("\n" + "="*70)
        print("BF FOR MPS TEMPLATE PARAMETERS:")
        print("="*70)
        print("  1. MP_BF - Malaria Parasites (BF)")
        print("     Type: Choice (Negative/Positive)")
        print("     Reference: Negative (No malaria parasites seen)")
        print("")
        print("  2. MAL_SPECIE - Specie")
        print("     Type: Dropdown")
        print("     Options: P. falciparum, P. malariae, P. ovale, P. vivax, Mixed, Not Identified")
        print("")
        print("  3. GAM_SEEN - Gametocytes Seen")
        print("     Type: Choice (Seen/Not Seen)")
        print("     Reference: Not Seen")
        print("")
        print("  4. TROPH_COUNT - Trophozoites Count")
        print("     Type: Text (numeric or +/++/+++/++++)")
        print("     Unit: Parasites/uL OR Parasites per HPF")
        print("")
        print("  Age & Gender: Stored for epidemiology (not used in reference range)")
        print("="*70)
        
    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
