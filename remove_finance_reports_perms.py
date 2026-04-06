#!/usr/bin/env python3
"""
Script to remove financial reports from Finance role.
Run with: python3 remove_finance_reports_perms.py
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

def remove_finance_reports_permissions(conn):
    """Remove financial report permissions from Finance/accountant role"""
    cursor = conn.cursor()
    
    # Permissions to remove from Finance role
    report_perms_to_remove = [
        'menu_reports',
        'financial_reports', 
        'patient_reports',
        'expense_reports',
        'admin_reports'
    ]
    
    # Get accountant role ID
    cursor.execute("SELECT id FROM roles WHERE name = 'accountant'")
    accountant_role = cursor.fetchone()
    
    # Get finance role ID
    cursor.execute("SELECT id FROM roles WHERE name = 'finance'")
    finance_role = cursor.fetchone()
    
    role_ids = []
    if accountant_role:
        role_ids.append(('accountant', accountant_role[0]))
    if finance_role:
        role_ids.append(('finance', finance_role[0]))
    
    if not role_ids:
        print("⚠ Neither accountant nor finance role found!")
        return
    
    print("🗑️ Removing report permissions from Finance role...")
    for role_name, role_id in role_ids:
        print(f"\n  Processing role: {role_name}")
        for perm_name in report_perms_to_remove:
            try:
                # First get the permission ID
                cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
                perm = cursor.fetchone()
                if perm:
                    perm_id = perm[0]
                    # Remove from role_permissions
                    cursor.execute("""
                        DELETE FROM role_permissions 
                        WHERE role_id = %s AND permission_id = %s
                    """, (role_id, perm_id))
                    if cursor.rowcount > 0:
                        print(f"    ✓ Removed: {perm_name}")
                    else:
                        print(f"    - Not assigned: {perm_name}")
                else:
                    print(f"    - Permission not found: {perm_name}")
            except Exception as e:
                print(f"    ✗ Error removing {perm_name}: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("\n✅ Report permissions removed from Finance role successfully!")

if __name__ == "__main__":
    print("🔧 Removing financial reports from Finance role...")
    try:
        conn = get_connection()
        remove_finance_reports_permissions(conn)
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        sys.exit(1)
