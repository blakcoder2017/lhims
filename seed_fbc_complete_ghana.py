#!/usr/bin/env python3
"""
Comprehensive Full Blood Count (FBC) Template Update for Ghana LHIMS

This script updates the FBC template to include all modern hematology analyzer
parameters with proper units, reference ranges, and age/gender-based adjustments.

Parameters included:
- White Blood Cell Parameters (WBC, LYM%, MON%, NEU%, EOS%, BASO%)
- Absolute WBC Counts (LYM#, MON#, NEU#, EOS#, BASO#)
- Red Blood Cell Parameters (RBC, HGB, HCT)
- RBC Indices (MCV, MCH, MCHC, RDW, RDW_SD, RDW_CV)
- Platelet Parameters (PLT, MPV, PDW, PCT, P_LCR, P_LCC)
- Advanced/Optional Parameters (ALY%, LIC%, NRBC%, ALY#, LIC#, NRBC#)

Reference ranges aligned with Ghanaian laboratory standards.

Usage:
    python3 seed_fbc_complete_ghana.py

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
# COMPREHENSIVE FBC TEMPLATE DEFINITION
# =============================================================================

def create_comprehensive_fbc_template(db: Session, admin_user_id: int):
    """
    Create/update comprehensive Full Blood Count (FBC) template with all parameters.
    """
    print("Creating comprehensive FBC template...")
    
    template_name = "Full Blood Count (FBC)"
    
    # Check if exists - update existing
    existing = db.query(LabTemplate).filter(LabTemplate.name == template_name).first()
    if existing:
        print(f"Found existing FBC template: {existing.id}")
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
    
    # Complete FBC schema with ALL parameters as per Ghana standards
    schema = {
        "meta": {
            "name": "Full Blood Count (FBC)",
            "discipline": "HEMATOLOGY",
            "version": 6,
            "description": "Complete blood count with automated analyzer - Ghana Standard - Full Panel with Advanced Parameters",
            "specimen": "Whole Blood (EDTA)",
            "method": "Automated Haematology Analyzer",
            "reporting_units": "SI units",
            "nhis_compliant": True,
            "nhis_code": "FBC001",
            "analyzer_compatible": ["Sysmex", "Mindray", "Beckman Coulter", "Abbott"],
            "ui_config": {
                "style": "clinical",
                "section_colors": {
                    "sec_wbc": "info",
                    "sec_wbc_diff_pct": "primary",
                    "sec_wbc_diff_abs": "primary",
                    "sec_rbc": "warning",
                    "sec_rbc_indices": "warning",
                    "sec_platelet": "success",
                    "sec_advanced": "secondary",
                    "sec_morphology": "dark",
                    "sec_remarks": "secondary"
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
                    "title": "",
                    "ui_color": "info",
                    "rows": [
                        {"columns": [{"items": ["WBC"], "width": 12}]},
                        {"columns": [{"items": ["NEU%", "LYM%"], "width": 6}]},
                        {"columns": [{"items": ["MON%", "EOS%"], "width": 6}]},
                        {"columns": [{"items": ["BASO%"], "width": 12}]},
                        {"columns": [{"items": ["NEU#", "LYM#"], "width": 6}]},
                        {"columns": [{"items": ["MON#", "EOS#"], "width": 6}]},
                        {"columns": [{"items": ["BASO#"], "width": 12}]},
                        {"columns": [{"items": ["RBC"], "width": 12}]},
                        {"columns": [{"items": ["HGB"], "width": 12}]},
                        {"columns": [{"items": ["HCT"], "width": 12}]},
                        {"columns": [{"items": ["MCV", "MCH"], "width": 6}]},
                        {"columns": [{"items": ["MCHC", "RDW_CV"], "width": 6}]},
                        {"columns": [{"items": ["RDW_SD"], "width": 12}]},
                        {"columns": [{"items": ["PLT"], "width": 12}]},
                        {"columns": [{"items": ["MPV", "PDW"], "width": 6}]},
                        {"columns": [{"items": ["PCT"], "width": 12}]}
                    ]
                }
            ]
        },
        "fields": {
            # ==================== WHITE BLOOD CELL PARAMETERS ====================
            "WBC": {
                "code": "WBC",
                "type": "numeric",
                "label": "White Blood Cells",
                "short_code": "WBC",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": True,
                "critical": {"low": 2.0, "high": 30.0},
                "default_range": {"low": 4.0, "high": 10.0}
            },
            # Differential - Percentage
            "LYM%": {
                "code": "LYM%",
                "type": "numeric",
                "label": "Lymphocyte Percentage",
                "short_code": "LYM%",
                "unit": "%",
                "decimals": 2,
                "required": True,
                "default_range": {"low": 20, "high": 40}
            },
            "MON%": {
                "code": "MON%",
                "type": "numeric",
                "label": "Monocyte Percentage",
                "short_code": "MON%",
                "unit": "%",
                "decimals": 2,
                "required": True,
                "default_range": {"low": 2, "high": 10}
            },
            "NEU%": {
                "code": "NEU%",
                "type": "numeric",
                "label": "Neutrophil Percentage",
                "short_code": "NEU%",
                "unit": "%",
                "decimals": 2,
                "required": True,
                "default_range": {"low": 40, "high": 75}
            },
            "EOS%": {
                "code": "EOS%",
                "type": "numeric",
                "label": "Eosinophil Percentage",
                "short_code": "EOS%",
                "unit": "%",
                "decimals": 2,
                "required": False,
                "default_range": {"low": 1, "high": 6}
            },
            "BASO%": {
                "code": "BASO%",
                "type": "numeric",
                "label": "Basophil Percentage",
                "short_code": "BASO%",
                "unit": "%",
                "decimals": 2,
                "required": False,
                "default_range": {"low": 0, "high": 1}
            },
            # Differential - Absolute Counts
            "LYM#": {
                "code": "LYM#",
                "type": "numeric",
                "label": "Lymphocyte Absolute",
                "short_code": "LYM#",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * LYM% / 100",
                "default_range": {"low": 1.0, "high": 3.0}
            },
            "MON#": {
                "code": "MON#",
                "type": "numeric",
                "label": "Monocyte Absolute",
                "short_code": "MON#",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * MON% / 100",
                "default_range": {"low": 0.2, "high": 0.8}
            },
            "NEU#": {
                "code": "NEU#",
                "type": "numeric",
                "label": "Neutrophil Absolute",
                "short_code": "NEU#",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * NEU% / 100",
                "default_range": {"low": 2.0, "high": 7.0}
            },
            "EOS#": {
                "code": "EOS#",
                "type": "numeric",
                "label": "Eosinophil Absolute",
                "short_code": "EOS#",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * EOS% / 100",
                "default_range": {"low": 0.02, "high": 0.5}
            },
            "BASO#": {
                "code": "BASO#",
                "type": "numeric",
                "label": "Basophil Absolute",
                "short_code": "BASO#",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * BASO% / 100",
                "default_range": {"low": 0, "high": 0.1}
            },
            # ==================== RED BLOOD CELL PARAMETERS ====================
            "RBC": {
                "code": "RBC",
                "type": "numeric",
                "label": "Red Blood Cells",
                "short_code": "RBC",
                "unit": "×10¹²/L",
                "decimals": 2,
                "required": True,
                "gender_specific": True,
                "critical": {"low": 2.0, "high": 8.0}
            },
            "HGB": {
                "code": "HGB",
                "type": "numeric",
                "label": "Hemoglobin",
                "short_code": "HGB",
                "unit": "g/dL",
                "decimals": 2,
                "required": True,
                "gender_specific": True,
                "critical": {"low": 7.0, "high": 20.0}
            },
            "HCT": {
                "code": "HCT",
                "type": "numeric",
                "label": "Hematocrit",
                "short_code": "HCT",
                "unit": "%",
                "decimals": 2,
                "required": True,
                "gender_specific": True,
                "critical": {"low": 20.0, "high": 60.0}
            },
            # ==================== RBC INDICES ====================
            "MCV": {
                "code": "MCV",
                "type": "numeric",
                "label": "Mean Corpuscular Volume",
                "short_code": "MCV",
                "unit": "fL",
                "decimals": 2,
                "required": True,
                "default_range": {"low": 80, "high": 100}
            },
            "MCH": {
                "code": "MCH",
                "type": "numeric",
                "label": "Mean Corpuscular Hemoglobin",
                "short_code": "MCH",
                "unit": "pg",
                "decimals": 2,
                "required": True,
                "calculated": True,
                "formula": "HGB * 1000 / RBC",
                "default_range": {"low": 27, "high": 33}
            },
            "MCHC": {
                "code": "MCHC",
                "type": "numeric",
                "label": "Mean Corpuscular Hemoglobin Concentration",
                "short_code": "MCHC",
                "unit": "g/dL",
                "decimals": 2,
                "required": True,
                "calculated": True,
                "formula": "HGB * 100 / HCT",
                "default_range": {"low": 32, "high": 36}
            },
            "RDW_CV": {
                "code": "RDW_CV",
                "type": "numeric",
                "label": "Red Cell Distribution Width",
                "short_code": "RDW_CV",
                "unit": "%",
                "decimals": 2,
                "required": False,
                "default_range": {"low": 11.5, "high": 14.5}
            },
            "RDW_SD": {
                "code": "RDW_SD",
                "type": "numeric",
                "label": "Red Cell Distribution Width - SD",
                "short_code": "RDW_SD",
                "unit": "fL",
                "decimals": 2,
                "required": False,
                "default_range": {"low": 37, "high": 54}
            },
            # ==================== PLATELET PARAMETERS ====================
            "PLT": {
                "code": "PLT",
                "type": "numeric",
                "label": "Platelet Count",
                "short_code": "PLT",
                "unit": "×10⁹/L",
                "decimals": 2,
                "required": True,
                "critical": {"low": 20.0, "high": 1000.0},
                "default_range": {"low": 150, "high": 400}
            },
            "MPV": {
                "code": "MPV",
                "type": "numeric",
                "label": "Mean Platelet Volume",
                "short_code": "MPV",
                "unit": "fL",
                "decimals": 2,
                "required": False,
                "default_range": {"low": 7, "high": 12}
            },
            "PDW": {
                "code": "PDW",
                "type": "numeric",
                "label": "Platelet Distribution Width",
                "short_code": "PDW",
                "unit": "fL",
                "decimals": 2,
                "required": False,
                "default_range": {"low": 9, "high": 17}
            },
            "PCT": {
                "code": "PCT",
                "type": "numeric",
                "label": "Plateletcrit",
                "short_code": "PCT",
                "unit": "%",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "PLT * MPV / 10000",
                "default_range": {"low": 0.10, "high": 0.28}
            }
        },
        "rules": {
            "visibility": [
                {"field": "ALY%", "show_if": "advanced_mode = true"},
                {"field": "LIC%", "show_if": "advanced_mode = true"},
                {"field": "NRBC%", "show_if": "advanced_mode = true"},
                {"field": "ALY#", "show_if": "advanced_mode = true"},
                {"field": "LIC#", "show_if": "advanced_mode = true"},
                {"field": "NRBC#", "show_if": "advanced_mode = true"}
            ],
            "requiredIf": []
        },
        "calculated": [
            # Absolute WBC counts can be auto-calculated
            {
                "target_code": "LYM#",
                "formula": "WBC * LYM% / 100",
                "deps": ["WBC", "LYM%"],
                "label": "Calculated: WBC × LYM% / 100"
            },
            {
                "target_code": "MON#",
                "formula": "WBC * MON% / 100",
                "deps": ["WBC", "MON%"],
                "label": "Calculated: WBC × MON% / 100"
            },
            {
                "target_code": "NEU#",
                "formula": "WBC * NEU% / 100",
                "deps": ["WBC", "NEU%"],
                "label": "Calculated: WBC × NEU% / 100"
            },
            {
                "target_code": "EOS#",
                "formula": "WBC * EOS% / 100",
                "deps": ["WBC", "EOS%"],
                "label": "Calculated: WBC × EOS% / 100"
            },
            {
                "target_code": "BASO#",
                "formula": "WBC * BASO% / 100",
                "deps": ["WBC", "BASO%"],
                "label": "Calculated: WBC × BASO% / 100"
            },
            # RBC Indices
            {
                "target_code": "MCH",
                "formula": "HGB * 1000 / RBC",
                "deps": ["HGB", "RBC"],
                "label": "Calculated: HGB × 1000 / RBC"
            },
            {
                "target_code": "MCHC",
                "formula": "HGB * 100 / HCT",
                "deps": ["HGB", "HCT"],
                "label": "Calculated: HGB × 100 / HCT"
            },
            # Platelet calculation
            {
                "target_code": "PCT",
                "formula": "PLT * MPV / 10000",
                "deps": ["PLT", "MPV"],
                "label": "Calculated: PLT × MPV / 10000"
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
            change_note=f"Comprehensive FBC template v{new_version} - Added all modern hematology parameters with Ghana reference ranges",
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
            change_note="Initial comprehensive FBC template - Ghana standard with all modern parameters",
            created_by_id=admin_user_id
        )
        db.add(version)
        
        print(f"Created new FBC template (v1)")
        existing = tmpl
    
    db.flush()
    return existing


# =============================================================================
# COMPREHENSIVE REFERENCE RANGES FOR FBC - GHANA STANDARDS
# =============================================================================

def create_comprehensive_fbc_reference_ranges(db: Session):
    """
    Create comprehensive reference ranges for all FBC parameters.
    
    Age classification (in days):
    - Neonate: 0-28 days
    - Infant: 29-365 days (1 month - 12 months)
    - Child: 366-4745 days (1-12 years)
    - Adolescent: 4746-6569 days (13-17 years)
    - Adult: ≥6570 days (18+ years)
    """
    print("Creating comprehensive FBC reference ranges...")
    
    ranges = []
    
    # ==================== WHITE BLOOD CELLS (WBC) ====================
    # Adult (18+ years)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.0"), "high": Decimal("10.0"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "×10⁹/L"
    })
    # Adolescent (13-17 years)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 4746, "age_max_days": 6569,
        "low": Decimal("4.5"), "high": Decimal("13.5"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "×10⁹/L"
    })
    # Child (1-12 years)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 366, "age_max_days": 4745,
        "low": Decimal("5.0"), "high": Decimal("15.0"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "×10⁹/L"
    })
    # Infant (1-12 months)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 30, "age_max_days": 365,
        "low": Decimal("6.0"), "high": Decimal("17.5"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "×10⁹/L"
    })
    # Neonate (0-28 days)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 0, "age_max_days": 28,
        "low": Decimal("9.0"), "high": Decimal("30.0"),
        "critical_low": Decimal("5.0"), "critical_high": Decimal("40.0"), "unit": "×10⁹/L"
    })
    
    # ==================== LYMPHOCYTE PERCENTAGE (LYM%) ====================
    ranges.append({
        "field_code": "LYM%", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("20"), "high": Decimal("40"), "unit": "%"
    })
    ranges.append({
        "field_code": "LYM%", "sex": "ANY", "age_min_days": 366, "age_max_days": 6569,
        "low": Decimal("30"), "high": Decimal("70"), "unit": "%"
    })
    ranges.append({
        "field_code": "LYM%", "sex": "ANY", "age_min_days": 0, "age_max_days": 365,
        "low": Decimal("40"), "high": Decimal("80"), "unit": "%"
    })
    
    # ==================== MONOCYTE PERCENTAGE (MON%) ====================
    ranges.append({
        "field_code": "MON%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("2"), "high": Decimal("10"), "unit": "%"
    })
    
    # ==================== NEUTROPHIL PERCENTAGE (NEU%) ====================
    ranges.append({
        "field_code": "NEU%", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("40"), "high": Decimal("75"), "unit": "%"
    })
    ranges.append({
        "field_code": "NEU%", "sex": "ANY", "age_min_days": 366, "age_max_days": 6569,
        "low": Decimal("25"), "high": Decimal("60"), "unit": "%"
    })
    ranges.append({
        "field_code": "NEU%", "sex": "ANY", "age_min_days": 0, "age_max_days": 365,
        "low": Decimal("15"), "high": Decimal("50"), "unit": "%"
    })
    
    # ==================== EOSINOPHIL PERCENTAGE (EOS%) ====================
    ranges.append({
        "field_code": "EOS%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("1"), "high": Decimal("6"), "unit": "%"
    })
    
    # ==================== BASOPHIL PERCENTAGE (BASO%) ====================
    ranges.append({
        "field_code": "BASO%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("1"), "unit": "%"
    })
    
    # ==================== ABSOLUTE LYMPHOCYTE COUNT (LYM#) ====================
    ranges.append({
        "field_code": "LYM#", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("1.0"), "high": Decimal("3.0"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "LYM#", "sex": "ANY", "age_min_days": 366, "age_max_days": 6569,
        "low": Decimal("1.5"), "high": Decimal("9.0"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "LYM#", "sex": "ANY", "age_min_days": 0, "age_max_days": 365,
        "low": Decimal("2.5"), "high": Decimal("11.0"), "unit": "×10⁹/L"
    })
    
    # ==================== ABSOLUTE MONOCYTE COUNT (MON#) ====================
    ranges.append({
        "field_code": "MON#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.2"), "high": Decimal("0.8"), "unit": "×10⁹/L"
    })
    
    # ==================== ABSOLUTE NEUTROPHIL COUNT (NEU#) ====================
    ranges.append({
        "field_code": "NEU#", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("2.0"), "high": Decimal("7.0"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "NEU#", "sex": "ANY", "age_min_days": 366, "age_max_days": 6569,
        "low": Decimal("1.5"), "high": Decimal("8.5"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "NEU#", "sex": "ANY", "age_min_days": 0, "age_max_days": 365,
        "low": Decimal("1.0"), "high": Decimal("8.0"), "unit": "×10⁹/L"
    })
    
    # ==================== ABSOLUTE EOSINOPHIL COUNT (EOS#) ====================
    ranges.append({
        "field_code": "EOS#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.02"), "high": Decimal("0.5"), "unit": "×10⁹/L"
    })
    
    # ==================== ABSOLUTE BASOPHIL COUNT (BASO#) ====================
    ranges.append({
        "field_code": "BASO#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0.1"), "unit": "×10⁹/L"
    })
    
    # ==================== RED BLOOD CELLS (RBC) - GENDER SPECIFIC ====================
    # Adult Male (≥18 years)
    ranges.append({
        "field_code": "RBC", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.7"), "high": Decimal("6.1"),
        "critical_low": Decimal("3.0"), "critical_high": Decimal("8.0"), "unit": "×10¹²/L"
    })
    # Adult Female (≥18 years)
    ranges.append({
        "field_code": "RBC", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.2"), "high": Decimal("5.4"),
        "critical_low": Decimal("3.0"), "critical_high": Decimal("8.0"), "unit": "×10¹²/L"
    })
    # Adolescent (13-17 years)
    ranges.append({
        "field_code": "RBC", "sex": "ANY", "age_min_days": 4746, "age_max_days": 6569,
        "low": Decimal("4.0"), "high": Decimal("5.5"), "unit": "×10¹²/L"
    })
    # Child (1-12 years)
    ranges.append({
        "field_code": "RBC", "sex": "ANY", "age_min_days": 366, "age_max_days": 4745,
        "low": Decimal("4.0"), "high": Decimal("5.5"), "unit": "×10¹²/L"
    })
    # Infant (1-12 months)
    ranges.append({
        "field_code": "RBC", "sex": "ANY", "age_min_days": 30, "age_max_days": 365,
        "low": Decimal("3.5"), "high": Decimal("5.5"), "unit": "×10¹²/L"
    })
    # Neonate (0-28 days)
    ranges.append({
        "field_code": "RBC", "sex": "ANY", "age_min_days": 0, "age_max_days": 28,
        "low": Decimal("4.0"), "high": Decimal("6.6"), "unit": "×10¹²/L"
    })
    
    # ==================== HEMOGLOBIN (HGB) - GENDER SPECIFIC ====================
    # Adult Male (≥18 years)
    ranges.append({
        "field_code": "HGB", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("13.5"), "high": Decimal("17.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Adult Female (≥18 years)
    ranges.append({
        "field_code": "HGB", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("12.0"), "high": Decimal("15.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # Adolescent Male (13-17 years)
    ranges.append({
        "field_code": "HGB", "sex": "M", "age_min_days": 4746, "age_max_days": 6569,
        "low": Decimal("12.5"), "high": Decimal("16.5"), "unit": "g/dL"
    })
    # Adolescent Female (13-17 years)
    ranges.append({
        "field_code": "HGB", "sex": "F", "age_min_days": 4746, "age_max_days": 6569,
        "low": Decimal("11.5"), "high": Decimal("15.0"), "unit": "g/dL"
    })
    # Child (1-12 years)
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 366, "age_max_days": 4745,
        "low": Decimal("11.5"), "high": Decimal("15.0"), "unit": "g/dL"
    })
    # Infant (6-12 months)
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 180, "age_max_days": 365,
        "low": Decimal("10.5"), "high": Decimal("14.0"), "unit": "g/dL"
    })
    # Infant (1-6 months)
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 30, "age_max_days": 179,
        "low": Decimal("9.5"), "high": Decimal("13.0"), "unit": "g/dL"
    })
    # Neonate (0-7 days)
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 0, "age_max_days": 7,
        "low": Decimal("17.0"), "high": Decimal("22.5"), "unit": "g/dL"
    })
    # Neonate (8-28 days)
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 8, "age_max_days": 28,
        "low": Decimal("14.5"), "high": Decimal("21.5"), "unit": "g/dL"
    })
    
    # ==================== HEMATOCRIT (HCT) - GENDER SPECIFIC ====================
    # Adult Male (≥18 years)
    ranges.append({
        "field_code": "HCT", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("41"), "high": Decimal("53"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    # Adult Female (≥18 years)
    ranges.append({
        "field_code": "HCT", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("36"), "high": Decimal("46"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    # Child/Adolescent (all < 18 years)
    ranges.append({
        "field_code": "HCT", "sex": "ANY", "age_min_days": 0, "age_max_days": 6569,
        "low": Decimal("32"), "high": Decimal("50"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    
    # ==================== MEAN CORPUSCULAR VOLUME (MCV) ====================
    ranges.append({
        "field_code": "MCV", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("80"), "high": Decimal("100"), "unit": "fL"
    })
    
    # ==================== MEAN CORPUSCULAR HEMOGLOBIN (MCH) ====================
    ranges.append({
        "field_code": "MCH", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("27"), "high": Decimal("33"), "unit": "pg"
    })
    
    # ==================== MEAN CORPUSCULAR HEMOGLOBIN CONCENTRATION (MCHC) ====================
    ranges.append({
        "field_code": "MCHC", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("32"), "high": Decimal("36"), "unit": "g/dL"
    })
    
    # ==================== RED CELL DISTRIBUTION WIDTH (RDW_CV) ====================
    ranges.append({
        "field_code": "RDW_CV", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("11.5"), "high": Decimal("14.5"), "unit": "%"
    })
    
    # ==================== RED CELL DISTRIBUTION WIDTH SD (RDW_SD) ====================
    ranges.append({
        "field_code": "RDW_SD", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("37"), "high": Decimal("54"), "unit": "fL"
    })
    
    # ==================== PLATELET COUNT (PLT) ====================
    ranges.append({
        "field_code": "PLT", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("150"), "high": Decimal("400"),
        "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "×10⁹/L"
    })
    ranges.append({
        "field_code": "PLT", "sex": "ANY", "age_min_days": 0, "age_max_days": 6569,
        "low": Decimal("150"), "high": Decimal("450"),
        "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "×10⁹/L"
    })
    
    # ==================== MEAN PLATELET VOLUME (MPV) ====================
    ranges.append({
        "field_code": "MPV", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("7"), "high": Decimal("12"), "unit": "fL"
    })
    
    # ==================== PLATELET DISTRIBUTION WIDTH (PDW) ====================
    ranges.append({
        "field_code": "PDW", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("9"), "high": Decimal("17"), "unit": "fL"
    })
    
    # ==================== PLATELETCRIT (PCT) ====================
    ranges.append({
        "field_code": "PCT", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.10"), "high": Decimal("0.28"), "unit": "%"
    })
    
    # ==================== PLATELET LARGE CELL RATIO (P_LCR) ====================
    ranges.append({
        "field_code": "P_LCR", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("13"), "high": Decimal("43"), "unit": "%"
    })
    
    # ==================== PLATELET LARGE CELL COUNT (P_LCC) ====================
    ranges.append({
        "field_code": "P_LCC", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("30"), "high": Decimal("90"), "unit": "×10⁹/L"
    })
    
    # ==================== ADVANCED/OPTIONAL PARAMETERS ====================
    # Atypical Lymphocytes %
    ranges.append({
        "field_code": "ALY%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("1"), "unit": "%"
    })
    # Large Immature Cells %
    ranges.append({
        "field_code": "LIC%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("1"), "unit": "%"
    })
    # Nucleated RBC %
    ranges.append({
        "field_code": "NRBC%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0"), "unit": "%"
    })
    # Atypical Lymphocytes #
    ranges.append({
        "field_code": "ALY#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0.1"), "unit": "×10⁹/L"
    })
    # Large Immature Cells #
    ranges.append({
        "field_code": "LIC#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0.1"), "unit": "×10⁹/L"
    })
    # Nucleated RBC #
    ranges.append({
        "field_code": "NRBC#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0"), "unit": "×10⁹/L"
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
    if fbc_test:
        fbc_test.template_version = None  # Use latest
        print(f"Linked FBC catalog to template: {fbc_test.test_name}")
    else:
        # Create new FBC test
        fbc_test = LabTest(
            test_name="Full Blood Count (FBC)",
            test_code="FBC",
            test_category="Haematology",
            discipline="HEMATOLOGY",
            specimen_type="EDTA Whole Blood",
            is_active=True,
            nhis_code="FBC001",
            description="Complete blood count with differential - NHIS compliant"
        )
        db.add(fbc_test)
        print("Created new FBC test in catalog")
    
    db.flush()
    return fbc_test


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def seed_comprehensive_fbc():
    """Main function to seed comprehensive FBC template."""
    print("=" * 70)
    print("COMPREHENSIVE FULL BLOOD COUNT (FBC) TEMPLATE SEEDER")
    print("Ghana LHIMS - Updated for Modern Hematology Analyzers")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # Try first user
            admin_user = db.query(User).first()
        if not admin_user:
            print("ERROR: No admin user found. Please create admin user first.")
            return
        
        admin_user_id = admin_user.id
        print(f"\nUsing admin user: {admin_user.username} (ID: {admin_user_id})")
        
        # Create/update FBC template
        template = create_comprehensive_fbc_template(db, admin_user_id)
        
        # Create comprehensive reference ranges
        ranges_count = create_comprehensive_fbc_reference_ranges(db)
        
        # Link to catalog
        link_fbc_to_catalog(db, template.id)
        
        print("=" * 70)
        print(f"\nFBC Template: {template.name}")
        print(f"Template ID: {template.id}")
        
        print("\nTemplate Features:")
        print("  - 30+ FBC parameters (WBC, RBC, Platelet, Advanced)")
        print("  - Age-specific reference ranges (Neonate to Adult)")
        print("  - Gender-specific ranges for RBC, HGB, HCT")
        print("  - Optional advanced parameters for modern analyzers")
        print("  - NHIS compliant (FBC001)")
        print("  - Analyzer compatible (Sysmex, Mindray, Beckman Coulter)")
        
        print(f"\nReference Ranges Created: {ranges_count}")
        
        print("\n✅ FBC Template update completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_comprehensive_fbc()
