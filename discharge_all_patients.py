#!/usr/bin/env python3
"""
Discharge all currently admitted patients.
This script finds all active admissions and discharges them by:
- Setting discharge_date to current time
- Setting status to DISCHARGED
- Releasing the bed (setting bed status to AVAILABLE)
- Updating ward occupancy

This version uses direct SQLAlchemy queries to avoid model import issues.
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


def discharge_all_patients():
    """Discharge all currently admitted patients."""
    db = SessionLocal()
    
    try:
        # First, let's find all active admissions with their bed and ward info
        # We use raw SQL to avoid model relationship issues
        result = db.execute(text("""
            SELECT 
                a.id,
                a.admission_number,
                a.patient_id,
                a.ward_id,
                a.bed_id,
                a.admission_date,
                w.name as ward_name,
                b.bed_number
            FROM admissions a
            LEFT JOIN wards w ON a.ward_id = w.id
            LEFT JOIN beds b ON a.bed_id = b.id
            WHERE a.status = 'admitted'
        """))
        
        active_admissions = result.fetchall()
        
        if not active_admissions:
            print("No active admissions found. All patients have already been discharged.")
            return
        
        print(f"Found {len(active_admissions)} active admission(s)")
        print("-" * 60)
        
        discharged_count = 0
        error_count = 0
        
        for admission in active_admissions:
            try:
                admission_id = admission[0]
                admission_number = admission[1]
                patient_id = admission[2]
                ward_id = admission[3]
                bed_id = admission[4]
                admission_date = admission[5]
                ward_name = admission[6] if admission[6] else "N/A"
                bed_number = admission[7] if admission[7] else "N/A"
                
                print(f"\nDischarging: Admission #{admission_number} - Patient ID: {patient_id}")
                print(f"  Ward: {ward_name}")
                print(f"  Bed: {bed_number}")
                print(f"  Admission Date: {admission_date}")
                
                # Update admission status to discharged
                db.execute(text("""
                    UPDATE admissions 
                    SET status = 'discharged', 
                        discharge_date = :discharge_date
                    WHERE id = :admission_id
                """), {
                    "discharge_date": datetime.now(),
                    "admission_id": admission_id
                })
                
                # Release the bed
                if bed_id:
                    db.execute(text("""
                        UPDATE beds 
                        SET status = 'available'
                        WHERE id = :bed_id
                    """), {"bed_id": bed_id})
                    print(f"  Bed {bed_number} released")
                
                # Update ward occupancy
                if ward_id:
                    db.execute(text("""
                        UPDATE wards 
                        SET current_occupancy = current_occupancy - 1
                        WHERE id = :ward_id AND current_occupancy > 0
                    """), {"ward_id": ward_id})
                    print(f"  Ward {ward_name} occupancy decremented")
                
                discharged_count += 1
                print(f"  Status: DISCHARGED")
                
            except Exception as e:
                error_count += 1
                print(f"  ERROR: {str(e)}")
                db.rollback()
                continue
        
        # Commit all changes
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"SUMMARY:")
        print(f"  Total active admissions: {len(active_admissions)}")
        print(f"  Successfully discharged: {discharged_count}")
        print(f"  Errors: {error_count}")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DISCHARGE ALL PATIENTS")
    print("=" * 60)
    discharge_all_patients()
    print("\nDone!")
