"""
Enhanced Backup Script with Google Drive Integration

This script creates comprehensive backups and uploads them to Google Drive.
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db.database import SessionLocal
from app.services.backup_service import create_full_backup, BACKUP_DIR
from scripts.google_drive_service import GoogleDriveService


class BackupToDrive:
    """Main backup orchestrator with Google Drive integration."""
    
    def __init__(self, config_path: str = ".backup_config"):
        """Initialize backup system."""
        self.config_path = config_path
        self.config = self.load_config()
        self.drive_service = GoogleDriveService()
    
    def load_config(self) -> Dict[str, Any]:
        """Load backup configuration."""
        default_config = {
            "backup_scope": "full",  # "database", "files", "full"
            "compress_backups": True,
            "encrypt_backups": False,
            "local_retention_days": 30,
            "drive_retention_days": 90,
            "include_patterns": [
                "app/**/*.py",
                "migrations/**/*",
                "requirements.txt",
                "docker-compose.yml",
                ".env",
                "app/static/uploads/**/*"
            ],
            "exclude_patterns": [
                "venv/**/*",
                "__pycache__/**/*",
                "*.pyc",
                ".git/**/*",
                "test_*.db"
            ]
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config, using defaults: {e}")
        
        return default_config
    
    def create_database_backup(self) -> Optional[Path]:
        """Create database backup using existing service."""
        db = SessionLocal()
        try:
            backup_path = create_full_backup(db, include_data=True)
            if backup_path:
                print(f"✅ Database backup created: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            return None
        finally:
            db.close()
    
    def create_files_backup(self) -> Optional[Path]:
        """Create application files backup."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"lhims_files_backup_{timestamp}"
            backup_path = BACKUP_DIR / f"{backup_name}.zip"
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for pattern in self.config["include_patterns"]:
                    for file_path in BASE_DIR.glob(pattern):
                        if file_path.is_file():
                            # Add file to zip with relative path
                            arcname = file_path.relative_to(BASE_DIR)
                            zipf.write(file_path, arcname)
            
            print(f"✅ Files backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Files backup failed: {e}")
            return None
    
    def create_comprehensive_backup(self) -> Optional[Path]:
        """Create comprehensive backup including database and files."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"lhims_comprehensive_backup_{timestamp}"
            backup_dir = BACKUP_DIR / backup_name
            backup_dir.mkdir(exist_ok=True)
            
            # Create database backup
            db_backup = self.create_database_backup()
            if db_backup and db_backup.exists():
                shutil.copytree(db_backup, backup_dir / "database", dirs_exist_ok=True)
            
            # Create files backup
            files_backup = self.create_files_backup()
            if files_backup and files_backup.exists():
                shutil.copy2(files_backup, backup_dir / "files.zip")
            
            # Create metadata
            metadata = {
                "backup_date": datetime.now().isoformat(),
                "backup_type": "comprehensive",
                "components": ["database", "files"],
                "config": self.config
            }
            
            with open(backup_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Compress if enabled
            if self.config["compress_backups"]:
                archive_path = BACKUP_DIR / f"{backup_name}.zip"
                shutil.make_archive(
                    str(archive_path.with_suffix('')),
                    'zip',
                    str(backup_dir),
                    '.'
                )
                shutil.rmtree(backup_dir)
                backup_path = archive_path
            else:
                backup_path = backup_dir
            
            print(f"✅ Comprehensive backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Comprehensive backup failed: {e}")
            return None
    
    def upload_to_drive(self, backup_path: Path) -> Optional[str]:
        """Upload backup to Google Drive."""
        try:
            # Setup folder structure
            folder_structure = self.drive_service.setup_backup_structure()
            if not folder_structure:
                raise Exception("Failed to setup Drive folders")
            
            # Upload backup
            file_id = self.drive_service.upload_file(
                str(backup_path),
                folder_structure['month'],
                overwrite=True
            )
            
            if file_id:
                print(f"✅ Backup uploaded to Google Drive: {file_id}")
                return file_id
            else:
                raise Exception("Upload failed")
                
        except Exception as e:
            print(f"❌ Drive upload failed: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Clean up old local and remote backups."""
        try:
            # Clean local backups
            local_retention = self.config["local_retention_days"]
            if BACKUP_DIR.exists():
                cutoff_date = datetime.now().timestamp() - (local_retention * 24 * 60 * 60)
                
                for item in BACKUP_DIR.iterdir():
                    if item.is_dir() or item.suffix in ['.zip', '.tar.gz']:
                        item_time = item.stat().st_mtime
                        if item_time < cutoff_date:
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                            print(f"🗑️ Deleted old local backup: {item.name}")
            
            # Clean Drive backups
            drive_retention = self.config["drive_retention_days"]
            folder_structure = self.drive_service.setup_backup_structure()
            if folder_structure:
                self.drive_service.cleanup_old_backups(
                    folder_structure['main'],
                    drive_retention
                )
                print(f"🗑️ Cleaned up Drive backups older than {drive_retention} days")
                
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    
    def run_backup(self) -> bool:
        """Execute complete backup workflow."""
        print(f"🚀 Starting backup at {datetime.now()}")
        
        try:
            # Create backup based on scope
            backup_scope = self.config["backup_scope"]
            
            if backup_scope == "database":
                backup_path = self.create_database_backup()
            elif backup_scope == "files":
                backup_path = self.create_files_backup()
            else:  # full
                backup_path = self.create_comprehensive_backup()
            
            if not backup_path or not backup_path.exists():
                raise Exception("Backup creation failed")
            
            # Upload to Drive
            file_id = self.upload_to_drive(backup_path)
            if not file_id:
                raise Exception("Drive upload failed")
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            print(f"✅ Backup completed successfully!")
            print(f"📁 Local: {backup_path}")
            print(f"☁️ Drive: {file_id}")
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False


if __name__ == "__main__":
    # Run backup when executed directly
    backup_system = BackupToDrive()
    success = backup_system.run_backup()
    sys.exit(0 if success else 1)
