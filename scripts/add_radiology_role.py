#!/usr/bin/env python3
"""
Simple script to add Radiology Staff role to the database.
Run this if the role doesn't exist yet.
"""
import sys
import os

# Add app to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.db.database import SessionLocal
from app.models.user_models import Role

def add_radiology_role():
    """Add Radiology Staff role if it doesn't exist"""
    db = SessionLocal()
    
    try:
        # Check if role exists
        role = db.query(Role).filter(Role.name == "Radiology Staff").first()
        
        if role:
            print(f"Role 'Radiology Staff' already exists (ID: {role.id})")
        else:
            # Create the role
            role = Role(
                name="Radiology Staff",
                description="Fulfills radiology orders, manages PACS images"
            )
            db.add(role)
            db.commit()
            print(f"Successfully created role: 'Radiology Staff' (ID: {role.id})")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_radiology_role()

