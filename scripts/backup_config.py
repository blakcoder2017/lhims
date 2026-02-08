"""
Backup Configuration Management

This module handles backup configuration, validation, and management.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class BackupConfig:
    """Backup configuration manager."""
    
    DEFAULT_CONFIG = {
        "backup_scope": "full",
        "compress_backups": True,
        "encrypt_backups": False,
        "local_retention_days": 30,
        "drive_retention_days": 90,
        "backup_schedule": {
            "hour": 2,
            "minute": 0
        },
        "notifications": {
            "email_enabled": False,
            "email_address": "",
            "success_notifications": True,
            "failure_notifications": True
        },
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
            "test_*.db",
            "*.log",
            "backups/**/*",
            "node_modules/**/*"
        ],
        "database_backup": {
            "include_tables": [
                "patients", "invoices", "payments", "encounters",
                "appointments", "users", "hospital_settings"
            ],
            "dump_format": "csv"
        },
        "drive_settings": {
            "folder_name": "LHIMS Backups",
            "chunk_size": 1024 * 1024,  # 1MB chunks
            "max_retries": 3
        }
    }
    
    def __init__(self, config_path: str = ".backup_config"):
        """Initialize configuration manager."""
        self.config_path = Path(config_path)
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_configs(self.DEFAULT_CONFIG, config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user config with defaults."""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        return self.save_config()
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        issues = []
        warnings = []
        
        # Check retention periods
        local_days = self.get("local_retention_days", 30)
        drive_days = self.get("drive_retention_days", 90)
        
        if local_days < 1:
            issues.append("local_retention_days must be at least 1")
        if drive_days < 1:
            issues.append("drive_retention_days must be at least 1")
        
        if drive_days < local_days:
            warnings.append("drive_retention_days is less than local_retention_days")
        
        # Check backup scope
        scope = self.get("backup_scope", "full")
        valid_scopes = ["database", "files", "full"]
        if scope not in valid_scopes:
            issues.append(f"backup_scope must be one of: {valid_scopes}")
        
        # Check schedule
        hour = self.get("backup_schedule.hour", 2)
        minute = self.get("backup_schedule.minute", 0)
        if not (0 <= hour <= 23):
            issues.append("backup_schedule.hour must be between 0 and 23")
        if not (0 <= minute <= 59):
            issues.append("backup_schedule.minute must be between 0 and 59")
        
        # Check notification settings
        email_enabled = self.get("notifications.email_enabled", False)
        email_address = self.get("notifications.email_address", "")
        if email_enabled and not email_address:
            issues.append("email_address is required when email_enabled is true")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    def create_default_config(self) -> bool:
        """Create default configuration file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.DEFAULT_CONFIG, f, indent=2)
            return True
        except Exception as e:
            print(f"Error creating default config: {e}")
            return False
    
    def show_config(self) -> str:
        """Display current configuration."""
        return json.dumps(self.config, indent=2)


def create_default_config_file(config_path: str = ".backup_config") -> bool:
    """Create a default configuration file."""
    config_manager = BackupConfig(config_path)
    return config_manager.create_default_config()


if __name__ == "__main__":
    # Test configuration management
    config = BackupConfig()
    
    print("Current configuration:")
    print(config.show_config())
    
    # Validate configuration
    validation = config.validate_config()
    print(f"\nConfiguration valid: {validation['valid']}")
    if validation['issues']:
        print("Issues:", validation['issues'])
    if validation['warnings']:
        print("Warnings:", validation['warnings'])
