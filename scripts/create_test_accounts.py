#!/usr/bin/env python3
"""
Create Test Accounts for LHIMS UI Testing

This script creates comprehensive test accounts for all user roles
to support real-life scenario testing.
"""

import sys
import os
from datetime import datetime, date
from getpass import getpass

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import engine, get_db
from app.models.user_models import User, Role
from app.core.security import get_password_hash
from app.models.patient_models import Patient, PaymentMechanism
from app.models.scheduled_appointment_models import Appointment, AppointmentStatus, AppointmentType
from app.models.triage_models import TriageVitals
from app.models.encounter_models import Encounter, EncounterStatus
from app.models.billing_models import Invoice, InvoiceStatus, Charge, ChargeType
from decimal import Decimal

def create_test_roles(db: Session):
    """Create test roles if they don't exist."""
    roles_data = [
        {"name": "Admin", "description": "System Administrator"},
        {"name": "Doctor", "description": "Medical Doctor"},
        {"name": "Nurse", "description": "Registered Nurse"},
        {"name": "Front Office", "description": "Front Office Staff"},
        {"name": "Midwife", "description": "Midwife"},
        {"name": "Lab Technician", "description": "Laboratory Technician"},
        {"name": "Pharmacist", "description": "Pharmacist"},
    ]
    
    for role_data in roles_data:
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            role = Role(**role_data)
            db.add(role)
            print(f"✅ Created role: {role_data['name']}")
        else:
            print(f"✅ Role already exists: {role_data['name']}")
    
    db.commit()

def create_test_users(db: Session):
    """Create test users for all roles."""
    users_data = [
        {
            "username": "admin",
            "password": "Admin123",
            "email": "admin@lhims.com",
            "full_name": "System Administrator",
            "role_name": "Admin",
            "is_active": True
        },
        {
            "username": "doctor1",
            "password": "Doctor123",
            "email": "doctor1@lhims.com",
            "full_name": "Dr. Kwame Osei",
            "role_name": "Doctor",
            "is_active": True
        },
        {
            "username": "nurse1",
            "password": "Nurse123",
            "email": "nurse1@lhims.com",
            "full_name": "Grace Amponsah",
            "role_name": "Nurse",
            "is_active": True
        },
        {
            "username": "frontdesk1",
            "password": "Front123",
            "email": "frontdesk1@lhims.com",
            "full_name": "Ama Asante",
            "role_name": "Front Office",
            "is_active": True
        },
        {
            "username": "midwife1",
            "password": "Midwife123",
            "email": "midwife1@lhims.com",
            "full_name": "Comfort Boateng",
            "role_name": "Midwife",
            "is_active": True
        },
        {
            "username": "labtech1",
            "password": "Lab123",
            "email": "labtech1@lhims.com",
            "full_name": "Samuel Mensah",
            "role_name": "Lab Technician",
            "is_active": True
        },
        {
            "username": "pharm1",
            "password": "Pharm123",
            "email": "pharm1@lhims.com",
            "full_name": "Beatrice Owusu",
            "role_name": "Pharmacist",
            "is_active": True
        }
    ]
    
    for user_data in users_data:
        existing_user = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing_user:
            role = db.query(Role).filter(Role.name == user_data["role_name"]).first()
            if role:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role_id=role.id,
                    is_active=user_data["is_active"]
                )
                db.add(user)
                print(f"✅ Created user: {user_data['username']} ({user_data['role_name']})")
            else:
                print(f"❌ Role not found: {user_data['role_name']}")
        else:
            print(f"✅ User already exists: {user_data['username']}")
    
    db.commit()

def create_test_patients(db: Session):
    """Create test patients for testing scenarios."""
    patients_data = [
        {
            "first_name": "Ama",
            "last_name": "Mensah",
            "date_of_birth": date(1990, 5, 15),
            "gender": "Female",
            "phone_number": "0201234567",
            "address": "Accra, Ghana",
            "payment_mechanism": PaymentMechanism.NHIS,
            "nhis_number": "NHIS123456789"
        },
        {
            "first_name": "Kofi",
            "last_name": "Asante",
            "date_of_birth": date(1985, 8, 22),
            "gender": "Male",
            "phone_number": "0234567890",
            "address": "Kumasi, Ghana",
            "payment_mechanism": PaymentMechanism.CASH
        },
        {
            "first_name": "Adwoa",
            "last_name": "Osei",
            "date_of_birth": date(1995, 3, 10),
            "gender": "Female",
            "phone_number": "0245678901",
            "address": "Tema, Ghana",
            "payment_mechanism": PaymentMechanism.PRIVATE_INSURANCE,
            "insurance_provider": "Ghana Insurance Company",
            "insurance_policy_number": "POL987654321"
        },
        {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": date(1978, 12, 5),
            "gender": "Male",
            "phone_number": "0278901234",
            "address": "Takoradi, Ghana",
            "payment_mechanism": PaymentMechanism.CASH
        }
    ]
    
    for patient_data in patients_data:
        existing_patient = db.query(Patient).filter(
            Patient.first_name == patient_data["first_name"],
            Patient.last_name == patient_data["last_name"]
        ).first()
        
        if not existing_patient:
            patient = Patient(**patient_data)
            db.add(patient)
            print(f"✅ Created patient: {patient_data['first_name']} {patient_data['last_name']}")
        else:
            print(f"✅ Patient already exists: {patient_data['first_name']} {patient_data['last_name']}")
    
    db.commit()

def create_test_appointments(db: Session):
    """Create test appointments."""
    # Get test patients and users
    patient_ama = db.query(Patient).filter(Patient.first_name == "Ama", Patient.last_name == "Mensah").first()
    patient_kofi = db.query(Patient).filter(Patient.first_name == "Kofi", Patient.last_name == "Asante").first()
    doctor = db.query(User).filter(User.username == "doctor1").first()
    
    if patient_ama and doctor:
        existing_appointment = db.query(Appointment).filter(
            Appointment.patient_id == patient_ama.id,
            Appointment.scheduled_date >= datetime.now().date()
        ).first()
        
        if not existing_appointment:
            appointment = Appointment(
                patient_id=patient_ama.id,
                assigned_doctor_id=doctor.id,
                created_by_id=doctor.id,
                scheduled_date=datetime.now(),
                appointment_type="SCHEDULED",
                status=AppointmentStatus.SCHEDULED,
                department="General Practice",
                notes="Regular checkup"
            )
            db.add(appointment)
            print("✅ Created appointment for Ama Mensah")
        else:
            print("✅ Appointment already exists for Ama Mensah")
    
    if patient_kofi and doctor:
        existing_appointment = db.query(Appointment).filter(
            Appointment.patient_id == patient_kofi.id,
            Appointment.scheduled_date >= datetime.now().date()
        ).first()
        
        if not existing_appointment:
            appointment = Appointment(
                patient_id=patient_kofi.id,
                assigned_doctor_id=doctor.id,
                created_by_id=doctor.id,
                scheduled_date=datetime.now(),
                appointment_type="FOLLOW_UP",
                status=AppointmentStatus.SCHEDULED,
                department="General Practice",
                notes="Follow-up consultation"
            )
            db.add(appointment)
            print("✅ Created appointment for Kofi Asante")
        else:
            print("✅ Appointment already exists for Kofi Asante")
    
    db.commit()

def main():
    """Main function to create all test data."""
    print("🚀 Creating LHIMS Test Accounts and Data")
    print("=" * 50)
    
    try:
        # Create database session
        db = next(get_db())
        
        print("\n📋 Creating Test Roles...")
        create_test_roles(db)
        
        print("\n👥 Creating Test Users...")
        create_test_users(db)
        
        print("\n🏥 Creating Test Patients...")
        create_test_patients(db)
        
        print("\n📅 Creating Test Appointments...")
        create_test_appointments(db)
        
        print("\n" + "=" * 50)
        print("✅ Test data creation completed successfully!")
        print("\n🔑 Test Login Credentials:")
        print("-" * 30)
        print("Admin: admin / Admin123")
        print("Doctor: doctor1 / Doctor123")
        print("Nurse: nurse1 / Nurse123")
        print("Front Office: frontdesk1 / Front123")
        print("Midwife: midwife1 / Midwife123")
        print("Lab Tech: labtech1 / Lab123")
        print("Pharmacist: pharm1 / Pharm123")
        print("-" * 30)
        print("\n🌐 Access the application at: http://localhost:8000")
        print("\n📋 Follow the testing scenarios in UI_TESTING_SCENARIOS.md")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
