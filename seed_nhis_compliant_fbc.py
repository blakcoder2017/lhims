#!/usr/bin/env python3
"""
NHIS-Compliant Full Blood Count (FBC) Template Seeder

This script creates/updates the FBC template to conform strictly to NHIS and GHS reporting standards.

Requirements:
- Test Name: FULL BLOOD COUNT (FBC)
- Specimen: Whole Blood (EDTA)
- Method: Automated Haematology Analyzer
- Reporting Units: SI units

Parameters:
A. Red Blood Cell Parameters
   - Haemoglobin (Hb) – g/dL
   - Packed Cell Volume / Haematocrit (PCV / HCT) – %
   - Red Blood Cell Count (RBC) – ×10¹²/L
   - Mean Corpuscular Volume (MCV) – fL
   - Mean Corpuscular Haemoglobin (MCH) – pg
   - Mean Corpuscular Haemoglobin Concentration (MCHC) – g/dL
   - Red Cell Distribution Width (RDW-CV) – %

B. White Blood Cell Parameters
   - Total White Blood Cell Count (TWBC) – ×10⁹/L
   - WBC Differential (%): Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils

C. Platelet Parameters
   - Platelet Count (PLT) – ×10⁹/L
   - Mean Platelet Volume (MPV) – fL
   - Platelet Distribution Width (PDW) – fL
   - Plateletcrit (PCT) – %

Reference Range Logic:
- Adults (≥18 years): Sex-specific reference ranges for Hb, PCV/HCT, RBC
- Paediatric Patients (<18 years): Age-appropriate ranges (Neonate, Infant, Child, Adolescent)
- Sex handling: Sex-based ranges activate only when sex = Male or Female

Usage:
    python3 seed_nhis_compliant_fbc.py

Requirements:
    - Database must be initialized
    - Admin user must exist
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set DEBUG env var before importing app modules
os.environ['DEBUG'] = 'false'

# Import via app.main to ensure proper model loading order
from app.main import app
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from decimal import Decimal

from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabReferenceRange
)
from app.models.lab_catalog_models import LabTest
from app.models.user_models import User

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# NHIS-COMPLIANT FBC TEMPLATE DEFINITION
# =============================================================================

def create_nhis_compliant_fbc_template(db: Session, admin_user_id: int):
    """
    Create NHIS-compliant Full Blood Count (FBC) template with complete parameters.
    """
    print("Creating NHIS-compliant FBC template...")
    
    # Template name - use FBC as it's more common in Ghana
    template_name = "Full Blood Count (FBC)"
    
    # Check if exists - update existing
    existing = db.query(LabTemplate).filter(LabTemplate.name == template_name).first()
    if existing:
        print(f"Found existing FBC template: {existing.id}")
        # Get current version
        current_ver = db.query(LabTemplateVersion).filter(
            LabTemplateVersion.template_id == existing.id,
            LabTemplateVersion.version == existing.current_version
        ).first()
        
        new_version = existing.current_version + 1
        print(f"Updating to version {new_version}")
    else:
        existing = None
        new_version = 1
        print("Creating new FBC template")
    
    # Complete NHIS-compliant FBC schema with ALL parameters
    schema = {
        "meta": {
            "name": "Full Blood Count (FBC)",
            "discipline": "HEMATOLOGY",
            "version": 5,
            "description": "Complete blood count with automated analyser - NHIS compliant - Full Panel",
            "specimen": "Whole Blood (EDTA)",
            "method": "Automated Haematology Analyzer",
            "reporting_units": "SI units",
            "nhis_compliant": True,
            "ui_config": {
                "style": "clinical",
                "section_colors": {
                    "sec_haemoglobin": "danger",
                    "sec_rbc": "warning",
                    "sec_wbc": "info",
                    "sec_differential": "primary",
                    "sec_platelet": "success",
                    "sec_retic": "secondary",
                    "sec_morphology": "dark",
                    "sec_remarks": "secondary"
                }
            }
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_haemoglobin",
                    "title": "🩸 Haemoglobin & Haematocrit",
                    "ui_color": "danger",
                    "rows": [
                        {"columns": [{"items": ["haemoglobin", "haematocrit"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_rbc",
                    "title": "🔴 Red Blood Cell Indices",
                    "ui_color": "warning",
                    "rows": [
                        {"columns": [{"items": ["rbc", "mcv"], "width": 6}]},
                        {"columns": [{"items": ["mch", "mchc"], "width": 6}]},
                        {"columns": [{"items": ["rdw_cv", "rdw_sd"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_wbc",
                    "title": "🩳 White Blood Cells",
                    "ui_color": "info",
                    "rows": [
                        {"columns": [{"items": ["wbc"], "width": 12}]}
                    ]
                },
                {
                    "id": "sec_differential",
                    "title": "📊 Differential Count (Percentage)",
                    "ui_color": "primary",
                    "rows": [
                        {"columns": [{"items": ["neutrophils", "lymphocytes", "monocytes"], "width": 4}]},
                        {"columns": [{"items": ["eosinophils", "basophils"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_differential_abs",
                    "title": "📊 Differential Count (Absolute)",
                    "ui_color": "primary",
                    "rows": [
                        {"columns": [{"items": ["neutrophils_abs", "lymphocytes_abs", "monocytes_abs"], "width": 4}]},
                        {"columns": [{"items": ["eosinophils_abs", "basophils_abs"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_retic",
                    "title": "🔬 Reticulocytes",
                    "ui_color": "secondary",
                    "rows": [
                        {"columns": [{"items": ["retic", "retic_abs"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_platelet",
                    "title": "💚 Platelets",
                    "ui_color": "success",
                    "rows": [
                        {"columns": [{"items": ["platelet_count", "mpv"], "width": 6}]},
                        {"columns": [{"items": ["pdw", "pct"], "width": 6}]}
                    ]
                },
                {
                    "id": "sec_morphology",
                    "title": "🔍 Morphology",
                    "ui_color": "dark",
                    "rows": [
                        {"columns": [{"items": ["rbcmorph", "wbc_morph"], "width": 6}]},
                        {"columns": [{"items": ["platelet_morph", "parasites"], "width": 6}]}
                    ]
                }
            ]
        },
        "fields": {
            # Haemoglobin & Haematocrit
            "haemoglobin": {
                "code": "haemoglobin",
                "type": "numeric",
                "label": "Haemoglobin",
                "unit": "g/dL",
                "decimals": 2,
                "required": True,
                "critical": {"low": 7.0, "high": 20.0}
            },
            "haematocrit": {
                "code": "haematocrit",
                "type": "numeric",
                "label": "Haematocrit",
                "unit": "%",
                "decimals": 2,
                "required": True,
                "critical": {"low": 20.0, "high": 60.0}
            },
            # Red Blood Cells
            "rbc": {
                "code": "rbc",
                "type": "numeric",
                "label": "Red Blood Cell Count (RBC)",
                "unit": "×10¹²/L",
                "decimals": 2,
                "required": True
            },
            "mcv": {
                "code": "mcv",
                "type": "numeric",
                "label": "Mean Corpuscular Volume (MCV)",
                "unit": "fL",
                "decimals": 2,
                "required": True
            },
            "mch": {
                "code": "mch",
                "type": "numeric",
                "label": "Mean Corpuscular Haemoglobin (MCH)",
                "unit": "pg",
                "decimals": 2,
                "required": True
            },
            "mchc": {
                "code": "mchc",
                "type": "numeric",
                "label": "Mean Corpuscular Hb Concentration (MCHC)",
                "unit": "g/dL",
                "decimals": 2,
                "required": True
            },
            "rdw_cv": {
                "code": "rdw_cv",
                "type": "numeric",
                "label": "Red Cell Distribution Width (RDW-CV)",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            "rdw_sd": {
                "code": "rdw_sd",
                "type": "numeric",
                "label": "Red Cell Distribution Width (RDW-SD)",
                "unit": "fL",
                "decimals": 2,
                "required": False
            },
            # White Blood Cells
            "wbc": {
                "code": "wbc",
                "type": "numeric",
                "label": "White Blood Cells (WBC)",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": True,
                "critical": {"low": 2.0, "high": 30.0}
            },
            # Differential Count
            "neutrophils": {
                "code": "neutrophils",
                "type": "numeric",
                "label": "Granulocytes (Neutrophils)",
                "unit": "%",
                "decimals": 2,
                "required": True
            },
            "lymphocytes": {
                "code": "lymphocytes",
                "type": "numeric",
                "label": "Lymphocytes",
                "unit": "%",
                "decimals": 2,
                "required": True
            },
            "monocytes": {
                "code": "monocytes",
                "type": "numeric",
                "label": "Mid Cells (Monocytes)",
                "unit": "%",
                "decimals": 2,
                "required": True
            },
            "eosinophils": {
                "code": "eosinophils",
                "type": "numeric",
                "label": "Eosinophils",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            "basophils": {
                "code": "basophils",
                "type": "numeric",
                "label": "Basophils",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            # Platelets
            "platelet_count": {
                "code": "platelet_count",
                "type": "numeric",
                "label": "Platelet Count",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": True,
                "critical": {"low": 20.0, "high": 1000.0}
            },
            "mpv": {
                "code": "mpv",
                "type": "numeric",
                "label": "Mean Platelet Volume (MPV)",
                "unit": "fL",
                "decimals": 2,
                "required": False
            },
            "pdw": {
                "code": "pdw",
                "type": "numeric",
                "label": "Platelet Distribution Width (PDW)",
                "unit": "fL",
                "decimals": 2,
                "required": False
            },
            "pct": {
                "code": "pct",
                "type": "numeric",
                "label": "Plateletcrit (PCT)",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            # Absolute Differential Counts (calculated from WBC × %)
            "neutrophils_abs": {
                "code": "neutrophils_abs",
                "type": "numeric",
                "label": "Neutrophils #",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False
            },
            "lymphocytes_abs": {
                "code": "lymphocytes_abs",
                "type": "numeric",
                "label": "Lymphocytes #",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False
            },
            "monocytes_abs": {
                "code": "monocytes_abs",
                "type": "numeric",
                "label": "Monocytes #",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False
            },
            "eosinophils_abs": {
                "code": "eosinophils_abs",
                "type": "numeric",
                "label": "Eosinophils #",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False
            },
            "basophils_abs": {
                "code": "basophils_abs",
                "type": "numeric",
                "label": "Basophils #",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False
            },
            # Reticulocytes
            "retic": {
                "code": "retic",
                "type": "numeric",
                "label": "Reticulocytes",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            "retic_abs": {
                "code": "retic_abs",
                "type": "numeric",
                "label": "Absolute Reticulocyte Count",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False
            },
            # Morphology
            "rbcmorph": {
                "code": "rbcmorph",
                "type": "text",
                "label": "RBC Morphology",
                "multiline": True,
                "required": False
            },
            "wbc_morph": {
                "code": "wbc_morph",
                "type": "text",
                "label": "WBC Morphology",
                "multiline": True,
                "required": False
            },
            "platelet_morph": {
                "code": "platelet_morph",
                "type": "text",
                "label": "Platelet Morphology",
                "multiline": True,
                "required": False
            },
            "parasites": {
                "code": "parasites",
                "type": "text",
                "label": "Blood Parasites",
                "multiline": True,
                "required": False
            }
        },
        "rules": {
            "visibility": [],
            "requiredIf": []
        },
        "calculated": [
            # MCH can be calculated: MCH = (Hb × 1000) / RBC
            {
                "target_code": "mch",
                "formula": "haemoglobin * 1000 / rbc",
                "deps": ["haemoglobin", "rbc"],
                "label": "Calculated: Haemoglobin × 1000 / RBC"
            },
            # MCHC can be calculated: MCHC = (Hb / HCT) × 100
            {
                "target_code": "mchc",
                "formula": "(haemoglobin / haematocrit) * 100",
                "deps": ["haemoglobin", "haematocrit"],
                "label": "Calculated: (Haemoglobin / Haematocrit) × 100"
            }
        ]
    }
    
    if existing:
        # Update existing template
        existing.discipline = "HEMATOLOGY"
        existing.status = "PUBLISHED"
        
        # Create new version
        version = LabTemplateVersion(
            template_id=existing.id,
            version=new_version,
            status="PUBLISHED",
            schema_json=schema,
            change_note=f"NHIS-compliant FBC template v{new_version} - Added RDW-CV, MPV, PDW, PCT parameters with age/sex-specific reference ranges",
            created_by_id=admin_user_id
        )
        db.add(version)
        existing.current_version = new_version
        
        print(f"Updated FBC template to version {new_version}")
    else:
        # Create new template
        tmpl = LabTemplate(
            name=template_name,
            discipline="HEMATOLOGY",
            status="PUBLISHED",
            created_by_id=admin_user_id
        )
        db.add(tmpl)
        db.flush()
        
        version = LabTemplateVersion(
            template_id=tmpl.id,
            version=1,
            status="PUBLISHED",
            schema_json=schema,
            change_note="Initial NHIS-compliant FBC template - Complete parameters with age/sex-specific reference ranges",
            created_by_id=admin_user_id
        )
        db.add(version)
        tmpl.current_version = 1
        
        print(f"Created new FBC template (v1)")
        existing = tmpl
    
    db.commit()
    return existing


# =============================================================================
# COMPREHENSIVE REFERENCE RANGES FOR FBC
# =============================================================================

def create_fbc_reference_ranges(db: Session):
    """
    Create comprehensive reference ranges for all FBC parameters.
    
    Age classification:
    - Neonate: 0-28 days (0-28 days)
    - Infant: 1-12 months (30-365 days)
    - Child: 1-12 years (366-4745 days)
    - Adolescent: 13-17 years (4746-6569 days)
    - Adult: ≥18 years (6570+ days)
    """
    print("Creating FBC reference ranges...")
    
    ranges = []
    
    # ==================== HAEMOGLOBIN ====================
    # Adult Male (≥18 years)
    ranges.append({
        "field_code": "haemoglobin", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("12.5"), "high": Decimal("17.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Adult Female (≥18 years)
    ranges.append({
        "field_code": "haemoglobin", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("11.5"), "high": Decimal("15.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Adolescent (13-17 years)
    ranges.append({
        "field_code": "haemoglobin", "sex": "ANY", "age_min_days": 4745, "age_max_days": 6570,
        "low": Decimal("12.0"), "high": Decimal("16.0"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Child (6-12 years)
    ranges.append({
        "field_code": "haemoglobin", "sex": "ANY", "age_min_days": 2190, "age_max_days": 4745,
        "low": Decimal("11.5"), "high": Decimal("15.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Preschool (3-5 years)
    ranges.append({
        "field_code": "haemoglobin", "sex": "ANY", "age_min_days": 1095, "age_max_days": 2190,
        "low": Decimal("11.0"), "high": Decimal("14.0"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Toddler (1-3 years)
    ranges.append({
        "field_code": "haemoglobin", "sex": "ANY", "age_min_days": 365, "age_max_days": 1095,
        "low": Decimal("10.5"), "high": Decimal("14.0"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Infant (1-12 months)
    ranges.append({
        "field_code": "haemoglobin", "sex": "ANY", "age_min_days": 30, "age_max_days": 365,
        "low": Decimal("9.5"), "high": Decimal("13.0"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Newborn (0-28 days)
    ranges.append({
        "field_code": "haemoglobin", "sex": "ANY", "age_min_days": 0, "age_max_days": 28,
        "low": Decimal("14.5"), "high": Decimal("22.5"),
        "critical_low": Decimal("10.0"), "critical_high": Decimal("25.0"), "unit": "g/dL"
    })
    
    # ==================== HAEMATOCRIT ====================
    # Adult Male
    ranges.append({
        "field_code": "haematocrit", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("36"), "high": Decimal("50"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    # Adult Female
    ranges.append({
        "field_code": "haematocrit", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("34"), "high": Decimal("46"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    # Child/Adolescent (all ages < 18)
    ranges.append({
        "field_code": "haematocrit", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570,
        "low": Decimal("32"), "high": Decimal("50"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    
    # ==================== RBC COUNT ====================
    # Adult Male
    ranges.append({
        "field_code": "rbc", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.5"), "high": Decimal("6.5"), "unit": "×10¹²/L"
    })
    # Adult Female
    ranges.append({
        "field_code": "rbc", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("3.8"), "high": Decimal("5.8"), "unit": "×10¹²/L"
    })
    # Child/Adolescent
    ranges.append({
        "field_code": "rbc", "sex": "ANY", "age_min_days": 0, "age_max_days": 6570,
        "low": Decimal("3.8"), "high": Decimal("6.0"), "unit": "×10¹²/L"
    })
    
    # ==================== MCV ====================
    ranges.append({
        "field_code": "mcv", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("80"), "high": Decimal("100"), "unit": "fL"
    })
    
    # ==================== MCH ====================
    ranges.append({
        "field_code": "mch", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("27"), "high": Decimal("33"), "unit": "pg"
    })
    
    # ==================== MCHC ====================
    ranges.append({
        "field_code": "mchc", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("31.5"), "high": Decimal("35.5"), "unit": "g/dL"
    })
    
    # ==================== RDW-CV ====================
    ranges.append({
        "field_code": "rdw_cv", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": None, "high": Decimal("14.5"), "unit": "%"
    })
    
    # ==================== RDW-SD ====================
    ranges.append({
        "field_code": "rdw_sd", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("37"), "high": Decimal("54"), "unit": "fL"
    })
    
    # ==================== WBC COUNT ====================
    ranges.append({
        "field_code": "wbc", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("4.0"), "high": Decimal("11.0"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "×10⁹/L"
    })
    
    # ==================== DIFFERENTIAL COUNT ====================
    # Neutrophils (Granulocytes)
    ranges.append({
        "field_code": "neutrophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("40"), "high": Decimal("75"), "unit": "%"
    })
    # Lymphocytes
    ranges.append({
        "field_code": "lymphocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("20"), "high": Decimal("50"), "unit": "%"
    })
    # Monocytes (Mid cells)
    ranges.append({
        "field_code": "monocytes", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("2"), "high": Decimal("10"), "unit": "%"
    })
    # Eosinophils
    ranges.append({
        "field_code": "eosinophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("1"), "high": Decimal("6"), "unit": "%"
    })
    # Basophils
    ranges.append({
        "field_code": "basophils", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("2"), "unit": "%"
    })
    
    # ==================== ABSOLUTE DIFFERENTIAL COUNTS ====================
    ranges.append({
        "field_code": "neutrophils_abs", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("1.5"), "high": Decimal("7.5"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "lymphocytes_abs", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("1.0"), "high": Decimal("4.0"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "monocytes_abs", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.1"), "high": Decimal("1.0"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "eosinophils_abs", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.02"), "high": Decimal("0.5"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "basophils_abs", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0.1"), "unit": "×10⁹/L"
    })
    
    # ==================== RETICULOCYTES ====================
    ranges.append({
        "field_code": "retic", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.5"), "high": Decimal("2.5"), "unit": "%"
    })
    ranges.append({
        "field_code": "retic_abs", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.02"), "high": Decimal("0.1"), "unit": "×10⁹/L"
    })
    
    # ==================== PLATELET PARAMETERS ====================
    # Platelet Count
    ranges.append({
        "field_code": "platelet_count", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("150"), "high": Decimal("400"),
        "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "×10⁹/L"
    })
    # MPV
    ranges.append({
        "field_code": "mpv", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("7.5"), "high": Decimal("11.5"), "unit": "fL"
    })
    # PDW
    ranges.append({
        "field_code": "pdw", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("9.0"), "high": Decimal("17.0"), "unit": "fL"
    })
    # PCT
    ranges.append({
        "field_code": "pct", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.17"), "high": Decimal("0.35"), "unit": "%"
    })
    
    # Insert ranges
    count = 0
    for range_def in ranges:
        # Check if exists
        existing = db.query(LabReferenceRange).filter(
            LabReferenceRange.field_code == range_def["field_code"],
            LabReferenceRange.sex == range_def["sex"],
            LabReferenceRange.age_min_days == range_def.get("age_min_days"),
            LabReferenceRange.age_max_days == range_def.get("age_max_days")
        ).first()
        
        if not existing:
            rr = LabReferenceRange(**range_def)
            db.add(rr)
            count += 1
        else:
            # Update existing
            existing.low = range_def.get("low")
            existing.high = range_def.get("high")
            existing.critical_low = range_def.get("critical_low")
            existing.critical_high = range_def.get("critical_high")
            existing.unit = range_def.get("unit")
            count += 1
    
    db.commit()
    print(f"Created/updated {count} FBC reference ranges")
    return count


# =============================================================================
# LINK FBC TEMPLATE TO CATALOG
# =============================================================================

def link_fbc_to_catalog(db: Session, template_id):
    """Link the FBC template to the lab test catalog."""
    print("Linking FBC template to catalog...")
    
    # Find or create FBC test in catalog
    fbc_test = db.query(LabTest).filter(LabTest.test_code == "FBC").first()
    if not fbc_test:
        fbc_test = db.query(LabTest).filter(
            LabTest.test_name.ilike("%full blood count%")
        ).first()
    
    if fbc_test:
        fbc_test.template_id = template_id
        fbc_test.template_version = None  # Use latest
        print(f"Linked FBC catalog to template: {fbc_test.test_name}")
    else:
        # Create new FBC test
        fbc_test = LabTest(
            test_name="Full Blood Count (FBC)",
            test_code="FBC",
            test_category="Haematology",
            test_type="Panel",
            description="Complete blood count with differential - NHIS compliant",
            specimen_type="EDTA Whole Blood",
            specimen_volume="2-3 mL",
            routine_tat=4,
            urgent_tat=1,
            stat_tat=0.5,
            nhis_covered=True,
            nhis_code="HEM001",
            template_id=template_id
        )
        db.add(fbc_test)
        print("Created new FBC test in catalog")
    
    db.commit()
    return fbc_test


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def seed_nhis_compliant_fbc():
    """Main function to seed NHIS-compliant FBC template."""
    print("=" * 70)
    print("NHIS-COMPLIANT FULL BLOOD COUNT (FBC) TEMPLATE SEEDER")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("ERROR: Admin user not found. Run init_db.py first.")
            return
        
        admin_user_id = admin_user.id
        print(f"Using admin user ID: {admin_user_id}")
        
        # Create/update FBC template
        template = create_nhis_compliant_fbc_template(db, admin_user_id)
        
        # Create reference ranges
        ranges_count = create_fbc_reference_ranges(db)
        
        # Link to catalog
        link_fbc_to_catalog(db, template.id)
        
        print("=" * 70)
        print("SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nFBC Template: {template.name}")
        print(f"Template ID: {template.id}")
        print(f"Version: {template.current_version}")
        print(f"Reference Ranges: {ranges_count}")
        print("\nTemplate Features:")
        print("  - 17 FBC parameters (RBC, WBC, Platelet)")
        print("  - Age-specific reference ranges (Neonate to Adult)")
        print("  - Sex-specific reference ranges for Hb, HCT, RBC")
        print("  - SI units throughout")
        print("  - NHIS-compliant reporting format")
        print("  - Calculated fields: MCH, MCHC")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_nhis_compliant_fbc()
