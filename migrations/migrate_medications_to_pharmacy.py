"""
Migration Script: Migrate Legacy Medications to Ghana Pharmacy System

This script migrates:
- medications → pharmacy_drug
- stock_items → pharmacy_batch (if they have valid expiry dates)

Usage:
    alembic upgrade head
    # Then run this migration
    python -c "from migrations.versions.migrate_medications_to_pharmacy import migrate_all; migrate_all()"

Or run as standalone:
    python migrations/versions/migrate_medications_to_pharmacy.py
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, date
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL - import from config or use environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/lhims")

def get_session():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def seed_dosage_forms(session):
    """Seed pharmacy_dosage_form table with common Ghana dosage forms."""
    
    dosage_forms = [
        "Tablet", "Capsule", "Syrup", "Suspension", "Injection", 
        "Intravenous", "Intramuscular", "Subcutaneous", "Cream", 
        "Ointment", "Gel", "Lotion", "Drops", "Eye Drops", "Ear Drops",
        "Nasal Drops", "Inhaler", "Patch", "Suppository", "Enema",
        "Oral Rehydration Salt", "Powder", "Granules", "Solution",
        "Tincture", "Lozenge", "Pessary", "Vaginal Tablet"
    ]
    
    from app.models.pharmacy_models import PharmacyDosageForm
    
    existing_count = session.query(PharmacyDosageForm).count()
    print(f"Existing dosage forms: {existing_count}")
    
    if existing_count > 0:
        print("Dosage forms already seeded. Skipping...")
        return
    
    for name in dosage_forms:
        df = PharmacyDosageForm(name=name)
        session.add(df)
    
    session.commit()
    print(f"Seeded {len(dosage_forms)} dosage forms.")

def parse_strength(strength_str):
    """Parse strength string like '500mg' into value and unit."""
    if not strength_str:
        return None, None
    
    strength_str = str(strength_str).strip().lower()
    
    # Common units
    units = ['mg', 'g', 'mcg', 'ml', 'iu', 'meq', '%', 'units', 'unit']
    
    for unit in units:
        if unit in strength_str:
            value_str = strength_str.replace(unit, '').strip()
            try:
                value = float(value_str)
                return value, unit
            except ValueError:
                return None, None
    
    # Try to extract just numbers
    import re
    numbers = re.findall(r'[\d.]+', strength_str)
    if numbers:
        try:
            return float(numbers[0]), None
        except ValueError:
            pass
    
    return None, None

def map_dosage_form_legacy_to_uuid(session, legacy_dosage_form):
    """Map legacy dosage form string to pharmacy_dosage_form UUID."""
    if not legacy_dosage_form:
        return None
    
    from app.models.pharmacy_models import PharmacyDosageForm
    
    # Direct match
    df = session.query(PharmacyDosageForm).filter(
        PharmacyDosageForm.name.ilike(legacy_dosage_form)
    ).first()
    
    if df:
        return df.id
    
    # Partial match mappings
    mappings = {
        'tab': 'Tablet',
        'tabs': 'Tablet',
        'cap': 'Capsule',
        'caps': 'Capsule',
        'syp': 'Syrup',
        'syr': 'Syrup',
        'inj': 'Injection',
        'iv': 'Intravenous',
        'im': 'Intramuscular',
        'sc': 'Subcutaneous',
        'cre': 'Cream',
        'oint': 'Ointment',
        'g': 'Gel',
        'lot': 'Lotion',
        'drop': 'Drops',
        'eye': 'Eye Drops',
        'ear': 'Ear Drops',
        'nasal': 'Nasal Drops',
        'inhal': 'Inhaler',
        'ors': 'Oral Rehydration Salt',
        'powder': 'Powder',
        'soln': 'Solution',
        'supp': 'Suppository',
        'vag': 'Vaginal Tablet',
    }
    
    legacy_lower = legacy_dosage_form.lower().strip()
    for key, value in mappings.items():
        if key in legacy_lower:
            df = session.query(PharmacyDosageForm).filter(
                PharmacyDosageForm.name.ilike(value)
            ).first()
            if df:
                return df.id
    
    return None

def migrate_medications_to_pharmacy_drug(session):
    """Migrate medications table to pharmacy_drug table."""
    
    from app.models.inventory_models import Medication
    from app.models.pharmacy_models import PharmacyDrug
    
    # Check if there are already drugs in pharmacy_drug
    existing_count = session.query(PharmacyDrug).count()
    print(f"Existing pharmacy_drug records: {existing_count}")
    
    if existing_count > 0:
        print("Pharmacy drugs already exist. Skipping migration...")
        return 0
    
    # Get all active medications
    medications = session.query(Medication).filter(Medication.is_active == True).all()
    print(f"Found {len(medications)} active medications to migrate.")
    
    migrated_count = 0
    
    for med in medications:
        # Parse strength
        strength_value, strength_unit = parse_strength(med.strength)
        
        # Map dosage form
        dosage_form_id = map_dosage_form_legacy_to_uuid(session, med.dosage_form)
        
        # Generate item_code if not exists
        item_code = med.medication_code or f"MED-{med.id:05d}"
        
        # Determine route based on dosage form
        route = None
        if med.dosage_form:
            dosage_lower = med.dosage_form.lower()
            if 'inj' in dosage_lower or 'iv' in dosage_lower or 'im' in dosage_lower:
                route = 'PARENTERAL'
            elif 'oral' in dosage_lower or 'tab' in dosage_lower or 'cap' in dosage_lower or 'syp' in dosage_lower:
                route = 'ORAL'
            elif 'eye' in dosage_lower:
                route = 'OPHTHALMIC'
            elif 'ear' in dosage_lower:
                route = 'OTIC'
            elif 'nasal' in dosage_lower:
                route = 'NASAL'
            elif 'cream' in dosage_lower or 'oint' in dosage_lower or 'gel' in dosage_lower:
                route = 'TOPICAL'
        
        drug = PharmacyDrug(
            id=uuid.uuid4(),
            item_code=item_code,
            generic_name=med.generic_name or med.name,
            brand_name=med.brand_name,
            dosage_form_id=dosage_form_id,
            strength_value=strength_value,
            strength_unit=strength_unit,
            route=route,
            is_controlled=med.is_controlled,
            is_active=med.is_active,
            created_at=med.created_at or datetime.now()
        )
        
        session.add(drug)
        migrated_count += 1
    
    session.commit()
    print(f"Migrated {migrated_count} medications to pharmacy_drug.")
    return migrated_count

def migrate_stock_items_to_pharmacy_batch(session):
    """Migrate stock_items to pharmacy_batch table."""
    
    from app.models.inventory_models import StockItem
    from app.models.pharmacy_models import PharmacyBatch, PharmacyDrug, PharmacyStore
    
    # Get default store or create one
    store = session.query(PharmacyStore).first()
    if not store:
        store = PharmacyStore(name="Main Pharmacy")
        session.add(store)
        session.commit()
        session.refresh(store)
        print(f"Created default store: {store.id}")
    
    # Check if there are already batches
    existing_count = session.query(PharmacyBatch).count()
    print(f"Existing pharmacy_batch records: {existing_count}")
    
    if existing_count > 0:
        print("Pharmacy batches already exist. Skipping migration...")
        return 0
    
    # Get all active stock items with expiry dates
    stock_items = session.query(StockItem).filter(
        StockItem.is_active == True,
        StockItem.expiry_date != None,
        StockItem.quantity > 0
    ).all()
    
    print(f"Found {len(stock_items)} stock items with expiry dates to migrate.")
    
    # Build a mapping from medication_id to pharmacy_drug_id
    from app.models.inventory_models import Medication
    med_to_drug = {}
    medications = session.query(Medication).all()
    for med in medications:
        drug = session.query(PharmacyDrug).filter(
            PharmacyDrug.generic_name.ilike(med.generic_name or med.name)
        ).first()
        if drug:
            med_to_drug[med.id] = drug.id
    
    migrated_count = 0
    
    for item in stock_items:
        drug_id = med_to_drug.get(item.medication_id)
        
        if not drug_id:
            print(f"Warning: No pharmacy_drug found for stock_item {item.id} (medication_id: {item.medication_id}). Skipping...")
            continue
        
        # Handle expiry_date (could be datetime or date)
        expiry_date = item.expiry_date
        if isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()
        
        batch = PharmacyBatch(
            id=uuid.uuid4(),
            drug_id=drug_id,
            store_id=store.id,
            batch_no=item.batch_number or f"BATCH-{item.id}",
            expiry_date=expiry_date,
            received_date=item.purchase_date,
            unit_cost=item.purchase_price,
            selling_price=item.purchase_price * 1.3 if item.purchase_price else None,  # Approx 30% markup
            qty_on_hand=item.quantity,
            qty_reserved=item.reserved_quantity,
            status="ACTIVE",
            created_at=item.created_at or datetime.now()
        )
        
        session.add(batch)
        migrated_count += 1
    
    session.commit()
    print(f"Migrated {migrated_count} stock items to pharmacy_batch.")
    return migrated_count

def update_prescriptions_with_pharmacy_drug_id(session):
    """Update existing prescriptions to link to pharmacy_drug records."""
    
    from app.models.encounter_models import Prescription
    from app.models.pharmacy_models import PharmacyDrug
    
    # Get prescriptions that have medication_id but no pharmacy_drug_id
    prescriptions = session.query(Prescription).filter(
        Prescription.medication_id != None,
        Prescription.pharmacy_drug_id == None
    ).all()
    
    print(f"Found {len(prescriptions)} prescriptions to update with pharmacy_drug_id.")
    
    # Build mapping from medication_id to pharmacy_drug_id
    from app.models.inventory_models import Medication
    med_to_drug = {}
    medications = session.query(Medication).all()
    for med in medications:
        drug = session.query(PharmacyDrug).filter(
            PharmacyDrug.generic_name.ilike(med.generic_name or med.name)
        ).first()
        if drug:
            med_to_drug[med.id] = drug.id
    
    updated_count = 0
    
    for pres in prescriptions:
        drug_id = med_to_drug.get(pres.medication_id)
        if drug_id:
            pres.pharmacy_drug_id = drug_id
            updated_count += 1
    
    session.commit()
    print(f"Updated {updated_count} prescriptions with pharmacy_drug_id.")
    return updated_count

def add_archived_flag_to_legacy_tables(session):
    """Add is_archived flag to legacy tables."""
    
    # Check if column exists
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    
    # Check medications table
    med_columns = [col['name'] for col in inspector.get_columns('medications')]
    if 'is_archived' not in med_columns:
        session.execute(text("ALTER TABLE medications ADD COLUMN is_archived BOOLEAN DEFAULT FALSE"))
        print("Added is_archived column to medications table.")
    
    # Check stock_items table
    stock_columns = [col['name'] for col in inspector.get_columns('stock_items')]
    if 'is_archived' not in stock_columns:
        session.execute(text("ALTER TABLE stock_items ADD COLUMN is_archived BOOLEAN DEFAULT FALSE"))
        print("Added is_archived column to stock_items table.")
    
    session.commit()

def migrate_all():
    """Run all migration steps."""
    print("=" * 60)
    print("Starting Pharmacy Migration: Legacy → Ghana System")
    print("=" * 60)
    
    session = get_session()
    
    try:
        # Phase 1: Seed dosage forms
        print("\n[Phase 1] Seeding dosage forms...")
        seed_dosage_forms(session)
        
        # Phase 2: Migrate medications to pharmacy_drug
        print("\n[Phase 2] Migrating medications to pharmacy_drug...")
        migrate_medications_to_pharmacy_drug(session)
        
        # Phase 3: Migrate stock items to pharmacy_batch
        print("\n[Phase 3] Migrating stock_items to pharmacy_batch...")
        migrate_stock_items_to_pharmacy_batch(session)
        
        # Phase 4: Update prescriptions with pharmacy_drug_id
        print("\n[Phase 4] Updating prescriptions with pharmacy_drug_id...")
        update_prescriptions_with_pharmacy_drug_id(session)
        
        # Phase 5: Add archived flags
        print("\n[Phase 5] Adding archived flags to legacy tables...")
        add_archived_flag_to_legacy_tables(session)
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_all()
