#!/usr/bin/env python3
"""
Script to delete all beds from LHIMS database.
This script deletes all data that depends on admissions, then admissions, then beds.

Usage:
    python delete_all_beds.py
"""

import os
import sys
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix DEBUG environment issue - override any conflicting env var
if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'release':
    del os.environ['DEBUG']

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Use the actual database URL from environment
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL

# check_same_thread is SQLite-only; PostgreSQL rejects it
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def delete_all_beds():
    """Delete all beds from the database."""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("DELETING ALL BEDS FROM LHIMS")
        print("=" * 60)
        
        # Get count of beds
        result = db.execute(text("SELECT COUNT(*) FROM beds"))
        bed_count_before = result.scalar()
        print(f"Beds found before deletion: {bed_count_before}")
        
        print("\nDeleting dependent data...")
        
        # Tables that reference admissions
        dependent_tables = [
            "admission_notes",
            "fluid_balance",
            "discharge_summaries",
            "drug_administrations",
        ]
        
        for table in dependent_tables:
            try:
                result = db.execute(text(f"DELETE FROM {table}"))
                print(f"Deleted {result.rowcount} from {table}")
                db.commit()
            except Exception as e:
                print(f"Note: {table} - {str(e)[:50]}")
                db.rollback()
        
        # Clear nullable FKs to admissions
        nullable_fks = [
            ("encounters", "admission_id"),
            ("invoices", "admission_id"),
            ("baby_records", "admission_id"),
            ("procedures", "admission_id"),
        ]
        
        for table, column in nullable_fks:
            try:
                result = db.execute(text(f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL"))
                if result.rowcount > 0:
                    print(f"Cleared {column} in {result.rowcount} {table} records")
                db.commit()
            except Exception as e:
                db.rollback()
        
        # Delete admissions using TRUNCATE with CASCADE (more reliable)
        print("\nDeleting admissions with TRUNCATE CASCADE...")
        try:
            # First try DELETE with CASCADE
            result = db.execute(text("DELETE FROM admissions"))
            print(f"Deleted {result.rowcount} admissions")
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"DELETE failed, trying TRUNCATE: {str(e)[:60]}")
            try:
                # Use TRUNCATE with CASCADE for complete cleanup
                db.execute(text("TRUNCATE TABLE admissions CASCADE"))
                print("Truncated admissions with CASCADE")
                db.commit()
            except Exception as e2:
                db.rollback()
                print(f"TRUNCATE also failed: {str(e2)[:60]}")
        
        print("\n" + "=" * 60)
        print("DELETING ALL BEDS")
        print("=" * 60)
        
        if bed_count_before > 0:
            result = db.execute(text("DELETE FROM beds"))
            deleted_count = result.rowcount
            print(f"Deleted {deleted_count} bed record(s)")
        else:
            print("No beds to delete.")
        
        db.commit()
        
        # Verify deletion
        result = db.execute(text("SELECT COUNT(*) FROM beds"))
        bed_count_after = result.scalar()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Beds before deletion: {bed_count_before}")
        print(f"Beds after deletion: {bed_count_after}")
        
        if bed_count_after == 0:
            print("\nAll beds have been successfully deleted!")
        else:
            print(f"\nWarning: {bed_count_after} beds still remain!")
        
        return bed_count_after == 0
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    success = delete_all_beds()
    sys.exit(0 if success else 1)
