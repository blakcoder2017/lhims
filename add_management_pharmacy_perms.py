#!/usr/bin/env python3
"""
Script to grant all pharmacy and inventory permissions to the Management role.
Run with: python3 add_management_pharmacy_perms.py

This script gives the Management role full access to:
- Pharmacy menu
- Inventory menu  
- All pharmacy module permissions
- All inventory permissions
- IMS (Inventory Management System) permissions
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


def add_pharmacy_permissions_to_management(conn):
    """Add all pharmacy/inventory permissions to the Management role"""
    conn.set_session(autocommit=True)
    cursor = conn.cursor()
    
    # Get Management role ID
    cursor.execute("SELECT id FROM roles WHERE name = 'Management'")
    result = cursor.fetchone()
    if not result:
        print("Creating Management role...")
        cursor.execute("""
            INSERT INTO roles (name, description)
            VALUES ('Management', 'Management role for reports and dashboards')
            ON CONFLICT (name) DO NOTHING
            RETURNING id
        """)
        result = cursor.fetchone()
        if not result:
            print("Failed to create Management role")
            return
    
    mgmt_id = result[0]
    print(f"Management role ID: {mgmt_id}")
    
    # Get current max permission ID
    cursor.execute("SELECT COALESCE(MAX(id), 0) FROM permissions")
    next_id = cursor.fetchone()[0] + 1
    
    # Define all permissions to create and assign
    permissions_to_create = [
        # Menu permissions
        ('menu_pharmacy', 'Access Pharmacy menu', 'menu'),
        ('menu_inventory', 'Access Inventory menu', 'menu'),
        
        # Pharmacy module permissions
        ('create_prescriptions', 'Create prescriptions', 'pharmacy'),
        ('dispense_medications', 'Dispense medications', 'pharmacy'),
        ('manage_inventory', 'Manage pharmacy inventory', 'pharmacy'),
        ('prescription_create', 'Create prescriptions for encounters', 'pharmacy'),
        ('view_prescriptions', 'View prescriptions', 'pharmacy'),
        
        # Additional pharmacy permissions
        ('pharmacy_dispense', 'Dispense medications', None),
        ('pharmacy_inventory', 'Manage inventory', None),
        ('pharmacy_view', 'View pharmacy records', None),
        
        # Reports
        ('pharmacy_reports', 'View pharmacy reports', 'reports'),
        
        # Inventory module permissions
        ('inventory_dashboard', 'Access inventory dashboard', 'inventory'),
        ('inventory_medications', 'Manage medications', 'inventory'),
        ('inventory_stock', 'Manage stock', 'inventory'),
        
        # IMS permissions
        ('ims_dashboard', 'Access IMS dashboard', 'ims'),
        ('ims_manage', 'Full IMS management', 'ims'),
    ]
    
    # Create permissions
    print("\n📝 Creating permissions...")
    for perm_name, perm_desc, module in permissions_to_create:
        cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO permissions (id, name, description, module, is_active) VALUES (%s, %s, %s, %s, true)",
                (next_id, perm_name, perm_desc, module)
            )
            print(f"  ✓ Created {perm_name}")
            next_id += 1
        else:
            print(f"  ✓ {perm_name} already exists")
    
    # Assign permissions to Management role
    print("\n🔐 Assigning permissions to Management role...")
    for perm_name, _, _ in permissions_to_create:
        cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
        result = cursor.fetchone()
        if result:
            cursor.execute(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (mgmt_id, result[0])
            )
            print(f"  ✓ Assigned {perm_name}")
    
    # Show final count
    cursor.execute("""
        SELECT COUNT(*) FROM role_permissions rp
        JOIN permissions p ON rp.permission_id = p.id
        WHERE rp.role_id = %s
        AND (p.module IN ('pharmacy', 'menu', 'inventory', 'ims', 'reports') 
             OR p.name LIKE 'pharmacy_%' 
             OR p.name LIKE 'inventory_%'
             OR p.name LIKE 'ims_%')
    """, (mgmt_id,))
    count = cursor.fetchone()[0]
    print(f"\n✅ Total pharmacy/inventory/ims permissions assigned: {count}")
    
    cursor.close()


if __name__ == "__main__":
    print("🔧 Adding pharmacy/inventory/ims permissions to Management role...")
    try:
        conn = get_connection()
        add_pharmacy_permissions_to_management(conn)
        conn.close()
        print("\n✅ Done!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
