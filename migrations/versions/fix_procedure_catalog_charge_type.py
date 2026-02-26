"""
Migration: Fix Procedure Catalog charge_type and procedure_code

This migration:
1. Sets all procedures' charge_type to 'dental_unit'
2. Auto-populates procedure_code for procedures that don't have one
"""
import random
import string
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'fix_procedure_catalog_charge_type'
down_revision = None
branch_labels = None
depends_on = None


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


def upgrade():
    """Set charge_type to dental_unit and populate missing procedure codes."""
    conn = op.get_bind()
    
    # Get all procedures
    procedures = conn.execute(sa.text("SELECT id, procedure_name, procedure_code, charge_type FROM procedure_catalog")).fetchall()
    
    print(f"Found {len(procedures)} procedures")
    
    for proc in procedures:
        proc_id = proc[0]
        proc_name = proc[1]
        proc_code = proc[2]
        charge_type = proc[3]
        
        updates = []
        params = {'id': proc_id}
        
        # Update charge_type to dental_unit if not already
        if charge_type != 'dental_unit':
            updates.append("charge_type = :charge_type")
            params['charge_type'] = 'dental_unit'
        
        # Generate procedure_code if missing
        if proc_code is None or proc_code == '' or proc_code == 'None':
            new_code = generate_procedure_code(proc_name)
            # Make sure it's unique
            while True:
                existing = conn.execute(
                    sa.text("SELECT id FROM procedure_catalog WHERE procedure_code = :code AND id != :id"),
                    {'code': new_code, 'id': proc_id}
                ).fetchone()
                if not existing:
                    break
                new_code = generate_procedure_code(proc_name)
            
            updates.append("procedure_code = :procedure_code")
            params['procedure_code'] = new_code
            print(f"  Procedure {proc_id} ('{proc_name}'): generated code {new_code}")
        
        # Execute update if there are changes
        if updates:
            sql = f"UPDATE procedure_catalog SET {', '.join(updates)} WHERE id = :id"
            conn.execute(sa.text(sql), params)
    
    print("Migration complete!")


def downgrade():
    """Revert charge_type changes (cannot revert generated codes)."""
    # We cannot revert the generated procedure codes, but we can note that
    # charge_type changes could be reverted if needed
    pass
