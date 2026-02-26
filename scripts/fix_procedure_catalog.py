#!/usr/bin/env python3
"""
Standalone script to fix procedure_catalog:
1. Set all charge_type to 'dental_unit'
2. Auto-populate procedure_code for procedures that don't have one

Usage: python scripts/fix_procedure_catalog.py
"""
import sys
import os
import random
import string

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def generate_procedure_code(procedure_name: str) -> str:
    """Generate a unique procedure code based on procedure name."""
    if not procedure_name:
        return "PROC" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Get first 3-4 letters from procedure name (uppercase, alphanumeric only)
    clean_name = ''.join(c for c in procedure_name if c.isalnum()).upper()
    prefix = clean_name[:4] if len(clean_name) >= 4 else clean_name[:3]
    
    if not prefix:
        prefix = "PROC"
    
    # Generate random suffix
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    return f"{prefix}{suffix}"


def main():
    """Run the fix script."""
    # Database connection - use localhost with port 5433
    database_url = "postgresql://postgres:password123@localhost:5433/lhims"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Get all procedures
        result = conn.execute(text("SELECT id, procedure_name, procedure_code, charge_type FROM procedure_catalog"))
        procedures = result.fetchall()
        
        print(f"Found {len(procedures)} procedures in database")
        print("-" * 60)
        
        updated_count = 0
        code_generated_count = 0
        
        for proc in procedures:
            proc_id, proc_name, proc_code, charge_type = proc
            
            updates = []
            params = {'id': proc_id}
            
            # Update charge_type to dental_unit if not already
            if charge_type != 'dental_unit':
                updates.append("charge_type = :charge_type")
                params['charge_type'] = 'dental_unit'
                print(f"Procedure {proc_id} ('{proc_name}'): changing charge_type from '{charge_type}' to 'dental_unit'")
            
            # Generate procedure_code if missing
            needs_code = proc_code is None or str(proc_code).strip() == '' or str(proc_code).strip() == 'None'
            
            if needs_code:
                new_code = generate_procedure_code(proc_name)
                
                # Make sure it's unique
                max_attempts = 10
                for attempt in range(max_attempts):
                    existing = conn.execute(
                        text("SELECT id FROM procedure_catalog WHERE procedure_code = :code AND id != :id"),
                        {'code': new_code, 'id': proc_id}
                    ).fetchone()
                    if not existing:
                        break
                    new_code = generate_procedure_code(proc_name)
                
                updates.append("procedure_code = :procedure_code")
                params['procedure_code'] = new_code
                print(f"Procedure {proc_id} ('{proc_name}'): generated code {new_code}")
                code_generated_count += 1
            
            # Execute update if there are changes
            if updates:
                sql = f"UPDATE procedure_catalog SET {', '.join(updates)} WHERE id = :id"
                conn.execute(text(sql), params)
                updated_count += 1
        
        conn.commit()
        
        print("-" * 60)
        print(f"Migration complete!")
        print(f"  Total procedures: {len(procedures)}")
        print(f"  Procedures updated: {updated_count}")
        print(f"  Procedure codes generated: {code_generated_count}")


if __name__ == '__main__':
    main()
