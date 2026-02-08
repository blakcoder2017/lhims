#!/usr/bin/env python3
"""
LHIMS Backup Management Script

This script provides easy command-line interface for managing backups.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from scripts.backup_to_drive import BackupToDrive
from app.services.backup_scheduler import install_cron_job, remove_cron_job, get_cron_job_status
from scripts.backup_config import BackupConfig


def run_manual_backup():
    """Run a manual backup immediately."""
    print("🚀 Starting manual backup...")
    backup_system = BackupToDrive()
    success = backup_system.run_backup()
    
    if success:
        print("✅ Manual backup completed successfully!")
    else:
        print("❌ Manual backup failed!")
        sys.exit(1)


def setup_cron_job():
    """Install cron job for automatic backups."""
    print("📅 Installing cron job for automatic backups...")
    
    # Load configuration
    config = BackupConfig()
    hour = config.get("backup_schedule.hour", 2)
    minute = config.get("backup_schedule.minute", 0)
    
    success, message = install_cron_job(hour, minute, "LHIMS Google Drive Backup")
    
    if success:
        print(f"✅ {message}")
        print(f"⏰ Backups will run daily at {hour:02d}:{minute:02d}")
    else:
        print(f"❌ Failed to install cron job: {message}")
        sys.exit(1)


def remove_cron():
    """Remove the backup cron job."""
    print("🗑️ Removing backup cron job...")
    
    success, message = remove_cron_job()
    
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ Failed to remove cron job: {message}")
        sys.exit(1)


def check_status():
    """Check backup system status."""
    print("📊 Checking backup system status...")
    
    # Check cron job status
    cron_status = get_cron_job_status()
    print(f"\n📅 Cron Job Status:")
    if cron_status["installed"]:
        print("✅ Cron job is installed")
        if "cron_entry" in cron_status:
            print(f"📝 Entry: {cron_status['cron_entry']}")
    else:
        print("❌ No cron job found")
        print(f"📝 Message: {cron_status.get('message', 'Unknown')}")
    
    # Check Google Drive authentication
    try:
        from scripts.google_drive_service import GoogleDriveService
        drive_service = GoogleDriveService()
        
        if drive_service.service:
            print("✅ Google Drive authentication successful")
            
            # Get storage info
            storage_info = drive_service.get_storage_info()
            if storage_info:
                usage_mb = storage_info.get('usage', 0) / (1024 * 1024)
                limit_mb = storage_info.get('limit', 0) / (1024 * 1024)
                usage_percent = (usage_mb / limit_mb * 100) if limit_mb > 0 else 0
                print(f"💾 Drive Storage: {usage_mb:.1f} MB / {limit_mb:.1f} MB ({usage_percent:.1f}%)")
        else:
            print("❌ Google Drive authentication failed")
    except Exception as e:
        print(f"❌ Error checking Drive status: {e}")
    
    # Check configuration
    config = BackupConfig()
    validation = config.validate_config()
    print(f"\n⚙️ Configuration Status:")
    if validation["valid"]:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has issues:")
        for issue in validation["issues"]:
            print(f"   • {issue}")
    
    # Check backup directory
    backup_dir = Path("backups")
    if backup_dir.exists():
        backup_count = len([item for item in backup_dir.iterdir() if item.is_file() or item.is_dir()])
        print(f"📁 Local backups: {backup_count} items")
    else:
        print("📁 Local backup directory not found")


def show_config():
    """Display current backup configuration."""
    print("⚙️ Current Backup Configuration:")
    
    config = BackupConfig()
    print(config.show_config())


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="LHIMS Backup Management")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Manual backup
    subparsers.add_parser('backup', help='Run manual backup')
    
    # Cron job management
    subparsers.add_parser('install-cron', help='Install cron job for automatic backups')
    subparsers.add_parser('remove-cron', help='Remove backup cron job')
    
    # Status and configuration
    subparsers.add_parser('status', help='Check backup system status')
    subparsers.add_parser('config', help='Show backup configuration')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        if args.command == 'backup':
            run_manual_backup()
        elif args.command == 'install-cron':
            setup_cron_job()
        elif args.command == 'remove-cron':
            remove_cron()
        elif args.command == 'status':
            check_status()
        elif args.command == 'config':
            show_config()
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
