#!/usr/bin/env python3
"""
Script to discharge a patient and release the bed.
Usage: python discharge_patient.py <admission_number>
Example: python discharge_patient.py ADM-20260302-0001
"""
import sys
import os

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.crud import ipd_crud


def discharge_patient_and_release_bed(admission_number: str):
    """
    Discharge a patient and release the bed.
    
    Args:
        admission_number: The admission number (e.g., ADM-20260302-0001)
    
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    try:
        # First, find the admission by number
        print(f"Looking for admission: {admission_number}")
        admission = ipd_crud.get_admission_by_number(db, admission_number)
        
        if not admission:
            print(f"ERROR: Admission not found: {admission_number}")
            return False
        
        print(f"Found admission:")
        print(f"  - Admission ID: {admission.id}")
        print(f"  - Admission Number: {admission.admission_number}")
        print(f"  - Patient: {admission.patient.first_name} {admission.patient.last_name}")
        print(f"  - Status: {admission.status.value}")
        print(f"  - Ward: {admission.ward.name if admission.ward else 'N/A'}")
        print(f"  - Bed: {admission.bed.bed_number if admission.bed else 'N/A'}")
        
        # Check if already discharged
        if admission.status.value == "discharged":
            print(f"Patient is already discharged.")
            return True
        
        # Discharge the patient (this also releases the bed)
        # Note: discharged_by_id can be None, but it's better to use a valid user
        # Let's get the first admin user
        from app.models.user_models import User
        admin_user = db.query(User).filter(User.role_id == 1).first()
        discharged_by_id = admin_user.id if admin_user else 1
        
        print(f"\nDischarging patient and releasing bed (discharged_by user_id: {discharged_by_id})...")
        discharged_admission = ipd_crud.discharge_patient(db, admission.id, discharged_by_id)
        
        if discharged_admission:
            print(f"SUCCESS: Patient discharged successfully!")
            print(f"  - Discharge Date: {discharged_admission.discharge_date}")
            print(f"  - Status: {discharged_admission.status.value}")
            return True
        else:
            print(f"ERROR: Failed to discharge patient")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python discharge_patient.py <admission_number>")
        print("Example: python discharge_patient.py ADM-20260302-0001")
        sys.exit(1)
    
    admission_number = sys.argv[1]
    success = discharge_patient_and_release_bed(admission_number)
    sys.exit(0 if success else 1)
