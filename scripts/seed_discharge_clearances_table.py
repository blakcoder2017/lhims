"""
Seed script to create the discharge_clearances table.

This script creates the discharge_clearances table manually if it doesn't exist.
Use this if the migration fails or the table needs to be created manually.

Usage:
    python scripts/seed_discharge_clearances_table.py
"""
import sys
import os

# --- Add app to Python path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# --- End path setup ---

from app.db.database import engine, Base
from app.models.discharge_models import DischargeClearance
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

def check_table_exists(engine, table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def create_discharge_clearances_table():
    """Create the discharge_clearances table if it doesn't exist"""
    table_name = "discharge_clearances"
    
    print(f"--- Creating {table_name} table ---")
    
    # Check if table already exists
    if check_table_exists(engine, table_name):
        print(f"Table '{table_name}' already exists. Skipping creation.")
        return
    
    try:
        # Create the table using raw SQL to match the migration exactly
        # Note: Using SERIAL for auto-incrementing ID in PostgreSQL
        create_table_sql = """
        CREATE TABLE discharge_clearances (
            id SERIAL NOT NULL,
            admission_id INTEGER NOT NULL,
            patient_id INTEGER NOT NULL,
            payment_cleared BOOLEAN NOT NULL DEFAULT false,
            payment_cleared_at TIMESTAMP,
            payment_cleared_by_id INTEGER,
            nursing_cleared BOOLEAN NOT NULL DEFAULT false,
            nursing_cleared_at TIMESTAMP,
            nursing_cleared_by_id INTEGER,
            payment_notes TEXT,
            nursing_notes TEXT,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT true,
            PRIMARY KEY (id),
            CONSTRAINT fk_discharge_clearances_admission_id_admissions 
                FOREIGN KEY(admission_id) REFERENCES admissions (id),
            CONSTRAINT fk_discharge_clearances_patient_id_patients 
                FOREIGN KEY(patient_id) REFERENCES patients (id),
            CONSTRAINT fk_discharge_clearances_payment_cleared_by_id_users 
                FOREIGN KEY(payment_cleared_by_id) REFERENCES users (id),
            CONSTRAINT fk_discharge_clearances_nursing_cleared_by_id_users 
                FOREIGN KEY(nursing_cleared_by_id) REFERENCES users (id),
            CONSTRAINT uq_discharge_clearances_admission_id UNIQUE (admission_id)
        )
        """
        
        # Create index SQL
        create_index_sql = """
        CREATE INDEX ix_discharge_clearances_id ON discharge_clearances (id)
        """
        
        # Execute SQL
        with engine.connect() as conn:
            # Start a transaction
            trans = conn.begin()
            try:
                # Create the table
                conn.execute(text(create_table_sql))
                print(f"✓ Created table '{table_name}'")
                
                # Create the index
                conn.execute(text(create_index_sql))
                print(f"✓ Created index 'ix_discharge_clearances_id'")
                
                # Commit the transaction
                trans.commit()
                print(f"✓ Successfully created table '{table_name}' with all constraints and indexes")
                
            except Exception as e:
                trans.rollback()
                raise
        
        # Verify the table was created
        if check_table_exists(engine, table_name):
            print(f"✓ Verification: Table '{table_name}' exists in database")
        else:
            print(f"✗ Warning: Table '{table_name}' was not created successfully")
            
    except ProgrammingError as e:
        # If table creation fails due to missing dependencies (e.g., foreign key tables)
        error_msg = str(e).lower()
        if "does not exist" in error_msg or "relation" in error_msg:
            print(f"✗ Error: Required table does not exist: {e}")
            print("  Please ensure all dependent tables (admissions, patients, users) exist first.")
            raise
        elif "already exists" in error_msg:
            print(f"✓ Table '{table_name}' already exists (created concurrently)")
        else:
            print(f"✗ Error creating table: {e}")
            raise
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise

def verify_table_structure():
    """Verify the table structure matches the model"""
    print("\n--- Verifying table structure ---")
    
    inspector = inspect(engine)
    
    if not check_table_exists(engine, "discharge_clearances"):
        print("✗ Table 'discharge_clearances' does not exist")
        return False
    
    # Get table columns
    columns = inspector.get_columns("discharge_clearances")
    column_names = [col['name'] for col in columns]
    
    # Expected columns from the model
    expected_columns = [
        'id', 'admission_id', 'patient_id', 
        'payment_cleared', 'payment_cleared_at', 'payment_cleared_by_id',
        'nursing_cleared', 'nursing_cleared_at', 'nursing_cleared_by_id',
        'payment_notes', 'nursing_notes',
        'created_at', 'updated_at', 'is_active'
    ]
    
    missing_columns = [col for col in expected_columns if col not in column_names]
    
    if missing_columns:
        print(f"✗ Missing columns: {', '.join(missing_columns)}")
        return False
    
    print(f"✓ Table has all required columns ({len(column_names)} total)")
    
    # Check foreign keys
    foreign_keys = inspector.get_foreign_keys("discharge_clearances")
    expected_fk_count = 4  # admission_id, patient_id, payment_cleared_by_id, nursing_cleared_by_id
    
    if len(foreign_keys) < expected_fk_count:
        print(f"✗ Missing foreign keys: Expected at least {expected_fk_count}, found {len(foreign_keys)}")
        return False
    
    print(f"✓ Table has all required foreign keys ({len(foreign_keys)} total)")
    
    # Check unique constraint on admission_id
    unique_constraints = inspector.get_unique_constraints("discharge_clearances")
    has_admission_unique = any(
        'admission_id' in constraint['column_names'] 
        for constraint in unique_constraints
    )
    
    if not has_admission_unique:
        print("✗ Missing unique constraint on 'admission_id'")
        return False
    
    print("✓ Unique constraint on 'admission_id' exists")
    print("✓ Table structure verification complete")
    
    return True

def main():
    """Main function"""
    print("=" * 60)
    print("Discharge Clearances Table Seed Script")
    print("=" * 60)
    
    try:
        # Create the table
        create_discharge_clearances_table()
        
        # Verify the structure
        verify_table_structure()
        
        print("\n" + "=" * 60)
        print("✓ Seed script completed successfully")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Seed script failed: {e}")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
