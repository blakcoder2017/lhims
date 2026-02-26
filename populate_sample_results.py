#!/usr/bin/env python3
"""
Populate sample lab orders with test results to demonstrate the enhanced display.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.core.config import settings
from app.models.encounter_models import LabOrder, OrderStatus
from app.models.user_models import User
from app.services.lab_result_validation import compute_flags
from app.crud import lab_template_crud

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def populate_sample_results():
    """Populate sample lab orders with test data."""
    print("Populating sample lab orders with results...")
    
    db = SessionLocal()
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        # Get CBC lab order (Order #46)
        lab_order = db.query(LabOrder).filter(LabOrder.id == 46).first()
        if not lab_order:
            print("Lab order #46 not found")
            return
        
        # Sample CBC results with mix of normal and abnormal values
        result_json = {
            "hb": 8.5,  # LOW - normal is 13.0-17.5
            "hct": 28.0,  # LOW
            "rbc_count": 4.2,
            "mcv": 72.0,
            "mch": 24.0,
            "mchc": 32.5,
            "wbc_count": 18.5,  # HIGH - normal is 4.0-11.0
            "neutrophils": 65.0,
            "lymphocytes": 25.0,
            "monocytes": 8.0,
            "eosinophils": 1.5,
            "basophils": 0.5,
            "platelet_count": 180,
            "comment": "Patient shows mild anemia with elevated WBC count suggesting possible infection. Recommend follow-up."
        }
        
        # Get reference ranges and compute flags
        ref_ranges = {}
        pub = lab_template_crud.get_published_version(db, lab_order.template_id)
        
        if pub:
            schema_json = pub.schema_json
            # Get reference ranges for each field
            for fc, fld in (schema_json.get("fields") or {}).items():
                if fld.get("type") == "numeric":
                    rr = lab_template_crud.get_reference_range(db, fc, "M", 15000)  # Adult male
                    if rr and (rr.low is not None or rr.high is not None):
                        ref_ranges[fc] = {"low": float(rr.low or 0), "high": float(rr.high or 0)}
        
        # Compute flags
        from app.services.lab_result_validation import compute_flags, get_flags_dict
        flags = compute_flags(pub.schema_json if pub else {}, result_json, {}, ref_ranges)
        
        # Update lab order
        lab_order.result_json = result_json
        lab_order.flags_json = get_flags_dict(flags)
        lab_order.result_status = "SUBMITTED"
        lab_order.result_entered_by_id = admin_user.id
        lab_order.result_entered_at = datetime.now()
        
        db.commit()
        
        print(f"\n{'='*60}")
        print("SAMPLE RESULTS POPULATED!")
        print(f"{'='*60}")
        print(f"Order #46 - Complete Blood Count (CBC)")
        print(f"\nResults entered:")
        print(f"  • Hemoglobin (Hb): 8.5 g/dL - ⚠️ LOW")
        print(f"  • Hematocrit (Hct): 28.0% - ⚠️ LOW")
        print(f"  • WBC Count: 18.5 x10^9/L - 🔴 HIGH (Critical)")
        print(f"  • Platelet Count: 180 x10^9/L - ✅ Normal")
        print(f"\nView the result at:")
        print(f"  http://localhost:8000/lab/orders/46")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    populate_sample_results()
