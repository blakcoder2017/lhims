#!/usr/bin/env python3
"""
Script to add prescription_create permission to LHIMS database.
Run with: python3 add_prescription_permission.py
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
        return conn, 'postgres'
    except ImportError:
        try:
            import pymysql
            conn = pymysql.connect(
                host=DB_CONFIG['host'],
                port=int(DB_CONFIG['port']),
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['dbname']
            )
            return conn, 'mysql'
        except Exception as e:
            raise e

def add_prescription_permission(conn, db_type):
    """Add prescription_create permission and assign to roles"""
    cursor = conn.cursor()
    
    # Permission to add
    permission = ('prescription_create', 'Create prescriptions for encounters', 'pharmacy')
    
    print(f"Adding permission: {permission[0]} - {permission[1]}")
    
    # Check if permission already exists
    cursor.execute("SELECT id FROM permissions WHERE name = %s", (permission[0],))
    existing_perm = cursor.fetchone()
    
    if existing_perm:
        print(f"✓ Permission '{permission[0]}' already exists in database")
        perm_id = existing_perm[0]
    else:
        # Insert permission - get max id first to avoid conflict
        cursor.execute("SELECT MAX(id) FROM permissions")
        max_id = cursor.fetchone()[0] or 0
        new_id = max_id + 1
        
        try:
            if db_type == 'postgres':
                cursor.execute("""
                    INSERT INTO permissions (id, name, description, module, is_active)
                    VALUES (%s, %s, %s, %s, true)
                """, (new_id, permission[0], permission[1], permission[2]))
            else:
                cursor.execute("""
                    INSERT INTO permissions (name, description, module, is_active)
                    VALUES (%s, %s, %s, true)
                """, (permission[0], permission[1], permission[2]))
            print(f"✓ Added permission: {permission[0]}")
        except Exception as e:
            print(f"✗ Error adding permission: {e}")
            return
        
        # Get permission ID after insert
        cursor.execute("SELECT id FROM permissions WHERE name = %s", (permission[0],))
        perm_result = cursor.fetchone()
        if not perm_result:
            print("✗ Permission not found after insert!")
            return
        perm_id = perm_result[0]
    
    print(f"Permission ID: {perm_id}")
    
    # Roles to assign permission to
    roles_to_assign = ['Doctor', 'Nurse', 'Clinician', 'Admin']
    
    for role_name in roles_to_assign:
        cursor.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
        role = cursor.fetchone()
        if role:
            role_id = role[0]
            try:
                if db_type == 'postgres':
                    cursor.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                        ON CONFLICT (role_id, permission_id) DO NOTHING
                    """, (role_id, perm_id))
                else:
                    cursor.execute("""
                        INSERT IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                    """, (role_id, perm_id))
                print(f"✓ Assigned {permission[0]} to {role_name} role")
            except Exception as e:
                print(f"✗ Error assigning to {role_name}: {e}")
        else:
            print(f"⚠ Role '{role_name}' not found!")
    
    conn.commit()
    cursor.close()
    print("\n✅ prescription_create permission added successfully!")
    print("\nThe following roles now have prescription_create permission:")
    for role_name in roles_to_assign:
        print(f"  - {role_name}")

if __name__ == "__main__":
    print("🔧 Adding prescription_create permission to LHIMS database...")
    try:
        conn, db_type = get_connection()
        print(f"Detected database type: {db_type}")
        add_prescription_permission(conn, db_type)
        conn.close()
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("\nPlease set the following environment variables:")
        print("  POSTGRES_HOST (default: localhost)")
        print("  POSTGRES_PORT (default: 5432)")
        print("  POSTGRES_DB (default: lhims)")
        print("  POSTGRES_USER (default: postgres)")
        print("  POSTGRES_PASSWORD (default: password123)")
        sys.exit(1)
