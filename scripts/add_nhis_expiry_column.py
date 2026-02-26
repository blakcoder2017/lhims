#!/usr/bin/env python3
"""
Add nhis_expiry_date column to patients table.
Run this if the alembic migration fails: python scripts/add_nhis_expiry_column.py
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS nhis_expiry_date DATE"))
        conn.commit()
    print("Column patients.nhis_expiry_date added successfully.")

if __name__ == "__main__":
    main()
