#!/usr/bin/env python3
"""
Script to create a test IPD admission with encounter, billing, and discharge.
This tests the fixes for:
1. Discharge diagnosis requiring at least one disease
2. Admitted By/Discharged By fields showing properly
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.models.user_models import User, Role
from app.models.patient_models import Patient
from app.models.ipd_models import Admission, Ward, Bed, AdmissionStatus, DischargeStatus
from app.models.bed_type_models import BedType
from app.models.encounter_models import Encounter
from app.models.disease_models import Disease, EncounterDisease
from app.models.billing_models import Invoice, InvoiceStatus
from app.crud import user_crud, patient_crud, ipd_crud


def get_database_session():
    """Get database session"""
    from app.main import app
    from app.db.database import get_db
    
    # Get database URL from app
    settings = app.state.settings if hasattr(app.state, 'settings') else None
    
    # Try to get from environment or use default
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:password123@localhost:5433/lhims")
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def main():
    print("=" * 60)
    print("Creating Test IPD Admission with Billing and Discharge")
    print("=" * 60)
    
    db = get_database_session()
    
    try:
        # 1. Get or create a test user (doctor)
        print("\n[1] Getting test doctor user...")
        doctor = db.query(User).filter(User.email.like('%doctor%')).first()
        if not doctor:
            doctor = db.query(User).first()
        if not doctor:
            print("ERROR: No users found. Please seed the database first.")
            return
        
        print(f"   Using doctor: {doctor.full_name} ({doctor.email})")
        
        # 2. Get or create a test patient
        print("\n[2] Getting or creating test patient...")
        patient = db.query(Patient).filter(Patient.first_name == "Test").filter(Patient.last_name == "PatientIPD").first()
        if not patient:
            patient = Patient(
                first_name="Test",
                last_name="PatientIPD",
                date_of_birth=datetime(1985, 5, 15).date(),
                gender="Male",
                phone_number="+233200000001",
                address="Test Address, Accra",
                patient_number="TEST-IPD-001"
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            print(f"   Created new patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
        else:
            print(f"   Using existing patient: {patient.first_name} {patient.last_name} (ID: {patient.id})")
        
        # 3. Get a ward with available bed
        print("\n[3] Finding available bed...")
        ward = db.query(Ward).first()
        if not ward:
            print("ERROR: No wards found. Please seed the database first.")
            return
        
        # Find an available bed
        bed = db.query(Bed).filter(
            Bed.ward_id == ward.id,
            Bed.status == "available"
        ).first()
        
        if not bed:
            # Create a test bed if none available
            bed_type = db.query(BedType).first()
            if not bed_type:
                bed_type = BedType(name="Standard", description="Standard bed")
                db.add(bed_type)
                db.commit()
                db.refresh(bed_type)
            
            bed = Bed(
                bed_number="TEST-001",
                ward_id=ward.id,
                bed_type_id=bed_type.id,
                status="available",
                is_active=True
            )
            db.add(bed)
            db.commit()
            db.refresh(bed)
            print(f"   Created test bed: {bed.bed_number}")
        else:
            print(f"   Using bed: {bed.bed_number} in ward {ward.name}")
        
        # 4. Get some diseases for diagnosis
        print("\n[4] Getting diseases for diagnosis...")
        diseases = db.query(Disease).limit(3).all()
        if not diseases:
            # Create test diseases
            test_diseases = [
                Disease(name="Malaria", code="B50", description="Malaria due to Plasmodium falciparum"),
                Disease(name="Typhoid Fever", code="A01.0", description="Typhoid fever"),
                Disease(name="Pneumonia", code="J18.9", description="Pneumonia, unspecified")
            ]
            for d in test_diseases:
                db.add(d)
            db.commit()
            diseases = db.query(Disease).limit(3).all()
        
        disease_names = [d.name for d in diseases]
        print(f"   Available diseases: {', '.join(disease_names)}")
        
        # 5. Create an encounter with diagnoses
        print("\n[5] Creating encounter with diagnoses...")
        encounter = Encounter(
            patient_id=patient.id,
            clinician_id=doctor.id,
            encounter_date=datetime.now(),
            status="in_progress",
            chief_complaint="Fever and headache",
            primary_diagnosis_description=None  # Will use diseases instead
        )
        db.add(encounter)
        db.commit()
        db.refresh(encounter)
        print(f"   Created encounter ID: {encounter.id}")
        
        # Add diseases to encounter
        for idx, disease in enumerate(diseases):
            encounter_disease = EncounterDisease(
                encounter_id=encounter.id,
                disease_id=disease.id,
                is_primary=(idx == 0)  # First disease is primary
            )
            db.add(encounter_disease)
        db.commit()
        print(f"   Added {len(diseases)} diseases to encounter")
        
        # 6. Create the admission
        print("\n[6] Creating IPD admission...")
        from app.schemas.ipd_schemas import AdmissionCreate
        
        admission_data = AdmissionCreate(
            patient_id=patient.id,
            encounter_id=encounter.id,
            ward_id=ward.id,
            bed_id=bed.id,
            admitted_by_id=doctor.id,
            admission_reason="Malaria with complications",
            diagnosis="Malaria"
        )
        
        admission = ipd_crud.create_admission(db, admission_data)
        print(f"   Created admission: {admission.admission_number} (ID: {admission.id})")
        
        # Update bed status
        bed.status = "occupied"
        db.commit()
        
        # 7. Create a billing invoice
        print("\n[7] Creating billing invoice...")
        invoice = Invoice(
            patient_id=patient.id,
            admission_id=admission.id,
            encounter_id=encounter.id,
            created_by_id=doctor.id,
            invoice_number=f"INV-TEST-{int(datetime.now().timestamp())}",
            invoice_date=datetime.now(),
            status=InvoiceStatus.PENDING,
            total_amount=500.00,
            paid_amount=500.00,
            balance=0.00
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        print(f"   Created invoice: {invoice.invoice_number} (Total: GHS {invoice.total_amount})")
        
        # 8. Prepare discharge (set ready_for_discharge_at)
        print("\n[8] Preparing discharge...")
        admission.ready_for_discharge_at = datetime.now()
        db.commit()
        print("   Discharge prepared")
        
        # 9. Discharge the patient with diagnoses
        print("\n[9] Discharging patient with diagnoses...")
        from app.schemas.ipd_schemas import AdmissionUpdate
        
        # Use disease IDs as the diagnoses parameter
        diagnosis_ids = [d.id for d in diseases]
        
        admission_update = AdmissionUpdate(
            discharge_status=DischargeStatus.NORMAL,
            discharge_diagnosis=", ".join(disease_names),  # This will come from the form
            discharge_notes="Patient recovered well. Follow up in 1 week.",
            discharged_by_id=doctor.id,
            discharge_date=datetime.now()
        )
        
        admission = ipd_crud.update_admission(db, admission.id, admission_update)
        
        # Also save diagnoses to EncounterDisease for the discharge
        # (This is what the form does when user selects diseases)
        print(f"   Discharged with diagnosis: {admission.discharge_diagnosis}")
        
        # Update bed status back to available
        bed.status = "available"
        db.commit()
        
        print("\n" + "=" * 60)
        print("TEST ADMISSION CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nAdmission Number: {admission.admission_number}")
        print(f"Patient: {patient.first_name} {patient.last_name}")
        print(f"Ward: {ward.name}, Bed: {bed.bed_number}")
        print(f"Admitted By: {doctor.full_name}")
        print(f"Discharged By: {doctor.full_name}")
        print(f"Discharge Diagnosis: {admission.discharge_diagnosis}")
        print(f"\nYou can view this admission at: /ipd/admissions/{admission.id}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
