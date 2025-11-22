"""
Data Migration Script: Migrate Existing Encounters to OPD Visits

This script creates OPD visits for existing encounters that don't have an OPD visit linked.
It groups encounters by patient and date to create appropriate OPD visits.

Usage:
    python scripts/migrate_existing_encounters_to_opd.py

Note: This script should be run AFTER the database migration that adds opd_visit_id columns.
"""

import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal, engine
from app.models.encounter_models import Encounter
from app.models.opd_models import OPDVisit, OPDVisitStatus
from app.models.patient_models import Patient
from app.crud import opd_crud
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload


def migrate_encounters_to_opd_visits():
    """
    Migrate existing encounters to OPD visits.
    Groups encounters by patient and date, creating one OPD visit per patient per day.
    """
    db = SessionLocal()
    
    try:
        print("Starting migration of existing encounters to OPD visits...")
        print("=" * 60)
        
        # Find all encounters without opd_visit_id
        encounters_without_opd = db.query(Encounter).filter(
            Encounter.opd_visit_id.is_(None),
            Encounter.admission_id.is_(None),  # Don't migrate IPD encounters
            Encounter.is_active == True
        ).options(joinedload(Encounter.patient)).all()
        
        if not encounters_without_opd:
            print("No encounters found that need migration.")
            return
        
        print(f"Found {len(encounters_without_opd)} encounters to migrate.")
        
        # Group encounters by patient and date
        from collections import defaultdict
        encounters_by_patient_date = defaultdict(list)
        
        for encounter in encounters_without_opd:
            if encounter.patient_id:
                encounter_date = encounter.encounter_date.date() if encounter.encounter_date else date.today()
                key = (encounter.patient_id, encounter_date)
                encounters_by_patient_date[key].append(encounter)
        
        print(f"Grouped into {len(encounters_by_patient_date)} patient-date combinations.")
        print()
        
        created_visits = 0
        linked_encounters = 0
        
        # Create OPD visits and link encounters
        for (patient_id, visit_date), encounters in encounters_by_patient_date.items():
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                print(f"Warning: Patient {patient_id} not found, skipping encounters.")
                continue
            
            # Determine visit type and payment status
            visit_type = "walk_in"
            payment_status = "pending"
            
            if patient.payment_mechanism:
                if patient.payment_mechanism.value == "cash":
                    payment_status = "pending"
                elif patient.payment_mechanism.value in ["nhis", "private_insurance"]:
                    payment_status = "paid"
            
            # Create OPD visit
            try:
                from app.schemas.opd_schemas import OPDVisitCreate
                opd_visit_data = OPDVisitCreate(
                    visit_type=visit_type,
                    payment_status=payment_status,
                    chief_complaint=encounters[0].chief_complaint if encounters[0].chief_complaint else None
                )
                
                opd_visit = opd_crud.create_opd_visit(db, opd_visit_data, patient_id)
                
                # Set visit_date to match the encounter date
                opd_visit.visit_date = datetime.combine(visit_date, datetime.min.time())
                db.commit()
                
                created_visits += 1
                print(f"Created OPD visit {opd_visit.opd_number} for patient {patient_id} on {visit_date}")
                
                # Link all encounters for this patient-date to the OPD visit
                for encounter in encounters:
                    encounter.opd_visit_id = opd_visit.id
                    linked_encounters += 1
                
                db.commit()
                print(f"  Linked {len(encounters)} encounter(s) to OPD visit {opd_visit.opd_number}")
                
            except Exception as e:
                db.rollback()
                print(f"Error creating OPD visit for patient {patient_id} on {visit_date}: {e}")
                continue
        
        print()
        print("=" * 60)
        print(f"Migration completed!")
        print(f"  Created {created_visits} OPD visits")
        print(f"  Linked {linked_encounters} encounters to OPD visits")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("OPD Visit Migration Script")
    print("=" * 60)
    print("This script will:")
    print("  1. Find all encounters without opd_visit_id")
    print("  2. Group them by patient and date")
    print("  3. Create OPD visits for each group")
    print("  4. Link encounters to the created OPD visits")
    print()
    
    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate_encounters_to_opd_visits()
    else:
        print("Migration cancelled.")

