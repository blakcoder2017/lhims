"""
Pharmacy Seed CRUD Operations

Functions for seeding pharmacy data like dosage forms, initial drugs, etc.
"""
import uuid
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.pharmacy_models import (
    PharmacyDosageForm, PharmacySupplier, PharmacyStore, 
    PharmacyDrug, PharmacyDrugInteraction, PharmacyRolePolicy
)


# Standard Ghana dosage forms
DOSAGE_FORMS = [
    "Tablet",
    "Capsule", 
    "Syrup",
    "Suspension",
    "Injection",
    "Intravenous",
    "Intramuscular",
    "Subcutaneous",
    "Cream",
    "Ointment",
    "Gel",
    "Lotion",
    "Drops",
    "Eye Drops",
    "Ear Drops",
    "Nasal Drops",
    "Inhaler",
    "Patch",
    "Suppository",
    "Enema",
    "Oral Rehydration Salt",
    "Powder",
    "Granules",
    "Solution",
    "Tincture",
    "Lozenge",
    "Pessary",
    "Vaginal Tablet",
    "Dental Paste",
    "Mouthwash",
    "Spray",
]


def seed_dosage_forms(db: Session) -> List[PharmacyDosageForm]:
    """Seed dosage forms if they don't exist."""
    existing = db.query(PharmacyDosageForm).count()
    if existing > 0:
        return db.query(PharmacyDosageForm).all()
    
    forms = []
    for name in DOSAGE_FORMS:
        df = PharmacyDosageForm(name=name)
        db.add(df)
        forms.append(df)
    
    db.commit()
    for form in forms:
        db.refresh(form)
    
    return forms


def get_or_create_dosage_form(db: Session, name: str) -> PharmacyDosageForm:
    """Get or create a dosage form."""
    form = db.query(PharmacyDosageForm).filter(
        PharmacyDosageForm.name.ilike(name)
    ).first()
    
    if not form:
        form = PharmacyDosageForm(name=name)
        db.add(form)
        db.commit()
        db.refresh(form)
    
    return form


def create_default_store(db: Session, name: str = "Main Pharmacy") -> PharmacyStore:
    """Create or get the default pharmacy store."""
    store = db.query(PharmacyStore).filter(PharmacyStore.name == name).first()
    
    if not store:
        store = PharmacyStore(name=name)
        db.add(store)
        db.commit()
        db.refresh(store)
    
    return store


def create_default_supplier(db: Session, name: str = "General Supplier") -> PharmacySupplier:
    """Create or get a default supplier."""
    supplier = db.query(PharmacySupplier).filter(PharmacySupplier.name == name).first()
    
    if not supplier:
        supplier = PharmacySupplier(name=name)
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
    
    return supplier


def create_pharmacy_role_policy(
    db: Session,
    role_name: str,
    can_view_unit_cost: bool = False,
    can_view_margin: bool = False,
    can_edit_selling_price: bool = False,
    can_adjust_stock: bool = False,
    can_approve_adjustment: bool = False,
    can_dispense_controlled: bool = False
) -> PharmacyRolePolicy:
    """Create or update a pharmacy role policy."""
    policy = db.query(PharmacyRolePolicy).filter(
        PharmacyRolePolicy.role_name == role_name
    ).first()
    
    if policy:
        policy.can_view_unit_cost = can_view_unit_cost
        policy.can_view_margin = can_view_margin
        policy.can_edit_selling_price = can_edit_selling_price
        policy.can_adjust_stock = can_adjust_stock
        policy.can_approve_adjustment = can_approve_adjustment
        policy.can_dispense_controlled = can_dispense_controlled
    else:
        policy = PharmacyRolePolicy(
            role_name=role_name,
            can_view_unit_cost=can_view_unit_cost,
            can_view_margin=can_view_margin,
            can_edit_selling_price=can_edit_selling_price,
            can_adjust_stock=can_adjust_stock,
            can_approve_adjustment=can_approve_adjustment,
            can_dispense_controlled=can_dispense_controlled
        )
        db.add(policy)
    
    db.commit()
    db.refresh(policy)
    return policy


def seed_pharmacy_role_policies(db: Session) -> List[PharmacyRolePolicy]:
    """Seed default pharmacy role policies."""
    policies = [
        ("Admin", True, True, True, True, True, True),
        ("Pharmacy Staff", False, False, False, True, False, True),
        ("Doctor", False, False, False, False, False, False),
        ("Clinician", False, False, False, False, False, False),
        ("Nurse", False, False, False, False, False, False),
        ("Finance", True, True, False, False, False, False),
    ]
    
    results = []
    for p in policies:
        policy = create_pharmacy_role_policy(
            db, p[0], p[1], p[2], p[3], p[4], p[5], p[6]
        )
        results.append(policy)
    
    return results


# Common drug interactions for Ghana
COMMON_DRUG_INTERACTIONS = [
    # Warfarin interactions
    ("Warfarin", "Aspirin", "MAJOR", "Increased bleeding risk"),
    ("Warfarin", "Ibuprofen", "MAJOR", "Increased bleeding risk"),
    ("Warfarin", "Metronidazole", "MAJOR", "Increased anticoagulant effect"),
    
    # ACE Inhibitors interactions
    ("Lisinopril", "Potassium Chloride", "MAJOR", "Risk of hyperkalemia"),
    ("Enalapril", "Spironolactone", "MAJOR", "Risk of hyperkalemia"),
    
    # Metformin interactions
    ("Metformin", "Alcohol", "MODERATE", "Risk of lactic acidosis"),
    
    # NSAID interactions
    ("Ibuprofen", "Aspirin", "MODERATE", "Reduced cardioprotective effect"),
    ("Diclofenac", "Warfarin", "MAJOR", "Increased bleeding risk"),
    
    # Antibiotic interactions
    ("Ampicillin", "Allopurinol", "MODERATE", "Increased risk of rash"),
    ("Ciprofloxacin", "Antacids", "MODERATE", "Reduced absorption"),
    ("Erythromycin", "Simvastatin", "MAJOR", "Risk of rhabdomyolysis"),
    
    # Beta-blocker interactions
    ("Metoprolol", "Fluoxetine", "MODERATE", "Increased beta-blocker effect"),
    ("Atenolol", "Insulin", "MODERATE", "May mask hypoglycemia symptoms"),
    
    # Methotrexate interactions
    ("Methotrexate", "Ibuprofen", "MAJOR", "Increased methotrexate toxicity"),
    ("Methotrexate", "Probenecid", "MAJOR", "Increased methotrexate toxicity"),
]


def seed_drug_interactions(db: Session) -> List[PharmacyDrugInteraction]:
    """Seed common drug interactions."""
    # Get all drugs
    drugs = db.query(PharmacyDrug).all()
    drug_map = {d.generic_name.lower(): d for d in drugs}
    
    interactions = []
    for interaction in COMMON_DRUG_INTERACTIONS:
        drug_a_name = interaction[0].lower()
        drug_b_name = interaction[1].lower()
        
        drug_a = drug_map.get(drug_a_name)
        drug_b = drug_map.get(drug_b_name)
        
        if drug_a and drug_b:
            # Check if interaction already exists
            existing = db.query(PharmacyDrugInteraction).filter(
                PharmacyDrugInteraction.drug_a_id == drug_a.id,
                PharmacyDrugInteraction.drug_b_id == drug_b.id
            ).first()
            
            if not existing:
                inter = PharmacyDrugInteraction(
                    drug_a_id=drug_a.id,
                    drug_b_id=drug_b.id,
                    severity=interaction[2],
                    description=interaction[3],
                    is_active=True
                )
                db.add(inter)
                interactions.append(inter)
    
    if interactions:
        db.commit()
    
    return interactions


def initialize_pharmacy_system(db: Session) -> dict:
    """
    Initialize the pharmacy system with all required seed data.
    Call this once during setup.
    """
    result = {
        "dosage_forms": [],
        "stores": [],
        "suppliers": [],
        "policies": [],
        "interactions": []
    }
    
    # Seed dosage forms
    result["dosage_forms"] = seed_dosage_forms(db)
    
    # Create default store
    result["stores"] = [create_default_store(db)]
    
    # Create default supplier
    result["suppliers"] = [create_default_supplier(db)]
    
    # Seed role policies
    result["policies"] = seed_pharmacy_role_policies(db)
    
    # Seed drug interactions (requires drugs to exist first)
    # result["interactions"] = seed_drug_interactions(db)  # Call after drugs are created
    
    return result
