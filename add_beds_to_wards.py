#!/usr/bin/env python3
"""
Script to add 100 beds in each ward with no charge.
This script creates 100 beds per ward with charge_per_day = 0.00
Uses direct SQL to avoid model import issues.
"""
import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

# Use the database URL from .env
DATABASE_URL = "postgresql+psycopg2://postgres:password123@localhost:5433/lhims"

# check_same_thread is SQLite-only; PostgreSQL rejects it
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def add_beds_to_wards():
    """Add 100 beds to each ward with no charge using direct SQL"""
    
    session = SessionLocal()
    
    try:
        # Get all active wards using SQL
        result = session.execute(text("SELECT id, name, capacity FROM wards WHERE is_active = true"))
        wards = result.fetchall()
        
        if not wards:
            print("No active wards found in the database.")
            return
        
        print(f"Found {len(wards)} active wards:")
        for ward in wards:
            print(f"  - {ward[1]} (ID: {ward[0]}, Current Capacity: {ward[2]})")
        
        total_beds_created = 0
        
        # Add 100 beds to each ward
        for ward in wards:
            ward_id = ward[0]
            ward_name = ward[1]
            
            # Check existing beds in this ward using SQL
            result = session.execute(
                text("SELECT COUNT(*) FROM beds WHERE ward_id = :ward_id AND is_active = true"),
                {"ward_id": ward_id}
            )
            existing_beds = result.scalar()
            
            print(f"\nProcessing ward: {ward_name} (ID: {ward_id})")
            print(f"  Existing beds: {existing_beds}")
            
            beds_to_create = 100 - existing_beds
            
            if beds_to_create <= 0:
                print(f"  Ward already has {existing_beds} beds, skipping...")
                continue
            
            print(f"  Creating {beds_to_create} new beds...")
            
            # Generate bed numbers and insert
            ward_prefix = ward_name[:3].upper().replace(" ", "")
            
            for i in range(1, beds_to_create + 1):
                bed_number = f"{ward_prefix}-{i:03d}"
                
                # Check if bed number already exists
                result = session.execute(
                    text("SELECT COUNT(*) FROM beds WHERE ward_id = :ward_id AND bed_number = :bed_number"),
                    {"ward_id": ward_id, "bed_number": bed_number}
                )
                exists = result.scalar()
                
                if exists > 0:
                    print(f"    Bed {bed_number} already exists, skipping...")
                    continue
                
                # Insert new bed with no charge (charge_per_day = 0)
                session.execute(
                    text("""
                        INSERT INTO beds (ward_id, bed_number, bed_name, status, bed_type, charge_per_day, is_active, created_at)
                        VALUES (:ward_id, :bed_number, :bed_name, 'available', 'Standard', 0.00, true, NOW())
                    """),
                    {
                        "ward_id": ward_id,
                        "bed_number": bed_number,
                        "bed_name": f"Bed {i}"
                    }
                )
                total_beds_created += 1
            
            # Commit after each ward
            session.commit()
            
            # Update ward capacity
            result = session.execute(
                text("SELECT COUNT(*) FROM beds WHERE ward_id = :ward_id AND is_active = true"),
                {"ward_id": ward_id}
            )
            new_capacity = result.scalar()
            
            session.execute(
                text("UPDATE wards SET capacity = :capacity WHERE id = :ward_id"),
                {"capacity": new_capacity, "ward_id": ward_id}
            )
            session.commit()
            print(f"  Updated ward capacity: {new_capacity}")
        
        print(f"\n=== Summary ===")
        print(f"Total new beds created: {total_beds_created}")
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    add_beds_to_wards()
