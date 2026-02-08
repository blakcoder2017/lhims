# LHIMS Backup System

A comprehensive backup solution for the LHIMS project with automated local backups and Google Drive integration.

## 🚀 Quick Start

### Run Manual Backup
```bash
# Activate virtual environment
source venv/bin/activate

# Run backup immediately
python manage_backups.py backup
```

### Check System Status
```bash
python manage_backups.py status
```

### Install Automatic Backups
```bash
python manage_backups.py install-cron
```

## 📋 Features

### ✅ What's Included
- **Database Backups**: PostgreSQL database exports to CSV
- **File Backups**: Application code, configurations, and uploads
- **Google Drive Integration**: Automatic upload to organized folder structure
- **Automated Scheduling**: Daily backups via cron job
- **Retention Management**: Automatic cleanup of old backups
- **Comprehensive Logging**: Detailed backup operation logs

### 🗂️ Google Drive Organization
```
LHIMS Backups/
├── 2026/
│   ├── 02-February/
│   │   ├── lhims_comprehensive_backup_20260206_020000.zip
│   │   └── lhims_comprehensive_backup_20260206_120000.zip
│   └── 03-March/
└── 2025/
    └── 12-December/
```

## ⚙️ Configuration

### Backup Configuration File: `.backup_config`
```json
{
  "backup_scope": "full",
  "compress_backups": true,
  "local_retention_days": 30,
  "drive_retention_days": 90,
  "backup_schedule": {
    "hour": 2,
    "minute": 0
  }
}
```

### Configuration Options
- **backup_scope**: `"database"`, `"files"`, or `"full"`
- **compress_backups**: `true`/`false` - Compress backup files
- **local_retention_days**: Days to keep local backups
- **drive_retention_days**: Days to keep Google Drive backups
- **backup_schedule**: When to run automatic backups

## 🛠️ Management Commands

### Backup Operations
```bash
# Run manual backup
python manage_backups.py backup

# Show current configuration
python manage_backups.py config

# Check system status
python manage_backups.py status
```

### Cron Job Management
```bash
# Install automatic backup cron job
python manage_backups.py install-cron

# Remove cron job
python manage_backups.py remove-cron
```

## 📁 File Structure

```
lhims/
├── scripts/
│   ├── backup_to_drive.py           # Main backup script
│   ├── google_drive_service.py      # Google Drive API wrapper
│   └── backup_config.py            # Configuration management
├── manage_backups.py               # CLI management tool
├── .backup_config                  # Backup configuration
├── credentials.json                # Google Drive API credentials
├── token.json                     # OAuth2 authentication token
├── backup_logs/                   # Backup operation logs
└── backups/                       # Local backup storage
```

## 🔐 Security

### Google Drive Authentication
- Uses OAuth2 with secure token storage
- No passwords stored in application
- Scoped access (Drive files only)
- Revocable anytime from Google Account settings

### File Security
- Credentials excluded from version control (.gitignore)
- Optional backup encryption available
- Secure HTTPS transfers

## 📊 Monitoring

### Storage Information
```bash
python manage_backups.py status
```
Shows:
- Cron job status
- Google Drive authentication
- Drive storage usage
- Local backup count
- Configuration validation

### Backup Logs
Backup operations are logged with timestamps and status:
- Successful uploads
- Error messages
- File sizes and locations
- Cleanup operations

## 🔄 Backup Process

### Automatic Daily Backup
1. **Database Export**: Key tables exported to CSV
2. **File Collection**: Application files and uploads
3. **Compression**: Combined into single archive
4. **Google Drive Upload**: Organized by date
5. **Cleanup**: Old backups removed
6. **Logging**: Operation details recorded

### Manual Backup
Same process as automatic, triggered on-demand:
```bash
python manage_backups.py backup
```

## 🚨 Troubleshooting

### Common Issues

**Google Authentication Failed**
```bash
# Remove old token and re-authenticate
rm token.json
python manage_backups.py status
```

**Cron Job Not Working**
```bash
# Check cron job status
python manage_backups.py status

# Reinstall cron job
python manage_backups.py remove-cron
python manage_backups.py install-cron
```

**Permission Denied**
```bash
# Fix file permissions
chmod 600 credentials.json
chmod +x manage_backups.py
```

### Getting Help

1. Check system status: `python manage_backups.py status`
2. Review backup logs in `backup_logs/`
3. Verify Google Drive access
4. Check configuration validity

## 📈 Performance

### Backup Sizes
- **Database Only**: ~100-500 KB
- **Files Only**: ~1-5 MB
- **Full Backup**: ~1-10 MB (compressed)

### Transfer Speeds
- **Local Backup**: < 1 minute
- **Drive Upload**: 1-5 minutes (depending on size)
- **Cleanup**: < 30 seconds

## 🔄 Maintenance

### Monthly Tasks
- Review Google Drive storage usage
- Check backup logs for errors
- Verify retention policies
- Update configuration if needed

### Quarterly Tasks
- Test backup restoration process
- Review and update backup scope
- Check Google API quotas
- Update dependencies

## 📞 Support

For issues or questions:
1. Check this documentation
2. Run `python manage_backups.py status`
3. Review backup logs
4. Check Google Cloud Console settings

---

**Backup System Version**: 1.0  
**Last Updated**: February 2026  
**Compatible**: LHIMS v2.0+
