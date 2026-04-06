"""
Automated Backup Service

This module provides automated backup functionality for the LHIMS database.
"""
import os
import re
import json
import csv
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

from app.models.patient_models import Patient
from app.models.billing_models import Invoice, Payment
from app.models.encounter_models import Encounter
from app.models.scheduled_appointment_models import Appointment
from app.core.config import settings


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
                # Convert RowProxy to dict properly
                row_dict = {key: value for key, value in zip(columns, row)}
                writer.writerow(row_dict)
        
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


def parse_database_url(url: str) -> Dict[str, str]:
    """
    Parse PostgreSQL connection URL into components.
    
    Args:
        url: PostgreSQL connection URL (postgresql://user:pass@host:port/db)
    
    Returns:
        Dictionary with host, port, user, password, database
    """
    # Pattern to match postgresql://user:password@host:port/database
    pattern = r'postgresql://(?:(?P<user>[^:]+):(?P<password>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)/(?P<database>.+)'
    match = re.match(pattern, url)
    
    if match:
        return {
            'user': match.group('user') or 'postgres',
            'password': match.group('password') or '',
            'host': match.group('host'),
            'port': match.group('port'),
            'database': match.group('database')
        }
    
    # Default fallback
    return {
        'user': 'postgres',
        'password': '',
        'host': 'localhost',
        'port': '5432',
        'database': 'lhims'
    }


def get_database_info() -> Dict[str, any]:
    """
    Get information about the database.
    
    Returns:
        Dictionary with database information
    """
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Get table count and sizes
        result = db.execute(text("""
            SELECT 
                count(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """))
        table_count = result.scalar() or 0
        
        # Get total database size
        result = db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as size
        """))
        db_size = result.scalar() or 'unknown'
        
        # Get list of tables
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        return {
            'table_count': table_count,
            'database_size': db_size,
            'tables': tables,
            'database_name': parse_database_url(settings.SQLALCHEMY_DATABASE_URL).get('database', 'lhims')
        }
    except Exception as e:
        return {
            'table_count': 0,
            'database_size': 'unknown',
            'tables': [],
            'database_name': 'lhims',
            'error': str(e)
        }
    finally:
        db.close()


def create_complete_backup(include_data: bool = True, compress: bool = True) -> Optional[Path]:
    """
    Create a complete database backup using pg_dump.
    
    Args:
        include_data: Whether to include data (True) or schema only (False)
        compress: Whether to compress the backup with gzip
    
    Returns:
        Path to backup file or None if failed
    """
    try:
        # Parse database URL
        db_config = parse_database_url(settings.SQLALCHEMY_DATABASE_URL)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"lhims_complete_backup_{timestamp}"
        
        # Ensure backup directory exists
        BACKUP_DIR.mkdir(exist_ok=True)
        
        # Determine output path
        if compress:
            output_file = BACKUP_DIR / f"{backup_name}.sql.gz"
        else:
            output_file = BACKUP_DIR / f"{backup_name}.sql"
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', db_config['database'],
            '-F', 'p',  # Plain text format
        ]
        
        # Add password if provided (via PGPASSWORD env var)
        if db_config['password']:
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
        else:
            env = None
        
        # Data only or full
        if not include_data:
            cmd.append('--schema-only')
        
        # Create the backup
        if compress:
            # Use gzip to compress output
            with open(output_file, 'wb') as f:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                compress_proc = subprocess.Popen(['gzip'], stdin=proc.stdout, stdout=f)
                proc.stdout.close()
                stdout, stderr = proc.communicate()
                compress_proc.wait()
                
                if proc.returncode != 0:
                    error_msg = stderr.decode() if stderr else 'Unknown error'
                    print(f"pg_dump error: {error_msg}")
                    output_file.unlink(missing_ok=True)
                    return None
        else:
            with open(output_file, 'w') as f:
                proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)
                if proc.returncode != 0:
                    error_msg = proc.stderr.decode() if proc.stderr else 'Unknown error'
                    print(f"pg_dump error: {error_msg}")
                    output_file.unlink(missing_ok=True)
                    return None
        
        # Get file size
        file_size = output_file.stat().st_size
        
        # Create metadata
        metadata = {
            "backup_date": datetime.now().isoformat(),
            "backup_type": "complete",
            "backup_method": "pg_dump",
            "includes_data": include_data,
            "compressed": compress,
            "file_size_bytes": file_size,
            "file_size_readable": _format_file_size(file_size),
            "database_name": db_config['database'],
            "sql_file": str(output_file.name)
        }
        
        # Also save metadata
        metadata_path = BACKUP_DIR / f"{backup_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update list of backups in metadata
        _update_backup_list(backup_name, metadata)
        
        print(f"Complete backup created: {output_file}")
        return output_file
        
    except FileNotFoundError:
        print("Error: pg_dump not found. Make sure PostgreSQL client is installed.")
        return None
    except Exception as e:
        print(f"Error creating complete backup: {e}")
        return None


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def _update_backup_list(backup_name: str, metadata: dict):
    """Update the backup list JSON file."""
    list_file = BACKUP_DIR / "backups_list.json"
    
    backups = []
    if list_file.exists():
        try:
            with open(list_file, 'r') as f:
                backups = json.load(f)
        except:
            pass
    
    metadata['backup_name'] = backup_name
    backups.append(metadata)
    
    # Keep only last 100 backups in list
    backups = backups[-100:]
    
    with open(list_file, 'w') as f:
        json.dump(backups, f, indent=2)


def restore_from_backup(backup_file: Path, drop_existing: bool = True) -> tuple[bool, str]:
    """
    Restore database from a backup file using psql.
    
    Args:
        backup_file: Path to the SQL backup file (.sql or .sql.gz)
        drop_existing: Whether to drop existing tables before restoring
    
    Returns:
        Tuple of (success, message)
    """
    try:
        if not backup_file.exists():
            return False, f"Backup file not found: {backup_file}"
        
        # Parse database URL
        db_config = parse_database_url(settings.SQLALCHEMY_DATABASE_URL)
        
        # Build psql command
        cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', db_config['database'],
        ]
        
        # Add password if provided
        if db_config['password']:
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
        else:
            env = None
        
        # Determine how to handle the input file
        if str(backup_file).endswith('.gz'):
            # Decompress with gzip
            with open(backup_file, 'rb') as f:
                proc = subprocess.Popen(
                    ['gunzip'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                decompressed = proc.stdout
                
                proc2 = subprocess.Popen(
                    cmd,
                    stdin=decompressed,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                stdout, stderr = proc2.communicate()
                proc.wait()
        else:
            # Direct SQL file
            with open(backup_file, 'r') as f:
                proc = subprocess.run(
                    cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                stdout, stderr = proc.stdout, proc.stderr
        
        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else 'Unknown error'
            return False, f"Restore failed: {error_msg}"
        
        return True, "Database restored successfully"
        
    except FileNotFoundError:
        return False, "psql not found. Make sure PostgreSQL client is installed."
    except Exception as e:
        return False, f"Error restoring backup: {e}"


def list_complete_backups() -> List[dict]:
    """
    List all complete SQL backups.
    
    Returns:
        List of complete backup metadata
    """
    backups = []
    list_file = BACKUP_DIR / "backups_list.json"
    
    if list_file.exists():
        try:
            with open(list_file, 'r') as f:
                all_backups = json.load(f)
                backups = [b for b in all_backups if b.get('backup_type') == 'complete']
        except:
            pass
    
    # Also check filesystem for any SQL files we might have missed
    if BACKUP_DIR.exists():
        for f in BACKUP_DIR.iterdir():
            if f.is_file() and (f.suffix == '.sql' or f.suffix == '.gz'):
                # Check if this backup is already in our list
                if not any(b.get('sql_file') == str(f.name) for b in backups):
                    try:
                        stat = f.stat()
                        backups.append({
                            'backup_name': f.stem,
                            'backup_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'backup_type': 'complete',
                            'sql_file': f.name,
                            'file_size_bytes': stat.st_size,
                            'file_size_readable': _format_file_size(stat.st_size)
                        })
                    except:
                        pass
    
    # Sort by date
    backups.sort(key=lambda x: x.get('backup_date', ''), reverse=True)
    return backups

