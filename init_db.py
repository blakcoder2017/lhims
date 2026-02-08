#!/usr/bin/env python3
"""Initialize the database with required tables and an admin user."""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they're registered
from app.models.user_models import User, Role
from app.models.patient_models import Patient
from app.models.department_models import Department
from app.models.ward_type_models import WardType
from app.models.bed_type_models import BedType
from app.models.hospital_settings_models import HospitalSettings
from app.models.disease_models import Disease
from app.models.service_pricing_models import ServicePricing
from app.models.shift_type_models import ShiftType
from app.models.insurance_provider_models import InsuranceProvider
from app.models.supplier_models import Supplier
from app.models.inventory_models import Medication
from app.models.lab_catalog_models import LabTest
from app.models.procedure_catalog_models import ProcedureCatalog
from app.db.database import Base

from app.core.config import settings

# Update the database URL to use SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_lhims.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def init_db():
    """Initialize the database with all tables and initial data."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    
    db = SessionLocal()
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user:
            print("Admin user already exists!")
            # Update password to ensure it matches
            admin_user.hashed_password = hash_password("Westafrica1")
            db.commit()
            print("Admin password updated!")
        else:
            # Create admin role
            admin_role = db.query(Role).filter(Role.name == "Admin").first()
            if not admin_role:
                admin_role = Role(name="Admin", description="Administrator with full access")
                db.add(admin_role)
                db.commit()
                db.refresh(admin_role)
                print(f"Created admin role with ID: {admin_role.id}")
            else:
                print(f"Admin role already exists with ID: {admin_role.id}")
            
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@lhims.com",
                full_name="System Administrator",
                hashed_password=hash_password("Westafrica1"),
                is_active=True,
                role_id=admin_role.id
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Created admin user with ID: {admin_user.id}")
        
        # Create other default roles
        default_roles = [
            ("Doctor", "Medical Doctor with clinical access"),
            ("Nurse", "Nursing staff with patient care access"),
            ("Pharmacist", "Pharmacy staff with medication management access"),
            ("LabTechnician", "Laboratory technician with lab test access"),
            ("Billing", "Billing staff with financial access"),
            ("Receptionist", "Front desk staff with patient registration access"),
        ]
        
        for role_name, description in default_roles:
            existing_role = db.query(Role).filter(Role.name == role_name).first()
            if not existing_role:
                role = Role(name=role_name, description=description)
                db.add(role)
                print(f"Created role: {role_name}")
        
        db.commit()
        
        # Create default hospital settings
        if not db.query(HospitalSettings).first():
            hospital_settings = HospitalSettings(
                hospital_name="LHIMS Test Hospital",
                hospital_address="123 Test Street, Accra, Ghana",
                hospital_phone="+233 20 123 4567",
                hospital_email="info@lhims.test",
                logo_url=None
            )
            db.add(hospital_settings)
            db.commit()
            print("Created default hospital settings")
        
        # Create default departments
        default_departments = [
            ("General Medicine", "General medical consultations"),
            ("Surgery", "Surgical procedures and consultations"),
            ("Pediatrics", "Child healthcare services"),
            ("Obstetrics and Gynecology", "Women's health and maternity services"),
            ("Emergency", "Emergency medical services"),
            ("Pharmacy", "Hospital pharmacy services"),
            ("Laboratory", "Diagnostic laboratory services"),
            ("Radiology", "Imaging and radiology services"),
        ]
        
        for dept_name, description in default_departments:
            existing_dept = db.query(Department).filter(Department.name == dept_name).first()
            if not existing_dept:
                dept = Department(name=dept_name, description=description)
                db.add(dept)
                print(f"Created department: {dept_name}")
        
        db.commit()
        
        # Create default shift types
        default_shifts = [
            ("Morning", "MORN", "Morning shift (6 AM - 2 PM)", 6, 14),
            ("Afternoon", "AFTER", "Afternoon shift (2 PM - 10 PM)", 14, 22),
            ("Night", "NIGHT", "Night shift (10 PM - 6 AM)", 22, 6),
        ]
        
        for shift_name, code, description, start_hour, end_hour in default_shifts:
            existing_shift = db.query(ShiftType).filter(ShiftType.name == shift_name).first()
            if not existing_shift:
                shift = ShiftType(name=shift_name, code=code, description=description, default_start_hour=start_hour, default_end_hour=end_hour)
                db.add(shift)
                print(f"Created shift type: {shift_name}")
        
        db.commit()
        
        # Create default ward types
        default_ward_types = [
            ("General Ward", "GEN", "Shared ward with multiple beds"),
            ("Semi-Private Ward", "SEMI", "Semi-private room with 2 beds"),
            ("Private Ward", "PRIV", "Private room with 1 bed"),
            ("ICU", "ICU", "Intensive Care Unit"),
            ("Maternity Ward", "MAT", "Maternity ward with delivery facilities"),
        ]
        
        for ward_name, code, description in default_ward_types:
            existing_ward = db.query(WardType).filter(WardType.name == ward_name).first()
            if not existing_ward:
                ward = WardType(name=ward_name, code=code, description=description)
                db.add(ward)
                print(f"Created ward type: {ward_name}")
        
        db.commit()
        
        # Create default bed types
        default_bed_types = [
            ("Standard Bed", "STD", "Standard hospital bed", "50.00"),
            ("Electric Bed", "ELEC", "Electric adjustable bed", "100.00"),
            ("ICU Bed", "ICU", "Specialized ICU bed with monitoring", "200.00"),
            ("Pediatric Bed", "PED", "Child-friendly bed with rails", "75.00"),
            ("Maternity Bed", "MAT", "Adjustable maternity bed", "80.00"),
        ]
        
        for bed_name, code, description, charge in default_bed_types:
            existing_bed = db.query(BedType).filter(BedType.name == bed_name).first()
            if not existing_bed:
                bed = BedType(name=bed_name, code=code, description=description, default_charge_per_day=charge)
                db.add(bed)
                print(f"Created bed type: {bed_name}")
        
        db.commit()
        
        # Create some sample diseases
        sample_diseases = [
            ("Malaria", "Malaria caused by Plasmodium parasites", "A00"),
            ("Typhoid Fever", "Bacterial infection caused by Salmonella Typhi", "A01"),
            ("Pneumonia", "Infection that inflames air sacs in lungs", "J18"),
            ("Diabetes Mellitus", "Chronic disease affecting blood sugar regulation", "E11"),
            ("Hypertension", "High blood pressure condition", "I10"),
            ("Asthma", "Chronic lung disease causing breathing difficulties", "J45"),
        ]
        
        for disease_name, description, code in sample_diseases:
            existing_disease = db.query(Disease).filter(Disease.name == disease_name).first()
            if not existing_disease:
                disease = Disease(name=disease_name, description=description, code=code)
                db.add(disease)
                print(f"Created disease: {disease_name}")
        
        db.commit()
        
        # Create sample service pricing
        sample_services = [
            ("General Consultation", "Standard doctor consultation", "consultation", "Consultation", 150.00),
            ("Specialist Consultation", "Consultation with specialist doctor", "consultation", "Consultation", 250.00),
            ("Blood Test - CBC", "Complete Blood Count test", "lab_test", "Laboratory", 80.00),
            ("Malaria Test", "Rapid diagnostic test for malaria", "lab_test", "Laboratory", 50.00),
            ("X-Ray - Chest", "Chest X-ray imaging", "radiology", "Imaging", 200.00),
            ("Ultrasound - Abdomen", "Abdominal ultrasound scan", "radiology", "Imaging", 300.00),
            ("Normal Delivery", "Standard vaginal delivery", "procedure", "Maternity", 1500.00),
            ("Caesarean Section", "Surgical delivery procedure", "procedure", "Surgery", 3500.00),
            ("Hospital Bed - General", "Daily charge for general ward bed", "admission", "Admission", 500.00),
            ("Hospital Bed - Private", "Daily charge for private room", "admission", "Admission", 1500.00),
        ]
        
        for service_name, description, charge_type, category, price in sample_services:
            existing_service = db.query(ServicePricing).filter(ServicePricing.service_name == service_name).first()
            if not existing_service:
                service = ServicePricing(service_name=service_name, description=description, charge_type=charge_type, category=category, unit_price=price)
                db.add(service)
                print(f"Created service: {service_name}")
        
        db.commit()
        
        print("\nDatabase initialization completed successfully!")
        print("Admin user credentials:")
        print("  Username: admin")
        print("  Password: Westafrica1")
        
    except Exception as e:
        db.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
