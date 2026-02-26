#!/usr/bin/env python3
"""
Script to add submenu permissions to LHIMS database.
Run with: python3 add_submenu_permissions.py
"""
import os
import sys

# Database configuration - adjust these values to match your setup
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

def add_submenu_permissions(conn):
    """Add submenu permissions to the database"""
    cursor = conn.cursor()
    
    # All submenu permissions needed
    submenu_permissions = [
        # Front Office submenu
        ('register_patient', 'Register new patients', 'patients'),
        ('view_patients_list', 'View patients list', 'patients'),
        ('view_opd_queue', 'View OPD queue', 'front_office'),
        ('manage_appointments', 'Manage appointments', 'appointments'),
        ('record_vitals', 'Record patient vitals', 'clinical'),
        
        # Nurse submenu
        ('nurse_dashboard', 'Access nurse dashboard', 'nurse'),
        ('view_triage_queue', 'View triage queue', 'nurse'),
        
        # Doctor submenu
        ('doctor_dashboard', 'Access doctor dashboard', 'doctor'),
        ('doctor_appointments', 'View doctor appointments', 'doctor'),
        ('doctor_queue', 'View doctor queue', 'doctor'),
        
        # Clinical Services submenu
        ('view_pending_encounters', 'View pending encounters', 'clinical'),
        ('view_procedures', 'View procedures', 'procedures'),
        ('search_patients', 'Search patient records', 'patients'),
        ('view_differentials', 'View G-STG differentials', 'clinical'),
        
        # IPD submenu
        ('manage_wards', 'Manage wards', 'ipd'),
        ('manage_admissions', 'Manage patient admissions', 'ipd'),
        ('doctor_duties', 'Manage doctor duties', 'ipd'),
        
        # Pharmacy submenu
        ('manage_inventory', 'Manage pharmacy inventory', 'pharmacy'),
        
        # Laboratory submenu
        ('manage_lab', 'Manage laboratory', 'lab'),
        
        # Radiology submenu
        ('manage_radiology', 'Manage radiology', 'radiology'),
        ('view_pacs', 'View PACS images', 'radiology'),
        
        # Procedures submenu
        ('manage_procedures', 'Manage procedures', 'procedures'),
        
        # Finance submenu
        ('billing', 'Access billing module', 'billing'),
        ('claims', 'Manage insurance claims', 'billing'),
        
        # Reports submenu
        ('financial_reports', 'View financial reports', 'reports'),
        ('patient_reports', 'View patient reports', 'reports'),
        ('pharmacy_reports', 'View pharmacy reports', 'reports'),
        ('lab_reports', 'View lab reports', 'reports'),
        ('radiology_reports', 'View radiology reports', 'reports'),
        ('clinical_reports', 'View clinical reports', 'reports'),
        ('expense_reports', 'View expense reports', 'reports'),
    ]
    
    # Insert permissions
    for perm_name, perm_desc, module in submenu_permissions:
        try:
            cursor.execute("""
                INSERT INTO permissions (name, description, module, is_active)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (name) DO NOTHING
            """, (perm_name, perm_desc, module))
            print(f"✓ Added/updated permission: {perm_name}")
        except Exception as e:
            print(f"✗ Error adding {perm_name}: {e}")
    
    # Get Admin role ID
    cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
    admin_role = cursor.fetchone()
    if admin_role:
        admin_role_id = admin_role[0]
        
        # Assign all submenu permissions to Admin role
        for perm_name, _, _ in submenu_permissions:
            try:
                cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
                perm = cursor.fetchone()
                if perm:
                    perm_id = perm[0]
                    cursor.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                        ON CONFLICT (role_id, permission_id) DO NOTHING
                    """, (admin_role_id, perm_id))
                    print(f"✓ Assigned {perm_name} to Admin role")
            except Exception as e:
                print(f"✗ Error assigning {perm_name}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Submenu permissions added successfully!")

if __name__ == "__main__":
    print("🔧 Adding submenu permissions to LHIMS database...")
    try:
        conn = get_connection()
        add_submenu_permissions(conn)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        sys.exit(1)
