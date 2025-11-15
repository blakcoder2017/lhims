"""
Script to seed default permissions for the LHIMS system.
Run this after creating the permissions table.
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.permission_models import Permission
from app.crud import permission_crud

# Default permissions organized by module
DEFAULT_PERMISSIONS = [
    # Patient Management
    {"name": "view_patients", "description": "View patient records", "module": "patients"},
    {"name": "create_patients", "description": "Create new patient records", "module": "patients"},
    {"name": "edit_patients", "description": "Edit patient records", "module": "patients"},
    {"name": "delete_patients", "description": "Delete patient records", "module": "patients"},
    
    # Encounters
    {"name": "view_encounters", "description": "View clinical encounters", "module": "encounters"},
    {"name": "create_encounters", "description": "Create new encounters", "module": "encounters"},
    {"name": "edit_encounters", "description": "Edit encounters", "module": "encounters"},
    {"name": "close_encounters", "description": "Close encounters", "module": "encounters"},
    
    # Lab Orders
    {"name": "view_lab_orders", "description": "View lab orders", "module": "lab"},
    {"name": "create_lab_orders", "description": "Create lab orders", "module": "lab"},
    {"name": "enter_lab_results", "description": "Enter lab test results", "module": "lab"},
    {"name": "view_lab_results", "description": "View lab test results", "module": "lab"},
    
    # Radiology
    {"name": "view_radiology_orders", "description": "View radiology orders", "module": "radiology"},
    {"name": "create_radiology_orders", "description": "Create radiology orders", "module": "radiology"},
    {"name": "enter_radiology_reports", "description": "Enter radiology reports", "module": "radiology"},
    {"name": "view_radiology_reports", "description": "View radiology reports", "module": "radiology"},
    {"name": "manage_pacs", "description": "Manage PACS images", "module": "radiology"},
    
    # Pharmacy
    {"name": "view_prescriptions", "description": "View prescriptions", "module": "pharmacy"},
    {"name": "create_prescriptions", "description": "Create prescriptions", "module": "pharmacy"},
    {"name": "dispense_medications", "description": "Dispense medications", "module": "pharmacy"},
    {"name": "manage_inventory", "description": "Manage pharmacy inventory", "module": "pharmacy"},
    
    # Billing
    {"name": "view_billing", "description": "View billing information", "module": "billing"},
    {"name": "create_invoices", "description": "Create invoices", "module": "billing"},
    {"name": "process_payments", "description": "Process payments", "module": "billing"},
    {"name": "view_reports", "description": "View financial reports", "module": "billing"},
    
    # Appointments
    {"name": "view_appointments", "description": "View appointments", "module": "appointments"},
    {"name": "create_appointments", "description": "Create appointments", "module": "appointments"},
    {"name": "edit_appointments", "description": "Edit appointments", "module": "appointments"},
    {"name": "check_in_patients", "description": "Check in patients", "module": "appointments"},
    
    # Admin
    {"name": "manage_users", "description": "Manage system users", "module": "admin"},
    {"name": "manage_roles", "description": "Manage roles and permissions", "module": "admin"},
    {"name": "manage_settings", "description": "Manage system settings", "module": "admin"},
    {"name": "view_audit_logs", "description": "View audit logs", "module": "admin"},
    {"name": "manage_service_pricing", "description": "Manage service pricing", "module": "admin"},
    
    # Reports
    {"name": "view_analytics", "description": "View analytics and reports", "module": "reports"},
    {"name": "export_data", "description": "Export system data", "module": "reports"},
]


def seed_permissions():
    """Seed default permissions into the database"""
    db: Session = SessionLocal()
    try:
        created_count = 0
        skipped_count = 0
        
        for perm_data in DEFAULT_PERMISSIONS:
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
        
        print(f"\n✅ Permissions seeding complete!")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(DEFAULT_PERMISSIONS)}")
        
    except Exception as e:
        print(f"❌ Error seeding permissions: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_permissions()

