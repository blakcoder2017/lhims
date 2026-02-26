#!/usr/bin/env python3
"""
Script to delete all drugs and related data from LHIMS database.
This deletes:
- Pharmacy drugs (pharmacy_drug table)
- Inventory medications (medications table)
- All related data (batches, stock, transactions, interactions, etc.)
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql+psycopg2://postgres:password123@localhost:5433/lhims"

def delete_all_drugs():
    """Delete all drugs and related data from the database."""
    
    engine = create_engine(DATABASE_URL)
    
    # Use explicit connection to handle transactions properly
    with engine.connect() as conn:
        try:
            # Start a transaction
            trans = conn.begin()
            
            print("=" * 60)
            print("DELETING ALL DRUGS AND RELATED DATA FROM LHIMS")
            print("=" * 60)
            
            # ============================================================
            # PHARMACY MODULE - Delete in order of dependencies
            # ============================================================
            
            # 1. Delete pharmacy_dispense_allocations (depends on dispense_item and batch)
            result = conn.execute(text("DELETE FROM pharmacy_dispense_allocation"))
            print(f"Deleted {result.rowcount} pharmacy_dispense_allocation records")
            
            # 2. Delete pharmacy_dispense_items (depends on dispense and drug)
            result = conn.execute(text("DELETE FROM pharmacy_dispense_item"))
            print(f"Deleted {result.rowcount} pharmacy_dispense_item records")
            
            # 3. Delete pharmacy_dispenses
            result = conn.execute(text("DELETE FROM pharmacy_dispense"))
            print(f"Deleted {result.rowcount} pharmacy_dispense records")
            
            # 4. Delete pharmacy_stock_ledger (depends on store, drug, batch)
            result = conn.execute(text("DELETE FROM pharmacy_stock_ledger"))
            print(f"Deleted {result.rowcount} pharmacy_stock_ledger records")
            
            # 5. Delete pharmacy_batches (depends on drug, store, supplier)
            result = conn.execute(text("DELETE FROM pharmacy_batch"))
            print(f"Deleted {result.rowcount} pharmacy_batch records")
            
            # 6. Delete pharmacy_drug_interactions (depends on drugs)
            result = conn.execute(text("DELETE FROM pharmacy_drug_interaction"))
            print(f"Deleted {result.rowcount} pharmacy_drug_interaction records")
            
            # 7. Delete patient_active_medication (depends on patient and drug)
            result = conn.execute(text("DELETE FROM patient_active_medication"))
            print(f"Deleted {result.rowcount} patient_active_medication records")
            
            # 8. Clear pharmacy_drug_id references in prescriptions (foreign key constraint)
            result = conn.execute(text("UPDATE prescriptions SET pharmacy_drug_id = NULL WHERE pharmacy_drug_id IS NOT NULL"))
            print(f"Cleared pharmacy_drug_id in {result.rowcount} prescription records")
            
            # 9. Delete pharmacy_drugs (main drug table)
            result = conn.execute(text("DELETE FROM pharmacy_drug"))
            print(f"Deleted {result.rowcount} pharmacy_drug records")
            
            # ============================================================
            # INVENTORY MODULE - Delete in order of dependencies
            # ============================================================
            
            # 9. Delete inventory_transactions (depends on medication, stock_item, prescription)
            result = conn.execute(text("DELETE FROM inventory_transactions"))
            print(f"Deleted {result.rowcount} inventory_transactions records")
            
            # 10. Delete drug_interactions (depends on medications)
            result = conn.execute(text("DELETE FROM drug_interactions"))
            print(f"Deleted {result.rowcount} drug_interactions records")
            
            # 11. Delete formulary_rules (depends on medication)
            result = conn.execute(text("DELETE FROM formulary_rules"))
            print(f"Deleted {result.rowcount} formulary_rules records")
            
            # 12. Clear medication_id references in prescriptions (foreign key constraint)
            result = conn.execute(text("UPDATE prescriptions SET medication_id = NULL WHERE medication_id IS NOT NULL"))
            print(f"Cleared medication_id in {result.rowcount} prescription records")
            
            # 13. Delete stock_items (depends on medication and supplier)
            result = conn.execute(text("DELETE FROM stock_items"))
            print(f"Deleted {result.rowcount} stock_items records")
            
            # 14. Delete medications (main medication table)
            result = conn.execute(text("DELETE FROM medications"))
            print(f"Deleted {result.rowcount} medications records")
            
            # ============================================================
            # DRUG ADMINISTRATION MODULE
            # ============================================================
            
            # 14. Delete drug_administrations
            result = conn.execute(text("DELETE FROM drug_administrations"))
            print(f"Deleted {result.rowcount} drug_administrations records")
            
            print("=" * 60)
            print("DELETION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            
            # Commit the transaction
            trans.commit()
            print("\nAll changes have been committed to the database.")
            
        except Exception as e:
            print(f"\nERROR: {e}")
            print("Rolling back all changes...")
            trans.rollback()
            print("Rollback complete. No changes were made.")
            sys.exit(1)
    
    engine.dispose()


def verify_deletion():
    """Verify that all drug data has been deleted."""
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("\n" + "=" * 60)
        print("VERIFICATION - Remaining drug records:")
        print("=" * 60)
        
        tables = [
            "pharmacy_drug",
            "medications",
            "pharmacy_batch",
            "stock_items",
            "pharmacy_dispense",
            "pharmacy_dispense_item",
            "pharmacy_stock_ledger",
            "pharmacy_drug_interaction",
            "drug_interactions",
            "patient_active_medication",
            "drug_administrations"
        ]
        
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  {table}: {count} records")
            except Exception as e:
                print(f"  {table}: Error - {e}")
    
    engine.dispose()


if __name__ == "__main__":
    print("\nThis will delete ALL drugs and related data from LHIMS.")
    print("This action cannot be undone!")
    print()
    
    # Run deletion
    delete_all_drugs()
    
    # Verify
    verify_deletion()
