#!/usr/bin/env python3
"""
NHIS-Compliant Lipid Profile Template for LHIMS
================================================
This script creates/updates the Lipid Profile test template with:
- All required parameters (Total Cholesterol, HDL, LDL, Triglycerides, VLDL, C-Risk)
- Age and gender-specific reference ranges
- Auto-calculation formulas (VLDL, C-Risk ratio)
- Validation rules and interpretation flags
- NHIS-compliant single claim configuration

Run with: python seed_lipid_profile_nhis_compliant.py
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database connection - update this to match your environment
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://postgres:password123@localhost:5433/lhims")

from app.models.lab_template_models import LabTemplate, LabTemplateVersion, LabReferenceRange
from app.models.lab_catalog_models import LabTest


def create_lipid_profile_template(db, admin_user_id: int = 1):
    """
    Create NHIS-compliant Lipid Profile template with all parameters.
    """
    print("\n" + "="*60)
    print("Creating NHIS-Compliant Lipid Profile Template")
    print("="*60)
    
    # Check if template already exists
    existing_template = db.query(LabTemplate).filter(
        LabTemplate.name == "Lipid Profile"
    ).first()
    
    if existing_template:
        print(f"Found existing Lipid Profile template: {existing_template.id}")
        template = existing_template
        # Get the current version number
        current_ver = template.current_version or 0
        new_version = current_ver + 1
    else:
        print("Creating new Lipid Profile template...")
        template = LabTemplate(
            name="Lipid Profile",
            discipline="CHEMISTRY",
            status="PUBLISHED",
            current_version=1,
            created_by_id=admin_user_id
        )
        db.add(template)
        db.flush()
        new_version = 1
    
    # Define the comprehensive schema
    schema = {
        "meta": {
            "name": "Lipid Profile",
            "discipline": "CHEMISTRY",
            "version": new_version,
            "description": "NHIS-Compliant Lipid Profile - Cardiovascular Risk Assessment",
            "nhis_code": "LIPID",
            "category": "Panel",
            "specimen_type": "Serum (Fasting 12hrs)",
            "tat_hours": 8,
            "requires_age": True,
            "requires_gender": True
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_cholesterol_panel",
                    "title": "Cholesterol Profile",
                    "order": 1,
                    "rows": [
                        {
                            "columns": [
                                {"width": 6, "items": ["total_cholesterol"], "order": 1},
                                {"width": 6, "items": ["hdl_cholesterol"], "order": 2}
                            ]
                        },
                        {
                            "columns": [
                                {"width": 6, "items": ["ldl_cholesterol"], "order": 3},
                                {"width": 6, "items": ["vldl_cholesterol"], "order": 4}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_triglycerides",
                    "title": "Triglycerides",
                    "order": 2,
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["triglycerides"], "order": 5}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_cardiac_risk",
                    "title": "Cardiac Risk Assessment",
                    "order": 3,
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["c_risk_ratio"], "order": 6}
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
                                {"width": 12, "items": ["interpretation"], "order": 7}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_comment",
                    "title": "Comments",
                    "order": 5,
                    "rows": [
                        {
                            "columns": [
                                {"width": 12, "items": ["comment"], "order": 8}
                            ]
                        }
                    ]
                }
            ]
        },
        "fields": {
            "total_cholesterol": {
                "code": "total_cholesterol",
                "label": "Total Cholesterol",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 20,
                "required": True,
                "critical": {
                    "enabled": True,
                    "low": 1.5,
                    "high": 7.75
                },
                "interpretation": {
                    "enabled": True,
                    "ranges": [
                        {"label": "Normal (Adult)", "min": 0, "max": 5.2, "flag": "N"},
                        {"label": "Normal (Child/Adolescent)", "min": 0, "max": 4.4, "flag": "N"},
                        {"label": "Borderline High", "min": 5.2, "max": 6.2, "flag": "B"},
                        {"label": "High", "min": 6.2, "max": 100, "flag": "H"}
                    ]
                },
                "display_order": 1
            },
            "hdl_cholesterol": {
                "code": "hdl_cholesterol",
                "label": "HDL Cholesterol (High-Density Lipoprotein)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 5,
                "required": True,
                "critical": {
                    "enabled": True,
                    "low": 0.5,
                    "high": None
                },
                "gender_specific": True,
                "interpretation": {
                    "enabled": True,
                    "ranges": [
                        {"label": "Adult Male - Normal", "min": 1.0, "max": 5.0, "flag": "N", "gender": "M", "age_min": 18},
                        {"label": "Adult Female - Normal", "min": 1.3, "max": 5.0, "flag": "N", "gender": "F", "age_min": 18},
                        {"label": "Children - Normal", "min": 1.1, "max": 5.0, "flag": "N", "gender": "ANY", "age_max": 17},
                        {"label": "Low (Increased CV Risk)", "min": 0, "max": 0.9, "flag": "L", "gender": "M"},
                        {"label": "Low (Increased CV Risk)", "min": 0, "max": 1.2, "flag": "L", "gender": "F"}
                    ]
                },
                "display_order": 2
            },
            "ldl_cholesterol": {
                "code": "ldl_cholesterol",
                "label": "LDL Cholesterol (Low-Density Lipoprotein)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 10,
                "required": True,
                "critical": {
                    "enabled": True,
                    "low": None,
                    "high": 4.9
                },
                "interpretation": {
                    "enabled": True,
                    "ranges": [
                        {"label": "Optimal", "min": 0, "max": 2.6, "flag": "N"},
                        {"label": "Near Optimal", "min": 2.6, "max": 3.3, "flag": "B"},
                        {"label": "Borderline High", "min": 3.4, "max": 4.1, "flag": "H"},
                        {"label": "High", "min": 4.1, "max": 4.9, "flag": "H"},
                        {"label": "Very High", "min": 4.9, "max": 100, "flag": "HH"}
                    ]
                },
                "display_order": 3
            },
            "triglycerides": {
                "code": "triglycerides",
                "label": "Triglycerides",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 15,
                "required": True,
                "critical": {
                    "enabled": True,
                    "low": None,
                    "high": 5.65
                },
                "age_specific": True,
                "interpretation": {
                    "enabled": True,
                    "ranges": [
                        {"label": "Normal (Adult)", "min": 0, "max": 1.7, "flag": "N", "age_min": 18},
                        {"label": "Borderline High (Adult)", "min": 1.7, "max": 2.2, "flag": "B", "age_min": 18},
                        {"label": "High (Adult)", "min": 2.3, "max": 5.6, "flag": "H", "age_min": 18},
                        {"label": "Very High (Adult)", "min": 5.6, "max": 100, "flag": "HH", "age_min": 18},
                        {"label": "Normal (Child)", "min": 0, "max": 1.1, "flag": "N", "age_max": 17}
                    ]
                },
                "display_order": 4
            },
            "vldl_cholesterol": {
                "code": "vldl_cholesterol",
                "label": "VLDL Cholesterol (Very Low-Density Lipoprotein)",
                "type": "numeric",
                "unit": "mmol/L",
                "decimals": 2,
                "min_value": 0,
                "max_value": 5,
                "required": False,
                "calculated": True,
                "formula": "triglycerides / 2.2",
                "auto_calculate": True,
                "interpretation": {
                    "enabled": True,
                    "ranges": [
                        {"label": "Normal", "min": 0.2, "max": 1.0, "flag": "N"},
                        {"label": "High", "min": 1.0, "max": 100, "flag": "H"}
                    ]
                },
                "display_order": 5
            },
            "c_risk_ratio": {
                "code": "c_risk_ratio",
                "label": "Cardiac Risk Ratio (Total Cholesterol / HDL)",
                "type": "numeric",
                "unit": "ratio",
                "decimals": 1,
                "min_value": 0,
                "max_value": 50,
                "required": True,
                "calculated": True,
                "formula": "total_cholesterol / hdl_cholesterol",
                "auto_calculate": True,
                "gender_specific": True,
                "age_specific": True,
                "interpretation": {
                    "enabled": True,
                    "ranges": [
                        # Adult Male (18+ years)
                        {"label": "Low Risk (Adult Male)", "min": 0, "max": 4.5, "flag": "N", "gender": "M", "age_min": 18},
                        {"label": "Moderate Risk (Adult Male)", "min": 4.5, "max": 6.0, "flag": "B", "gender": "M", "age_min": 18},
                        {"label": "High Risk (Adult Male)", "min": 6.0, "max": 100, "flag": "H", "gender": "M", "age_min": 18},
                        # Adult Female (18+ years)
                        {"label": "Low Risk (Adult Female)", "min": 0, "max": 4.0, "flag": "N", "gender": "F", "age_min": 18},
                        {"label": "Moderate Risk (Adult Female)", "min": 4.0, "max": 6.0, "flag": "B", "gender": "F", "age_min": 18},
                        {"label": "High Risk (Adult Female)", "min": 6.0, "max": 100, "flag": "H", "gender": "F", "age_min": 18},
                        # Children/Adolescents (< 18 years)
                        {"label": "Normal (Child/Adolescent)", "min": 0, "max": 3.0, "flag": "N", "age_max": 17}
                    ]
                },
                "display_order": 6
            },
            "interpretation": {
                "code": "interpretation",
                "label": "Clinical Interpretation",
                "type": "text",
                "required": False,
                "display_order": 7
            },
            "comment": {
                "code": "comment",
                "label": "Comments/Notes",
                "type": "text",
                "required": False,
                "display_order": 8
            }
        },
        "validation_rules": {
            "required_fields": ["total_cholesterol", "hdl_cholesterol", "ldl_cholesterol", "triglycerides", "c_risk_ratio"],
            "auto_calculations": [
                {
                    "field": "vldl_cholesterol",
                    "formula": "triglycerides / 2.2",
                    "trigger_on": ["triglycerides"]
                },
                {
                    "field": "c_risk_ratio",
                    "formula": "total_cholesterol / hdl_cholesterol",
                    "trigger_on": ["total_cholesterol", "hdl_cholesterol"]
                }
            ],
            "risk_patterns": [
                {
                    "name": "High LDL + High Total Cholesterol",
                    "condition": "ldl_cholesterol > 4.1 AND total_cholesterol > 6.2",
                    "flag": "HIGH_RISK",
                    "message": "High cardiovascular risk: Elevated LDL and Total Cholesterol"
                },
                {
                    "name": "Low HDL + High Triglycerides",
                    "condition": "hdl_cholesterol < 1.0 AND triglycerides > 2.2",
                    "flag": "HIGH_RISK",
                    "message": "Metabolic syndrome pattern: Low HDL with high triglycerides"
                }
            ]
        },
        "nhis_config": {
            "claim_as_single_service": True,
            "service_code": "LIPID",
            "service_name": "Lipid Profile",
            "parameters_included": [
                "Total Cholesterol",
                "HDL Cholesterol",
                "LDL Cholesterol",
                "Triglycerides",
                "VLDL Cholesterol",
                "Cardiac Risk Ratio"
            ],
            "required_for_claim": [
                "diagnosis_code",
                "specimen_date",
                "finalized_result"
            ],
            "nhis_tariff_code": "Z0134"  # Example NHIS tariff code - configurable
        },
        "report_config": {
            "display_order": [
                "total_cholesterol",
                "hdl_cholesterol",
                "ldl_cholesterol",
                "triglycerides",
                "vldl_cholesterol",
                "c_risk_ratio"
            ],
            "show_reference_range": True,
            "show_interpretation": True,
            "show_unit": True,
            "export_formats": ["PDF", "CSV", "JSON", "API"]
        }
    }
    
    # Create new version
    version = LabTemplateVersion(
        template_id=template.id,
        version=new_version,
        status="PUBLISHED",
        schema_json=schema,
        change_note=f"NHIS-Compliant Lipid Profile Template v{new_version} - Updated with all parameters, reference ranges, auto-calculations, and risk patterns",
        created_by_id=admin_user_id
    )
    db.add(version)
    
    # Update template version
    template.current_version = new_version
    template.status = "PUBLISHED"
    
    db.flush()
    
    print(f"✓ Created Lipid Profile template: {template.id}")
    print(f"✓ Version: {new_version}")
    
    return template, version


def create_reference_ranges(db, template_id):
    """
    Create comprehensive reference ranges for all Lipid Profile parameters.
    Uses LabReferenceRange model for field-based ranges.
    """
    print("\n" + "="*60)
    print("Creating Reference Ranges for Lipid Profile")
    print("="*60)
    
    ranges = []
    
    # 1. TOTAL CHOLESTEROL - Age-specific ranges
    # Adults (≥18 years): < 5.2 mmol/L normal
    ranges.extend([
        # Adult normal range
        LabReferenceRange(
            field_code="total_cholesterol",
            sex="ANY",
            age_min_days=6570,  # 18 years
            age_max_days=36500,  # 100 years
            low=Decimal("0"),
            high=Decimal("5.2"),
            critical_high=Decimal("7.75"),
            text_range="< 5.2 mmol/L",
            unit="mmol/L"
        ),
        # Borderline High
        LabReferenceRange(
            field_code="total_cholesterol",
            sex="ANY",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("5.2"),
            high=Decimal("6.2"),
            text_range="5.2 - 6.2 mmol/L (Borderline High)",
            unit="mmol/L"
        ),
        # High
        LabReferenceRange(
            field_code="total_cholesterol",
            sex="ANY",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("6.2"),
            high=Decimal("15.0"),
            critical_high=Decimal("7.75"),
            text_range="> 6.2 mmol/L (High)",
            unit="mmol/L"
        ),
        # Children/Adolescents normal: < 4.4 mmol/L
        LabReferenceRange(
            field_code="total_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=6569,  # < 18 years
            low=Decimal("0"),
            high=Decimal("4.4"),
            text_range="< 4.4 mmol/L",
            unit="mmol/L"
        ),
    ])
    
    # 2. HDL CHOLESTEROL - Gender-specific ranges
    # Adult Male: ≥ 1.0 mmol/L
    ranges.append(
        LabReferenceRange(
            field_code="hdl_cholesterol",
            sex="M",
            age_min_days=6570,  # Adult
            age_max_days=36500,
            low=Decimal("1.0"),
            high=Decimal("2.5"),
            critical_low=Decimal("0.5"),
            text_range="≥ 1.0 mmol/L",
            unit="mmol/L"
        )
    )
    
    # Adult Female: ≥ 1.3 mmol/L
    ranges.append(
        LabReferenceRange(
            field_code="hdl_cholesterol",
            sex="F",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("1.3"),
            high=Decimal("2.5"),
            critical_low=Decimal("0.5"),
            text_range="≥ 1.3 mmol/L",
            unit="mmol/L"
        )
    )
    
    # Children: ≥ 1.1 mmol/L
    ranges.append(
        LabReferenceRange(
            field_code="hdl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=6569,  # < 18 years
            low=Decimal("1.1"),
            high=Decimal("2.0"),
            critical_low=Decimal("0.5"),
            text_range="≥ 1.1 mmol/L",
            unit="mmol/L"
        )
    )
    
    # 3. LDL CHOLESTEROL - Category-based ranges
    ranges.extend([
        # Optimal: < 2.6 mmol/L
        LabReferenceRange(
            field_code="ldl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=36500,
            low=Decimal("0"),
            high=Decimal("2.6"),
            text_range="< 2.6 mmol/L (Optimal)",
            unit="mmol/L"
        ),
        # Near Optimal: 2.6 - 3.3 mmol/L
        LabReferenceRange(
            field_code="ldl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=36500,
            low=Decimal("2.6"),
            high=Decimal("3.3"),
            text_range="2.6 - 3.3 mmol/L (Near Optimal)",
            unit="mmol/L"
        ),
        # Borderline High: 3.4 - 4.1 mmol/L
        LabReferenceRange(
            field_code="ldl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=36500,
            low=Decimal("3.4"),
            high=Decimal("4.1"),
            text_range="3.4 - 4.1 mmol/L (Borderline High)",
            unit="mmol/L"
        ),
        # High: 4.1 - 4.9 mmol/L
        LabReferenceRange(
            field_code="ldl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=36500,
            low=Decimal("4.1"),
            high=Decimal("4.9"),
            critical_high=Decimal("4.9"),
            text_range="4.1 - 4.9 mmol/L (High)",
            unit="mmol/L"
        ),
        # Very High: ≥ 4.9 mmol/L
        LabReferenceRange(
            field_code="ldl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=36500,
            low=Decimal("4.9"),
            high=Decimal("10.0"),
            critical_high=Decimal("4.9"),
            text_range="≥ 4.9 mmol/L (Very High)",
            unit="mmol/L"
        ),
    ])
    
    # 4. TRIGLYCERIDES - Age-specific ranges
    # Adults
    ranges.extend([
        # Normal: < 1.7 mmol/L
        LabReferenceRange(
            field_code="triglycerides",
            sex="ANY",
            age_min_days=6570,  # Adult
            age_max_days=36500,
            low=Decimal("0"),
            high=Decimal("1.7"),
            text_range="< 1.7 mmol/L (Normal)",
            unit="mmol/L"
        ),
        # Borderline High: 1.7 - 2.2 mmol/L
        LabReferenceRange(
            field_code="triglycerides",
            sex="ANY",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("1.7"),
            high=Decimal("2.2"),
            text_range="1.7 - 2.2 mmol/L (Borderline High)",
            unit="mmol/L"
        ),
        # High: 2.3 - 5.6 mmol/L
        LabReferenceRange(
            field_code="triglycerides",
            sex="ANY",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("2.3"),
            high=Decimal("5.6"),
            critical_high=Decimal("5.65"),
            text_range="2.3 - 5.6 mmol/L (High)",
            unit="mmol/L"
        ),
        # Very High: > 5.6 mmol/L
        LabReferenceRange(
            field_code="triglycerides",
            sex="ANY",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("5.6"),
            high=Decimal("15.0"),
            critical_high=Decimal("5.65"),
            text_range="> 5.6 mmol/L (Very High)",
            unit="mmol/L"
        ),
    ])
    
    # Children: < 1.1 mmol/L
    ranges.append(
        LabReferenceRange(
            field_code="triglycerides",
            sex="ANY",
            age_min_days=0,
            age_max_days=6569,  # < 18 years
            low=Decimal("0"),
            high=Decimal("1.1"),
            text_range="< 1.1 mmol/L",
            unit="mmol/L"
        )
    )
    
    # 5. VLDL CHOLESTEROL: 0.2 - 1.0 mmol/L
    ranges.append(
        LabReferenceRange(
            field_code="vldl_cholesterol",
            sex="ANY",
            age_min_days=0,
            age_max_days=36500,
            low=Decimal("0.2"),
            high=Decimal("1.0"),
            text_range="0.2 - 1.0 mmol/L",
            unit="mmol/L"
        )
    )
    
    # 6. CARDIAC RISK RATIO - Gender-specific (Adults only - 18+ years)
    # Male: < 4.5 low, 4.5-6.0 moderate, >6.0 high
    ranges.extend([
        # Adult Male ranges
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="M",
            age_min_days=6570,  # 18 years and above
            age_max_days=36500,
            low=Decimal("0"),
            high=Decimal("4.5"),
            text_range="< 4.5 (Low Risk - Adult Male)",
            unit="ratio"
        ),
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="M",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("4.5"),
            high=Decimal("6.0"),
            text_range="4.5 - 6.0 (Moderate Risk - Adult Male)",
            unit="ratio"
        ),
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="M",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("6.0"),
            high=Decimal("50.0"),
            text_range="> 6.0 (High Risk - Adult Male)",
            unit="ratio"
        ),
        # Adult Female: < 4.0 low, 4.0-6.0 moderate, >6.0 high
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="F",
            age_min_days=6570,  # 18 years and above
            age_max_days=36500,
            low=Decimal("0"),
            high=Decimal("4.0"),
            text_range="< 4.0 (Low Risk - Adult Female)",
            unit="ratio"
        ),
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="F",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("4.0"),
            high=Decimal("6.0"),
            text_range="4.0 - 6.0 (Moderate Risk - Adult Female)",
            unit="ratio"
        ),
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="F",
            age_min_days=6570,
            age_max_days=36500,
            low=Decimal("6.0"),
            high=Decimal("50.0"),
            text_range="> 6.0 (High Risk - Adult Female)",
            unit="ratio"
        ),
        # Children/Adolescent (< 18 years) - general reference
        LabReferenceRange(
            field_code="c_risk_ratio",
            sex="ANY",
            age_min_days=0,
            age_max_days=6569,  # < 18 years
            low=Decimal("0"),
            high=Decimal("3.0"),
            text_range="< 3.0 (Normal - Child/Adolescent)",
            unit="ratio"
        ),
    ])
    
    # Add all ranges to database
    for r in ranges:
        r.id = None  # Let SQLAlchemy generate new IDs
    
    db.add_all(ranges)
    db.flush()
    
    print(f"✓ Created {len(ranges)} reference ranges")
    
    # Print summary
    print("\nReference Range Summary:")
    print("-" * 40)
    field_codes = set(r.field_code for r in ranges)
    for code in field_codes:
        count = sum(1 for r in ranges if r.field_code == code)
        print(f"  {code}: {count} ranges")
    
    return ranges


def create_lab_test_entry(db):
    """
    Create/update LabTest catalog entry for Lipid Profile.
    """
    print("\n" + "="*60)
    print("Creating Lab Test Catalog Entry")
    print("="*60)
    
    # Check if test already exists
    test = db.query(LabTest).filter(LabTest.test_code == "LIPID").first()
    
    if test:
        print(f"Found existing LabTest: {test.id}")
        test.test_name = "Lipid Profile"
        test.description = "NHIS-Compliant Lipid Profile - Total Cholesterol, HDL, LDL, Triglycerides, VLDL, Cardiac Risk Ratio"
        test.specimen_type = "Serum (Fasting 12hrs)"
        test.routine_tat = 8
        test.is_panel = True
        test.test_category = "Biochemistry"
    else:
        test = LabTest(
            test_code="LIPID",
            test_name="Lipid Profile",
            description="NHIS-Compliant Lipid Profile - Total Cholesterol, HDL, LDL, Triglycerides, VLDL, Cardiac Risk Ratio",
            specimen_type="Serum (Fasting 12hrs)",
            routine_tat=8,
            is_panel=True,
            test_category="Biochemistry",
            test_type="Panel"
        )
        db.add(test)
    
    db.flush()
    print(f"✓ LabTest entry created/updated: {test.id} - {test.test_name}")
    
    return test


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("  NHIS-Compliant Lipid Profile Template Seeder")
    print("="*70)
    print(f"  Started at: {datetime.now().isoformat()}")
    print("="*70)
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create the template
        template, version = create_lipid_profile_template(db, admin_user_id=1)
        
        # Create reference ranges
        create_reference_ranges(db, template.id)
        
        # Create lab test catalog entry
        create_lab_test_entry(db)
        
        # Commit all changes
        db.commit()
        
        print("\n" + "="*70)
        print("  SUCCESS: NHIS-Compliant Lipid Profile Template Created!")
        print("="*70)
        print(f"\nTemplate ID: {template.id}")
        print(f"Template Name: {template.name}")
        print(f"Version: {template.current_version}")
        print(f"Status: {template.status}")
        
        print("\n" + "-"*70)
        print("INCLUDED PARAMETERS:")
        print("-"*70)
        parameters = [
            "1. Total Cholesterol (mmol/L)",
            "2. HDL Cholesterol (mmol/L)",
            "3. LDL Cholesterol (mmol/L)",
            "4. Triglycerides (mmol/L)",
            "5. VLDL Cholesterol (mmol/L) - Auto-calculated",
            "6. Cardiac Risk Ratio (ratio) - Auto-calculated"
        ]
        for p in parameters:
            print(f"  {p}")
        
        print("\n" + "-"*70)
        print("KEY FEATURES:")
        print("-"*70)
        features = [
            "✓ Age-specific reference ranges (Adults vs Children)",
            "✓ Gender-specific reference ranges (HDL, C-Risk)",
            "✓ Auto-calculation of VLDL (Triglycerides / 2.2)",
            "✓ Auto-calculation of C-Risk Ratio (Total Chol / HDL)",
            "✓ Interpretation flags (Low, Normal, Borderline, High)",
            "✓ Risk pattern detection (High LDL+High TC, Low HDL+High TG)",
            "✓ NHIS single-claim configuration",
            "✓ Comprehensive reference ranges per NHIS guidelines",
            "✓ Audit trail support"
        ]
        for f in features:
            print(f"  {f}")
        
        print("\n" + "="*70)
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
