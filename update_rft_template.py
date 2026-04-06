#!/usr/bin/env python3
"""
Update Renal Function Test (RFT) Template

This script:
1. Removes eGFR, eGFR Interpretation (egfr_stage) parameters from the RFT template
2. Updates reference ranges to properly consider gender and age for all relevant parameters

Usage:
    python update_rft_template.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['DEBUG'] = 'false'

from app.main import app
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from decimal import Decimal
import json

from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabReferenceRange
)
from app.models.user_models import User, Role

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_rft_template_schema():
    """
    Returns the updated RFT template schema WITHOUT eGFR, eGFR Interpretation, and eGFR Stage.
    The reference ranges now properly consider gender and age for creatinine.
    """
    return {
        "meta": {
            "name": "Renal Function Test (RFT / BUE & CR)",
            "discipline": "CHEMISTRY",
            "version": 3,
            "description": "Renal function test panel with Blood Urea, Electrolytes and Creatinine - NHIS bundled service (eGFR removed)",
            "display_order": ["sodium", "potassium", "chloride", "urea", "creatinine"]
        },
        "layout": {
            "sections": [
                {"id": "sec_electrolytes", "title": "Electrolytes", "rows": [{"columns": [{"width": 4, "items": ["sodium"]}, {"width": 4, "items": ["potassium"]}, {"width": 4, "items": ["chloride"]}]}]},
                {"id": "sec_renal", "title": "Kidney Function", "rows": [{"columns": [{"width": 6, "items": ["urea"]}, {"width": 6, "items": ["creatinine"]}]}]},
                {"id": "sec_comment", "title": "Comments / Clinical Notes", "rows": [{"columns": [{"width": 12, "items": ["comment"]}]}]}
            ]
        },
        "fields": {
            "sodium": {
                "code": "sodium",
                "label": "Sodium (Na⁺)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 0,
                "critical": True,
                "critical_low": 120.0,
                "critical_high": 160.0,
                "minimum": 100,
                "maximum": 180,
                "validation_message": "Sodium should be between 100-180 mmol/L"
            },
            "potassium": {
                "code": "potassium",
                "label": "Potassium (K⁺)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": True,
                "critical_low": 2.5,
                "critical_high": 6.5,
                "minimum": 2.0,
                "maximum": 8.0,
                "validation_message": "Potassium should be between 2.0-8.0 mmol/L"
            },
            "chloride": {
                "code": "chloride",
                "label": "Chloride (Cl⁻)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 0,
                "critical": False,
                "minimum": 70,
                "maximum": 130,
                "validation_message": "Chloride should be between 70-130 mmol/L"
            },
            "creatinine": {
                "code": "creatinine",
                "label": "Creatinine",
                "type": "numeric",
                "unit": "µmol/L",
                "decimals": 0,
                "critical": True,
                "critical_low": 44.0,
                "critical_high": 707.0,
                "minimum": 10,
                "maximum": 1500,
                "validation_message": "Creatinine should be between 10-1500 µmol/L",
                "uses_gender_age_reference": True  # Flag to indicate reference ranges depend on gender/age
            },
            "urea": {
                "code": "urea",
                "label": "Urea",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 1,
                "critical": False,
                "critical_high": 35.7,
                "minimum": 0.5,
                "maximum": 50.0,
                "validation_message": "Urea should be between 0.5-50.0 mmol/L"
            },
            "comment": {
                "code": "comment",
                "label": "Clinical Comments / Notes",
                "type": "textarea",
                "required": False
            }
        },
        "rules": {
            "required": ["sodium", "potassium", "chloride", "urea", "creatinine"],
            "requiredIf": [],
            "validation": [],
            "alerts": [
                {
                    "id": "hyperkalemia",
                    "condition": "potassium > 5.5",
                    "message": "⚠️ HYPERKALEMIA: Critical potassium level - urgent clinical attention required",
                    "severity": "critical",
                    "display_on": ["report", "entry"]
                },
                {
                    "id": "hypokalemia",
                    "condition": "potassium < 3.0",
                    "message": "⚠️ HYPOKALEMIA: Critical potassium level - urgent clinical attention required",
                    "severity": "critical",
                    "display_on": ["report", "entry"]
                },
                {
                    "id": "hyponatremia",
                    "condition": "sodium < 125",
                    "message": "⚠️ HYPONATREMIA: Critical sodium level - urgent clinical attention required",
                    "severity": "critical",
                    "display_on": ["report", "entry"]
                },
                {
                    "id": "hypernatremia",
                    "condition": "sodium > 155",
                    "message": "⚠️ HYPERNATREMIA: Critical sodium level - urgent clinical attention required",
                    "severity": "critical",
                    "display_on": ["report", "entry"]
                },
                {
                    "id": "renal_impairment",
                    "condition": "creatinine > reference_high",
                    "message": "⚠️ ELEVATED CREATININE: May indicate renal impairment - please correlate clinically",
                    "severity": "high",
                    "display_on": ["report", "entry"]
                }
            ]
        },
        "calculated": [],
        "display": {
            "show_units": True,
            "show_reference_ranges": True,
            "show_interpretation": True,
            "show_critical_flags": True,
            "result_order": ["sodium", "potassium", "chloride", "urea", "creatinine"],
            "report_header": "RENAL FUNCTION TEST (RFT / BUE & CR)",
            "nhis_claim_bundle": True
        }
    }


def get_reference_ranges():
    """
    Returns reference ranges that consider gender and age for all parameters.
    - Sodium, Potassium, Chloride: Same for all ages and genders
    - Creatinine: Gender and age specific (Adult Male, Adult Female, Children)
    - Urea: Age specific (Adults vs Children)
    """
    return [
        # Sodium (Na⁺) - All ages, both sexes
        {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("135"), "high": Decimal("145"), "critical_low": Decimal("120"), "critical_high": Decimal("160"), "unit": "mmol/L"},
        
        # Potassium (K⁺) - All ages, both sexes
        {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("3.5"), "high": Decimal("5.1"), "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mmol/L"},
        
        # Chloride (Cl⁻) - All ages, both sexes
        {"field_code": "chloride", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, 
         "low": Decimal("98"), "high": Decimal("107"), "critical_low": Decimal("80"), "critical_high": Decimal("115"), "unit": "mmol/L"},
        
        # Creatinine - Adult Male (≥18 years = 6570 days)
        {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("64"), "high": Decimal("104"), "critical_low": Decimal("44"), "critical_high": Decimal("707"), "unit": "µmol/L"},
        
        # Creatinine - Adult Female (≥18 years = 6570 days)
        {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("49"), "high": Decimal("90"), "critical_low": Decimal("44"), "critical_high": Decimal("707"), "unit": "µmol/L"},
        
        # Creatinine - Children and Adolescents (<18 years = 6570 days)
        {"field_code": "creatinine", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, 
         "low": Decimal("27"), "high": Decimal("62"), "critical_low": Decimal("18"), "critical_high": Decimal("200"), "unit": "µmol/L"},
        
        # Urea - Adults (≥18 years = 6570 days)
        {"field_code": "urea", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, 
         "low": Decimal("2.5"), "high": Decimal("7.8"), "critical_low": Decimal("1.0"), "critical_high": Decimal("35.7"), "unit": "mmol/L"},
        
        # Urea - Children (<18 years = 6570 days)
        {"field_code": "urea", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, 
         "low": Decimal("1.8"), "high": Decimal("6.4"), "critical_low": Decimal("1.0"), "critical_high": Decimal("20.0"), "unit": "mmol/L"},
    ]


def update_rft_template(db: Session, admin_user_id: int):
    """Update the RFT template to remove eGFR and update reference ranges."""
    print("=" * 60)
    print("Updating Renal Function Test (RFT) Template")
    print("=" * 60)
    
    # Find the RFT template - check multiple possible names
    template_names = [
        "Lab Test - RFT",
        "Renal Function Test (RFT / BUE & CR)",
        "Renal Function Tests (RFT)",
        "RFT"
    ]
    template = None
    for name in template_names:
        template = db.query(LabTemplate).filter(LabTemplate.name == name).first()
        if template:
            print(f"Found template with name: {name}")
            break
    
    if not template:
        # Try partial match
        template = db.query(LabTemplate).filter(LabTemplate.name.like("%RFT%")).first()
        if template:
            print(f"Found template with partial match: {template.name}")
    
    print(f"Found template: {template.name} (ID: {template.id})")
    
    # Create new version - get max version from database
    max_version = db.query(LabTemplateVersion).filter(
        LabTemplateVersion.template_id == template.id
    ).order_by(LabTemplateVersion.version.desc()).first()
    new_version = (max_version.version if max_version else 0) + 1
    print(f"Creating version {new_version}...")
    
    # Get the schema
    schema = get_rft_template_schema()
    
    # Create new version
    version = LabTemplateVersion(
        id=uuid4(),
        template_id=template.id,
        version=new_version,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Removed eGFR, eGFR Interpretation, eGFR Stage parameters. Updated reference ranges to consider gender and age automatically.",
        created_by_id=admin_user_id
    )
    db.add(version)
    
    # Update template
    template.current_version = new_version
    template.status = "PUBLISHED"
    
    print(f"Created new template version {new_version}")
    
    # Update reference ranges - first delete existing eGFR ranges for RFT
    print("\nUpdating reference ranges...")
    
    # Delete existing reference ranges for eGFR and egfr_stage
    db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code.in_(["egfr", "egfr_stage", "gfr_value"])
    ).delete()
    print("Removed old eGFR reference ranges")
    
    # Delete existing RFT reference ranges
    db.query(LabReferenceRange).filter(
        LabReferenceRange.field_code.in_(["sodium", "potassium", "chloride", "creatinine", "urea"])
    ).delete()
    print("Removed old RFT reference ranges")
    
    # Add new reference ranges with gender/age consideration
    reference_ranges = get_reference_ranges()
    for rr in reference_ranges:
        new_rr = LabReferenceRange(
            id=uuid4(),
            field_code=rr["field_code"],
            sex=rr["sex"],
            age_min_days=rr.get("age_min_days"),
            age_max_days=rr.get("age_max_days"),
            low=rr["low"],
            high=rr["high"],
            critical_low=rr.get("critical_low"),
            critical_high=rr.get("critical_high"),
            unit=rr["unit"]
        )
        db.add(new_rr)
        print(f"  Added: {rr['field_code']} - sex={rr['sex']}, age={rr.get('age_min_days', 'ANY')}-{rr.get('age_max_days', 'ANY')}, range={rr['low']}-{rr['high']} {rr['unit']}")
    
    # Commit changes
    db.commit()
    
    print("\n" + "=" * 60)
    print("RFT Template Updated Successfully!")
    print("=" * 60)
    print("\nChanges made:")
    print("1. Removed eGFR parameter from template")
    print("2. Removed eGFR Interpretation (egfr_stage) parameter from template")
    print("3. Removed eGFR Stage from template layout")
    print("4. Updated reference ranges to automatically consider:")
    print("   - Gender: Male vs Female for Creatinine")
    print("   - Age: Adults (≥18 years) vs Children (<18 years)")
    print("   - All other parameters use 'ANY' for universal ranges")
    
    return True


def main():
    """Main function to run the update."""
    print("Connecting to database...")
    
    db = SessionLocal()
    try:
        # Get admin user - use join to get role
        admin_user = db.query(User).join(Role).filter(Role.name == "ADMIN").first()
        if not admin_user:
            # Try to get first user
            admin_user = db.query(User).first()
        
        if not admin_user:
            print("ERROR: No admin user found!")
            return
        
        print(f"Using admin user: {admin_user.username}")
        
        # Update the template
        success = update_rft_template(db, admin_user.id)
        
        if success:
            print("\nUpdate completed successfully!")
        else:
            print("\nUpdate failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
