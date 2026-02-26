#!/usr/bin/env python3
"""
Create more sample lab orders for testing different templates.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.encounter_models import LabOrder, OrderStatus
from app.models.user_models import User
from app.models.patient_models import Patient

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_more_sample_orders():
    """Create more sample lab orders for testing."""
    print("Creating more sample lab orders...")
    
    db = SessionLocal()
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        
        # Get a patient
        patient = db.query(Patient).first()
        
        # Get lab tests that have templates
        tests = db.query(LabTest).filter(
            LabTest.template_id.isnot(None),
            LabTest.is_active == True
        ).all()
        
        print(f"Found {len(tests)} lab tests with templates")
        
        for test in tests:
            # Check if order already exists for this test
            existing = db.query(LabOrder).filter(
                LabOrder.test_code == test.test_code,
                LabOrder.status == OrderStatus.PENDING
            ).first()
            
            if existing:
                print(f"  Skipping {test.test_name} - order already exists (ID: {existing.id})")
                continue
            
            # Create lab order
            lab_order = LabOrder(
                patient_id=patient.id,
                ordered_by_id=admin_user.id,
                test_name=test.test_name,
                test_code=test.test_code,
                template_id=test.template_id,
                template_version_used=test.template_version,
                priority="routine",
                status=OrderStatus.PENDING,
                is_walk_in=True,
                checked_in_by_id=admin_user.id
            )
            
            db.add(lab_order)
            print(f"  Created order for: {test.test_name}")
        
        db.commit()
        
        print(f"\n{'='*60}")
        print("ALL SAMPLE LAB ORDERS CREATED!")
        print(f"{'='*60}")
        print("\nTo test result entry, visit the lab dashboard:")
        print("  http://localhost:8000/lab")
        print("\nThen click 'View/Enter Result' on any pending order")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_more_sample_orders()
