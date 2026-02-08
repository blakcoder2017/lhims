import sys
import os

# --- Add app to Python path ---
# This allows us to import from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# --- End path setup ---

from app.db.database import SessionLocal, engine
from app.models.user_models import User, Role
from app.core.security import get_password_hash
from sqlalchemy.orm import Session

# --- CONFIGURATION ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Westafrica1" # Change this in a real system
ADMIN_EMAIL = "sherifdata@gmail.com"

# Roles from your LHIMS Workflows doc
ROLES_TO_CREATE = [
    {"name": "Admin", "description": "System Administrator"},
    {"name": "Front Office", "description": "Registration, Triage, Appointments"},
    {"name": "Doctor", "description": "Physicians - Clinical encounters, diagnoses, and treatment orders"},
    {"name": "Nurse", "description": "Nurses - Patient care, triage, and clinical support"},
    {"name": "Midwife", "description": "Midwives - Antenatal care, patient information, and pregnancy management"},
    {"name": "Clinician", "description": "Legacy role - Doctors, Nurses - Clinical Encounters (kept for backward compatibility)"},
    {"name": "Lab Staff", "description": "Fulfills laboratory orders"},
    {"name": "Pharmacy Staff", "description": "Dispenses medication, manages inventory"},
    {"name": "Radiology Staff", "description": "Fulfills radiology orders, manages PACS images"},
    {"name": "Finance", "description": "Billing and NHIS Claims processing"},
    {"name": "Management", "description": "Views dashboards and reports"},
]

def seed_database():
    print("--- Seeding Database ---")
    db: Session = SessionLocal()
    
    try:
        # --- 1. Create Roles ---
        admin_role = None
        for role_data in ROLES_TO_CREATE:
            role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not role:
                role = Role(name=role_data["name"], description=role_data["description"])
                db.add(role)
                print(f"Created role: {role.name}")
            if role.name == "Admin":
                admin_role = role
        
        db.commit() # Commit roles so the User can link to them

        # --- 2. Create Admin User ---
        if not admin_role:
            print("Error: 'Admin' role was not created. Aborting admin user creation.")
            return

        admin_user = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not admin_user:
            hashed_password = get_password_hash(ADMIN_PASSWORD)
            admin_user = User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                full_name="LHIMS Administrator",
                hashed_password=hashed_password,
                is_active=True,
                role_id=admin_role.id
            )
            db.add(admin_user)
            db.commit()
            print(f"Created admin user: {admin_user.username}")
        else:
            print(f"Admin user '{ADMIN_USERNAME}' already exists.")

        print("--- Seeding Complete ---")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()