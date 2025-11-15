"""
Automated Backup Service

This module provides automated backup functionality for the LHIMS database.
"""
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.patient_models import Patient
from app.models.billing_models import Invoice, Payment
from app.models.encounter_models import Encounter
from app.models.appointment_models import Appointment


BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)


def generate_backup_filename(prefix: str = "lhims") -> str:
    """Generate a backup filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_backup_{timestamp}"


def backup_table_to_csv(db: Session, table_name: str, output_path: Path) -> bool:
    """
    Backup a database table to CSV.
    
    Args:
        db: Database session
        table_name: Name of the table to backup
        output_path: Path to output CSV file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get table data
        result = db.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        columns = result.keys()
        
        if not rows:
            return False
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        return True
    except Exception as e:
        print(f"Error backing up table {table_name}: {e}")
        return False


def backup_patients(db: Session, output_path: Path) -> bool:
    """Backup patients table to CSV."""
    return backup_table_to_csv(db, "patients", output_path)


def backup_invoices(db: Session, output_path: Path) -> bool:
    """Backup invoices table to CSV."""
    return backup_table_to_csv(db, "invoices", output_path)


def backup_payments(db: Session, output_path: Path) -> bool:
    """Backup payments table to CSV."""
    return backup_table_to_csv(db, "payments", output_path)


def create_full_backup(db: Session, include_data: bool = True) -> Optional[Path]:
    """
    Create a full backup of the system.
    
    Args:
        db: Database session
        include_data: Whether to include data backups (CSV files)
        
    Returns:
        Path to backup directory or None if failed
    """
    try:
        # Create backup directory
        backup_name = generate_backup_filename()
        backup_path = BACKUP_DIR / backup_name
        backup_path.mkdir(exist_ok=True)
        
        # Create metadata file
        metadata = {
            "backup_date": datetime.now().isoformat(),
            "backup_type": "full",
            "includes_data": include_data,
            "tables_backed_up": []
        }
        
        if include_data:
            # Backup key tables
            tables = [
                ("patients", backup_patients),
                ("invoices", backup_invoices),
                ("payments", backup_payments),
            ]
            
            for table_name, backup_func in tables:
                csv_path = backup_path / f"{table_name}.csv"
                if backup_func(db, csv_path):
                    metadata["tables_backed_up"].append(table_name)
        
        # Save metadata
        metadata_path = backup_path / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None


def list_backups() -> List[dict]:
    """
    List all available backups.
    
    Returns:
        List of backup metadata dictionaries
    """
    backups = []
    
    if not BACKUP_DIR.exists():
        return backups
    
    for backup_dir in BACKUP_DIR.iterdir():
        if backup_dir.is_dir():
            metadata_path = backup_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        metadata["backup_path"] = str(backup_dir)
                        backups.append(metadata)
                except Exception:
                    continue
    
    # Sort by date (newest first)
    backups.sort(key=lambda x: x.get("backup_date", ""), reverse=True)
    return backups

