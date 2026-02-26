#!/usr/bin/env python3
"""
Create 5 random lab orders with random patients and random tests.
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.lab_catalog_models import LabTest
from app.models.encounter_models import LabOrder, OrderStatus
from app.models.user_models import User
from app.models.patient_models import Patient

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Sample first names and last names for random patient generation
FIRST_NAMES = [
    "Kwame", "Akua", "Kofi", "Adjoa", "Yaw", "Abena", "Kwesi", "Akosua",
    "Emmanuel", "Grace", "David", "Sarah", "Michael", "Elizabeth", "Joseph", "Mary",
    "Daniel", "Rebecca", "Samuel", "Ruth", "John", "Hannah", "James", "Comfort",
    "Peter", "Mercy", "Paul", "Joyce", "Stephen", "Patricia"
]

LAST_NAMES = [
    "Osei", "Agyeman", "Mensah", "Owusu", "Kumah", "Boateng", "Adjei", "Asante",
    "Darko", "Opong", "Arthur", "Ampofo", "Okoe", "Tetteh", "Nkyekyer", "Amoah",
    "Baba", "Ofori", "Agyapong", "Nkrumah", "Acquah", "Osei", "Ayew", "Asiedu"
]

GENDERS = ["Male", "Female"]
PAYMENT_MECHANISMS = ["cash", "nhis", "private_insurance"]


def get_or_create_patient(db: Session):
    """Get a random patient or create a new one if none exist."""
    # Try to get an existing random patient first
    existing_patients = db.query(Patient).all()
    
    if existing_patients:
        # Randomly select an existing patient or create a new one (50% chance)
        if random.random() > 0.5:
            return random.choice(existing_patients)
    
    # Create a new random patient
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    gender = random.choice(GENDERS)
    
    # Generate random date of birth (between 1 and 80 years old)
    age_days = random.randint(365, 80 * 365)
    dob = datetime.now().date() - timedelta(days=age_days)
    
    # Generate random phone number (Ghana format)
    phone = f"23324{random.randint(1000000, 9999999)}"
    
    # Generate patient number
    patient_count = db.query(Patient).count()
    patient_number = f"DGM{str(patient_count + 1).zfill(5)}"
    
    # Random payment mechanism
    payment = random.choice(PAYMENT_MECHANISMS)
    
    patient = Patient(
        first_name=first_name,
        last_name=last_name,
        patient_number=patient_number,
        gender=gender,
        date_of_birth=dob,
        phone_number=phone,
        address=f"House {random.randint(1, 500)}, Street {random.randint(1, 100)}",
        payment_mechanism=payment
    )
    
    db.add(patient)
    db.flush()
    return patient


def get_random_lab_test(db: Session):
    """Get a random active lab test from the database."""
    tests = db.query(LabTest).filter(LabTest.is_active == True).all()
    
    if not tests:
        print("ERROR: No active lab tests found in the catalog")
        return None
    
    return random.choice(tests)


def create_random_lab_order(db: Session, admin_user: User):
    """Create a single random lab order."""
    # Get or create a random patient
    patient = get_or_create_patient(db)
    
    # Get a random lab test
    lab_test = get_random_lab_test(db)
    
    if not lab_test:
        return None
    
    # Random priority
    priorities = ["routine", "urgent", "stat"]
    priority = random.choice(priorities)
    
    # Random status (weighted towards PENDING)
    status_weights = [0.7, 0.2, 0.1]  # PENDING, IN_PROGRESS, COMPLETED
    status = random.choices(
        [OrderStatus.PENDING, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED],
        weights=status_weights
    )[0]
    
    # Create the lab order
    lab_order = LabOrder(
        patient_id=patient.id,
        ordered_by_id=admin_user.id,
        test_name=lab_test.test_name,
        test_code=lab_test.test_code,
        lab_test_id=lab_test.id,
        template_id=lab_test.template_id,
        template_version_used=lab_test.template_version,
        priority=priority,
        status=status,
        is_walk_in=random.random() > 0.3,  # 70% walk-in, 30% from encounter
        checked_in_by_id=admin_user.id if status != OrderStatus.PENDING else None,
        result_entered_by_id=admin_user.id if status == OrderStatus.COMPLETED else None,
        result_entered_at=datetime.now() - timedelta(hours=random.randint(1, 12)) if status == OrderStatus.COMPLETED else None,
        verified_by_id=admin_user.id if status == OrderStatus.COMPLETED else None,
        verified_at=datetime.now() - timedelta(hours=random.randint(0, 6)) if status == OrderStatus.COMPLETED else None,
        completed_at=datetime.now() - timedelta(hours=random.randint(0, 3)) if status == OrderStatus.COMPLETED else None
    )
    
    db.add(lab_order)
    db.flush()
    
    return lab_order, patient, lab_test


def create_five_random_lab_orders():
    """Create 5 random lab orders."""
    print("Creating 5 random lab orders...")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("ERROR: Admin user not found. Please run seed_admin.py first.")
            return
        
        print(f"Admin user: {admin_user.username}")
        print()
        
        # Get all available patients
        patients = db.query(Patient).all()
        print(f"Found {len(patients)} existing patients in database")
        
        # Get all available tests
        tests = db.query(LabTest).filter(LabTest.is_active == True).all()
        print(f"Found {len(tests)} active lab tests in catalog")
        print()
        
        # Create 5 random lab orders
        created_orders = []
        
        for i in range(5):
            print(f"Creating order {i + 1}...")
            
            lab_order, patient, lab_test = create_random_lab_order(db, admin_user)
            
            if lab_order:
                created_orders.append(lab_order)
                print(f"  ✓ Patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
                print(f"  ✓ Test: {lab_test.test_name} ({lab_test.test_code})")
                print(f"  ✓ Priority: {lab_order.priority}")
                print(f"  ✓ Status: {lab_order.status.value}")
                print()
        
        # Commit all changes
        db.commit()
        
        print("=" * 60)
        print("5 RANDOM LAB ORDERS CREATED SUCCESSFULLY!")
        print("=" * 60)
        
        # Print summary
        print("\nSUMMARY:")
        print("-" * 40)
        
        for i, order in enumerate(created_orders, 1):
            patient = db.query(Patient).filter(Patient.id == order.patient_id).first()
            test = db.query(LabTest).filter(LabTest.test_code == order.test_code).first()
            print(f"\nOrder {i}:")
            print(f"  Order ID: {order.id}")
            print(f"  Patient: {patient.first_name} {patient.last_name} ({patient.patient_number})")
            print(f"  Test: {test.test_name} ({test.test_code})")
            print(f"  Priority: {order.priority}")
            print(f"  Status: {order.status.value}")
        
        print("\n" + "=" * 60)
        print("To view these orders, visit the lab dashboard:")
        print("  http://localhost:8000/lab")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_five_random_lab_orders()
