#!/usr/bin/env python3
"""
Standalone script to add menu permissions to LHIMS database.
Run with: python3 add_permissions_direct.py
"""
import os
import sys

# Database configuration - adjust these values to match your setup
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'dbname': os.getenv('POSTGRES_DB', 'lhims'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password123'),
}

def get_connection():
    """Get database connection"""
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except ImportError:
        # Try MySQL as fallback
        import pymysql
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=int(DB_CONFIG['port']),
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['dbname']
        )
        return conn

def add_menu_permissions(conn):
    """Add menu permissions to the database"""
    cursor = conn.cursor()
    
    # Menu permissions to add
    menu_permissions = [
        ('menu_front_office', 'Access Front Office menu', 'menu'),
        ('menu_direct_service', 'Access Direct Service Requests menu', 'menu'),
        ('menu_nurse', 'Access Nurse menu', 'menu'),
        ('menu_doctor', 'Access Doctor menu', 'menu'),
        ('menu_clinical', 'Access Clinical Services menu', 'menu'),
        ('menu_opd', 'Access OPD menu', 'menu'),
        ('menu_emergency', 'Access Emergency menu', 'menu'),
        ('menu_ipd', 'Access IPD menu', 'menu'),
        ('menu_patients', 'Access Patients menu', 'menu'),
        ('menu_pharmacy', 'Access Pharmacy menu', 'menu'),
        ('menu_lab', 'Access Laboratory menu', 'menu'),
        ('menu_radiology', 'Access Radiology menu', 'menu'),
        ('menu_procedures', 'Access Procedures menu', 'menu'),
        ('menu_maternity', 'Access Maternity menu', 'menu'),
        ('menu_finance', 'Access Finance menu', 'menu'),
        ('menu_reports', 'Access Reports menu', 'menu'),
    ]
    
    # Check database type
    cursor.execute("SELECT version()")
    db_type = 'postgres' if 'PostgreSQL' in cursor.fetchone()[0] else 'mysql'
    
    print(f"Detected database type: {db_type}")
    
    # Insert permissions
    for perm_name, perm_desc, module in menu_permissions:
        try:
            if db_type == 'postgres':
                cursor.execute("""
                    INSERT INTO permissions (name, description, module, is_active)
                    VALUES (%s, %s, %s, true)
                    ON CONFLICT (name) DO NOTHING
                """, (perm_name, perm_desc, module))
            else:
                cursor.execute("""
                    INSERT INTO permissions (name, description, module, is_active)
                    VALUES (%s, %s, %s, true)
                    ON DUPLICATE KEY UPDATE description = VALUES(description)
                """, (perm_name, perm_desc, module))
            print(f"✓ Added/updated permission: {perm_name}")
        except Exception as e:
            print(f"✗ Error adding {perm_name}: {e}")
    
    # Get permission IDs for Admin role
    cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
    admin_role = cursor.fetchone()
    if admin_role:
        admin_role_id = admin_role[0]
        print(f"\nAdmin role ID: {admin_role_id}")
        
        # Assign all menu permissions to Admin role
        for perm_name, _, _ in menu_permissions:
            try:
                cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
                perm = cursor.fetchone()
                if perm:
                    perm_id = perm[0]
                    if db_type == 'postgres':
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s)
                            ON CONFLICT (role_id, permission_id) DO NOTHING
                        """, (admin_role_id, perm_id))
                    else:
                        cursor.execute("""
                            INSERT IGNORE INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s)
                        """, (admin_role_id, perm_id))
                    print(f"✓ Assigned {perm_name} to Admin role")
            except Exception as e:
                print(f"✗ Error assigning {perm_name}: {e}")
    else:
        print("⚠ Admin role not found!")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Menu permissions added successfully!")

if __name__ == "__main__":
    print("🔧 Adding menu permissions to LHIMS database...")
    try:
        conn = get_connection()
        add_menu_permissions(conn)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("\nPlease set the following environment variables:")
        print("  POSTGRES_HOST (default: localhost)")
        print("  POSTGRES_PORT (default: 5432)")
        print("  POSTGRES_DB (default: lhims)")
        print("  POSTGRES_USER (default: postgres)")
        print("  POSTGRES_PASSWORD (default: password123)")
        sys.exit(1)
