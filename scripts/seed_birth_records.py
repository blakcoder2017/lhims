"""
Seed script for birth records.
Run this script to populate sample birth records for testing.

Usage:
    python scripts/seed_birth_records.py

Note: Make sure the database is running and accessible.
This script connects directly to PostgreSQL using SQLAlchemy.
"""
import sys
import os
from datetime import date, time, datetime
from decimal import Decimal

# --- Add app to Python path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# --- End path setup ---

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, Time, Boolean, Numeric, Enum
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
import enum

# --- Database Configuration ---
# Docker PostgreSQL is exposed on port 5433 on the host
DATABASE_URL = "postgresql://postgres:password123@localhost:5433/lhims"

print(f"Connecting to database: {DATABASE_URL.split('@')[0]}@...")

# Create engine and session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Define Enums ---
class DeliveryType(str, enum.Enum):
    VAGINAL = "vaginal"
    CAESAREAN = "caesarean"
    ASSISTED = "assisted"
    VACUUM = "vacuum"
    FORCEPS = "forceps"
    OTHER = "other"

class BirthOutcome(str, enum.Enum):
    LIVE = "live"
    STILLBIRTH = "stillbirth"
    NEONATAL_DEATH = "neonatal_death"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"

# --- Define BirthRecord Model (same as app/models/birth_models.py) ---
class BirthRecord(Base):
    __tablename__ = "birth_records"
    
    id = Column(Integer, primary_key=True, index=True)
    mother_patient_id = Column(Integer, nullable=False)
    admission_id = Column(Integer, nullable=True)
    encounter_id = Column(Integer, nullable=True)
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=True)
    delivery_type = Column(String(20), nullable=False, default=DeliveryType.VAGINAL.value)
    birth_outcome = Column(String(20), nullable=False, default=BirthOutcome.LIVE.value)
    gender = Column(String(10), nullable=True)
    weight_kg = Column(Numeric(5, 3), nullable=True)
    length_cm = Column(Numeric(5, 2), nullable=True)
    head_circumference_cm = Column(Numeric(5, 2), nullable=True)
    apgar_1min = Column(Integer, nullable=True)
    apgar_5min = Column(Integer, nullable=True)
    apgar_10min = Column(Integer, nullable=True)
    delivered_by_id = Column(Integer, nullable=True)
    assisted_by_id = Column(Integer, nullable=True)
    birth_number = Column(String(50), unique=True, nullable=True, index=True)
    gravida = Column(Integer, nullable=True)
    para = Column(Integer, nullable=True)
    complications = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)


def seed_birth_records():
    """Seed sample birth records for testing."""
    print("--- Seeding Birth Records ---")
    db = SessionLocal()
    
    try:
        # Check if birth records already exist
        existing_count = db.query(BirthRecord).filter(BirthRecord.is_active == True).count()
        if existing_count > 0:
            print(f"Birth records already exist ({existing_count} records). Skipping seed.")
            return

        # Sample birth records data
        # Note: These use existing patient IDs from test_patients.csv
        # Patient ID 23 is female (Abubakari Musherifa)
        
        sample_births = [
            {
                "mother_patient_id": 23,
                "birth_date": date.today(),
                "birth_time": time(8, 30),
                "delivery_type": DeliveryType.VAGINAL.value,
                "birth_outcome": BirthOutcome.LIVE.value,
                "gender": Gender.FEMALE.value,
                "weight_kg": Decimal("3.200"),
                "length_cm": Decimal("50.5"),
                "head_circumference_cm": Decimal("35.0"),
                "apgar_1min": 8,
                "apgar_5min": 9,
                "apgar_10min": 10,
                "gravida": 1,
                "para": 0,
                "delivered_by_id": 1,
                "complications": None,
                "notes": "Normal delivery, healthy baby girl",
            },
            {
                "mother_patient_id": 23,
                "birth_date": date.today(),
                "birth_time": time(14, 45),
                "delivery_type": DeliveryType.CAESAREAN.value,
                "birth_outcome": BirthOutcome.LIVE.value,
                "gender": Gender.MALE.value,
                "weight_kg": Decimal("3.500"),
                "length_cm": Decimal("51.0"),
                "head_circumference_cm": Decimal("36.0"),
                "apgar_1min": 7,
                "apgar_5min": 9,
                "apgar_10min": 9,
                "gravida": 2,
                "para": 1,
                "delivered_by_id": 1,
                "complications": "Slight bleeding, controlled",
                "notes": "Planned C-section, mother and baby doing well",
            },
            {
                "mother_patient_id": 23,
                "birth_date": date.today(),
                "birth_time": time(22, 15),
                "delivery_type": DeliveryType.VAGINAL.value,
                "birth_outcome": BirthOutcome.LIVE.value,
                "gender": Gender.MALE.value,
                "weight_kg": Decimal("2.800"),
                "length_cm": Decimal("48.5"),
                "head_circumference_cm": Decimal("34.0"),
                "apgar_1min": 6,
                "apgar_5min": 8,
                "apgar_10min": 9,
                "gravida": 3,
                "para": 2,
                "delivered_by_id": 1,
                "complications": "Premature birth, low birth weight",
                "notes": "Baby admitted to NICU for monitoring",
            },
            {
                "mother_patient_id": 23,
                "birth_date": date.today(),
                "birth_time": time(6, 0),
                "delivery_type": DeliveryType.ASSISTED.value,
                "birth_outcome": BirthOutcome.STILLBIRTH.value,
                "gender": Gender.FEMALE.value,
                "weight_kg": Decimal("4.100"),
                "length_cm": Decimal("52.0"),
                "head_circumference_cm": Decimal("36.5"),
                "apgar_1min": 0,
                "apgar_5min": 0,
                "apgar_10min": 0,
                "gravida": 4,
                "para": 3,
                "delivered_by_id": 1,
                "complications": "Umbilical cord prolapse",
                "notes": "Tragic stillbirth, mother counselled",
            },
            {
                "mother_patient_id": 23,
                "birth_date": date.today(),
                "birth_time": time(11, 30),
                "delivery_type": DeliveryType.VACUUM.value,
                "birth_outcome": BirthOutcome.LIVE.value,
                "gender": Gender.MALE.value,
                "weight_kg": Decimal("3.350"),
                "length_cm": Decimal("50.0"),
                "head_circumference_cm": Decimal("35.5"),
                "apgar_1min": 5,
                "apgar_5min": 7,
                "apgar_10min": 8,
                "gravida": 2,
                "para": 1,
                "delivered_by_id": 1,
                "complications": "Fetal distress, vacuum extraction",
                "notes": "Emergency vacuum delivery, baby recovered well",
            },
        ]

        # Create birth records
        for i, birth_data in enumerate(sample_births):
            # Generate birth number
            today = date.today()
            count = i + 1
            birth_number = f"BIRTH-{today.strftime('%Y')}-{str(count).zfill(4)}"
            birth_data["birth_number"] = birth_number
            
            birth_record = BirthRecord(**birth_data)
            db.add(birth_record)
            print(f"Created birth record: {birth_number}")

        db.commit()
        print(f"--- Seeding Complete: {len(sample_births)} birth records created ---")

    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_birth_records()
