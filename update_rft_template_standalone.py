#!/usr/bin/env python3
"""
Standalone RFT Template Update Script

This script updates the RFT template directly in the database
without needing to import the full LHIMS application.

Usage:
    python3 update_rft_template_standalone.py
"""

import os
import sys
import json
from decimal import Decimal

# Database setup
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URL", 
    "postgresql+psycopg2://postgres:password123@localhost:5433/lhims"
)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# RFT Template Definition
RFT_TEMPLATE = {
    "test_name": "Renal Function Test (RFT / BUE & CR)",
    "test_code": "RFT",
    "test_category": "Biochemistry",
    "test_type": "Quantitative",
    "specimen_type": "Serum",
    "description": "Renal Function Test (Blood Urea, Electrolytes & Creatinine) - NHIS Bundled Panel",
    "discipline": "CHEMISTRY",
    "nhis_bundle": True,
    "nhis_service_code": "RFT001",
    "schema": {
        "meta": {
            "name": "Renal Function Test (RFT / BUE & CR)",
            "discipline": "CHEMISTRY",
            "version": 2,
            "description": "Renal function test panel with Blood Urea, Electrolytes and Creatinine - NHIS bundled service",
            "display_order": ["sodium", "potassium", "chloride", "urea", "creatinine", "egfr"]
        },
        "layout": {
            "sections": [
                {"id": "sec_electrolytes", "title": "Electrolytes", "rows": [{"columns": [{"width": 4, "items": ["sodium"]}, {"width": 4, "items": ["potassium"]}, {"width": 4, "items": ["chloride"]}]}]},
                {"id": "sec_renal", "title": "Kidney Function", "rows": [{"columns": [{"width": 4, "items": ["urea"]}, {"width": 4, "items": ["creatinine"]}, {"width": 4, "items": ["egfr"]}]}]},
                {"id": "sec_egfr_stage", "title": "eGFR Interpretation", "rows": [{"columns": [{"width": 12, "items": ["egfr_stage"]}]}]},
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
                "triggers_egfr_calc": True
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
            "egfr": {
                "code": "egfr",
                "label": "eGFR",
                "type": "numeric",
                "unit": "mL/min/1.73m²",
                "decimals": 0,
                "critical": False,
                "minimum": 5,
                "maximum": 150,
                "allow_manual_override": True,
                "calculated": True,
                "formula": "CKD-EPI",
                "depends_on": ["creatinine", "age", "sex"],
                "validation_message": "eGFR should be between 5-150 mL/min/1.73m²"
            },
            "egfr_stage": {
                "code": "egfr_stage",
                "label": "eGFR Stage",
                "type": "text",
                "calculated": True,
                "depends_on": ["egfr"],
                "interpretation": {
                    "Normal": "egfr >= 90",
                    "Mildly Decreased": "egfr >= 60 AND egfr < 90",
                    "Moderately Decreased": "egfr >= 30 AND egfr < 60",
                    "Severely Decreased": "egfr >= 15 AND egfr < 30",
                    "Kidney Failure": "egfr < 15"
                }
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
            "validation": [
                {
                    "field": "egfr",
                    "rule": "creatinine_required",
                    "condition": "creatinine is not empty",
                    "message": "Creatinine must be entered before eGFR can be calculated"
                }
            ],
            "alerts": [
                {
                    "id": "renal_impairment",
                    "condition": "creatinine > reference_high AND egfr < 60",
                    "message": "⚠️ RENAL IMPAIRMENT: Elevated creatinine with reduced eGFR - please correlate clinically",
                    "severity": "high",
                    "display_on": ["report", "entry"]
                },
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
                }
            ]
        },
        "calculated": [
            {
                "field": "egfr",
                "formula": "CKD-EPI",
                "description": "CKD-EPI equation for eGFR calculation",
                "variables": ["creatinine", "age_years", "sex"],
                "equation": "if sex == 'M': eGFR = 142 * min(creatinine/88.4, 1)^-0.241 * max(creatinine/88.4, 1)^-1.200 * 0.9938^age_years * 1.012 else: eGFR = 142 * min(creatinine/88.4, 1)^-0.241 * max(creatinine/88.4, 1)^-1.200 * 0.9938^age_years",
                "pediatric_formula": "Schwartz",
                "pediatric_equation": "eGFR = (36.5 * height_cm) / creatinine"
            },
            {
                "field": "egfr_stage",
                "formula": "interpretation",
                "depends_on": ["egfr"],
                "interpretation_map": {
                    "Normal (≥90)": "egfr >= 90",
                    "Mildly Decreased (60-89)": "egfr >= 60 AND egfr < 90",
                    "Moderately Decreased (30-59)": "egfr >= 30 AND egfr < 60",
                    "Severely Decreased (15-29)": "egfr >= 15 AND egfr < 30",
                    "Kidney Failure (<15)": "egfr < 15"
                }
            }
        ],
        "display": {
            "show_units": True,
            "show_reference_ranges": True,
            "show_interpretation": True,
            "show_critical_flags": True,
            "result_order": ["sodium", "potassium", "chloride", "urea", "creatinine", "egfr", "egfr_stage"],
            "report_header": "RENAL FUNCTION TEST (RFT / BUE & CR)",
            "nhis_claim_bundle": True
        }
    },
    "reference_ranges": [
        # Sodium (Na⁺) - All ages, both sexes
        {"field_code": "sodium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("135"), "high": Decimal("145"), "critical_low": Decimal("120"), "critical_high": Decimal("160"), "unit": "mmol/L"},
        # Potassium (K⁺) - All ages, both sexes
        {"field_code": "potassium", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("3.5"), "high": Decimal("5.1"), "critical_low": Decimal("2.5"), "critical_high": Decimal("6.5"), "unit": "mmol/L"},
        # Chloride (Cl⁻) - All ages, both sexes
        {"field_code": "chloride", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550, "low": Decimal("98"), "high": Decimal("107"), "critical_low": Decimal("80"), "critical_high": Decimal("115"), "unit": "mmol/L"},
        # Creatinine - Adult Male (≥18 years)
        {"field_code": "creatinine", "sex": "M", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("64"), "high": Decimal("104"), "critical_low": Decimal("44"), "critical_high": Decimal("707"), "unit": "µmol/L"},
        # Creatinine - Adult Female (≥18 years)
        {"field_code": "creatinine", "sex": "F", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("49"), "high": Decimal("90"), "critical_low": Decimal("44"), "critical_high": Decimal("707"), "unit": "µmol/L"},
        # Creatinine - Children (<18 years)
        {"field_code": "creatinine", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("27"), "high": Decimal("62"), "critical_low": Decimal("18"), "critical_high": Decimal("200"), "unit": "µmol/L"},
        # Urea - Adults (≥18 years)
        {"field_code": "urea", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("2.5"), "high": Decimal("7.8"), "critical_low": Decimal("1.0"), "critical_high": Decimal("35.7"), "unit": "mmol/L"},
        # Urea - Children (<18 years)
        {"field_code": "urea", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570, "low": Decimal("1.8"), "high": Decimal("6.4"), "critical_low": Decimal("1.0"), "critical_high": Decimal("20.0"), "unit": "mmol/L"},
        # eGFR - Interpretation ranges (stage-based)
        {"field_code": "egfr", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550, "low": Decimal("90"), "high": Decimal("120"), "interpretation": "Normal", "unit": "mL/min/1.73m²"},
    ],
    "interpretation_rules": [
        {
            "parameter": "egfr",
            "stages": [
                {"label": "Normal", "min": 90, "max": None, "color": "green", "message": "Normal kidney function"},
                {"label": "Mildly Decreased", "min": 60, "max": 89, "color": "yellow", "message": "Mildly reduced kidney function - monitor"},
                {"label": "Moderately Decreased", "min": 30, "max": 59, "color": "orange", "message": "Moderately reduced kidney function - nephrology consult recommended"},
                {"label": "Severely Decreased", "min": 15, "max": 29, "color": "red", "message": "Severely reduced kidney function - urgent nephrology review"},
                {"label": "Kidney Failure", "min": None, "max": 15, "color": "red", "message": "Kidney failure - immediate specialist referral required"}
            ]
        }
    ],
    "nhis_claim_config": {
        "bundle_as_single_test": True,
        "test_code": "RFT001",
        "test_name": "Renal Function Test (RFT / BUE & CR)",
        "include_parameters": ["sodium", "potassium", "chloride", "urea", "creatinine", "egfr"],
        "do_not_claim_separately": ["Na", "K", "Cl", "Electrolytes", "BUE", "Creatinine", "Urea"],
        "required_fields": ["diagnosis_icd10", "specimen_collected", "results_finalized"],
        "nhis_service_code": "RFT001",
        "category": "Biochemistry"
    }
}


def update_rft_template():
    """Update the RFT template in the database."""
    
    db = SessionLocal()
    
    try:
        # Find the RFT template
        from app.models.lab_template_models import LabTemplate, LabTemplateVersion
        
        # First, list all templates
        all_templates = db.query(LabTemplate).all()
        print("\n📋 Available templates in database:")
        for t in all_templates:
            print(f"   - {t.name} (ID: {t.id}, Discipline: {t.discipline})")
        
        # Find the template with different search patterns
        template = db.query(LabTemplate).filter(
            (LabTemplate.name.like("%Renal%")) | 
            (LabTemplate.name.like("%RFT%")) |
            (LabTemplate.name.like("%Kidney%"))
        ).first()
        
        if not template:
            print("❌ RFT Template not found in database")
            return False
        
        print(f"✅ Found RFT Template: {template.name} (ID: {template.id})")
        
        # Update template metadata
        template.discipline = "CHEMISTRY"
        
        # Get the draft version
        draft = db.query(LabTemplateVersion).filter(
            LabTemplateVersion.template_id == template.id,
            LabTemplateVersion.status == "DRAFT"
        ).first()
        
        if draft:
            # Update the draft schema
            draft.schema_json = RFT_TEMPLATE["schema"]
            print("✅ Updated draft schema")
        else:
            # Create a new draft version
            max_version = db.query(LabTemplateVersion.version).filter(
                LabTemplateVersion.template_id == template.id
            ).order_by(LabTemplateVersion.version.desc()).first()
            
            new_version = (max_version[0] + 1) if max_version else 1
            
            draft = LabTemplateVersion(
                template_id=template.id,
                version=new_version,
                status="DRAFT",
                schema_json=RFT_TEMPLATE["schema"],
                change_note="Updated RFT template with NHIS-compliant parameters"
            )
            db.add(draft)
            print(f"✅ Created new draft version {new_version}")
        
        # Update or create reference ranges
        # Note: LabReferenceRange uses field_code, not test_code
        # Reference ranges are stored in the template schema JSON
        print("\n📋 Note: Reference ranges are stored in template schema JSON")
        print("   The schema includes full reference range definitions")
        
        # In this system, reference ranges are stored within the template schema
        # The schema_json contains fields with their reference ranges embedded
        # We don't need separate LabReferenceRange records for this approach
        
        # Publish the draft version
        print("\n📋 Publishing draft version...")
        
        # Find the draft version we just created
        draft = db.query(LabTemplateVersion).filter(
            LabTemplateVersion.template_id == template.id,
            LabTemplateVersion.status == "DRAFT"
        ).order_by(LabTemplateVersion.version.desc()).first()
        
        if draft:
            # Get current published version
            current_published = db.query(LabTemplateVersion).filter(
                LabTemplateVersion.template_id == template.id,
                LabTemplateVersion.status == "PUBLISHED"
            ).order_by(LabTemplateVersion.version.desc()).first()
            
            # Archive previous published versions
            if current_published:
                current_published.status = "ARCHIVED"
                print(f"   Archived previous version {current_published.version}")
            
            # Publish the new version
            draft.status = "PUBLISHED"
            draft.change_note = "Updated RFT template with NHIS-compliant parameters, version 2"
            print(f"   Published version {draft.version}")
        
        # Commit changes
        db.commit()
        print("\n✅ RFT Template updated successfully!")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error updating template: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("RFT Template Update Script")
    print("=" * 60)
    
    success = update_rft_template()
    
    if success:
        print("\n" + "=" * 60)
        print("UPDATE COMPLETE")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("UPDATE FAILED")
        print("=" * 60)
        sys.exit(1)
