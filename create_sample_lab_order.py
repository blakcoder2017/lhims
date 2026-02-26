#!/usr/bin/env python3
"""
Create a sample lab order for testing template-driven result entry.
Run this script to create a sample CBC lab order that uses the template.
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


def create_sample_lab_order():
    """Create a sample lab order for testing."""
    print("Creating sample lab order...")
    
    db = SessionLocal()
    try:
        # Get admin user (who will be the ordering doctor)
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("ERROR: Admin user not found")
            return
        
        # Get or create a test patient
        patient = db.query(Patient).first()
        if not patient:
            print("No patient found. Creating a test patient...")
            patient = Patient(
                first_name="John",
                last_name="Doe",
                patient_number="PTT001",
                gender="M",
                date_of_birth=datetime(1985, 5, 15),
                phone_number="233240000001",
                address="Test Address"
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            print(f"Created test patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
        
        # Get CBC lab test (which now has a template linked)
        cbc_test = db.query(LabTest).filter(LabTest.test_code == "CBC").first()
        if not cbc_test:
            print("ERROR: CBC lab test not found in catalog")
            return
        
        print(f"Found CBC test: {cbc_test.test_name}")
        print(f"  Template ID: {cbc_test.template_id}")
        
        # Create a sample lab order
        lab_order = LabOrder(
            patient_id=patient.id,
            ordered_by_id=admin_user.id,
            test_name=cbc_test.test_name,
            test_code=cbc_test.test_code,
            template_id=cbc_test.template_id,
            template_version_used=cbc_test.template_version,
            priority="routine",
            status=OrderStatus.PENDING,
            is_walk_in=True,
            checked_in_by_id=admin_user.id
        )
        
        db.add(lab_order)
        db.commit()
        db.refresh(lab_order)
        
        print(f"\n{'='*60}")
        print("SAMPLE LAB ORDER CREATED!")
        print(f"{'='*60}")
        print(f"Order ID: {lab_order.id}")
        print(f"Patient: {patient.first_name} {patient.last_name}")
        print(f"Test: {lab_order.test_name} ({lab_order.test_code})")
        print(f"Template: {lab_order.template_id}")
        print(f"Status: {lab_order.status.value}")
        print(f"\nTo test result entry, visit:")
        print(f"  http://localhost:8000/lab/orders/{lab_order.id}")
        print(f"\nOr use the lab dashboard at:")
        print(f"  http://localhost:8000/lab")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_lab_order()
