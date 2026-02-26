"""
Seed Pharmacy Ghana-Ready: dosage forms, stores, suppliers, formulations, interactions, role policies.
Run after migration add_pharmacy_ghana_ready.
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.db.database import SessionLocal
from app.models.pharmacy_models import (
    PharmacyDosageForm, PharmacyDrug, PharmacySupplier, PharmacyStore,
    PharmacyDrugInteraction, PharmacyRolePolicy,
)
from sqlalchemy.orm import Session
from decimal import Decimal


DOSAGE_FORMS = [
    "Tablet", "Capsule", "Syrup", "Suspension", "Injection", "IV infusion",
    "Eye drops", "Ear drops", "Nasal spray", "Cream", "Ointment", "Gel",
    "Lotion", "Suppository", "Inhaler", "Nebule", "Patch", "Powder", "Solution",
]

STORES = [
    {"name": "Main Pharmacy"},
    {"name": "Ward Store"},
    {"name": "OPD Dispensary"},
]

# Formulations: (item_code, generic_name, brand_name, dosage_form_name, strength_value, strength_unit, route,
#   concentration_value, concentration_unit, pack_size, is_controlled)
FORMULATIONS = [
    ("AMX500CAP", "Amoxicillin", "Amoxil", "Capsule", 500, "mg", "PO", None, None, 100, False),
    ("AMX250SYP", "Amoxicillin", None, "Suspension", None, None, "PO", 250, "mg/5mL", 100, False),
    ("AMP500INJ", "Ampicillin", None, "Injection", 500, "mg", "IV", None, None, 10, False),
    ("PAR500TAB", "Paracetamol", "Panadol", "Tablet", 500, "mg", "PO", None, None, 100, False),
    ("IBU400TAB", "Ibuprofen", None, "Tablet", 400, "mg", "PO", None, None, 30, False),
    ("MET500TAB", "Metronidazole", "Flagyl", "Tablet", 500, "mg", "PO", None, None, 21, False),
    ("COT480TAB", "Co-trimoxazole", "Septrin", "Tablet", 480, "mg", "PO", None, None, 30, False),
    ("WAR5TAB", "Warfarin", None, "Tablet", 5, "mg", "PO", None, None, 28, True),
    ("ENL5TAB", "Enalapril", None, "Tablet", 5, "mg", "PO", None, None, 28, False),
    ("GEN80INJ", "Gentamicin", None, "Injection", 80, "mg", "IM", None, None, 10, False),
    ("FUR40TAB", "Furosemide", "Lasix", "Tablet", 40, "mg", "PO", None, None, 30, False),
    ("RIF450TAB", "Rifampicin", None, "Tablet", 450, "mg", "PO", None, None, 30, False),
    ("CIP500TAB", "Ciprofloxacin", None, "Tablet", 500, "mg", "PO", None, None, 10, False),
    ("OME20CAP", "Omeprazole", None, "Capsule", 20, "mg", "PO", None, None, 28, False),
    ("SAL0.9INJ", "Saline", "Normal Saline", "IV infusion", 0.9, "%", "IV", None, None, 1, False),
    # Additional drugs for interaction checking
    ("SPI25TAB", "Spironolactone", None, "Tablet", 25, "mg", "PO", None, None, 30, False),
    ("OCP30TAB", "Combined Oral Contraceptive", None, "Tablet", 30, "mcg", "PO", None, None, 21, False),
    ("ALU200TAB", "Aluminum Hydroxide", "Mylanta", "Tablet", 200, "mg", "PO", None, None, 50, False),
    ("FER200TAB", "Ferrous Sulfate", None, "Tablet", 200, "mg", "PO", None, None, 60, False),
    ("DEX40TAB", "Dexamethasone", None, "Tablet", 40, "mg", "PO", None, None, 10, False),
    ("PRED50TAB", "Prednisolone", None, "Tablet", 50, "mg", "PO", None, None, 20, False),
]

# (drug_a_generic, drug_b_generic, severity, description, recommendation)
# Only pairs where both drugs exist in FORMULATIONS above
# Note: Alcohol interactions are handled at UI/dispensing level (not seeded as drug)
INTERACTIONS = [
    ("Warfarin", "Metronidazole", "MAJOR", "Metronidazole increases warfarin effect; bleeding risk.", "Monitor INR closely; consider alternative antibiotic."),
    ("Warfarin", "Co-trimoxazole", "MAJOR", "Co-trimoxazole increases warfarin effect; bleeding risk.", "Monitor INR; consider dose reduction."),
    ("Warfarin", "Ibuprofen", "MAJOR", "NSAIDs increase bleeding risk with warfarin.", "Avoid or use with caution; monitor for bleeding."),
    ("Warfarin", "Dexamethasone", "MODERATE", "Corticosteroids may alter warfarin metabolism.", "Monitor INR when starting or stopping steroids."),
    ("Enalapril", "Spironolactone", "MAJOR", "ACEI + potassium-sparing diuretic: risk of hyperkalemia.", "Monitor potassium levels; avoid if K+ >5.0 mEq/L."),
    ("Enalapril", "Furosemide", "MAJOR", "ACEI + loop diuretic: risk of hypotension, renal impairment.", "Monitor BP, electrolytes, renal function."),
    ("Gentamicin", "Furosemide", "MAJOR", "Ototoxicity and nephrotoxicity risk increased.", "Monitor renal function, hearing; avoid if possible."),
    ("Rifampicin", "Combined Oral Contraceptive", "MAJOR", "Rifampicin induces hepatic enzymes; reduces contraceptive efficacy.", "Use alternative contraception; consider backup."),
    ("Ciprofloxacin", "Aluminum Hydroxide", "MODERATE", "Antacids reduce ciprofloxacin absorption.", "Space doses by 2-6 hours."),
    ("Ciprofloxacin", "Ferrous Sulfate", "MODERATE", "Iron reduces ciprofloxacin absorption.", "Space doses by 2-6 hours."),
    ("Ciprofloxacin", "Metronidazole", "MODERATE", "Theoretical CNS effects when combined.", "Monitor; space administration if concerned."),
    ("Metronidazole", "Amoxicillin", "MODERATE", "Combination therapy for H. pylori - standard practice.", "Used together for H. pylori eradication."),
]

ROLE_POLICIES = [
    {"role_name": "Admin", "can_view_unit_cost": True, "can_view_margin": True, "can_edit_selling_price": True,
     "can_adjust_stock": True, "can_approve_adjustment": True, "can_dispense_controlled": True},
    {"role_name": "Pharmacy Staff", "can_view_unit_cost": False, "can_view_margin": False, "can_edit_selling_price": False,
     "can_adjust_stock": False, "can_approve_adjustment": False, "can_dispense_controlled": False},
    {"role_name": "Head of Pharmacy", "can_view_unit_cost": True, "can_view_margin": True, "can_edit_selling_price": True,
     "can_adjust_stock": True, "can_approve_adjustment": True, "can_dispense_controlled": True},
]


def seed_pharmacy_ghana():
    db: Session = SessionLocal()
    try:
        # 1) Dosage forms
        for name in DOSAGE_FORMS:
            if not db.query(PharmacyDosageForm).filter(PharmacyDosageForm.name == name).first():
                db.add(PharmacyDosageForm(name=name))
                print(f"Created dosage form: {name}")
        db.commit()

        # 2) Stores
        for s in STORES:
            if not db.query(PharmacyStore).filter(PharmacyStore.name == s["name"]).first():
                db.add(PharmacyStore(name=s["name"]))
                print(f"Created store: {s['name']}")
        db.commit()

        # 3) Supplier (one default)
        supplier = db.query(PharmacySupplier).filter(PharmacySupplier.name == "Default Supplier").first()
        if not supplier:
            supplier = PharmacySupplier(name="Default Supplier", phone="", email="", address="")
            db.add(supplier)
            db.commit()
            print("Created supplier: Default Supplier")

        # 4) Formulations
        df_map = {df.name: df for df in db.query(PharmacyDosageForm).all()}
        for code, generic, brand, df_name, str_val, str_unit, route, conc_val, conc_unit, pack, controlled in FORMULATIONS:
            if db.query(PharmacyDrug).filter(PharmacyDrug.item_code == code).first():
                continue
            df_id = df_map.get(df_name)
            if not df_id:
                continue
            drug = PharmacyDrug(
                item_code=code,
                generic_name=generic,
                brand_name=brand,
                dosage_form_id=df_id.id,
                strength_value=Decimal(str(str_val)) if str_val else None,
                strength_unit=str_unit,
                route=route,
                concentration_value=Decimal(str(conc_val)) if conc_val else None,
                concentration_unit=conc_unit,
                pack_size=pack,
                is_controlled=controlled,
                is_active=True,
            )
            db.add(drug)
            print(f"Created drug: {generic} {str_val or conc_val} {df_name}")
        db.commit()

        # 5) Interactions (need drug IDs by generic name)
        drug_by_generic = {}
        for d in db.query(PharmacyDrug).filter(PharmacyDrug.is_active == True).all():
            if d.generic_name not in drug_by_generic:
                drug_by_generic[d.generic_name] = d

        for ga, gb, sev, desc, rec in INTERACTIONS:
            da = drug_by_generic.get(ga)
            db_drug = drug_by_generic.get(gb)
            if not da or not db_drug:
                continue
            existing = db.query(PharmacyDrugInteraction).filter(
                ((PharmacyDrugInteraction.drug_a_id == da.id) & (PharmacyDrugInteraction.drug_b_id == db_drug.id)) |
                ((PharmacyDrugInteraction.drug_a_id == db_drug.id) & (PharmacyDrugInteraction.drug_b_id == da.id))
            ).first()
            if existing:
                continue
            # Ensure drug_a_id < drug_b_id for uniqueness (or use both orderings)
            int_row = PharmacyDrugInteraction(
                drug_a_id=da.id,
                drug_b_id=db_drug.id,
                severity=sev,
                description=desc,
                recommendation=rec,
                is_active=True,
            )
            db.add(int_row)
            print(f"Created interaction: {ga} + {gb} ({sev})")
        db.commit()

        # 6) Role policies
        for pol in ROLE_POLICIES:
            existing = db.query(PharmacyRolePolicy).filter(PharmacyRolePolicy.role_name == pol["role_name"]).first()
            if not existing:
                db.add(PharmacyRolePolicy(**pol))
                print(f"Created role policy: {pol['role_name']}")
        db.commit()

        print("--- Pharmacy Ghana seeding complete ---")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_pharmacy_ghana()
