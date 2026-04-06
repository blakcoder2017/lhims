#!/usr/bin/env python3
"""
Fix FBC Template - Definitive parameter set, order, and reference ranges.

Sets the Full Blood Count template to exactly 23 parameters with correct order
and reference ranges. Removes the duplicate standalone RDW field.

Usage:
    python3 update_fbc_parameter_order.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['DEBUG'] = 'false'

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.models.lab_template_models import LabTemplate, LabTemplateVersion

# ---------------------------------------------------------------------------
# Definitive 23-parameter FBC definition (exact order, no duplicates)
# ---------------------------------------------------------------------------

PARAMETERS = [
    # code,      label,           unit,           ref_low,  ref_high, decimals
    ("WBC",      "WBC (WBC)",     "×10⁹/L",       4.0,      10.0,     2),
    ("NEU%",     "NEU% (NEU%)",   "%",             40.0,     75.0,     2),
    ("LYM%",     "LYM% (LYM%)",  "%",             20.0,     40.0,     2),
    ("MON%",     "MON% (MON%)",  "%",              2.0,      10.0,     2),
    ("EOS%",     "EOS% (EOS%)",  "%",              1.0,       6.0,     2),
    ("BASO%",    "BASO% (BASO%)", "%",             0.0,       1.0,     2),
    ("NEU#",     "NEU# (NEU#)",  "×10⁹/L",        2.0,       7.0,     2),
    ("LYM#",     "LYM# (LYM#)",  "×10⁹/L",        1.0,       3.0,     2),
    ("MON#",     "MON# (MON#)",  "×10⁹/L",        0.2,       0.8,     2),
    ("EOS#",     "EOS# (EOS#)",  "×10⁹/L",        0.02,      0.5,     2),
    ("BASO#",    "BASO# (BASO%)", "×10⁹/L",       0.0,       0.1,     2),
    ("RBC",      "RBC (RBC)",    "×10¹²/L",        4.0,       5.5,     2),
    ("HGB",      "HGB (HGB)",    "g/dL",          11.5,      15.0,     2),
    ("HCT",      "HCT (HCT)",    "%",             32.0,      50.0,     2),
    ("MCV",      "MCV (MCV)",    "fL",            80.0,     100.0,     2),
    ("MCH",      "MCH (MCH)",    "pg",            27.0,      33.0,     2),
    ("MCHC",     "MCHC (MCHC)",  "g/dL",          32.0,      36.0,     2),
    ("RDW_CV",   "RDW_CV (RDW_CV)", "%",          11.5,      14.5,     2),
    ("RDW_SD",   "RDW_SD (RDW_SD)", "fL",         37.0,      54.0,     2),
    ("PLT",      "PLT (PLT)",    "×10⁹/L",       150.0,     400.0,     2),
    ("MPV",      "MPV (MPV)",    "fL",             7.0,      12.0,     2),
    ("PDW",      "PDW (PDW)",    "fL",             9.0,      17.0,     2),
    ("PCT",      "PCT (PCT)",    "%",              0.1,       0.28,    2),
]


def build_schema():
    fields = {}
    for code, label, unit, ref_low, ref_high, decimals in PARAMETERS:
        fields[code] = {
            "code": code,
            "type": "numeric",
            "label": label,
            "unit": unit,
            "decimals": decimals,
            "required": True,
            "reference_range": {
                "default": {"low": ref_low, "high": ref_high}
            }
        }

    layout = {
        "sections": [
            {
                "id": "sec_main",
                "title": "Full Blood Count Results",
                "rows": [
                    {"columns": [{"items": [code], "width": 12}]}
                    for code, *_ in PARAMETERS
                ]
            }
        ]
    }

    return {
        "meta": {
            "name": "Full Blood Count (FBC)",
            "discipline": "HEMATOLOGY",
            "version": 1,
            "description": "Complete blood count with automated analyser",
            "specimen": "Whole Blood (EDTA)",
            "method": "Automated Haematology Analyzer",
            "reporting_units": "SI units"
        },
        "layout": layout,
        "fields": fields
    }


def fix_fbc_template():
    db = SessionLocal()
    try:
        template = db.query(LabTemplate).filter(
            LabTemplate.name.ilike('%Full Blood Count%')
        ).first()

        if not template:
            print("FBC template not found!")
            return

        print(f"Found template: {template.name} (ID: {template.id})")

        version = (
            db.query(LabTemplateVersion)
            .filter(
                LabTemplateVersion.template_id == template.id,
                LabTemplateVersion.status == "PUBLISHED"
            )
            .order_by(LabTemplateVersion.version.desc())
            .first()
        )

        if not version:
            version = (
                db.query(LabTemplateVersion)
                .filter(LabTemplateVersion.template_id == template.id)
                .order_by(LabTemplateVersion.version.desc())
                .first()
            )

        if not version:
            print("No template version found!")
            return

        print(f"Updating version {version.version} (status: {version.status})")

        new_schema = build_schema()
        version.schema_json = new_schema
        template.current_version = version.version

        db.commit()

        print(f"\nFBC template fixed — {len(PARAMETERS)} parameters:")
        for i, (code, label, unit, ref_low, ref_high, _) in enumerate(PARAMETERS, 1):
            print(f"  {i:2}. {label:<22} {ref_low} - {ref_high} {unit}")

        print("\nDone. Refresh the lab template preview to verify.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fix_fbc_template()
