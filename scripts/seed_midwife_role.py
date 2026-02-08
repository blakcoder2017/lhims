"""
Script to add Midwife role and seed necessary permissions and users for antenatal care.
This script adds the midwife role with appropriate permissions for antenatal and patient info management.
"""
import sys
import os

# --- Add app to Python path ---
# This allows us to import from 'app'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# --- End path setup ---

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user_models import User, Role
from app.models.permission_models import Permission
from app.core.security import get_password_hash
from app.crud import permission_crud

# --- CONFIGURATION ---
# Midwife-specific permissions
MIDWIFE_PERMISSIONS = [
    # Patient Management (limited to antenatal)
    {"name": "view_patients", "description": "View patient records", "module": "patients"},
    {"name": "create_patients", "description": "Create new patient records", "module": "patients"},
    {"name": "edit_patients", "description": "Edit patient records", "module": "patients"},
    
    # Antenatal Care specific
    {"name": "view_antenatal", "description": "View antenatal care records", "module": "antenatal"},
    {"name": "create_antenatal", "description": "Create antenatal care records", "module": "antenatal"},
    {"name": "edit_antenatal", "description": "Edit antenatal care records", "module": "antenatal"},
    {"name": "manage_antenatal_visits", "description": "Manage antenatal visit schedules", "module": "antenatal"},
    {"name": "record_antenatal_findings", "description": "Record antenatal examination findings", "module": "antenatal"},
    {"name": "manage_pregnancy_outcomes", "description": "Manage pregnancy outcomes and deliveries", "module": "antenatal"},
    
    # Basic Clinical (limited)
    {"name": "view_vitals", "description": "View patient vital signs", "module": "clinical"},
    {"name": "record_vitals", "description": "Record patient vital signs", "module": "clinical"},
    
    # Lab Orders (limited to pregnancy-related)
    {"name": "view_lab_orders", "description": "View lab orders", "module": "lab"},
    {"name": "create_lab_orders", "description": "Create lab orders", "module": "lab"},
    {"name": "view_lab_results", "description": "View lab test results", "module": "lab"},
    
    # Reports (limited)
    {"name": "view_antenatal_reports", "description": "View antenatal care reports", "module": "reports"},
]

# Sample midwife users to create
MIDWIFE_USERS = [
    {
        "username": "midwife1",
        "full_name": "Sarah Johnson",
        "email": "sarah.johnson@lhims.gov.gh",
        "phone_number": "+233241234567",
        "password": "Midwife123"
    },
    {
        "username": "midwife2", 
        "full_name": "Grace Amponsah",
        "email": "grace.amponsah@lhims.gov.gh",
        "phone_number": "+233242345678",
        "password": "Midwife123"
    },
    {
        "username": "midwife3",
        "full_name": "Beatrice Osei",
        "email": "beatrice.osei@lhims.gov.gh", 
        "phone_number": "+233243456789",
        "password": "Midwife123"
    }
]

def seed_midwife_permissions():
    """Seed midwife-specific permissions"""
    db: Session = SessionLocal()
    try:
        created_count = 0
        skipped_count = 0
        
        for perm_data in MIDWIFE_PERMISSIONS:
            # Check if permission already exists
            existing = permission_crud.get_permission_by_name(db, perm_data["name"])
            if existing:
                print(f"Permission '{perm_data['name']}' already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create permission
            permission = permission_crud.create_permission(
                db,
                name=perm_data["name"],
                description=perm_data["description"],
                module=perm_data["module"]
            )
            print(f"Created permission: {permission.name} ({permission.module})")
            created_count += 1
        
        print(f"\n✅ Midwife permissions seeding complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(MIDWIFE_PERMISSIONS)}")
        
    except Exception as e:
        print(f"❌ Error seeding midwife permissions: {e}")
        db.rollback()
    finally:
        db.close()

def create_midwife_role():
    """Create the Midwife role and assign permissions"""
    db: Session = SessionLocal()
    try:
        # Check if Midwife role already exists
        midwife_role = db.query(Role).filter(Role.name == "Midwife").first()
        if midwife_role:
            print("Midwife role already exists")
            return midwife_role
        
        # Create Midwife role
        midwife_role = Role(
            name="Midwife",
            description="Midwife - Antenatal care, patient information, and pregnancy management"
        )
        db.add(midwife_role)
        db.commit()
        db.refresh(midwife_role)
        
        print(f"Created role: {midwife_role.name}")
        
        # Assign permissions to Midwife role
        permissions_assigned = 0
        for perm_data in MIDWIFE_PERMISSIONS:
            permission = permission_crud.get_permission_by_name(db, perm_data["name"])
            if permission and permission not in midwife_role.permissions:
                midwife_role.permissions.append(permission)
                permissions_assigned += 1
        
        db.commit()
        print(f"Assigned {permissions_assigned} permissions to Midwife role")
        
        return midwife_role
        
    except Exception as e:
        print(f"❌ Error creating Midwife role: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def create_midwife_users():
    """Create sample midwife users"""
    db: Session = SessionLocal()
    try:
        # Get Midwife role
        midwife_role = db.query(Role).filter(Role.name == "Midwife").first()
        if not midwife_role:
            print("Error: Midwife role not found. Please create the role first.")
            return
        
        created_count = 0
        skipped_count = 0
        
        for user_data in MIDWIFE_USERS:
            # Check if user already exists
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()
            if existing_user:
                print(f"User '{user_data['username']}' already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create user
            hashed_password = get_password_hash(user_data["password"])
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                phone_number=user_data["phone_number"],
                hashed_password=hashed_password,
                is_active=True,
                role_id=midwife_role.id
            )
            db.add(user)
            created_count += 1
            print(f"Created midwife user: {user_data['username']} ({user_data['full_name']})")
        
        db.commit()
        
        print(f"\n✅ Midwife users creation complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(MIDWIFE_USERS)}")
        
    except Exception as e:
        print(f"❌ Error creating midwife users: {e}")
        db.rollback()
    finally:
        db.close()

def update_existing_roles():
    """Update existing roles to include midwife role in the admin seeding"""
    db: Session = SessionLocal()
    try:
        # Check if Midwife role exists in the roles list
        midwife_role = db.query(Role).filter(Role.name == "Midwife").first()
        if not midwife_role:
            print("Midwife role not found - creating it first...")
            midwife_role = create_midwife_role()
        
        if midwife_role:
            print("✅ Midwife role is available in the system")
        else:
            print("❌ Failed to create Midwife role")
            
    except Exception as e:
        print(f"❌ Error updating roles: {e}")
    finally:
        db.close()

def main():
    """Main function to execute all seeding operations"""
    print("🏥 LHIMS Midwife Role Seeding")
    print("=" * 50)
    
    print("\n1. Seeding Midwife Permissions...")
    seed_midwife_permissions()
    
    print("\n2. Creating Midwife Role...")
    midwife_role = create_midwife_role()
    
    if midwife_role:
        print("\n3. Creating Sample Midwife Users...")
        create_midwife_users()
        
        print("\n4. Updating Role System...")
        update_existing_roles()
        
        print("\n🎉 Midwife role seeding completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ Midwife role created")
        print("   ✅ Antenatal care permissions assigned")
        print("   ✅ Patient information permissions assigned")
        print("   ✅ Sample midwife users created")
        print("\n🔑 Login Credentials:")
        for user in MIDWIFE_USERS:
            print(f"   Username: {user['username']} | Password: {user['password']}")
    else:
        print("\n❌ Midwife role seeding failed!")

if __name__ == "__main__":
    main()
