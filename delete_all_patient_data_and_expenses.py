#!/usr/bin/env python3
"""
Script to delete all patient data, orders, and expenses from the LHIMS database.

This script will:
1. Delete all patient-related data (patients, encounters, admissions, visits, orders)
2. Delete all expenses

WARNING: This operation is IRREVERSIBLE. Make sure to backup your database first.

Uses PostgreSQL TRUNCATE with CASCADE to handle foreign key constraints.
"""

import os
import sys
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password123@localhost:5433/lhims")

def get_engine():
    """Create database engine."""
    return create_engine(DATABASE_URL, echo=False)

def delete_all_patient_data_and_expenses():
    """Delete all patient data, orders, and expenses using TRUNCATE with CASCADE."""
    
    engine = get_engine()
    
    # Tables to truncate in order (respecting dependencies - child tables first)
    # We'll use TRUNCATE with CASCADE which automatically handles FK constraints
    
    tables_to_truncate = [
        # Audit and logs (independent)
        "audit_logs",
        
        # Patient-related child tables first
        "image_annotations",
        "radiology_images",
        "lab_samples",
        "qc_records",
        "drug_administrations",
        "inventory_transactions",
        "encounter_diseases",
        "admission_notes",
        "fluid_balance",
        "birth_records",
        "antenatal_visits",
        "triage_vitals",
        "charge_payments",
        "receipts",
        
        # Orders and prescriptions
        "radiology_orders",
        "lab_orders",
        "prescriptions",
        "procedures",
        
        # Billing
        "charges",
        "payments",
        "nhis_claims",
        "invoices",
        
        # Encounters and visits
        "encounters",
        "admissions",
        "opd_visits",
        "opd_queue",
        "scheduled_appointments",
        
        # Main patient table (last)
        "patients",
        
        # Expenses (separate from patient data)
        "expenses",
    ]
    
    try:
        with engine.connect() as conn:
            # Start transaction
            transaction = conn.begin()
            
            for table in tables_to_truncate:
                try:
                    # Use TRUNCATE with CASCADE to delete all data
                    # CASCADE will automatically delete dependent tables
                    result = conn.execute(text(f'TRUNCATE TABLE {table} CASCADE'))
                    logger.info(f"Truncated table: {table}")
                except Exception as e:
                    logger.warning(f"Could not truncate {table}: {e}")
            
            transaction.commit()
            logger.info("All patient data, orders, and expenses have been deleted successfully!")
            
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        # Rollback on error
        with engine.connect() as conn:
            conn.rollback()
        raise

def main():
    """Main entry point."""
    print("=" * 60)
    print("WARNING: This will delete ALL patient data, orders, and expenses!")
    print("This operation is IRREVERSIBLE!")
    print("=" * 60)
    
    # Skip confirmation for automated execution
    print("\nStarting deletion process...")
    delete_all_patient_data_and_expenses()
    print("\nDeletion completed successfully!")

if __name__ == "__main__":
    main()
