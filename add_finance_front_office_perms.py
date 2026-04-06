#!/usr/bin/env python3
"""
Script to add front office permissions to Finance role.
Run with: python3 add_finance_front_office_perms.py
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

def add_finance_front_office_permissions(conn):
    """Add front office permissions to Finance/accountant role"""
    cursor = conn.cursor()
    
    # First, ensure all required permissions exist
    permissions_to_add = [
        # Menu permissions
        ('menu_front_office', 'Access Front Office menu', 'menu'),
        ('menu_direct_service', 'Access Direct Service Requests menu', 'menu'),
        ('menu_patients', 'Access Patients menu', 'menu'),
        # Submenu permissions  
        ('register_patient', 'Register new patients', 'patients'),
        ('view_patients_list', 'View patients list', 'patients'),
        ('view_opd_queue', 'View OPD queue', 'front_office'),
        ('manage_appointments', 'Manage appointments', 'appointments'),
        # Patient permissions
        ('patient_view', 'View patient information', 'patients'),
        ('patient_create', 'Create new patients', 'patients'),
        ('patient_edit', 'Edit patient information', 'patients'),
        # Appointment permissions
        ('appointment_view', 'View appointments', 'appointments'),
        ('appointment_create', 'Create appointments', 'appointments'),
        ('appointment_edit', 'Edit appointments', 'appointments'),
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
    
    # Get permission IDs for front office permissions
    front_office_perms = [
        'menu_front_office', 'menu_direct_service', 'menu_patients',
        'register_patient', 'view_patients_list', 'view_opd_queue', 'manage_appointments',
        'patient_view', 'patient_create', 'patient_edit',
        'appointment_view', 'appointment_create', 'appointment_edit'
    ]
    
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
    
    print("\n🔗 Assigning permissions to roles...")
    for role_name, role_id in role_ids:
        print(f"\n  Processing role: {role_name}")
        for perm_name in front_office_perms:
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
    print("\n✅ Front office permissions added to Finance role successfully!")

if __name__ == "__main__":
    print("🔧 Adding front office permissions to Finance role...")
    try:
        conn = get_connection()
        add_finance_front_office_permissions(conn)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("\nPlease set the following environment variables:")
        print("  POSTGRES_HOST (default: localhost)")
        print("  POSTGRES_PORT (default: 5433)")
        print("  POSTGRES_DB (default: lhims)")
        print("  POSTGRES_USER (default: postgres)")
        print("  POSTGRES_PASSWORD (default: password123)")
        sys.exit(1)
