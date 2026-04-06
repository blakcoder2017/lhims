#!/usr/bin/env python3
"""
Female Infertility Profile Template Seeder for Ghana LHIMS
============================================================
Creates the lab template for Female Infertility Profile with parameters:
- LH (Luteinizing Hormone)
- FSH (Follicle Stimulating Hormone)
- PROL (Prolactin)
- ESTRADIOL (E2)
- PROG (Progesterone)

Usage:
    python3 seed_female_infertility_profile.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.lab_template_models import (
    LabTemplate, LabTemplateVersion
)

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_female_infertility_template(db: Session, admin_user_id: int):
    """Create Female Infertility Profile template."""
    print("Creating Female Infertility Profile template...")
    
    # Check if exists
    existing = db.query(LabTemplate).filter(LabTemplate.name == "Female Infertility Profile").first()
    if existing:
        db.query(LabTemplateVersion).filter(LabTemplateVersion.template_id == existing.id).delete()
        db.delete(existing)
        print("  Removed existing template")
    
    # Template schema with exact phase-specific reference ranges as provided
    schema = {
        "meta": {
            "name": "Female Infertility Profile",
            "discipline": "ENDOCRINOLOGY",
            "description": "Female infertility hormone panel - FSH, LH, Prolactin, Estradiol, Progesterone"
        },
        "layout": {
            "sections": [
                {
                    "id": "sec_hormones",
                    "title": "Hormone Levels",
                    "rows": [
                        {"columns": [{"items": ["fsh", "lh", "prolactin"], "width": 4}]},
                        {"columns": [{"items": ["estradiol", "progesterone"], "width": 6}]}
                    ]
                }
            ]
        },
        "fields": {
            "lh": {
                "type": "numeric",
                "label": "LH",
                "code": "lh",
                "unit": "",
                "decimals": 1,
                "normal_range": "",
                "description": "Luteinizing Hormone",
                "reference_ranges": [
                    {"phase": "Follicular", "min": 0.8, "max": 10.5, "unit": "mIU/ml"},
                    {"phase": "Midcycle", "min": 18.4, "max": 61.2, "unit": "mIU/ml"},
                    {"phase": "Luteal", "min": 0.8, "max": 10.5, "unit": "mIU/ml"},
                    {"phase": "P.Menopausal", "min": 8.2, "max": 40.8, "unit": "mIU/ml"},
                    {"phase": "Male", "min": 0.7, "max": 7.4, "unit": "mIU/ml"}
                ]
            },
            "fsh": {
                "type": "numeric",
                "label": "FSH",
                "code": "fsh",
                "unit": "",
                "decimals": 1,
                "normal_range": "",
                "description": "Follicle Stimulating Hormone",
                "reference_ranges": [
                    {"phase": "Follicular", "min": 2.0, "max": 12.0, "unit": "IU/I"},
                    {"phase": "Midcycle", "min": 8.0, "max": 120.0, "unit": "IU/I"},
                    {"phase": "Luteal", "min": 2.0, "max": 12.0, "unit": "IU/I"},
                    {"phase": "Menopausal", "min": 35.0, "max": 150.0, "unit": "IU/I"},
                    {"phase": "Male", "min": 1.0, "max": 14.0, "unit": "IU/I"}
                ]
            },
            "prolactin": {
                "type": "numeric",
                "label": "PROL",
                "code": "prolactin",
                "unit": "",
                "decimals": 0,
                "normal_range": "",
                "description": "Prolactin",
                "reference_ranges": [
                    {"phase": "FEMALE", "min": 3.8, "max": 23.2, "unit": "ng/ml"},
                    {"phase": "pregnancy(THIRD TRIM)", "min": 95.0, "max": 473.0, "unit": "ng/ml"},
                    {"phase": "Male", "min": 3.0, "max": 14.5, "unit": "ng/ml"}
                ]
            },
            "estradiol": {
                "type": "numeric",
                "label": "Estradiol (E2)",
                "code": "estradiol",
                "unit": "",
                "decimals": 0,
                "normal_range": "",
                "description": "Estradiol",
                "reference_ranges": [
                    {"phase": "Follicular", "min": 30, "max": 100, "unit": "pg/ml"},
                    {"phase": "Midcycle", "min": 100, "max": 400, "unit": "pg/ml"},
                    {"phase": "Luteal", "min": 60, "max": 150, "unit": "pg/ml"},
                    {"phase": "Menopausal", "min": 0, "max": 30, "unit": "pg/ml"},
                    {"phase": "Male", "min": 0, "max": 60, "unit": "pg/ml"}
                ]
            },
            "progesterone": {
                "type": "numeric",
                "label": "PROG",
                "code": "progesterone",
                "unit": "",
                "decimals": 1,
                "normal_range": "",
                "description": "Progesterone",
                "reference_ranges": [
                    {"phase": "Follicular", "min": 0.1, "max": 1.5, "unit": "ng/ml"},
                    {"phase": "Luteal", "min": 2.0, "max": 25.0, "unit": "ng/ml"},
                    {"phase": "P.Menopause", "min": 0.1, "max": 1.0, "unit": "ng/ml"},
                    {"phase": "Male", "min": 0.0, "max": 1.0, "unit": "ng/ml"}
                ]
            }
        },
        "rules": {
            "visibility": [],
            "requiredIf": []
        },
        "calculated": []
    }
    
    tmpl = LabTemplate(
        name="Female Infertility Profile",
        discipline="ENDOCRINOLOGY",
        status="DRAFT",
        created_by_id=admin_user_id
    )
    db.add(tmpl)
    db.flush()
    
    version = LabTemplateVersion(
        template_id=tmpl.id,
        version=1,
        status="PUBLISHED",
        schema_json=schema,
        change_note="Initial Female Infertility Profile template - LH, FSH, PROL, Estradiol, PROG with phase-specific ranges",
        created_by_id=admin_user_id
    )
    db.add(version)
    tmpl.current_version = 1
    tmpl.status = "PUBLISHED"
    
    db.commit()
    print(f"Created Female Infertility Profile template (v1)")
    
    # Link template to lab test catalog
    from app.models.lab_catalog_models import LabTest
    test = db.query(LabTest).filter(LabTest.test_code == "FEMALE_INFERTILITY").first()
    if test:
        old_template_id = test.template_id
        test.template_id = tmpl.id
        test.template_version = 1
        db.commit()
        print(f"  Linked to lab_test_catalog: {test.test_code}")
        if old_template_id:
            print(f"  Old Template ID: {old_template_id}")
    else:
        print("  WARNING: FEMALE_INFERTILITY test not found in lab_test_catalog")
    
    return tmpl


def main():
    """Main seeding function."""
    print("=" * 70)
    print("FEMALE INFERTILITY PROFILE TEMPLATE SEEDER")
    print("Ghana LHIMS - Hormone Panel Template")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Get admin user (first user with admin role)
        from app.models.user_models import User
        admin_user = db.query(User).order_by(User.id).first()
        
        if not admin_user:
            print("ERROR: No admin user found. Please run seed_admin.py first.")
            return
        
        admin_user_id = admin_user.id
        print(f"Using admin user: {admin_user.email}")
        
        # Create the template
        template = create_female_infertility_template(db, admin_user_id)
        
        print("\n" + "=" * 70)
        print("SUCCESS: Female Infertility Profile template created!")
        print("=" * 70)
        print(f"\nTemplate Details:")
        print(f"  - Name: {template.name}")
        print(f"  - Discipline: {template.discipline}")
        print(f"  - Status: {template.status}")
        print(f"  - Version: {template.current_version}")
        print(f"\nParameters with exact reference ranges:")
        print(f"  - LH (mIU/ml): Follicular 0.8-10.5, Midcycle 18.4-61.2, Luteal 0.8-10.5, P.Menopausal 8.2-40.8, Male 0.7-7.4")
        print(f"  - FSH (IU/I): Follicular 2.0-12.0, Midcycle 8.0-120.0, Luteal 2.0-12.0, Menopausal 35-150, Male 1.0-14.0")
        print(f"  - PROL (ng/ml): FEMALE 3.8-23.2, pregnancy(THIRD TRIM) 95-473, Male 3.0-14.5")
        print(f"  - Estradiol (E2) (pg/ml): Follicular 30-100, Midcycle 100-400, Luteal 60-150, Menopausal 0-30, Male 0-60")
        print(f"  - PROG (ng/ml): Follicular 0.1-1.5, Luteal 2-25, P.Menopause 0.1-1.0, Male 0-1.0")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
