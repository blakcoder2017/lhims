#!/usr/bin/env python3
"""
Bulk import drugs from CSV file to LHIMS pharmacy_drug catalog.
CSV Format: BRAND NAME, DOSAGE FORM, STRENGGTH, Strength Unit, Route, Reorder Level
"""

import csv
import uuid
import re
from sqlalchemy import create_engine, text
import sys

# Database connection
DATABASE_URL = "postgresql+psycopg2://postgres:password123@localhost:5433/lhims"

# CSV file path
CSV_FILE = "/home/dei-gratia-server/Downloads/2026-02-26 09:59:05.425/MEDS-2.csv"

# Mapping of common dosage forms to standardized values
DOSAGE_FORM_MAP = {
    'tablet': 'Tablet', 'tablets': 'Tablet', 'tab': 'Tablet',
    'capsule': 'Capsule', 'capsules': 'Capsule', 'cap': 'Capsule',
    'suspension': 'Suspension', 'syrup': 'Syrup', 'liquid': 'Liquid',
    'injection': 'Injection', 'inj': 'Injection', 'iv': 'IV', 'infusion': 'Infusion',
    'cream': 'Cream', 'ointment': 'Ointment', 'gel': 'Gel',
    'solution': 'Solution', 'drops': 'Drops', 'eye drops': 'Eye Drops',
    'nasal spray': 'Nasal Spray', 'spray': 'Spray', 'inhaler': 'Inhaler',
    'suppository': 'Suppository', 'supp': 'Suppository', 'pessaries': 'Pessaries',
    'nebule': 'Nebule', 'shampoo': 'Shampoo', 'powder': 'Powder',
}

# Route mapping
ROUTE_MAP = {
    'oral': 'Oral', 'po': 'Oral', 'iv': 'IV', 'im': 'IM', 'sc': 'SC',
    'topical': 'Topical', 'inhalation': 'Inhalation', 'nasal': 'Nasal',
    'ocular': 'Ocular', 'rectal': 'Rectal', 'vaginal': 'Vaginal',
}

# Controlled drugs list
CONTROLLED_DRUGS = [
    'morphine', 'pethidine', 'tramadol', 'diazepam', 'midazolam', 'clonazepam',
    'phenobarbitone', 'phenytoin', 'carbamazepine', 'methadone', 'fentanyl',
    'pentazocine', 'buprenorphine', 'codeine', 'dihydrocodeine',
]

DEFAULT_DOSAGE_FORM = 'Tablet'

def normalize_dosage_form(form):
    if not form or form.strip() == '':
        return DEFAULT_DOSAGE_FORM
    form = form.strip().lower()
    return DOSAGE_FORM_MAP.get(form, form.title())

def normalize_route(route):
    if not route:
        return 'Oral'
    route = route.strip().lower()
    return ROUTE_MAP.get(route, route.title())

def is_controlled_drug(brand_name):
    if not brand_name:
        return False
    brand_lower = brand_name.lower()
    return any(drug in brand_lower for drug in CONTROLLED_DRUGS)

def generate_item_code(brand_name, strength, strength_unit):
    """Generate a unique item code for the drug."""
    # Use more characters from brand name for uniqueness
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', brand_name.strip())
    
    if len(clean_name) > 15:
        slug = clean_name[:15].upper()
    else:
        slug = clean_name.upper()
    
    # Add strength if available
    if strength and strength_unit:
        unit_abbr = strength_unit.strip()[:3].upper()
        code = f"{slug[:10]}-{int(strength) if strength == int(strength) else strength}{unit_abbr}"
    elif strength:
        code = f"{slug[:10]}-{int(strength) if strength == int(strength) else strength}"
    else:
        code = slug[:18]
    
    return code

def clean_strength(strength_str):
    if not strength_str:
        return None
    try:
        if '/' in str(strength_str):
            return None
        return float(re.sub(r'[^0-9.]', '', str(strength_str).strip()))
    except (ValueError, TypeError):
        return None

def clean_reorder_level(level_str):
    """Clean and convert reorder level to numeric value."""
    if not level_str:
        return 10  # Default
    try:
        return float(re.sub(r'[^0-9.]', '', str(level_str).strip()))
    except (ValueError, TypeError):
        return 10  # Default

def import_drugs_from_csv():
    """Import drugs from CSV file with individual transactions per row."""
    
    engine = create_engine(DATABASE_URL)
    
    drugs_added = 0
    drugs_skipped = 0
    errors = []
    
    # Read CSV first
    csv_rows = []
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        print(f"CSV Header: {header}")
        
        for row_num, row in enumerate(reader, start=2):
            csv_rows.append((row_num, row))
    
    print(f"Found {len(csv_rows)} rows to process\n")
    
    # Process each row independently
    for row_num, row in csv_rows:
        conn = engine.connect()
        try:
            trans = conn.begin()
            
            brand_name = row[1].strip() if len(row) > 1 and row[1] else ''
            dosage_form_raw = row[2].strip() if len(row) > 2 and row[2] else ''
            strength_raw = row[3].strip() if len(row) > 3 and row[3] else ''
            strength_unit_raw = row[4].strip() if len(row) > 4 and row[4] else ''
            route_raw = row[5].strip() if len(row) > 5 and row[5] else ''
            reorder_level_raw = row[6].strip() if len(row) > 6 and row[6] else '10'  # Default to 10
            
            if not brand_name:
                drugs_skipped += 1
                trans.rollback()
                conn.close()
                continue
            
            dosage_form = normalize_dosage_form(dosage_form_raw)
            route = normalize_route(route_raw)
            strength_value = clean_strength(strength_raw)
            strength_unit = strength_unit_raw.strip() if strength_unit_raw else None
            reorder_level = clean_reorder_level(reorder_level_raw)
            controlled = is_controlled_drug(brand_name)
            item_code = generate_item_code(brand_name, strength_value, strength_unit)
            
            # Check if exists
            check_result = conn.execute(text("SELECT id FROM pharmacy_drug WHERE item_code = :code"), {"code": item_code})
            if check_result.fetchone():
                drugs_skipped += 1
                trans.rollback()
                conn.close()
                continue
            
            # Get or create dosage form
            result = conn.execute(text("SELECT id FROM pharmacy_dosage_form WHERE LOWER(name) = :name"), {"name": dosage_form.lower()})
            form_row = result.fetchone()
            
            if form_row:
                dosage_form_id = form_row[0]
            else:
                new_form_id = uuid.uuid4()
                conn.execute(text("INSERT INTO pharmacy_dosage_form (id, name) VALUES (:id, :name)"), {"id": new_form_id, "name": dosage_form})
                dosage_form_id = new_form_id
            
            # Insert drug
            drug_id = uuid.uuid4()
            conn.execute(text("""
                INSERT INTO pharmacy_drug (
                    id, item_code, generic_name, brand_name, dosage_form_id,
                    strength_value, strength_unit, route, is_controlled,
                    is_active, reorder_level, created_at
                ) VALUES (
                    :id, :item_code, :generic_name, :brand_name, :dosage_form_id,
                    :strength_value, :strength_unit, :route, :is_controlled,
                    :is_active, :reorder_level, NOW()
                )
            """), {
                "id": drug_id,
                "item_code": item_code,
                "generic_name": brand_name,
                "brand_name": brand_name,
                "dosage_form_id": dosage_form_id,
                "strength_value": strength_value,
                "strength_unit": strength_unit,
                "route": route,
                "is_controlled": controlled,
                "is_active": True,
                "reorder_level": reorder_level
            })
            
            trans.commit()
            drugs_added += 1
            
            if drugs_added % 50 == 0:
                print(f"  Imported {drugs_added} drugs...")
                
        except Exception as e:
            try:
                trans.rollback()
            except:
                pass
            error_msg = f"Row {row_num}: {str(e)[:80]}"
            errors.append(error_msg)
            print(f"  ERROR {error_msg}")
        finally:
            conn.close()
    
    print("\n" + "=" * 60)
    print(f"IMPORT COMPLETED!")
    print(f"  Drugs added: {drugs_added}")
    print(f"  Drugs skipped (exists): {drugs_skipped}")
    print(f"  Errors: {len(errors)}")
    print("=" * 60)
    
    if errors:
        print("\nFirst 5 errors:")
        for err in errors[:5]:
            print(f"  - {err}")
    
    engine.dispose()

def verify_import():
    """Verify the imported drugs."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM pharmacy_drug"))
        count = result.scalar()
        print(f"\nTotal drugs in database: {count}")
        
        result = conn.execute(text("""
            SELECT item_code, generic_name, dosage_form_id, strength_value, strength_unit, route, is_controlled 
            FROM pharmacy_drug 
            ORDER BY created_at DESC 
            LIMIT 10
        """))
        print("\nRecently added drugs:")
        for row in result:
            print(f"  {row[0]}: {row[1]} {row[3]}{row[4]} ({row[5]}) - Controlled: {row[6]}")
    
    engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("BULK DRUG IMPORT TO LHIMS")
    print("=" * 60)
    print(f"Reading from: {CSV_FILE}\n")
    
    import_drugs_from_csv()
    verify_import()
