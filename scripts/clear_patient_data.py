#!/usr/bin/env python3
"""
Clear all patient-related data from the database while preserving user login info.

Keeps: users, roles, permissions, hospital_settings, departments, service_pricing,
       wards, beds, ward_types, bed_types, shift_types, insurance_providers, etc.

Removes: patients and all linked data (encounters, invoices, vitals, queue, etc.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import SessionLocal


def clear_patient_data():
    """Clear all patient data. Deletes in FK-safe order."""
    db = SessionLocal()
    try:
        print("Clearing patient data (preserving users, roles, and config)...")

        # Tables to clear, in dependency order (children before parents)
        # Using raw SQL for efficiency; order respects foreign keys
        clear_operations = [
            ("charge_payments", "Charge allocations"),
            ("receipts", "Receipts"),
            ("payments", "Payments"),
            ("charges", "Charges"),
            ("invoices", "Invoices"),
            ("image_annotations", "Image annotations"),
            ("radiology_images", "Radiology images"),
            ("qc_records", "QC records"),
            ("lab_samples", "Lab samples"),
            ("lab_orders", "Lab orders"),
            ("radiology_orders", "Radiology orders"),
            ("prescriptions", "Prescriptions"),
            ("encounter_diseases", "Encounter diagnoses"),
            ("procedures", "Procedures"),
            ("nhis_claims", "NHIS claims"),
            ("encounters", "Encounters"),
            ("drug_administrations", "Drug administrations"),
            ("fluid_balance", "Fluid balance"),
            ("discharge_clearances", "Discharge clearances"),
            ("admission_notes", "Admission notes"),
            ("admissions", "Admissions"),
            ("opd_visits", "OPD visits"),
            ("opd_queue", "OPD queue"),
            ("scheduled_appointments", "Scheduled appointments"),
            ("triage_vitals", "Triage vitals"),
            ("antenatal_visits", "Antenatal visits"),
            ("birth_records", "Birth records"),
            ("patients", "Patients"),
        ]

        # Remove prescription-linked inventory transactions first (FK to prescriptions)
        try:
            result = db.execute(text("DELETE FROM inventory_transactions WHERE prescription_id IS NOT NULL"))
            count = result.rowcount
            db.commit()
            if count > 0:
                print(f"  Cleared prescription-linked inventory transactions: {count} rows")
        except Exception as e:
            db.rollback()
            print(f"  Warning: prescription-linked inventory transactions: {e}")

        # Null FK links that would block deletion (admissions->invoices, encounters->opd/queue/appointments)
        for sql, label in [
            ("UPDATE admissions SET invoice_id = NULL", "Admission invoice links"),
            ("UPDATE encounters SET admission_id = NULL, opd_visit_id = NULL, queue_entry_id = NULL, appointment_id = NULL", "Encounter admission/OPD/queue/appointment links"),
        ]:
            try:
                result = db.execute(text(sql))
                count = result.rowcount
                db.commit()
                if count > 0:
                    print(f"  Nulled {label}: {count} rows")
            except Exception as e:
                db.rollback()
                print(f"  Warning: {label}: {e}")

        for table, label in clear_operations:
            try:
                result = db.execute(text(f"DELETE FROM {table}"))
                count = result.rowcount
                db.commit()
                if count > 0:
                    print(f"  Cleared {label}: {count} rows")
            except Exception as e:
                db.rollback()
                # Table might not exist or have different name
                print(f"  Warning: {label} ({table}): {e}")
                continue

        # Reset patient number sequence if using serial/sequence
        try:
            db.execute(text("ALTER SEQUENCE IF EXISTS patients_id_seq RESTART WITH 1"))
            db.commit()
            print("  Reset patients ID sequence")
        except Exception as e:
            db.rollback()
            print(f"  Note: Could not reset sequence: {e}")

        print("\nPatient data cleared successfully.")
        print("Preserved: users, roles, permissions, hospital_settings, departments,")
        print("           service_pricing, wards, beds, and other configuration.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if "--yes" not in sys.argv and "-y" not in sys.argv:
        confirm = input("This will DELETE ALL patient data. Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
    clear_patient_data()
