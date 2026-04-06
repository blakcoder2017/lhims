#!/usr/bin/env python3
"""
LHIMS Database Seeding Script

Seeds roles, permissions, and diseases data for the LHIMS system.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user_models import User, Role
from app.models.permission_models import Permission
from app.models.disease_models import Disease
from app.core.config import settings

def seed_roles_permissions(db):
    """Seed roles and permissions"""
    
    # Create permissions
    permissions_data = [
        # Menu permissions (required for sidebar visibility)
        ("menu_front_office", "Access Front Office menu"),
        ("menu_direct_service", "Access Direct Service Requests menu"),
        ("menu_nurse", "Access Nurse menu"),
        ("menu_doctor", "Access Doctor menu"),
        ("menu_clinical", "Access Clinical Services menu"),
        ("menu_opd", "Access OPD menu"),
        ("menu_emergency", "Access Emergency menu"),
        ("menu_ipd", "Access IPD menu"),
        ("menu_patients", "Access Patients menu"),
        ("menu_pharmacy", "Access Pharmacy menu"),
        ("menu_lab", "Access Laboratory menu"),
        ("menu_radiology", "Access Radiology menu"),
        ("menu_procedures", "Access Procedures menu"),
        ("menu_maternity", "Access Maternity menu"),
        ("menu_finance", "Access Finance menu"),
        ("menu_reports", "Access Reports menu"),
        
        # Submenu permissions
        ("register_patient", "Register new patients"),
        ("view_patients_list", "View patients list"),
        ("view_opd_queue", "View OPD queue"),
        ("manage_appointments", "Manage appointments"),
        ("record_vitals", "Record patient vitals"),
        ("nurse_dashboard", "Access nurse dashboard"),
        ("view_triage_queue", "View triage queue"),
        ("doctor_dashboard", "Access doctor dashboard"),
        ("doctor_appointments", "View doctor appointments"),
        ("doctor_queue", "View doctor queue"),
        ("view_pending_encounters", "View pending encounters"),
        ("view_procedures", "View procedures"),
        ("search_patients", "Search patient records"),
        ("view_differentials", "View G-STG differentials"),
        ("manage_wards", "Manage wards"),
        ("manage_admissions", "Manage patient admissions"),
        ("doctor_duties", "Manage doctor duties"),
        ("manage_inventory", "Manage pharmacy inventory"),
        ("manage_lab", "Manage laboratory"),
        ("manage_radiology", "Manage radiology"),
        ("view_pacs", "View PACS images"),
        ("manage_procedures", "Manage procedures"),
        ("billing", "Access billing module"),
        ("claims", "Manage insurance claims"),
        ("financial_reports", "View financial reports"),
        ("patient_reports", "View patient reports"),
        ("pharmacy_reports", "View pharmacy reports"),
        ("lab_reports", "View lab reports"),
        ("radiology_reports", "View radiology reports"),
        ("clinical_reports", "View clinical reports"),
        ("expense_reports", "View expense reports"),
        
        # Patient permissions
        ("patient_view", "View patient information"),
        ("patient_create", "Create new patients"),
        ("patient_edit", "Edit patient information"),
        ("patient_delete", "Delete patient records"),
        
        # Appointment permissions
        ("appointment_view", "View appointments"),
        ("appointment_create", "Create appointments"),
        ("appointment_edit", "Edit appointments"),
        ("appointment_delete", "Delete appointments"),
        
        # Billing permissions
        ("billing_view", "View billing information"),
        ("billing_create", "Create invoices"),
        ("billing_edit", "Edit billing records"),
        ("billing_process", "Process payments"),
        
        # Lab permissions
        ("lab_view", "View lab results"),
        ("lab_create", "Create lab orders"),
        ("lab_edit", "Edit lab records"),
        ("lab_approve", "Approve lab results"),
        
        # Radiology permissions
        ("radiology_view", "View radiology reports"),
        ("radiology_create", "Create radiology orders"),
        ("radiology_edit", "Edit radiology records"),
        ("radiology_approve", "Approve radiology reports"),
        
        # Pharmacy permissions
        ("pharmacy_view", "View pharmacy records"),
        ("pharmacy_dispense", "Dispense medications"),
        ("pharmacy_inventory", "Manage inventory"),
        
        # Admin permissions
        ("admin_users", "Manage user accounts"),
        ("admin_roles", "Manage roles and permissions"),
        ("admin_settings", "Manage system settings"),
        ("admin_reports", "View system reports"),
    ]
    
    permissions = {}
    for perm_code, perm_desc in permissions_data:
        permission = db.query(Permission).filter_by(name=perm_code).first()
        if not permission:
            permission = Permission(name=perm_code, description=perm_desc)
            db.add(permission)
            db.flush()
        permissions[perm_code] = permission
    
    # Create roles
    roles_data = [
        ("admin", "System Administrator", [
            # All menu permissions
            "menu_front_office", "menu_direct_service", "menu_nurse", "menu_doctor",
            "menu_clinical", "menu_opd", "menu_emergency", "menu_ipd",
            "menu_patients", "menu_pharmacy", "menu_lab", "menu_radiology",
            "menu_procedures", "menu_maternity", "menu_finance", "menu_reports",
            # All submenu permissions
            "register_patient", "view_patients_list", "view_opd_queue", "manage_appointments",
            "record_vitals", "nurse_dashboard", "view_triage_queue",
            "doctor_dashboard", "doctor_appointments", "doctor_queue",
            "view_pending_encounters", "view_procedures", "search_patients", "view_differentials",
            "manage_wards", "manage_admissions", "doctor_duties",
            "manage_inventory", "manage_lab", "manage_radiology", "view_pacs",
            "manage_procedures", "billing", "claims",
            "financial_reports", "patient_reports", "pharmacy_reports", "lab_reports",
            "radiology_reports", "clinical_reports", "expense_reports",
            # All functional permissions
            "patient_view", "patient_create", "patient_edit", "patient_delete",
            "appointment_view", "appointment_create", "appointment_edit", "appointment_delete",
            "billing_view", "billing_create", "billing_edit", "billing_process",
            "lab_view", "lab_create", "lab_edit", "lab_approve",
            "radiology_view", "radiology_create", "radiology_edit", "radiology_approve",
            "pharmacy_view", "pharmacy_dispense", "pharmacy_inventory",
            "admin_users", "admin_roles", "admin_settings", "admin_reports"
        ]),
        
        ("doctor", "Doctor/Clinician", [
            # Menu permissions
            "menu_doctor", "menu_clinical", "menu_patients", "menu_opd",
            # Submenu permissions
            "doctor_dashboard", "doctor_appointments", "doctor_queue",
            "view_pending_encounters", "view_procedures", "search_patients", "view_differentials",
            # Functional permissions
            "patient_view", "patient_edit",
            "appointment_view", "appointment_create", "appointment_edit",
            "billing_view", "billing_create",
            "lab_view", "lab_create", "lab_edit",
            "radiology_view", "radiology_create", "radiology_edit",
            "pharmacy_view", "pharmacy_dispense"
        ]),
        
        ("nurse", "Nurse", [
            # Menu permissions
            "menu_nurse", "menu_front_office", "menu_patients",
            # Submenu permissions
            "nurse_dashboard", "view_triage_queue", "record_vitals",
            # Functional permissions
            "patient_view", "patient_edit",
            "appointment_view", "appointment_create",
            "lab_view", "lab_create",
            "pharmacy_view", "pharmacy_dispense"
        ]),
        
        ("lab_technician", "Lab Technician", [
            # Menu permissions
            "menu_lab", "menu_patients",
            # Submenu permissions
            "manage_lab", "lab_reports",
            # Functional permissions
            "patient_view",
            "lab_view", "lab_create", "lab_edit", "lab_approve"
        ]),
        
        ("radiologist", "Radiologist", [
            # Menu permissions
            "menu_radiology", "menu_patients",
            # Submenu permissions
            "manage_radiology", "view_pacs", "radiology_reports",
            # Functional permissions
            "patient_view",
            "radiology_view", "radiology_create", "radiology_edit", "radiology_approve"
        ]),
        
        ("pharmacist", "Pharmacist", [
            # Menu permissions
            "menu_pharmacy", "menu_patients",
            # Submenu permissions
            "manage_inventory", "pharmacy_reports",
            # Functional permissions
            "patient_view",
            "pharmacy_view", "pharmacy_dispense", "pharmacy_inventory"
        ]),
        
        ("receptionist", "Receptionist", [
            # Menu permissions
            "menu_front_office", "menu_direct_service", "menu_patients", "menu_emergency",
            # Submenu permissions
            "register_patient", "view_patients_list", "view_opd_queue", "manage_appointments",
            # Functional permissions
            "patient_view", "patient_create", "patient_edit",
            "appointment_view", "appointment_create", "appointment_edit",
            "billing_view", "billing_create", "billing_process"
        ]),
        
        ("accountant", "Accountant/Finance", [
            # Menu permissions - ADDED FRONT OFFICE + ALL FRONT DESK
            "menu_finance", "menu_front_office", "menu_patients", "menu_direct_service",
            # Submenu permissions - ALL FRONT DESK + BILLING/CLAIMS (NO REPORTS)
            "billing", "claims",
            "register_patient", "view_patients_list", "view_opd_queue", "manage_appointments",
            # Functional permissions - FRONT DESK + BILLING
            "billing_view", "billing_edit", "billing_process",
            "patient_view", "patient_create", "patient_edit",
            "appointment_view", "appointment_create", "appointment_edit"
        ]),
        
        ("finance", "Finance Officer", [
            # Menu permissions - FRONT OFFICE + ALL FRONT DESK
            "menu_finance", "menu_front_office", "menu_patients", "menu_direct_service",
            # Submenu permissions - ALL FRONT DESK + BILLING/CLAIMS (NO REPORTS)
            "billing", "claims",
            "register_patient", "view_patients_list", "view_opd_queue", "manage_appointments",
            # Functional permissions - FRONT DESK + BILLING (NO FINANCIAL REPORTS)
            "billing_view", "billing_edit", "billing_process",
            "patient_view", "patient_create", "patient_edit",
            "appointment_view", "appointment_create", "appointment_edit"
        ]),
    ]
    
    for role_code, role_name, role_permissions in roles_data:
        role = db.query(Role).filter_by(name=role_code).first()
        if not role:
            role = Role(name=role_code, description=role_name)
            db.add(role)
            db.flush()
        
        # Add permissions to role
        for perm_code in role_permissions:
            if perm_code in permissions:
                role.permissions.append(permissions[perm_code])
    
    print("✅ Roles and permissions seeded")

def seed_diseases(db):
    """Seed common diseases"""
    
    diseases_data = [
        # Infectious diseases
        ("Malaria", "B54", "Malaria infection"),
        ("Typhoid fever", "A01.0", "Typhoid fever infection"),
        ("Tuberculosis", "A15-A19", "Tuberculosis"),
        ("HIV/AIDS", "B20-B24", "Human immunodeficiency virus disease"),
        ("COVID-19", "U07.1", "COVID-19 infection"),
        ("Cholera", "A00", "Cholera"),
        ("Hepatitis B", "B16", "Acute hepatitis B"),
        ("Hepatitis A", "B15", "Acute hepatitis A"),
        
        # Cardiovascular
        ("Hypertension", "I10", "Essential hypertension"),
        ("Diabetes Mellitus Type 2", "E11", "Type 2 diabetes mellitus"),
        ("Diabetes Mellitus Type 1", "E10", "Type 1 diabetes mellitus"),
        ("Stroke", "I63-I64", "Stroke"),
        ("Heart Failure", "I50", "Heart failure"),
        ("Angina Pectoris", "I20", "Angina pectoris"),
        
        # Respiratory
        ("Asthma", "J45", "Asthma"),
        ("COPD", "J44", "Chronic obstructive pulmonary disease"),
        ("Pneumonia", "J12-J18", "Pneumonia"),
        ("Upper Respiratory Infection", "J00-J06", "Acute upper respiratory infections"),
        
        # Gastrointestinal
        ("Gastroenteritis", "K52.9", "Gastroenteritis"),
        ("Peptic Ulcer", "K25-K27", "Peptic ulcer"),
        ("Appendicitis", "K35-K38", "Appendicitis"),
        
        # Neurological
        ("Migraine", "G43", "Migraine"),
        ("Epilepsy", "G40-G41", "Epilepsy"),
        ("Meningitis", "G00-G03", "Meningitis"),
        
        # Musculoskeletal
        ("Arthritis", "M00-M25", "Arthritis"),
        ("Back Pain", "M54.5", "Low back pain"),
        ("Fracture", "S72", "Fracture of femur"),
        
        # Obstetrics/Gynecology
        ("Pregnancy", "O80", "Encounter for full-term uncomplicated delivery"),
        ("Ectopic Pregnancy", "O00", "Ectopic pregnancy"),
        ("Pelvic Inflammatory Disease", "N70-N77", "Inflammatory diseases of female pelvic organs"),
        
        # Pediatric
        ("Malnutrition", "E46", "Unspecified protein-energy malnutrition"),
        ("Anemia", "D64.9", "Anemia, unspecified"),
        
        # Mental Health
        ("Depression", "F32-F33", "Depressive episode"),
        ("Anxiety", "F41.1", "Generalized anxiety disorder"),
        
        # Skin
        ("Dermatitis", "L20-L30", "Dermatitis and eczema"),
        ("Scabies", "B86", "Scabies"),
        
        # Eye
        ("Conjunctivitis", "H10", "Conjunctivitis"),
        ("Cataract", "H25", "Cataract"),
        
        # General
        ("Fever", "R50.9", "Fever, unspecified"),
        ("Headache", "R51", "Headache"),
        ("Abdominal Pain", "R10.9", "Abdominal pain, unspecified"),
    ]
    
    for disease_name, disease_code, disease_desc in diseases_data:
        disease = db.query(Disease).filter_by(name=disease_name).first()
        if not disease:
            disease = Disease(
                name=disease_name,
                code=disease_code,
                description=disease_desc,
                is_system=True,
                is_active=True
            )
            db.add(disease)
    
    print("✅ Diseases seeded")

def main():
    """Main seeding function"""
    print("🏥 LHIMS Database Seeding")
    print("=" * 40)
    
    try:
        # Create database connection
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("📋 Seeding roles and permissions...")
        seed_roles_permissions(db)
        
        print("\n🦠 Seeding diseases...")
        seed_diseases(db)
        
        # Commit all changes
        db.commit()
        
        print("\n✅ Database seeding completed successfully!")
        
        # Show statistics
        role_count = db.query(Role).count()
        permission_count = db.query(Permission).count()
        disease_count = db.query(Disease).count()
        
        print(f"\n📊 Seeding Statistics:")
        print(f"  Roles: {role_count}")
        print(f"  Permissions: {permission_count}")
        print(f"  Diseases: {disease_count}")
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        if 'db' in locals():
            db.rollback()
        
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()
