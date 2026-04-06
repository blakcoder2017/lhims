#!/usr/bin/env python3
"""
Clear occupancy rate for all wards_all_ward.
This script sets the occupancy for all wards to 0 by:
1. Setting all wards' current_occupancy to 0
2. Setting all beds' status to 'available'

This ensures both the stored value and dynamically calculated occupancy show 0.
"""
import os
import sys

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


def clear_ward_occupancy():
    """Clear occupancy rate for all wards."""
    db = SessionLocal()
    
    try:
        # First, let's see the current state
        print("=" * 60)
        print("CURRENT WARD OCCUPANCY STATUS")
        print("=" * 60)
        
        # Get current ward occupancy
        wards_result = db.execute(text("""
            SELECT id, name, capacity, current_occupancy
            FROM wards
            WHERE is_active = true
            ORDER BY name
        """))
        wards = wards_result.fetchall()
        
        print("\nWards:")
        print("-" * 60)
        for ward in wards:
            ward_id, name, capacity, occupancy = ward
            occupancy_rate = (occupancy / capacity * 100) if capacity > 0 else 0
            print(f"  {name}: {occupancy}/{capacity} ({occupancy_rate:.1f}%)")
        
        # Get current bed status counts
        bed_result = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM beds
            WHERE is_active = true
            GROUP BY status
        """))
        bed_counts = bed_result.fetchall()
        
        print("\nBed Status Summary:")
        print("-" * 60)
        for status, count in bed_counts:
            print(f"  {status}: {count}")
        
        print("\n" + "=" * 60)
        print("CLEARING OCCUPANCY")
        print("=" * 60)
        
        # Step 1: Set all wards' current_occupancy to 0
        print("\n1. Setting all wards' current_occupancy to 0...")
        db.execute(text("""
            UPDATE wards 
            SET current_occupancy = 0
            WHERE is_active = true
        """))
        print("   Done!")
        
        # Step 2: Set all beds' status to 'available'
        print("\n2. Setting all beds' status to 'available'...")
        db.execute(text("""
            UPDATE beds 
            SET status = 'available'
            WHERE is_active = true AND status = 'occupied'
        """))
        print("   Done!")
        
        # Commit changes
        db.commit()
        
        # Verify the changes
        print("\n" + "=" * 60)
        print("VERIFICATION - AFTER CLEARING")
        print("=" * 60)
        
        # Get updated ward occupancy
        wards_result = db.execute(text("""
            SELECT id, name, capacity, current_occupancy
            FROM wards
            WHERE is_active = true
            ORDER BY name
        """))
        wards = wards_result.fetchall()
        
        print("\nWards (after update):")
        print("-" * 60)
        for ward in wards:
            ward_id, name, capacity, occupancy = ward
            occupancy_rate = (occupancy / capacity * 100) if capacity > 0 else 0
            print(f"  {name}: {occupancy}/{capacity} ({occupancy_rate:.1f}%)")
        
        # Get updated bed status counts
        bed_result = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM beds
            WHERE is_active = true
            GROUP BY status
        """))
        bed_counts = bed_result.fetchall()
        
        print("\nBed Status Summary (after update):")
        print("-" * 60)
        for status, count in bed_counts:
            print(f"  {status}: {count}")
        
        print("\n" + "=" * 60)
        print("SUCCESS: All ward occupancy rates have been cleared to 0!")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    clear_ward_occupancy()
    print("\nDone!")
