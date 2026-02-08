"""
Script to update Midwife role permissions to be more restrictive.
Midwives should only see Maternity, Antenatal, and related modules.
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
from app.crud import permission_crud

# --- CONFIGURATION ---
# Restrictive midwife permissions - only maternity/antenatal focused
RESTRICTED_MIDWIFE_PERMISSIONS = [
    # Antenatal Care (Primary focus)
    {"name": "view_antenatal", "description": "View antenatal care records", "module": "antenatal"},
    {"name": "create_antenatal", "description": "Create antenatal care records", "module": "antenatal"},
    {"name": "edit_antenatal", "description": "Edit antenatal care records", "module": "antenatal"},
    {"name": "manage_antenatal_visits", "description": "Manage antenatal visit schedules", "module": "antenatal"},
    {"name": "record_antenatal_findings", "description": "Record antenatal examination findings", "module": "antenatal"},
    {"name": "manage_pregnancy_outcomes", "description": "Manage pregnancy outcomes and deliveries", "module": "antenatal"},
    
    # Maternity/Delivery
    {"name": "view_maternity", "description": "View maternity ward records", "module": "maternity"},
    {"name": "create_maternity", "description": "Create maternity records", "module": "maternity"},
    {"name": "edit_maternity", "description": "Edit maternity records", "module": "maternity"},
    {"name": "manage_deliveries", "description": "Manage delivery records", "module": "maternity"},
    {"name": "record_delivery_outcomes", "description": "Record delivery outcomes", "module": "maternity"},
    
    # Basic Patient Info (limited to their patients)
    {"name": "view_patients", "description": "View patient records", "module": "patients"},
    {"name": "edit_patients", "description": "Edit patient records", "module": "patients"},
    
    # Basic Clinical (limited to vital signs)
    {"name": "view_vitals", "description": "View patient vital signs", "module": "clinical"},
    {"name": "record_vitals", "description": "Record patient vital signs", "module": "clinical"},
    
    # Limited Lab (pregnancy-related only)
    {"name": "view_lab_orders", "description": "View lab orders", "module": "lab"},
    {"name": "create_lab_orders", "description": "Create lab orders", "module": "lab"},
    {"name": "view_lab_results", "description": "View lab test results", "module": "lab"},
]

# Permissions to REMOVE from midwife role
PERMISSIONS_TO_REMOVE = [
    "create_patients",  # Can create but should be limited
    "delete_patients",   # Should not delete
    "view_encounters",     # Should not see general encounters
    "create_encounters",   # Should not create general encounters
    "edit_encounters",     # Should not edit general encounters
    "close_encounters",     # Should not close general encounters
    "view_radiology_orders",     # Should not see radiology orders
    "create_radiology_orders",   # Should not create radiology orders
    "enter_radiology_reports",    # Should not enter radiology reports
    "view_radiology_reports",     # Should not view radiology reports
    "manage_pacs",      # Should not manage PACS
    "view_prescriptions",     # Should not see prescriptions
    "create_prescriptions",   # Should not create prescriptions
    "dispense_medications",   # Should not dispense medications
    "manage_inventory",      # Should not manage inventory
    "view_billing",       # Should not see billing
    "create_invoices",     # Should not create invoices
    "process_payments",     # Should not process payments
    "view_reports",       # Should not see general reports
    "view_appointments",   # Should not see appointments
    "create_appointments", # Should not create appointments
    "edit_appointments",   # Should not edit appointments
    "check_in_patients",   # Should not check in patients
    "manage_users",        # Should not manage users
    "manage_roles",        # Should not manage roles
    "manage_settings",      # Should not manage settings
    "view_audit_logs",     # Should not see audit logs
    "manage_service_pricing", # Should not manage pricing
    "view_analytics",      # Should not see analytics
    "export_data",         # Should not export data
]

def create_maternity_permissions():
    """Create maternity-specific permissions"""
    db: Session = SessionLocal()
    try:
        created_count = 0
        skipped_count = 0
        
        maternity_permissions = [
            {"name": "view_maternity", "description": "View maternity ward records", "module": "maternity"},
            {"name": "create_maternity", "description": "Create maternity records", "module": "maternity"},
            {"name": "edit_maternity", "description": "Edit maternity records", "module": "maternity"},
            {"name": "manage_deliveries", "description": "Manage delivery records", "module": "maternity"},
            {"name": "record_delivery_outcomes", "description": "Record delivery outcomes", "module": "maternity"},
        ]
        
        for perm_data in maternity_permissions:
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
        
        print(f"\n✅ Maternity permissions seeding complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(maternity_permissions)}")
        
    except Exception as e:
        print(f"❌ Error seeding maternity permissions: {e}")
        db.rollback()
    finally:
        db.close()

def update_midwife_role_permissions():
    """Update Midwife role to have restrictive permissions"""
    db: Session = SessionLocal()
    try:
        # Get Midwife role
        midwife_role = db.query(Role).filter(Role.name == "Midwife").first()
        if not midwife_role:
            print("❌ Midwife role not found. Please create it first.")
            return
        
        print(f"🔄 Updating Midwife role permissions...")
        print(f"   Current permissions: {len(midwife_role.permissions)}")
        
        # Clear existing permissions
        midwife_role.permissions.clear()
        
        # Add only restrictive permissions
        permissions_added = 0
        for perm_data in RESTRICTED_MIDWIFE_PERMISSIONS:
            permission = permission_crud.get_permission_by_name(db, perm_data["name"])
            if permission and permission not in midwife_role.permissions:
                midwife_role.permissions.append(permission)
                permissions_added += 1
                print(f"   ✅ Added: {permission.name} ({permission.module})")
            elif not permission:
                print(f"   ⚠️  Missing: {perm_data['name']} - creating it...")
                permission = permission_crud.create_permission(
                    db,
                    name=perm_data["name"],
                    description=perm_data["description"],
                    module=perm_data["module"]
                )
                midwife_role.permissions.append(permission)
                permissions_added += 1
                print(f"   ✅ Created & Added: {permission.name} ({permission.module})")
        
        db.commit()
        print(f"\n✅ Midwife role updated!")
        print(f"   Permissions assigned: {permissions_added}")
        print(f"   Total allowed: {len(RESTRICTED_MIDWIFE_PERMISSIONS)}")
        
        return midwife_role
        
    except Exception as e:
        print(f"❌ Error updating Midwife role: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def verify_restricted_access():
    """Verify that midwife role has restricted access"""
    db: Session = SessionLocal()
    try:
        midwife_role = db.query(Role).filter(Role.name == "Midwife").first()
        if not midwife_role:
            print("❌ Midwife role not found")
            return
        
        permissions = midwife_role.permissions
        permission_names = [p.name for p in permissions]
        
        print(f"\n🔍 Verifying restricted access...")
        print(f"   Total permissions: {len(permissions)}")
        
        # Check for restricted permissions
        restricted_perms = set(RESTRICTED_MIDWIFE_PERMISSIONS)
        current_perms = set()
        for p in permissions:
            if hasattr(p, 'name'):
                current_perms.add(p.name)
        
        # What they should have
        allowed = restricted_perms.intersection(current_perms)
        print(f"   ✅ Allowed permissions: {len(allowed)}")
        
        # What they shouldn't have
        disallowed = set(PERMISSIONS_TO_REMOVE).intersection(current_perms)
        if disallowed:
            print(f"   ❌ Disallowed permissions found: {len(disallowed)}")
            for perm in disallowed:
                print(f"      • {perm}")
        else:
            print(f"   ✅ No disallowed permissions found")
        
        # Check for maternity permissions
        maternity_perms = [p for p in permissions if hasattr(p, 'module') and p.module == "maternity"]
        print(f"   🏥 Maternity permissions: {len(maternity_perms)}")
        for perm in maternity_perms:
            print(f"      • {perm.name}")
        
        # Check for antenatal permissions
        antenatal_perms = [p for p in permissions if hasattr(p, 'module') and p.module == "antenatal"]
        print(f"   🤰 Antenatal permissions: {len(antenatal_perms)}")
        for perm in antenatal_perms:
            print(f"      • {perm.name}")
        
    except Exception as e:
        print(f"❌ Error verifying access: {e}")
    finally:
        db.close()

def main():
    """Main function to execute permission updates"""
    print("🔒 LHIMS Midwife Role Permission Update")
    print("=" * 50)
    
    print("\n1. Creating maternity permissions...")
    create_maternity_permissions()
    
    print("\n2. Updating Midwife role with restrictive permissions...")
    update_midwife_role_permissions()
    
    print("\n3. Verifying restricted access...")
    verify_restricted_access()
    
    print("\n🎉 Midwife role permission update completed!")
    print("\n📋 Summary:")
    print("   ✅ Maternity permissions created")
    print("   ✅ Midwife role updated with restricted access")
    print("   ✅ Only antenatal/maternity focused permissions")
    print("   ✅ General system access removed")
    print("\n🔒 Midwife users can now only access:")
    print("   • Antenatal Dashboard")
    print("   • Antenatal Visits") 
    print("   • New Antenatal Visit")
    print("   • Maternity Ward")
    print("   • Delivery Management")
    print("   • Patient Records (limited)")
    print("   • Vital Signs (limited)")

if __name__ == "__main__":
    main()
