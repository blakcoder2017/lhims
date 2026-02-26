#!/usr/bin/env python3
"""Update all lab test costs to 200 GHS."""
import os
import sys
from decimal import Decimal

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they're registered
from app.models import *  # noqa: F401, F403
from app.core.config import settings

# Use the actual database URL from environment
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL

# check_same_thread is SQLite-only; PostgreSQL rejects it
_connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def update_lab_test_costs():
    """Update all lab test costs to 200 GHS."""
    db = SessionLocal()
    try:
        # Get all active lab tests
        lab_tests = db.query(LabTest).filter(LabTest.is_active == True).all()
        
        print(f"Found {len(lab_tests)} active lab tests")
        
        # Update each lab test cost to 200 GHS
        new_cost = Decimal('200.00')
        updated_count = 0
        
        for test in lab_tests:
            old_cost = test.cost
            test.cost = new_cost
            updated_count += 1
            print(f"Updated '{test.test_name}': {old_cost} -> {new_cost} GHS")
        
        # Commit the changes
        db.commit()
        print(f"\nSuccessfully updated {updated_count} lab test costs to 200 GHS")
        
    except Exception as e:
        db.rollback()
        print(f"Error updating lab test costs: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_lab_test_costs()
