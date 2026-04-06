#!/usr/bin/env python3
"""
Script to properly configure Finance role with front office and financial reports only.
Run with: python3 fix_finance_role_perms.py
"""
import os
import sys

# Database configuration from .env
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5433'),
    'dbname': os.getenv('POSTGRES_DB', 'lhims'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password123'),
}

def get_connection():
    """Get database connection"""
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)

def fix_finance_role(conn):
    """Properly configure Finance role with front office and financial reports only"""
    cursor = conn.cursor()
    
    # First, ensure all required permissions exist
    permissions_to_add = [
        # Menu permissions - Front Office + Finance (NO Reports menu)
        ('menu_front_office', 'Access Front Office menu', 'menu'),
        ('menu_finance', 'Access Finance menu', 'menu'),
        ('menu_patients', 'Access Patients menu', 'menu'),
        ('menu_direct_service', 'Access Direct Service Requests menu', 'menu'),
        # Submenu permissions - Front Office
        ('register_patient', 'Register new patients', 'patients'),
        ('view_patients_list', 'View patients list', 'patients'),
        ('view_opd_queue', 'View OPD queue', 'front_office'),
        ('manage_appointments', 'Manage appointments', 'appointments'),
        # Submenu permissions - Finance/Billing
        ('billing', 'Access billing module', 'billing'),
        ('claims', 'Manage insurance claims', 'billing'),
        ('financial_reports', 'View financial reports', 'reports'),
        # Patient permissions
        ('patient_view', 'View patient information', 'patients'),
        ('patient_create', 'Create new patients', 'patients'),
        ('patient_edit', 'Edit patient information', 'patients'),
        # Appointment permissions
        ('appointment_view', 'View appointments', 'appointments'),
        ('appointment_create', 'Create appointments', 'appointments'),
        ('appointment_edit', 'Edit appointments', 'appointments'),
        # Billing permissions
        ('billing_view', 'View billing information', 'billing'),
        ('billing_edit', 'Edit billing records', 'billing'),
        ('billing_process', 'Process payments', 'billing'),
    ]
    
    print("📋 Adding permissions...")
    for perm_name, perm_desc, module in permissions_to_add:
        try:
            cursor.execute("""
                INSERT INTO permissions (name, description, module, is_active)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (name) DO NOTHING
            """, (perm_name, perm_desc, module))
            print(f"✓ Added/updated: {perm_name}")
        except Exception as e:
            print(f"✗ Error adding {perm_name}: {e}")
    
    # Get accountant role ID
    cursor.execute("SELECT id FROM roles WHERE name = 'accountant'")
    accountant_role = cursor.fetchone()
    
    # Get finance role ID
    cursor.execute("SELECT id FROM roles WHERE name = 'finance'")
    finance_role = cursor.fetchone()
    
    role_ids = []
    if accountant_role:
        role_ids.append(('accountant', accountant_role[0]))
        print(f"\n📌 Accountant role ID: {accountant_role[0]}")
    if finance_role:
        role_ids.append(('finance', finance_role[0]))
        print(f"📌 Finance role ID: {finance_role[0]}")
    
    if not role_ids:
        print("⚠ Neither accountant nor finance role found!")
        conn.rollback()
        return
    
    # Define the correct permissions for Finance role
    finance_perms = [
        # Menus - Front Office + Finance (NO Reports)
        'menu_front_office', 'menu_finance', 'menu_patients', 'menu_direct_service',
        # Submenus - Front Office + Finance/Billing
        'register_patient', 'view_patients_list', 'view_opd_queue', 'manage_appointments',
        'billing', 'claims', 'financial_reports',
        # Functional
        'patient_view', 'patient_create', 'patient_edit',
        'appointment_view', 'appointment_create', 'appointment_edit',
        'billing_view', 'billing_edit', 'billing_process'
    ]
    
    # Report permissions to REMOVE from Finance
    report_perms_to_remove = [
        'menu_reports',
        'patient_reports',
        'pharmacy_reports',
        'lab_reports',
        'radiology_reports',
        'clinical_reports',
        'expense_reports',
        'admin_reports'
    ]
    
    print("\n🔗 Assigning correct permissions to Finance roles...")
    for role_name, role_id in role_ids:
        print(f"\n  Processing role: {role_name}")
        
        # First, remove ALL existing permissions
        print(f"    Removing all existing permissions...")
        cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
        print(f"    ✓ Removed all permissions")
        
        # Now add only the correct permissions
        print(f"    Adding correct permissions...")
        for perm_name in finance_perms:
            try:
                cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
                perm = cursor.fetchone()
                if perm:
                    perm_id = perm[0]
                    cursor.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                        ON CONFLICT (role_id, permission_id) DO NOTHING
                    """, (role_id, perm_id))
                    print(f"    ✓ Assigned: {perm_name}")
            except Exception as e:
                print(f"    ✗ Error assigning {perm_name}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Finance role configured correctly with Front Office and Financial Reports only!")

if __name__ == "__main__":
    print("🔧 Fixing Finance role permissions...")
    try:
        conn = get_connection()
        fix_finance_role(conn)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
