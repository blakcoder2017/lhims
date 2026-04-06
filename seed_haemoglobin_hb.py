#!/usr/bin/env python3
"""
Haemoglobin (HB) Test Template Seeder for Ghana LHIMS

This script creates the Haemoglobin (HB) laboratory test with:
1. Lab Test Catalog entry (LabTest)
2. Lab Template with schema (LabTemplate, LabTemplateVersion)
3. Template Reference Ranges (LabReferenceRange) - age in DAYS

Test Details:
- Parameter Name: Haemoglobin
- Parameter Code: HB
- Unit: g/dL
- Result Type: Numeric

Reference Ranges (Age and Gender Based):
- Neonates (0–28 Days): 16.5 – 21.5 g/dL (both male and female)
- Infants (1–12 Months): 10.5 – 13.5 g/dL (both male and female)
- Children (1–12 Years): 11.0 – 13.5 g/dL (both male and female)
- Adolescents (13–17 Years): Male 12.0 – 16.0 g/dL, Female 11.5 – 15.0 g/dL
- Adults (18+ Years): Male 13.5 – 17.5 g/dL, Female 12.0 – 15.5 g/dL

Usage:
    python3 seed_haemoglobin_hb.py

Requirements:
    - Database must be initialized
    - Admin user must exist
"""

import os
import sys
import uuid
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set DEBUG env var before importing app modules
os.environ['DEBUG'] = 'false'

# Import via app.main to ensure proper model loading order
from app.main import app
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.lab_catalog_models import LabTest
from app.models.lab_models import ReferenceRange
from app.models.lab_template_models import LabTemplate, LabTemplateVersion, LabReferenceRange

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_haemoglobin_test(db: Session):
    """
    Create/update the Haemoglobin (HB) lab test with all components.
    """
    print("=" * 60)
    print("Creating Haemoglobin (HB) Test Template")
    print("=" * 60)
    
    # Test code for Haemoglobin
    test_code = "HB"
    test_name = "Haemoglobin (HB)"
    test_category = "Haematology"
    specimen_type = "EDTA Blood"
    description = "Haemoglobin measurement - measures the concentration of haemoglobin in blood, used to assess anaemia, polycythaemia, and overall oxygen-carrying capacity."
    
    # Check if test already exists in lab catalog
    existing_test = db.query(LabTest).filter(
        LabTest.test_code == test_code,
        LabTest.is_active == True
    ).first()
    
    if existing_test:
        print(f"\n[INFO] Found existing Haemoglobin test in catalog with ID: {existing_test.id}")
        test = existing_test
        # Clear existing reference ranges for this test in lab_catalog
        db.query(ReferenceRange).filter(
            ReferenceRange.test_id == test.id
        ).delete()
        db.commit()
        print("[INFO] Cleared existing reference ranges in lab catalog")
    else:
        # Create new test in catalog
        test = LabTest(
            test_name=test_name,
            test_code=test_code,
            test_category=test_category,
            specimen_type=specimen_type,
            description=description,
            is_active=True
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        print(f"\n[SUCCESS] Created new Haemoglobin test in catalog with ID: {test.id}")
    
    # ================================================================
    # CREATE LAB TEMPLATE (for result entry)
    # ================================================================
    print("\n[INFO] Creating Lab Template...")
    
    template_name = "Haemoglobin (HB)"
    
    # Check if template exists
    existing_template = db.query(LabTemplate).filter(
        LabTemplate.name == template_name,
        LabTemplate.is_deleted == False
    ).first()
    
    if existing_template:
        print(f"[INFO] Found existing template: {existing_template.id}")
        template = existing_template
        # Get current version
        current_version = template.current_version or 0
        new_version = current_version + 1
    else:
        # Create new template
        template = LabTemplate(
            name=template_name,
            discipline="HEMATOLOGY",
            status="DRAFT",
            current_version=1,
            created_by_id=1  # Admin user
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        new_version = 1
        print(f"[SUCCESS] Created new template: {template.id}")
    
    # Create template schema
    schema = {
        "meta": {
            "name": "Haemoglobin (HB)",
            "discipline": "HEMATOLOGY",
            "version": new_version,
            "description": "Haemoglobin measurement - single parameter test",
            "specimen": "EDTA Blood",
            "method": "Automated Haematology Analyzer",
            "reporting_units": "SI units",
            "nhis_compliant": True,
            "nhis_code": "HB001",
            "ui_config": {
                "style": "clinical",
                "section_colors": {
                    "sec_main": "primary"
                },
                "result_entry": {
                    "show_flag_indicators": True,
                    "show_reference_range": True,
                    "auto_calculate_flags": True,
                    "highlight_abnormal": True
                }
            }
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_main",
                    "title": "Haemoglobin",
                    "ui_color": "primary",
                    "rows": [
                        {"columns": [{"items": ["HB"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            "HB": {
                "code": "HB",
                "type": "numeric",
                "label": "Haemoglobin",
                "short_code": "HB",
                "unit": "g/dL",
                "decimals": 1,
                "required": True,
                "critical": {"low": 7.0, "high": 20.0},
                "default_range": {"low": 12.0, "high": 17.5}
            }
        },
        "rules": {"visibility": [], "requiredIf": []},
        "calculated": []
    }
    
    # Create template version
    template_version = LabTemplateVersion(
        template_id=template.id,
        version=new_version,
        status="PUBLISHED",
        schema_json=schema,
        change_note=f"Haemoglobin (HB) template - version {new_version}",
        created_by_id=1
    )
    db.add(template_version)
    
    # Update template current version
    template.current_version = new_version
    template.status = "PUBLISHED"
    
    db.commit()
    db.refresh(template)
    print(f"[SUCCESS] Created template version {new_version}")
    
    # Link test to template
    test.template_id = template.id
    test.template_version = new_version
    db.commit()
    print(f"[SUCCESS] Linked test to template")
    
    # ================================================================
    # CREATE TEMPLATE REFERENCE RANGES (LabReferenceRange)
    # Uses age in DAYS (not years)
    # ================================================================
    print("\n[INFO] Creating Template Reference Ranges...")
    
    # Clear existing reference ranges for HB field
    db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code == "HB"
    ).delete()
    db.commit()
    
    # Convert age ranges to DAYS:
    # Neonates: 0-28 days
    # Infants: 29 days to 365 days (1 year = 365 days)
    # Children: 1-12 years (365 to 365*12 = 4380 days)
    # Adolescents: 13-17 years (4745 to 6570 days)
    # Adults: 18+ years (6570+ days)
    
    template_ranges = [
        # Neonates (0-28 days) - both male and female
        {
            "field_code": "HB",
            "sex": "ANY",
            "age_min_days": 0,
            "age_max_days": 28,
            "low": Decimal("16.5"),
            "high": Decimal("21.5"),
            "critical_low": Decimal("10.0"),
            "critical_high": Decimal("25.0"),
            "unit": "g/dL"
        },
        # Infants (29 days to 365 days / 1 year) - both male and female
        {
            "field_code": "HB",
            "sex": "ANY",
            "age_min_days": 29,
            "age_max_days": 365,
            "low": Decimal("10.5"),
            "high": Decimal("13.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("18.0"),
            "unit": "g/dL"
        },
        # Children (1-12 years) - both male and female
        # 1 year = 365 days, 12 years = 4380 days
        {
            "field_code": "HB",
            "sex": "ANY",
            "age_min_days": 366,
            "age_max_days": 4744,  # up to end of 12 years
            "low": Decimal("11.0"),
            "high": Decimal("13.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("18.0"),
            "unit": "g/dL"
        },
        # Adolescents (13-17 years) - Male
        # 13 years = 4745 days, 17 years = 6570 days
        {
            "field_code": "HB",
            "sex": "M",
            "age_min_days": 4745,
            "age_max_days": 6570,
            "low": Decimal("12.0"),
            "high": Decimal("16.0"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL"
        },
        # Adolescents (13-17 years) - Female
        {
            "field_code": "HB",
            "sex": "F",
            "age_min_days": 4745,
            "age_max_days": 6570,
            "low": Decimal("11.5"),
            "high": Decimal("15.0"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL"
        },
        # Adults (18+ years) - Male
        {
            "field_code": "HB",
            "sex": "M",
            "age_min_days": 6571,
            "age_max_days": None,  # No upper limit
            "low": Decimal("13.5"),
            "high": Decimal("17.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL"
        },
        # Adults (18+ years) - Female
        {
            "field_code": "HB",
            "sex": "F",
            "age_min_days": 6571,
            "age_max_days": None,  # No upper limit
            "low": Decimal("12.0"),
            "high": Decimal("15.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL"
        },
    ]
    
    for range_data in template_ranges:
        # Handle None age_max_days
        if range_data["age_max_days"] is None:
            range_data["age_max_days"] = 100000  # Very high number for "no upper limit"
        
        rr = LabReferenceRange(**range_data)
        db.add(rr)
        
        sex_label = "Male" if range_data["sex"] == "M" else ("Female" if range_data["sex"] == "F" else "All")
        
        # Calculate age label for display
        if range_data["age_max_days"] == 28:
            age_label = "0-28 days (Neonate)"
        elif range_data["age_max_days"] == 365:
            age_label = "29-365 days (Infant)"
        elif range_data["age_max_days"] <= 4744:
            age_label = f"{range_data['age_min_days']}-{range_data['age_max_days']} days (Child)"
        elif range_data["age_max_days"] == 6570:
            age_label = f"{range_data['age_min_days']}-{range_data['age_max_days']} days (Adolescent)"
        else:
            age_label = f"{range_data['age_min_days']}+ days (Adult)"
        
        print(f"  - Created: {age_label} | {sex_label} | {range_data['low']} - {range_data['high']} {range_data['unit']}")
    
    db.commit()
    
    # ================================================================
    # CREATE CATALOG REFERENCE RANGES (for reference_ranges table)
    # Uses age in YEARS
    # ================================================================
    print("\n[INFO] Creating Catalog Reference Ranges...")
    
    catalog_ranges = [
        # Neonates (0-28 days) - both male and female (age 0)
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 0,
            "age_max": 0,
            "gender": "ANY",
            "normal_min": Decimal("16.5"),
            "normal_max": Decimal("21.5"),
            "critical_low": Decimal("10.0"),
            "critical_high": Decimal("25.0"),
            "unit": "g/dL",
            "notes": "Neonates (0-28 days)"
        },
        # Infants (1-12 months) - both male and female (age 0-1)
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 0,
            "age_max": 1,
            "gender": "ANY",
            "normal_min": Decimal("10.5"),
            "normal_max": Decimal("13.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("18.0"),
            "unit": "g/dL",
            "notes": "Infants (1-12 months)"
        },
        # Children (1-12 years) - both male and female
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 1,
            "age_max": 12,
            "gender": "ANY",
            "normal_min": Decimal("11.0"),
            "normal_max": Decimal("13.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("18.0"),
            "unit": "g/dL",
            "notes": "Children (1-12 years)"
        },
        # Adolescents (13-17 years) - Male
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 13,
            "age_max": 17,
            "gender": "M",
            "normal_min": Decimal("12.0"),
            "normal_max": Decimal("16.0"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL",
            "notes": "Adolescent Male (13-17 years)"
        },
        # Adolescents (13-17 years) - Female
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 13,
            "age_max": 17,
            "gender": "F",
            "normal_min": Decimal("11.5"),
            "normal_max": Decimal("15.0"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL",
            "notes": "Adolescent Female (13-17 years)"
        },
        # Adults (18+ years) - Male
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 18,
            "age_max": 150,
            "gender": "M",
            "normal_min": Decimal("13.5"),
            "normal_max": Decimal("17.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL",
            "notes": "Adult Male (18+ years)"
        },
        # Adults (18+ years) - Female
        {
            "test_id": test.id,
            "test_name": test_name,
            "test_code": test_code,
            "age_min": 18,
            "age_max": 150,
            "gender": "F",
            "normal_min": Decimal("12.0"),
            "normal_max": Decimal("15.5"),
            "critical_low": Decimal("7.0"),
            "critical_high": Decimal("20.0"),
            "unit": "g/dL",
            "notes": "Adult Female (18+ years)"
        },
    ]
    
    for range_data in catalog_ranges:
        ref_range = ReferenceRange(**range_data)
        db.add(ref_range)
        print(f"  - Created: {range_data['notes']} | {range_data['gender']} | {range_data['normal_min']} - {range_data['normal_max']} {range_data['unit']}")
    
    db.commit()
    
    # Print summary
    print("\n" + "=" * 60)
    print("HAEMOGLOBIN (HB) TEST SUMMARY")
    print("=" * 60)
    print(f"Test ID:           {test.id}")
    print(f"Test Name:         {test_name}")
    print(f"Test Code:         {test_code}")
    print(f"Category:          {test_category}")
    print(f"Specimen:          {specimen_type}")
    print(f"Template ID:       {template.id}")
    print(f"Template Version: {new_version}")
    print(f"Unit:              g/dL")
    print(f"\nReference Ranges:")
    print("-" * 60)
    print(f"Neonates (0-28 days):     16.5 - 21.5 g/dL (M/F)")
    print(f"Infants (1-12 months):    10.5 - 13.5 g/dL (M/F)")
    print(f"Children (1-12 years):    11.0 - 13.5 g/dL (M/F)")
    print(f"Adolescents (13-17 yr):   M: 12.0 - 16.0, F: 11.5 - 15.0 g/dL")
    print(f"Adults (18+ years):       M: 13.5 - 17.5, F: 12.0 - 15.5 g/dL")
    print("=" * 60)
    
    return test, template


def main():
    """Main function to run the seeder."""
    print("\n" + "=" * 60)
    print("HAEMOGLOBIN (HB) TEST TEMPLATE SEEDER")
    print("=" * 60)
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Create the test
        test, template = create_haemoglobin_test(db)
        print("\n[SUCCESS] Haemoglobin (HB) test template created successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create Haemoglobin test: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
