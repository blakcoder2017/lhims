#!/usr/bin/env python3
"""
Script to delete all patient-related data from the database.

WARNING: This script will permanently delete ALL patient data including:
- Patients
- Appointments
- Encounters
- Vitals records
- Invoices, Charges, Payments
- Lab orders, Radiology orders, Prescriptions
- Procedures
- Admissions
- NHIS Claims
- Radiology Images
- Lab Samples

This action CANNOT be undone. Use with extreme caution.

Usage:
    python scripts/delete_all_patient_data.py [--confirm]
    
    Without --confirm flag, the script will ask for confirmation.
    With --confirm flag, it will proceed without asking.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal, engine
from app.models.patient_models import Patient
from app.models.scheduled_appointment_models import Appointment
from app.models.triage_models import TriageVitals
from app.models.encounter_models import Encounter, LabOrder, RadiologyOrder, Prescription
from app.models.billing_models import Invoice, Charge, Payment
from app.models.claims_models import NHISClaim
from app.models.procedure_models import Procedure
from app.models.ipd_models import Admission
from app.models.pacs_models import RadiologyImage, ImageAnnotation
from app.models.lab_models import LabSample
from app.models.drug_administration_models import DrugAdministration
from app.models.disease_models import EncounterDisease

def get_table_counts(db: Session) -> dict:
    """Get counts of records in patient-related tables."""
    counts = {}
    
    tables = {
        'patients': Patient,
        'appointments': Appointment,
        'triage_vitals': TriageVitals,
        'encounters': Encounter,
        'lab_orders': LabOrder,
        'radiology_orders': RadiologyOrder,
        'prescriptions': Prescription,
        'procedures': Procedure,
        'admissions': Admission,
        'invoices': Invoice,
        'charges': Charge,
        'payments': Payment,
        'nhis_claims': NHISClaim,
        'radiology_images': RadiologyImage,
        'image_annotations': ImageAnnotation,
        'lab_samples': LabSample,
        'drug_administrations': DrugAdministration,
        'encounter_diseases': EncounterDisease,
    }
    
    for table_name, model in tables.items():
        try:
            count = db.query(model).count()
            counts[table_name] = count
        except Exception as e:
            print(f"Warning: Could not count {table_name}: {e}")
            counts[table_name] = 0
    
    return counts

def delete_all_patient_data(db: Session, dry_run: bool = False) -> dict:
    """
    Delete all patient-related data from the database.
    
    Args:
        db: Database session
        dry_run: If True, only show what would be deleted without actually deleting
        
    Returns:
        Dictionary with deletion counts
    """
    deleted_counts = {}
    
    try:
        # Order matters due to foreign key constraints
        # Delete in reverse dependency order
        
        print("\n" + "="*60)
        print("DELETING PATIENT-RELATED DATA")
        print("="*60)
        
        if dry_run:
            print("\n[DRY RUN MODE - No data will be deleted]")
        
        # 1. Payments (references Invoice)
        print("\n1. Deleting Payments...")
        payments = db.query(Payment).all()
        deleted_counts['payments'] = len(payments)
        if not dry_run:
            for payment in payments:
                db.delete(payment)
            db.commit()
        print(f"   ✓ {deleted_counts['payments']} payments")
        
        # 2. Drug Administrations (references Admission and Prescription - must be deleted before both)
        print("\n2. Deleting Drug Administrations...")
        drug_administrations = db.query(DrugAdministration).all()
        deleted_counts['drug_administrations'] = len(drug_administrations)
        if not dry_run:
            for drug_admin in drug_administrations:
                db.delete(drug_admin)
            db.commit()
        print(f"   ✓ {deleted_counts['drug_administrations']} drug administrations")
        
        # 3. Image Annotations (references RadiologyImage - must be deleted before Radiology Images)
        print("\n3. Deleting Image Annotations...")
        image_annotations = db.query(ImageAnnotation).all()
        deleted_counts['image_annotations'] = len(image_annotations)
        if not dry_run:
            for annotation in image_annotations:
                db.delete(annotation)
            db.commit()
        print(f"   ✓ {deleted_counts['image_annotations']} image annotations")
        
        # 4. Lab Samples (references LabOrder - must be deleted before Lab Orders)
        print("\n4. Deleting Lab Samples...")
        lab_samples = db.query(LabSample).all()
        deleted_counts['lab_samples'] = len(lab_samples)
        if not dry_run:
            for sample in lab_samples:
                db.delete(sample)
            db.commit()
        print(f"   ✓ {deleted_counts['lab_samples']} lab samples")
        
        # 5. Radiology Images (references RadiologyOrder and Patient - must be deleted before Radiology Orders)
        print("\n5. Deleting Radiology Images...")
        radiology_images = db.query(RadiologyImage).all()
        deleted_counts['radiology_images'] = len(radiology_images)
        if not dry_run:
            for image in radiology_images:
                db.delete(image)
            db.commit()
        print(f"   ✓ {deleted_counts['radiology_images']} radiology images")
        
        # 6. Procedures (references Patient and Encounter)
        print("\n6. Deleting Procedures...")
        procedures = db.query(Procedure).all()
        deleted_counts['procedures'] = len(procedures)
        if not dry_run:
            for procedure in procedures:
                db.delete(procedure)
            db.commit()
        print(f"   ✓ {deleted_counts['procedures']} procedures")
        
        # 7. Prescriptions (references Encounter and Patient - must be deleted after Drug Administrations)
        print("\n7. Deleting Prescriptions...")
        prescriptions = db.query(Prescription).all()
        deleted_counts['prescriptions'] = len(prescriptions)
        if not dry_run:
            for prescription in prescriptions:
                db.delete(prescription)
            db.commit()
        print(f"   ✓ {deleted_counts['prescriptions']} prescriptions")
        
        # 8. Lab Orders (references Encounter and Patient - must be deleted after Lab Samples)
        print("\n8. Deleting Lab Orders...")
        lab_orders = db.query(LabOrder).all()
        deleted_counts['lab_orders'] = len(lab_orders)
        if not dry_run:
            for order in lab_orders:
                db.delete(order)
            db.commit()
        print(f"   ✓ {deleted_counts['lab_orders']} lab orders")
        
        # 9. Radiology Orders (references Encounter and Patient - must be deleted after Radiology Images)
        print("\n9. Deleting Radiology Orders...")
        radiology_orders = db.query(RadiologyOrder).all()
        deleted_counts['radiology_orders'] = len(radiology_orders)
        if not dry_run:
            for order in radiology_orders:
                db.delete(order)
            db.commit()
        print(f"   ✓ {deleted_counts['radiology_orders']} radiology orders")
        
        # 10. Charges (references Invoice, Encounter, LabOrder, RadiologyOrder, Prescription - delete after all orders)
        print("\n10. Deleting Charges...")
        charges = db.query(Charge).all()
        deleted_counts['charges'] = len(charges)
        if not dry_run:
            for charge in charges:
                db.delete(charge)
            db.commit()
        print(f"   ✓ {deleted_counts['charges']} charges")
        
        # 11. Admissions (references Patient, Encounter, and Invoice - must be deleted before Invoices)
        print("\n11. Deleting Admissions...")
        admissions = db.query(Admission).all()
        deleted_counts['admissions'] = len(admissions)
        if not dry_run:
            for admission in admissions:
                db.delete(admission)
            db.commit()
        print(f"   ✓ {deleted_counts['admissions']} admissions")
        
        # 12. Invoices (references Patient, Encounter, Appointment - must be deleted after Charges and Admissions)
        print("\n12. Deleting Invoices...")
        invoices = db.query(Invoice).all()
        deleted_counts['invoices'] = len(invoices)
        if not dry_run:
            for invoice in invoices:
                db.delete(invoice)
            db.commit()
        print(f"   ✓ {deleted_counts['invoices']} invoices")
        
        # 13. Encounter Diseases (references Encounter and Disease - must be deleted before Encounters)
        print("\n13. Deleting Encounter Diseases...")
        encounter_diseases = db.query(EncounterDisease).all()
        deleted_counts['encounter_diseases'] = len(encounter_diseases)
        if not dry_run:
            for encounter_disease in encounter_diseases:
                db.delete(encounter_disease)
            db.commit()
        print(f"   ✓ {deleted_counts['encounter_diseases']} encounter diseases")
        
        # 14. Encounters (references Patient and Appointment - must be deleted before NHIS Claims)
        print("\n14. Deleting Encounters...")
        encounters = db.query(Encounter).all()
        deleted_counts['encounters'] = len(encounters)
        if not dry_run:
            for encounter in encounters:
                db.delete(encounter)
            db.commit()
        print(f"   ✓ {deleted_counts['encounters']} encounters")
        
        # 15. NHIS Claims (references Encounter, Patient, Invoice - must be deleted after Invoices and Encounters)
        print("\n15. Deleting NHIS Claims...")
        claims = db.query(NHISClaim).all()
        deleted_counts['nhis_claims'] = len(claims)
        if not dry_run:
            for claim in claims:
                db.delete(claim)
            db.commit()
        print(f"   ✓ {deleted_counts['nhis_claims']} NHIS claims")
        
        # 16. Triage Vitals (references Patient)
        print("\n16. Deleting Triage Vitals...")
        vitals = db.query(TriageVitals).all()
        deleted_counts['triage_vitals'] = len(vitals)
        if not dry_run:
            for vital in vitals:
                db.delete(vital)
            db.commit()
        print(f"   ✓ {deleted_counts['triage_vitals']} vitals records")
        
        # 17. Appointments (references Patient)
        print("\n17. Deleting Appointments...")
        appointments = db.query(Appointment).all()
        deleted_counts['appointments'] = len(appointments)
        if not dry_run:
            for appointment in appointments:
                db.delete(appointment)
            db.commit()
        print(f"   ✓ {deleted_counts['appointments']} appointments")
        
        # 18. Patients (the main table - delete last)
        print("\n18. Deleting Patients...")
        patients = db.query(Patient).all()
        deleted_counts['patients'] = len(patients)
        if not dry_run:
            for patient in patients:
                db.delete(patient)
            db.commit()
        print(f"   ✓ {deleted_counts['patients']} patients")
        
        print("\n" + "="*60)
        print("DELETION COMPLETE")
        print("="*60)
        
        total_deleted = sum(deleted_counts.values())
        print(f"\nTotal records deleted: {total_deleted}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during deletion: {e}")
        print("Transaction rolled back. No data was deleted.")
        raise
    
    return deleted_counts

def main():
    """Main function to run the deletion script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Delete all patient-related data from the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WARNING: This script will permanently delete ALL patient data.
This action CANNOT be undone. Use with extreme caution.
        """
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt and proceed with deletion'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    # Connect to database
    db = SessionLocal()
    
    try:
        # Show current counts
        print("\n" + "="*60)
        print("CURRENT DATABASE STATE")
        print("="*60)
        counts = get_table_counts(db)
        
        total_records = sum(counts.values())
        
        print("\nCurrent record counts:")
        for table_name, count in sorted(counts.items()):
            if count > 0:
                print(f"  {table_name:25s}: {count:6d}")
        
        print(f"\n{'Total records':25s}: {total_records:6d}")
        
        if total_records == 0:
            print("\n✓ Database is already empty. Nothing to delete.")
            return
        
        # Confirmation
        if args.dry_run:
            print("\n" + "="*60)
            print("DRY RUN MODE")
            print("="*60)
            print("This will show what would be deleted without actually deleting.")
            delete_all_patient_data(db, dry_run=True)
            print("\n✓ Dry run complete. No data was deleted.")
            return
        
        if not args.confirm:
            print("\n" + "="*60)
            print("⚠️  WARNING ⚠️")
            print("="*60)
            print("This will PERMANENTLY DELETE ALL patient-related data:")
            print("  - All patients")
            print("  - All appointments")
            print("  - All encounters")
            print("  - All vitals records")
            print("  - All invoices, charges, and payments")
            print("  - All lab orders, radiology orders, prescriptions")
            print("  - All procedures")
            print("  - All admissions")
            print("  - All NHIS claims")
            print("  - All radiology images")
            print("  - All lab samples")
            print("\nThis action CANNOT be undone!")
            print("="*60)
            
            confirmation = input("\nType 'DELETE ALL' (in uppercase) to confirm: ")
            
            if confirmation != "DELETE ALL":
                print("\n❌ Deletion cancelled. No data was deleted.")
                return
        
        # Perform deletion
        print("\n⚠️  Starting deletion process...")
        deleted_counts = delete_all_patient_data(db, dry_run=False)
        
        # Verify deletion
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)
        final_counts = get_table_counts(db)
        
        print("\nRemaining record counts:")
        all_empty = True
        for table_name, count in sorted(final_counts.items()):
            if count > 0:
                print(f"  {table_name:25s}: {count:6d} ⚠️")
                all_empty = False
            else:
                print(f"  {table_name:25s}: {count:6d} ✓")
        
        if all_empty:
            print("\n✓ All patient-related data has been successfully deleted!")
        else:
            print("\n⚠️  Some records remain. Check the tables above.")
        
    except KeyboardInterrupt:
        print("\n\n❌ Deletion interrupted by user. Transaction rolled back.")
        db.rollback()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()

