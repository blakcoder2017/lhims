"""
Script to import diseases from CSV file into the database.
"""
import csv
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SessionLocal
from app.models.disease_models import Disease


def import_diseases_from_csv(csv_file_path: str):
    """Import diseases from CSV file."""
    db = SessionLocal()
    
    try:
        imported_count = 0
        skipped_count = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                disease_name = row.get('Disease', '').strip()
                
                if not disease_name:
                    continue
                
                # Check if disease already exists
                existing = db.query(Disease).filter(Disease.name == disease_name).first()
                if existing:
                    print(f"Skipping duplicate: {disease_name}")
                    skipped_count += 1
                    continue
                
                # Create new disease
                disease = Disease(
                    name=disease_name,
                    is_system=True,  # Mark as system-imported
                    is_active=True
                )
                
                db.add(disease)
                imported_count += 1
        
        db.commit()
        print(f"\nImport completed!")
        print(f"Imported: {imported_count} diseases")
        print(f"Skipped (duplicates): {skipped_count} diseases")
        
    except Exception as e:
        db.rollback()
        print(f"Error importing diseases: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Default CSV file path
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'diseases.csv')
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    print(f"Importing diseases from: {csv_path}")
    import_diseases_from_csv(csv_path)

