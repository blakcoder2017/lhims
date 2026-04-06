#!/usr/bin/env python3
"""
Urine R/E (Urinalysis) Template Update Seed Script

This script updates/creates the Urine R/E template with:
- Macroscopy parameters (Color, Appearance)
- Chemical Analysis parameters (Protein, Glucose, Ketone, Blood, etc.)
- Microscopy parameters (Epithelial Cells, Pus Cells, RBC, Yeast, Casts, Crystals, Sperm, Bacteria, Parasite)
- Age and gender-specific reference ranges
- Validation rules and clinical flags
- NHIS-compliant report formatting

Usage:
    python3 seed_urine_re_template.py

Requirements:
    - Database must be initialized
    - Run after lab templates are set up
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from app.core.config import settings
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabReferenceRange
)
from app.models.lab_catalog_models import LabTest

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# URINE R/E TEMPLATE DEFINITION
# =============================================================================

def get_urine_re_template_definition():
    """
    Returns the complete Urine R/E template with all parameters,
    reference ranges, validation rules, and formatting.
    """
    
    return {
        "meta": {
            "name": "Urine R/E",
            "discipline": "URINALYSIS",
            "version": 2,
            "description": "Complete Urinalysis - Macroscopy, Chemical Analysis, and Microscopy",
            "category": "Routine",
            "nhis_code": "URINE_RE",
            "tat_hours": 4
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_macroscopy",
                    "title": "A. MACROSCOPY",
                    "order": 1,
                    "rows": [
                        {
                            "columns": [
                                {"items": ["color"], "width": 6},
                                {"items": ["appearance"], "width": 6}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_chemical",
                    "title": "B. CHEMICAL ANALYSIS",
                    "order": 2,
                    "rows": [
                        {
                            "columns": [
                                {"items": ["protein"], "width": 4},
                                {"items": ["glucose"], "width": 4},
                                {"items": ["ketone"], "width": 4}
                            ]
                        },
                        {
                            "columns": [
                                {"items": ["blood"], "width": 4},
                                {"items": ["bilirubin"], "width": 4},
                                {"items": ["urobilinogen"], "width": 4}
                            ]
                        },
                        {
                            "columns": [
                                {"items": ["nitrite"], "width": 4},
                                {"items": ["leucocytes"], "width": 4},
                                {"items": ["ph"], "width": 4}
                            ]
                        },
                        {
                            "columns": [
                                {"items": ["specific_gravity"], "width": 12}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_microscopy",
                    "title": "C. MICROSCOPY",
                    "order": 3,
                    "rows": [
                        {
                            "columns": [
                                {"items": ["epithelial_cells"], "width": 4},
                                {"items": ["pus_cells"], "width": 4},
                                {"items": ["rbc"], "width": 4}
                            ]
                        },
                        {
                            "columns": [
                                {"items": ["yeast_cells"], "width": 4},
                                {"items": ["casts"], "width": 4},
                                {"items": ["crystals"], "width": 4}
                            ]
                        },
                        {
                            "columns": [
                                {"items": ["sperm_cells"], "width": 4},
                                {"items": ["bacteria"], "width": 4},
                                {"items": ["parasite"], "width": 4}
                            ]
                        }
                    ]
                },
                {
                    "id": "sec_interpretation",
                    "title": "INTERPRETATION & COMMENTS",
                    "order": 4,
                    "rows": [
                        {
                            "columns": [
                                {"items": ["clinical_interpretation"], "width": 12}
                            ]
                        },
                        {
                            "columns": [
                                {"items": ["remarks"], "width": 12}
                            ]
                        }
                    ]
                }
            ]
        },
        "fields": {
            # A. MACROSCOPY
            "color": {
                "code": "color",
                "label": "Color",
                "type": "select",
                "required": True,
                "options": ["Pale Yellow", "Straw", "Amber", "Dark Yellow", "Reddish", "Brownish"],
                "default": "Pale Yellow",
                "reference_range": {
                    "text": "Pale Yellow - Amber",
                    "normal_values": ["Pale Yellow", "Straw", "Amber"]
                }
            },
            "appearance": {
                "code": "appearance",
                "label": "Appearance",
                "type": "select",
                "required": True,
                "options": ["Clear", "Slightly Turbid", "Turbid"],
                "default": "Clear",
                "reference_range": {
                    "text": "Clear",
                    "normal_values": ["Clear"]
                }
            },
            
            # B. CHEMICAL ANALYSIS
            "protein": {
                "code": "protein",
                "label": "Protein",
                "type": "select",
                "required": True,
                "options": ["Negative", "Trace", "+", "++", "+++"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative / Trace",
                    "normal_values": ["Negative", "Trace"],
                    "abnormal_flags": ["+", "++", "+++"]
                }
            },
            "glucose": {
                "code": "glucose",
                "label": "Glucose",
                "type": "select",
                "required": True,
                "options": ["Negative", "Trace", "+", "++", "+++"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative",
                    "normal_values": ["Negative"],
                    "abnormal_flags": ["Trace", "+", "++", "+++"]
                }
            },
            "ketone": {
                "code": "ketone",
                "label": "Ketone",
                "type": "select",
                "required": True,
                "options": ["Negative", "Trace", "+", "++", "+++"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative",
                    "normal_values": ["Negative"],
                    "abnormal_flags": ["Trace", "+", "++", "+++"]
                }
            },
            "blood": {
                "code": "blood",
                "label": "Blood",
                "type": "select",
                "required": True,
                "options": ["Negative", "Trace", "+", "++", "+++"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative",
                    "normal_values": ["Negative"],
                    "abnormal_flags": ["Trace", "+", "++", "+++"]
                }
            },
            "bilirubin": {
                "code": "bilirubin",
                "label": "Bilirubin",
                "type": "select",
                "required": True,
                "options": ["Negative", "+", "++"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative",
                    "normal_values": ["Negative"],
                    "abnormal_flags": ["+", "++"]
                }
            },
            "urobilinogen": {
                "code": "urobilinogen",
                "label": "Urobilinogen",
                "type": "select",
                "required": True,
                "options": ["Normal", "Increased"],
                "default": "Normal",
                "reference_range": {
                    "text": "Normal",
                    "normal_values": ["Normal"],
                    "abnormal_flags": ["Increased"]
                }
            },
            "nitrite": {
                "code": "nitrite",
                "label": "Nitrite",
                "type": "select",
                "required": True,
                "options": ["Negative", "Positive"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative",
                    "normal_values": ["Negative"],
                    "abnormal_flags": ["Positive"]
                },
                "clinical_flag": {
                    "condition": "nitrite == 'Positive' && leucocytes in ['+', '++', '+++']",
                    "message": "Possible UTI - Positive Nitrite with Leucocyturia",
                    "severity": "warning"
                }
            },
            "leucocytes": {
                "code": "leucocytes",
                "label": "Leucocytes",
                "type": "select",
                "required": True,
                "options": ["Negative", "Trace", "+", "++", "+++"],
                "default": "Negative",
                "reference_range": {
                    "text": "Negative",
                    "normal_values": ["Negative"],
                    "abnormal_flags": ["Trace", "+", "++", "+++"]
                }
            },
            "ph": {
                "code": "ph",
                "label": "pH",
                "type": "numeric",
                "required": True,
                "decimals": 1,
                "min": 4.5,
                "max": 8.0,
                "unit": "",
                "default": 6.0,
                "reference_range": {
                    "low": 4.5,
                    "high": 8.0,
                    "unit": "pH",
                    "text": "4.5 - 8.0"
                }
            },
            "specific_gravity": {
                "code": "specific_gravity",
                "label": "Specific Gravity",
                "type": "numeric",
                "required": True,
                "decimals": 3,
                "min": 1.001,
                "max": 1.050,
                "unit": "SG",
                "default": 1.015,
                "reference_range": {
                    "low": 1.005,
                    "high": 1.030,
                    "unit": "SG",
                    "text": "1.005 - 1.030"
                }
            },
            
            # C. MICROSCOPY
            "epithelial_cells": {
                "code": "epithelial_cells",
                "label": "Epithelial Cells",
                "type": "select",
                "required": True,
                "options": ["Few", "Moderate", "Many"],
                "default": "Few",
                "reference_range": {
                    "text": "Few",
                    "normal_values": ["Few"],
                    "abnormal_flags": ["Moderate", "Many"]
                }
            },
            "pus_cells": {
                "code": "pus_cells",
                "label": "Pus Cells (WBC/µL)",
                "type": "numeric",
                "required": True,
                "decimals": 0,
                "min": 0,
                "max": 100,
                "unit": "/µL",
                "default": 0,
                "reference_range": {
                    "ranges": [
                        {"sex": "M", "low": 0, "high": 5, "text": "0-5 / µL", "age_min": 6570},  # Adult Male (18+ years)
                        {"sex": "F", "low": 0, "high": 10, "text": "0-10 / µL", "age_min": 6570},  # Adult Female
                        {"sex": "ANY", "low": 0, "high": 5, "text": "0-5 / µL", "age_max": 6569}  # Children
                    ],
                    "default": {"low": 0, "high": 5, "text": "0-5 / µL"}
                },
                "clinical_flag": {
                    "condition": "pus_cells > 10",
                    "message": "Pyuria - Significant pus cells detected",
                    "severity": "warning"
                }
            },
            "rbc": {
                "code": "rbc",
                "label": "Red Blood Cells (RBC/µL)",
                "type": "numeric",
                "required": True,
                "decimals": 0,
                "min": 0,
                "max": 100,
                "unit": "/µL",
                "default": 0,
                "reference_range": {
                    "low": 0,
                    "high": 2,
                    "unit": "/µL",
                    "text": "0-2 / µL",
                    "applies_to": "ALL"
                },
                "clinical_flag": {
                    "condition": "rbc > 2",
                    "message": "Hematuria - RBC exceeds reference range",
                    "severity": "warning"
                }
            },
            "yeast_cells": {
                "code": "yeast_cells",
                "label": "Yeast Cells",
                "type": "select",
                "required": True,
                "options": ["Seen", "Not Seen"],
                "default": "Not Seen",
                "reference_range": {
                    "text": "Not Seen",
                    "normal_values": ["Not Seen"],
                    "abnormal_flags": ["Seen"]
                }
            },
            "casts": {
                "code": "casts",
                "label": "Casts",
                "type": "select",
                "required": True,
                "options": ["Not Seen", "Hyaline", "Granular", "RBC Casts", "WBC Casts"],
                "default": "Not Seen",
                "reference_range": {
                    "text": "Not Seen / Occasional Hyaline",
                    "normal_values": ["Not Seen", "Hyaline"],
                    "abnormal_flags": ["Granular", "RBC Casts", "WBC Casts"]
                },
                "clinical_flag": {
                    "condition": "casts in ['RBC Casts', 'WBC Casts', 'Granular']",
                    "message": "Pathological casts detected - clinical correlation required",
                    "severity": "warning"
                }
            },
            "crystals": {
                "code": "crystals",
                "label": "Crystals",
                "type": "select",
                "required": True,
                "options": ["Not Seen", "Calcium Oxalate", "Uric Acid", "Triple Phosphate"],
                "default": "Not Seen",
                "reference_range": {
                    "text": "Not Seen / Occasional",
                    "normal_values": ["Not Seen"],
                    "abnormal_flags": ["Calcium Oxalate", "Uric Acid", "Triple Phosphate"]
                }
            },
            "sperm_cells": {
                "code": "sperm_cells",
                "label": "Sperm Cells",
                "type": "select",
                "required": True,
                "options": ["Seen", "Not Seen"],
                "default": "Not Seen",
                "gender_filter": "M",  # Only applicable to males
                "reference_range": {
                    "text": "Not Seen",
                    "normal_values": ["Not Seen"],
                    "abnormal_flags": ["Seen"]
                }
            },
            "bacteria": {
                "code": "bacteria",
                "label": "Bacteria",
                "type": "select",
                "required": True,
                "options": ["Not Seen", "Few", "Moderate", "Many"],
                "default": "Not Seen",
                "reference_range": {
                    "text": "Not Seen",
                    "normal_values": ["Not Seen"],
                    "abnormal_flags": ["Few", "Moderate", "Many"]
                },
                "clinical_flag": {
                    "condition": "bacteria in ['Moderate', 'Many'] && nitrite == 'Positive'",
                    "message": "Probable UTI - Positive nitrite with significant bacteriuria",
                    "severity": "warning"
                }
            },
            "parasite": {
                "code": "parasite",
                "label": "Parasite",
                "type": "select",
                "required": True,
                "options": ["Not Seen", "Schistosoma haematobium", "Other (specify)"],
                "default": "Not Seen",
                "reference_range": {
                    "text": "Not Seen",
                    "normal_values": ["Not Seen"],
                    "abnormal_flags": ["Schistosoma haematobium", "Other (specify)"]
                },
                "clinical_flag": {
                    "condition": "parasite != 'Not Seen'",
                    "message": "CRITICAL: Parasite detected - Requires urgent clinical attention",
                    "severity": "critical"
                }
            },
            
            # Interpretation & Comments
            "clinical_interpretation": {
                "code": "clinical_interpretation",
                "label": "Clinical Interpretation",
                "type": "text",
                "multiline": True,
                "required": False
            },
            "remarks": {
                "code": "remarks",
                "label": "Remarks",
                "type": "text",
                "multiline": True,
                "required": False
            }
        },
        
        # Validation Rules
        "rules": {
            "required": ["color", "appearance", "protein", "glucose", "ketone", "blood", 
                        "bilirubin", "urobilinogen", "nitrite", "leucocytes", "ph", 
                        "specific_gravity", "epithelial_cells", "pus_cells", "rbc",
                        "yeast_cells", "casts", "crystals", "sperm_cells", "bacteria", "parasite"],
            
            "conditional_required": [
                {
                    "field": "sperm_cells",
                    "condition": "patient_gender == 'M'",
                    "message": "Sperm cells field is required for male patients"
                }
            ],
            
            # Cross-field validation rules
            "clinical_rules": [
                {
                    "id": "rule_uti",
                    "name": "Possible UTI",
                    "condition": "nitrite == 'Positive' && leucocytes in ['+', '++', '+++']",
                    "message": "Possible Urinary Tract Infection",
                    "severity": "warning",
                    "suggested_action": "Consider urine culture"
                },
                {
                    "id": "rule_hematuria",
                    "name": "Hematuria",
                    "condition": "rbc > 2",
                    "message": "Hematuria detected - further investigation recommended",
                    "severity": "warning",
                    "suggested_action": "Consider RBC morphology and renal evaluation"
                },
                {
                    "id": "rule_critical_parasite",
                    "name": "Critical Parasite",
                    "condition": "parasite != 'Not Seen'",
                    "message": "CRITICAL: Parasite detected",
                    "severity": "critical",
                    "suggested_action": "Urgent clinical review required"
                },
                {
                    "id": "rule_pathological_casts",
                    "name": "Pathological Casts",
                    "condition": "casts in ['RBC Casts', 'WBC Casts', 'Granular']",
                    "message": "Pathological casts detected",
                    "severity": "warning",
                    "suggested_action": "Renal involvement possible - clinical correlation required"
                }
            ]
        },
        
        # Report Formatting
        "report": {
            "format": "NHIS_COMPLIANT",
            "sections_order": ["macroscopy", "chemical", "microscopy", "interpretation"],
            "show_reference_ranges": True,
            "highlight_abnormal": True,
            "show_critical_flags": True,
            "include_interpretation": True,
            "footer": {
                "laboratory_info": True,
                "report_date": True,
                "authorized_by": True,
                "nhis_billing_code": "URINE_RE"
            }
        },
        
        # Gender/Age Logic
        "demographics": {
            "require_age": True,
            "require_gender": True,
            "gender_specific_fields": {
                "sperm_cells": {
                    "applicable_genders": ["M"],
                    "hidden_for": ["F"]
                }
            },
            "age_specific_ranges": {
                "pus_cells": {
                    "default_range": {"low": 0, "high": 5, "text": "0-5 / µL"},
                    "ranges": [
                        {"sex": "M", "age_min_days": 6570, "low": 0, "high": 5, "text": "0-5 / µL"},
                        {"sex": "F", "age_min_days": 6570, "low": 0, "high": 10, "text": "0-10 / µL"},
                        {"sex": "ANY", "age_max_days": 6569, "low": 0, "high": 5, "text": "0-5 / µL"}
                    ]
                }
            }
        }
    }


def get_reference_ranges():
    """
    Returns reference ranges for Urine R/E parameters.
    These will be stored in the lab_reference_ranges table.
    """
    return [
        # Macroscopy
        {"field_code": "color", "sex": "ANY", "text_range": "Pale Yellow - Amber", "unit": None},
        {"field_code": "appearance", "sex": "ANY", "text_range": "Clear", "unit": None},
        
        # Chemical Analysis
        {"field_code": "protein", "sex": "ANY", "text_range": "Negative/Trace", "unit": None},
        {"field_code": "glucose", "sex": "ANY", "text_range": "Negative", "unit": None},
        {"field_code": "ketone", "sex": "ANY", "text_range": "Negative", "unit": None},
        {"field_code": "blood", "sex": "ANY", "text_range": "Negative", "unit": None},
        {"field_code": "bilirubin", "sex": "ANY", "text_range": "Negative", "unit": None},
        {"field_code": "urobilinogen", "sex": "ANY", "text_range": "Normal", "unit": None},
        {"field_code": "nitrite", "sex": "ANY", "text_range": "Negative", "unit": None},
        {"field_code": "leucocytes", "sex": "ANY", "text_range": "Negative", "unit": None},
        {"field_code": "ph", "sex": "ANY", "low": Decimal("4.5"), "high": Decimal("8.0"), "unit": "pH"},
        {"field_code": "specific_gravity", "sex": "ANY", "low": Decimal("1.005"), "high": Decimal("1.030"), "unit": "SG"},
        
        # Microscopy
        {"field_code": "epithelial_cells", "sex": "ANY", "text_range": "Few", "unit": None},
        {"field_code": "pus_cells", "sex": "M", "age_min_days": 6570, "low": Decimal("0"), "high": Decimal("5"), "unit": "/µL"},
        {"field_code": "pus_cells", "sex": "F", "age_min_days": 6570, "low": Decimal("0"), "high": Decimal("10"), "unit": "/µL"},
        {"field_code": "pus_cells", "sex": "ANY", "age_max_days": 6569, "low": Decimal("0"), "high": Decimal("5"), "unit": "/µL"},
        {"field_code": "rbc", "sex": "ANY", "low": Decimal("0"), "high": Decimal("2"), "unit": "/µL"},
        {"field_code": "yeast_cells", "sex": "ANY", "text_range": "Not Seen", "unit": None},
        {"field_code": "casts", "sex": "ANY", "text_range": "Not Seen/Occasional Hyaline", "unit": None},
        {"field_code": "crystals", "sex": "ANY", "text_range": "Not Seen/Occasional", "unit": None},
        {"field_code": "sperm_cells", "sex": "M", "text_range": "Not Seen", "unit": None},
        {"field_code": "bacteria", "sex": "ANY", "text_range": "Not Seen", "unit": None},
        {"field_code": "parasite", "sex": "ANY", "text_range": "Not Seen", "unit": None},
    ]


def update_urine_re_template(db: Session):
    """Update or create the Urine R/E template."""
    
    print("=" * 60)
    print("Urine R/E Template Update")
    print("=" * 60)
    
    template_def = get_urine_re_template_definition()
    template_name = template_def["meta"]["name"]
    
    # Check if template exists
    existing_template = db.query(LabTemplate).filter(
        LabTemplate.name == template_name
    ).first()
    
    if existing_template:
        print(f"\n[UPDATE] Found existing template: {template_name}")
        
        # Get current version
        current_version = existing_template.current_version or 0
        new_version = current_version + 1
        
        print(f"  Current version: {current_version}, New version: {new_version}")
        
        # Update template metadata
        existing_template.discipline = template_def["meta"]["discipline"]
        existing_template.status = "DRAFT"
        
        # Create new version
        template_version = LabTemplateVersion(
            id=uuid4(),
            template_id=existing_template.id,
            version=new_version,
            status="DRAFT",
            schema_json=template_def,
            change_note=f"Updated Urine R/E template v{new_version} with complete macroscopy, chemical, and microscopy parameters",
            created_by_id=None  # Will be set by caller
        )
        db.add(template_version)
        
        template = existing_template
        print(f"  Created new version: {new_version}")
        
    else:
        print(f"\n[CREATE] Creating new template: {template_name}")
        
        # Create new template
        template = LabTemplate(
            id=uuid4(),
            name=template_name,
            discipline=template_def["meta"]["discipline"],
            status="DRAFT",
            created_by_id=None
        )
        db.add(template)
        db.flush()
        
        # Create first version
        template_version = LabTemplateVersion(
            id=uuid4(),
            template_id=template.id,
            version=1,
            status="DRAFT",
            schema_json=template_def,
            change_note="Initial Urine R/E template with complete macroscopy, chemical, and microscopy parameters",
            created_by_id=None
        )
        db.add(template_version)
        
        print(f"  Created template with version 1")
    
    db.commit()
    
    # Refresh to get IDs
    db.refresh(template)
    
    # Update reference ranges
    print("\n[REFERENCE RANGES] Updating reference ranges...")
    
    reference_ranges = get_reference_ranges()
    ranges_updated = 0
    
    for range_def in reference_ranges:
        field_code = range_def["field_code"]
        
        # Check if range exists
        existing_range = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == field_code,
            LabReferenceRange.sex == range_def.get("sex", "ANY"),
            LabReferenceRange.age_min_days == range_def.get("age_min_days"),
            LabReferenceRange.age_max_days == range_def.get("age_max_days")
        ).first()
        
        if existing_range:
            # Update existing range
            existing_range.low = range_def.get("low")
            existing_range.high = range_def.get("high")
            existing_range.text_range = range_def.get("text_range")
            existing_range.unit = range_def.get("unit")
        else:
            # Create new range
            new_range = LabReferenceRange(
                id=uuid4(),
                field_code=field_code,
                sex=range_def.get("sex", "ANY"),
                age_min_days=range_def.get("age_min_days"),
                age_max_days=range_def.get("age_max_days"),
                low=range_def.get("low"),
                high=range_def.get("high"),
                text_range=range_def.get("text_range"),
                unit=range_def.get("unit")
            )
            db.add(new_range)
        
        ranges_updated += 1
    
    db.commit()
    
    print(f"  Updated/created {ranges_updated} reference ranges")
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEMPLATE SUMMARY")
    print("=" * 60)
    print(f"Template Name: {template_name}")
    print(f"Discipline: {template_def['meta']['discipline']}")
    print(f"Version: {template.current_version or 1}")
    print(f"\nSections:")
    for section in template_def['layout']['sections']:
        print(f"  - {section['title']}")
    
    print(f"\nFields ({len(template_def['fields'])}):")
    for field_code, field_def in template_def['fields'].items():
        print(f"  - {field_def['label']} ({field_def['type']})")
    
    print(f"\nValidation Rules:")
    print(f"  - Required fields: {len(template_def['rules']['required'])}")
    print(f"  - Clinical rules: {len(template_def['rules']['clinical_rules'])}")
    
    print(f"\nReference Ranges: {ranges_updated}")
    
    print("\n" + "=" * 60)
    print("NHIS COMPLIANCE FEATURES")
    print("=" * 60)
    print("✓ Complete macroscopy parameters (Color, Appearance)")
    print("✓ Complete chemical analysis (10 parameters)")
    print("✓ Complete microscopy (9 parameters)")
    print("✓ Age-specific reference ranges (Pus cells)")
    print("✓ Gender-specific field (Sperm cells - males only)")
    print("✓ Clinical validation rules (UTI, Hematuria, Parasites)")
    print("✓ Critical finding flags")
    print("✓ NHIS-compliant report formatting")
    
    print("\n[SUCCESS] Urine R/E template updated successfully!")
    
    # Link template to lab test catalog
    print("\n[CATALOG] Linking template to lab test catalog...")
    
    # Find the URINE_RE lab test
    lab_test = db.query(LabTest).filter(
        LabTest.test_code == "URINE_RE"
    ).first()
    
    if lab_test:
        print(f"  Found lab test: {lab_test.test_name} (ID: {lab_test.id})")
        
        # Update the template link
        lab_test.template_id = template.id
        lab_test.template_version = template.current_version or 1
        db.commit()
        print(f"  Linked template to lab test catalog")
    else:
        print("  WARNING: URINE_RE lab test not found in catalog")
        print("  Please ensure lab test catalog is seeded first")
    
    return template


def main():
    """Main entry point."""
    print("Starting Urine R/E template update...")
    
    db = SessionLocal()
    try:
        update_urine_re_template(db)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
