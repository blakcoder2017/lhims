#!/usr/bin/env python3
"""
Patch script to fix field types in existing lab templates.
Changes "select" to "choice" for dropdown fields.
"""
import sys
import os
import json
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres:password123@localhost:5433/lhims"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fix_template_field_types():
    """Update all templates to use 'choice' instead of 'select'."""
    db = SessionLocal()
    
    try:
        # Get all template versions (latest version per template)
        result = db.execute(text("""
            SELECT DISTINCT ON (lt.id)
                lt.id, lt.name, lt.current_version, ltv.schema_json 
            FROM lab_templates lt 
            JOIN lab_template_versions ltv ON lt.id = ltv.template_id 
            WHERE ltv.version = lt.current_version
            ORDER BY lt.id, ltv.version DESC
        """))
        
        updated_count = 0
        for row in result:
            template_id, template_name, current_version, schema_json = row
            
            # Handle both string and dict formats
            if isinstance(schema_json, str):
                schema = json.loads(schema_json)
            else:
                schema = schema_json
            
            fields = schema.get("fields", {})
            modified = False
            
            for field_code, field_def in fields.items():
                if field_def.get("type") == "select":
                    field_def["type"] = "choice"
                    modified = True
                    print(f"  Fixed: {field_code} -> choice ({template_name})")
            
            if modified:
                # Update the schema - create new version
                new_version = current_version + 1
                new_schema_json = json.dumps(schema)
                
                # Insert new version
                new_version_id = str(uuid.uuid4())
                db.execute(text("""
                    INSERT INTO lab_template_versions (id, template_id, version, status, schema_json)
                    VALUES (:id, :template_id, :version, 'PUBLISHED', :schema_json)
                """), {
                    "id": new_version_id,
                    "template_id": template_id,
                    "version": new_version,
                    "schema_json": new_schema_json
                })
                
                # Update template
                db.execute(text("""
                    UPDATE lab_templates SET current_version = :version WHERE id = :tid
                """), {"version": new_version, "tid": template_id})
                
                updated_count += 1
        
        db.commit()
        print(f"\n✓ Updated {updated_count} templates")
        return updated_count
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Fixing Lab Template Field Types")
    print("=" * 60)
    fix_template_field_types()
    print("\nDone!")
