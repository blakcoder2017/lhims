#!/usr/bin/env python3
"""
Full Blood Count (FBC) Template for Ghana LHIMS

This script creates/updates the FBC template with the exact parameters
and reference ranges specified for Ghanaian laboratories.

Parameters:
- WBC: White Blood Cell Count
- RBC, HGB, HCT: Red blood cell parameters (gender-specific)
- MCV, MCH, MCHC, RDW-SD, RDW-CV: RBC indices
- PLT, PDW, MPV, P-LCR, PCT: Platelet parameters
- NEUT#, LYMPH#, MONO#, EO#, BASO#: Absolute WBC counts
- NEUT%, LYMPH%, MONO%, EO%, BASO%: Differential percentages

Reference ranges auto-adjust based on:
- Age: Neonates, Infants, Children, Adolescents, Adults
- Gender: Male/Female for RBC, HGB, HCT
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

from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion, LabReferenceRange
)
from app.models.lab_catalog_models import LabTest
from app.models.user_models import User

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_fbc_template(db: Session, admin_user_id: int):
    """Create FBC template with specified parameters."""
    print("Creating FBC template...")
    
    template_name = "Full Blood Count (FBC)"
    
    existing = db.query(LabTemplate).filter(LabTemplate.name == template_name).first()
    if existing:
        print(f"Found existing FBC template: {existing.id}")
        new_version = existing.current_version + 1
    else:
        existing = None
        new_version = 1
    
    # Template schema with exact parameters
    schema = {
        "meta": {
            "name": "Full Blood Count (FBC)",
            "discipline": "HEMATOLOGY",
            "version": 14,
            "description": "Complete Blood Count - Ghana Standard",
            "specimen": "Whole Blood (EDTA)",
            "method": "Automated Haematology Analyzer",
            "nhis_compliant": True,
            "nhis_code": "FBC001"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_main",
                    "title": "",
                    "rows": [
                        {"columns": [{"items": ["WBC", "RBC"], "width": 6}]},
                        {"columns": [{"items": ["HGB", "HCT"], "width": 6}]},
                        {"columns": [{"items": ["MCV", "MCH"], "width": 6}]},
                        {"columns": [{"items": ["MCHC", "RDW_SD"], "width": 6}]},
                        {"columns": [{"items": ["RDW_CV", "PLT"], "width": 6}]},
                        {"columns": [{"items": ["MPV", "PDW"], "width": 6}]},
                        {"columns": [{"items": ["P_LCR", "PCT"], "width": 6}]},
                        {"columns": [{"items": ["NEUT#", "LYMPH#"], "width": 6}]},
                        {"columns": [{"items": ["MONO#", "EO#"], "width": 6}]},
                        {"columns": [{"items": ["BASO#", "NEUT%"], "width": 6}]},
                        {"columns": [{"items": ["LYMPH%", "MONO%"], "width": 6}]},
                        {"columns": [{"items": ["EO%", "BASO%"], "width": 6}]}
                    ]
                }
            ]
        },
        "fields": {
            # White Blood Cell Count
            "WBC": {
                "code": "WBC",
                "type": "numeric",
                "label": "WBC",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": True,
                "critical": {"low": 2.0, "high": 30.0}
            },
            # Red Blood Cell Parameters
            "RBC": {
                "code": "RBC",
                "type": "numeric",
                "label": "RBC",
                "unit": "x10¹²/L",
                "decimals": 2,
                "required": True,
                "gender_specific": True,
                "critical": {"low": 2.0, "high": 8.0}
            },
            "HGB": {
                "code": "HGB",
                "type": "numeric",
                "label": "HGB",
                "unit": "g/dL",
                "decimals": 2,
                "required": True,
                "gender_specific": True,
                "critical": {"low": 7.0, "high": 20.0}
            },
            "HCT": {
                "code": "HCT",
                "type": "numeric",
                "label": "HCT",
                "unit": "%",
                "decimals": 2,
                "required": True,
                "gender_specific": True,
                "critical": {"low": 20.0, "high": 60.0}
            },
            # RBC Indices
            "MCV": {
                "code": "MCV",
                "type": "numeric",
                "label": "MCV",
                "unit": "fL",
                "decimals": 2,
                "required": True
            },
            "MCH": {
                "code": "MCH",
                "type": "numeric",
                "label": "MCH",
                "unit": "pg",
                "decimals": 2,
                "required": True,
                "calculated": True,
                "formula": "HGB * 1000 / RBC"
            },
            "MCHC": {
                "code": "MCHC",
                "type": "numeric",
                "label": "MCHC",
                "unit": "g/dL",
                "decimals": 2,
                "required": True,
                "calculated": True,
                "formula": "HGB * 100 / HCT"
            },
            "RDW_SD": {
                "code": "RDW_SD",
                "type": "numeric",
                "label": "RDW-SD",
                "unit": "fL",
                "decimals": 2,
                "required": False
            },
            "RDW_CV": {
                "code": "RDW_CV",
                "type": "numeric",
                "label": "RDW-CV",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            # Platelet Parameters
            "PLT": {
                "code": "PLT",
                "type": "numeric",
                "label": "PLT",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": True,
                "critical": {"low": 20.0, "high": 1000.0}
            },
            "PDW": {
                "code": "PDW",
                "type": "numeric",
                "label": "PDW",
                "unit": "fL",
                "decimals": 2,
                "required": False
            },
            "MPV": {
                "code": "MPV",
                "type": "numeric",
                "label": "MPV",
                "unit": "fL",
                "decimals": 2,
                "required": False
            },
            "P_LCR": {
                "code": "P_LCR",
                "type": "numeric",
                "label": "P-LCR",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            "PCT": {
                "code": "PCT",
                "type": "numeric",
                "label": "PCT",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            # Absolute Differential Counts
            "NEUT#": {
                "code": "NEUT#",
                "type": "numeric",
                "label": "Neut#",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * NEUT% / 100"
            },
            "LYMPH#": {
                "code": "LYMPH#",
                "type": "numeric",
                "label": "Lymph#",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * LYMPH% / 100"
            },
            "MONO#": {
                "code": "MONO#",
                "type": "numeric",
                "label": "Mono#",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * MONO% / 100"
            },
            "EO#": {
                "code": "EO#",
                "type": "numeric",
                "label": "Eos#",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * EO% / 100"
            },
            "BASO#": {
                "code": "BASO#",
                "type": "numeric",
                "label": "Baso#",
                "unit": "x10⁹/L",
                "decimals": 2,
                "required": False,
                "calculated": True,
                "formula": "WBC * BASO% / 100"
            },
            # Differential Percentages
            "NEUT%": {
                "code": "NEUT%",
                "type": "numeric",
                "label": "Neut%",
                "unit": "%",
                "decimals": 2,
                "required": True
            },
            "LYMPH%": {
                "code": "LYMPH%",
                "type": "numeric",
                "label": "Lymph%",
                "unit": "%",
                "decimals": 2,
                "required": True
            },
            "MONO%": {
                "code": "MONO%",
                "type": "numeric",
                "label": "Mono%",
                "unit": "%",
                "decimals": 2,
                "required": True
            },
            "EO%": {
                "code": "EO%",
                "type": "numeric",
                "label": "Eos%",
                "unit": "%",
                "decimals": 2,
                "required": False
            },
            "BASO%": {
                "code": "BASO%",
                "type": "numeric",
                "label": "Baso%",
                "unit": "%",
                "decimals": 2,
                "required": False
            }
        },
        "calculated": [
            {"target_code": "MCH", "formula": "HGB * 1000 / RBC", "deps": ["HGB", "RBC"]},
            {"target_code": "MCHC", "formula": "HGB * 100 / HCT", "deps": ["HGB", "HCT"]},
            {"target_code": "NEUT#", "formula": "WBC * NEUT% / 100", "deps": ["WBC", "NEUT%"]},
            {"target_code": "LYMPH#", "formula": "WBC * LYMPH% / 100", "deps": ["WBC", "LYMPH%"]},
            {"target_code": "MONO#", "formula": "WBC * MONO% / 100", "deps": ["WBC", "MONO%"]},
            {"target_code": "EO#", "formula": "WBC * EO% / 100", "deps": ["WBC", "EO%"]},
            {"target_code": "BASO#", "formula": "WBC * BASO% / 100", "deps": ["WBC", "BASO%"]}
        ]
    }
    
    if existing:
        existing.discipline = "HEMATOLOGY"
        existing.status = "PUBLISHED"
        
        version = LabTemplateVersion(
            template_id=existing.id,
            version=new_version,
            status="PUBLISHED",
            schema_json=schema,
            change_note=f"FBC template v{new_version} - Exact Ghana parameters",
            created_by_id=admin_user_id
        )
        db.add(version)
        existing.current_version = new_version
        print(f"Updated to version {new_version}")
    else:
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
            change_note="Initial FBC template - Ghana standard",
            created_by_id=admin_user_id
        )
        db.add(version)
        existing = tmpl
    
    db.flush()
    return existing


def create_fbc_reference_ranges(db: Session):
    """Create reference ranges for FBC parameters."""
    print("Creating FBC reference ranges...")
    
    ranges = []
    
    # WBC - Adult
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.0"), "high": Decimal("10.0"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10⁹/L"
    })
    # WBC - Children (1-17 years)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 365, "age_max_days": 6569,
        "low": Decimal("5.0"), "high": Decimal("15.0"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10⁹/L"
    })
    # WBC - Infant (1-12 months)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 30, "age_max_days": 364,
        "low": Decimal("6.0"), "high": Decimal("17.5"),
        "critical_low": Decimal("2.0"), "critical_high": Decimal("30.0"), "unit": "x10⁹/L"
    })
    # WBC - Neonate (0-28 days)
    ranges.append({
        "field_code": "WBC", "sex": "ANY", "age_min_days": 0, "age_max_days": 29,
        "low": Decimal("9.0"), "high": Decimal("30.0"),
        "critical_low": Decimal("5.0"), "critical_high": Decimal("40.0"), "unit": "x10⁹/L"
    })
    
    # RBC - Male Adult
    ranges.append({
        "field_code": "RBC", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.7"), "high": Decimal("6.1"),
        "critical_low": Decimal("3.0"), "critical_high": Decimal("8.0"), "unit": "x10¹²/L"
    })
    # RBC - Female Adult
    ranges.append({
        "field_code": "RBC", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("4.2"), "high": Decimal("5.4"),
        "critical_low": Decimal("3.0"), "critical_high": Decimal("8.0"), "unit": "x10¹²/L"
    })
    # RBC - Child/Adolescent
    ranges.append({
        "field_code": "RBC", "sex": "ANY", "age_min_days": 0, "age_max_days": 6569,
        "low": Decimal("4.0"), "high": Decimal("5.5"), "unit": "x10¹²/L"
    })
    
    # HGB - Male Adult
    ranges.append({
        "field_code": "HGB", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("13.5"), "high": Decimal("17.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # HGB - Female Adult
    ranges.append({
        "field_code": "HGB", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("12.0"), "high": Decimal("15.5"),
        "critical_low": Decimal("7.0"), "critical_high": Decimal("20.0"), "unit": "g/dL"
    })
    # HGB - Child
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 366, "age_max_days": 6569,
        "low": Decimal("11.5"), "high": Decimal("15.0"), "unit": "g/dL"
    })
    # HGB - Infant
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 30, "age_max_days": 365,
        "low": Decimal("9.5"), "high": Decimal("13.0"), "unit": "g/dL"
    })
    # HGB - Neonate
    ranges.append({
        "field_code": "HGB", "sex": "ANY", "age_min_days": 0, "age_max_days": 29,
        "low": Decimal("14.5"), "high": Decimal("22.5"), "unit": "g/dL"
    })
    
    # HCT - Male Adult
    ranges.append({
        "field_code": "HCT", "sex": "M", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("41"), "high": Decimal("53"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    # HCT - Female Adult
    ranges.append({
        "field_code": "HCT", "sex": "F", "age_min_days": 6570, "age_max_days": 25550,
        "low": Decimal("36"), "high": Decimal("46"),
        "critical_low": Decimal("20"), "critical_high": Decimal("60"), "unit": "%"
    })
    # HCT - Child
    ranges.append({
        "field_code": "HCT", "sex": "ANY", "age_min_days": 0, "age_max_days": 6569,
        "low": Decimal("32"), "high": Decimal("50"), "unit": "%"
    })
    
    # RBC Indices
    ranges.append({"field_code": "MCV", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("80"), "high": Decimal("100"), "unit": "fL"})
    ranges.append({"field_code": "MCH", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("27"), "high": Decimal("33"), "unit": "pg"})
    ranges.append({"field_code": "MCHC", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("32"), "high": Decimal("36"), "unit": "g/dL"})
    ranges.append({"field_code": "RDW_SD", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("37"), "high": Decimal("54"), "unit": "fL"})
    ranges.append({"field_code": "RDW_CV", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("11.5"), "high": Decimal("14.5"), "unit": "%"})
    
    # Platelet Parameters
    ranges.append({
        "field_code": "PLT", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("150"), "high": Decimal("400"),
        "critical_low": Decimal("20"), "critical_high": Decimal("1000"), "unit": "x10⁹/L"
    })
    ranges.append({"field_code": "PDW", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("9"), "high": Decimal("17"), "unit": "fL"})
    ranges.append({"field_code": "MPV", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("7"), "high": Decimal("12"), "unit": "fL"})
    ranges.append({"field_code": "P_LCR", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("13"), "high": Decimal("43"), "unit": "%"})
    ranges.append({"field_code": "PCT", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.10"), "high": Decimal("0.28"), "unit": "%"})
    
    # Absolute Differential Counts
    ranges.append({"field_code": "NEUT#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("2.0"), "high": Decimal("7.5"), "unit": "x10⁹/L"})
    ranges.append({"field_code": "LYMPH#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("1.0"), "high": Decimal("3.5"), "unit": "x10⁹/L"})
    ranges.append({"field_code": "MONO#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.2"), "high": Decimal("0.8"), "unit": "x10⁹/L"})
    ranges.append({"field_code": "EO#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0.02"), "high": Decimal("0.5"), "unit": "x10⁹/L"})
    ranges.append({"field_code": "BASO#", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("0.1"), "unit": "x10⁹/L"})
    
    # Differential Percentages
    ranges.append({"field_code": "NEUT%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("40"), "high": Decimal("75"), "unit": "%"})
    ranges.append({"field_code": "LYMPH%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("20"), "high": Decimal("45"), "unit": "%"})
    ranges.append({"field_code": "MONO%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("2"), "high": Decimal("10"), "unit": "%"})
    ranges.append({"field_code": "EO%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("1"), "high": Decimal("6"), "unit": "%"})
    ranges.append({"field_code": "BASO%", "sex": "ANY", "age_min_days": 0, "age_max_days": 25550,
        "low": Decimal("0"), "high": Decimal("1"), "unit": "%"})
    
    # Insert ranges
    count = 0
    for range_def in ranges:
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
            existing.low = range_def.get("low")
            existing.high = range_def.get("high")
            existing.critical_low = range_def.get("critical_low")
            existing.critical_high = range_def.get("critical_high")
            existing.unit = range_def.get("unit")
            count += 1
    
    db.commit()
    print(f"Created/updated {count} FBC reference ranges")
    return count


def link_fbc_to_catalog(db: Session, template_id):
    """Link FBC template to catalog."""
    print("Linking FBC to catalog...")
    
    fbc_test = db.query(LabTest).filter(LabTest.test_code == "FBC").first()
    if fbc_test:
        print(f"Found FBC in catalog: {fbc_test.test_name}")
    else:
        fbc_test = LabTest(
            test_name="Full Blood Count (FBC)",
            test_code="FBC",
            test_category="Haematology",
            discipline="HEMATOLOGY",
            specimen_type="EDTA Whole Blood",
            is_active=True,
            nhis_code="FBC001",
            description="Complete blood count"
        )
        db.add(fbc_test)
        print("Created FBC in catalog")


def seed_fbc():
    """Main function."""
    print("=" * 60)
    print("FBC TEMPLATE SEEDER - GHANA STANDARD")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = db.query(User).first()
        if not admin_user:
            print("ERROR: No admin user found")
            return
        
        admin_user_id = admin_user.id
        print(f"Using admin: {admin_user.username}")
        
        # Create template
        template = create_fbc_template(db, admin_user_id)
        
        # Create reference ranges
        ranges_count = create_fbc_reference_ranges(db)
        
        # Link to catalog
        link_fbc_to_catalog(db, template.id)
        
        print("=" * 60)
        print(f"✅ FBC Template: {template.name}")
        print(f"✅ Parameters: 26 fields")
        print(f"✅ Reference Ranges: {ranges_count}")
        print(f"✅ NHIS Code: FBC001")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_fbc()
