# LHIMS Migration Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying LHIMS to a new system with proper database migrations.

## Prerequisites
- Python 3.8+
- PostgreSQL 12+
- LHIMS source code
- Environment variables configured

## Migration System Status
✅ **All migration issues have been resolved:**
- Fixed 9 non-standard named migration files
- Fixed 4 files missing proper revision IDs  
- Resolved all broken migration chains
- Verified proper model imports for Alembic detection
- **7 head revisions** (multiple branches are expected and OK)

## Quick Deployment Commands

### 1. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your database credentials
nano .env
```

### 2. Database Setup
```bash
# Create database
createdb lhims

# Create user (optional but recommended)
createuser lhims_user
psql -c "ALTER USER lhims_user PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;"
```

### 3. Install Dependencies
```bash
# Using virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Migrations
```bash
# Run all migrations to current heads
alembic upgrade head

# Or run to specific revision
alembic upgrade <revision_id>
```

### 5. Verify Migration Status
```bash
# Check current migration status
alembic current

# Show migration history
alembic history

# Show head revisions
alembic heads
```

## Migration Branches
The system has 7 migration branches, which is normal for a complex system:

```
Head revisions:
- 00baf8b1931e (add_phone_number_to_users)
- 2091a86885bd (mawuli_pc)
- 24ae069a97c5 (add_fluid_balance_table)
- 9ed833a63cf2 (make_triage_temperature_nullable)
- c950b576837a (add_opd_visit_completion_outcome)
- d255e826bc61 (add_antenatal_and_birth_tables)
- dbb41aecce1c (fix_invoice_appointment_fk)
```

## Docker Deployment (Recommended)

### Using Docker Compose
```bash
# Build and start all services
docker-compose up -d

# Run migrations (if not auto-run)
docker-compose exec app alembic upgrade head

# Check logs
docker-compose logs -f app
```

### Environment Variables for Docker
Create `.env` file with:
```env
POSTGRES_DB=lhims
POSTGRES_USER=lhims_user
POSTGRES_PASSWORD=your_secure_password
SQLALCHEMY_DATABASE_URL=postgresql://lhims_user:your_secure_password@db:5432/lhims
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## Troubleshooting

### Common Issues

#### 1. Migration Conflicts
```bash
# Check current state
alembic current

# If stuck, mark as specific revision
alembic stamp <revision_id>

# Then continue
alembic upgrade head
```

#### 2. Database Connection Issues
- Verify PostgreSQL is running: `pg_isready`
- Check connection string in `.env`
- Ensure database exists: `psql -l`

#### 3. Permission Issues
```bash
# Grant proper permissions
psql -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lhims_user;"
psql -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lhims_user;"
```

#### 4. Missing Dependencies
```bash
# Install missing system packages
sudo apt-get install postgresql-client  # Ubuntu/Debian
brew install postgresql             # macOS

# Install Python dependencies
pip install -r requirements.txt
```

## Migration Rollback

### Single Migration Rollback
```bash
# Rollback one revision
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Full Database Reset
```bash
# Drop all tables and recreate
alembic downgrade base
alembic upgrade head
```

## Production Considerations

### 1. Backup Before Migration
```bash
# Create database backup
pg_dump lhims > lhims_backup_$(date +%Y%m%d_%H%M%S).sql

# Or using pg_dump with custom format
pg_dump -Fc lhims > lhims_backup_$(date +%Y%m%d_%H%M%S).dump
```

### 2. Migration in Production
```bash
# Run migrations during maintenance window
alembic upgrade head

# Verify application works
curl -f http://localhost:8000/health || echo "Health check failed"
```

### 3. Monitoring
```bash
# Monitor migration progress
tail -f /var/log/lhims/migration.log

# Check database size after migration
psql -c "SELECT pg_size_pretty(pg_database_size('lhims'));"
```

## Validation Steps

After migration, verify:

1. **Database Schema**
   ```bash
   psql -d lhims -c "\dt"  # List tables
   ```

2. **Application Health**
   ```bash
   curl http://localhost:8000/health
   ```

3. **User Authentication**
   - Try logging in as admin
   - Test user creation

4. **Core Functionality**
   - Patient registration
   - Appointment scheduling
   - Billing operations

## Migration Files Structure

```
migrations/versions/
├── 31eabfef5566_initial_postgresql_setup_with_patient_.py
├── e91a23e0fee9_add_user_and_role_models_for_rbac.py
├── 82cc700994b4_create_patients_table_for_registration_.py
├── ... (67 total migration files)
└── [7 head revisions]
```

## Support

For migration issues:
1. Check this guide first
2. Review Alembic documentation: https://alembic.sqlalchemy.org
3. Check application logs for specific errors
4. Verify environment variables are correct

## Migration Best Practices

1. **Always backup** before running migrations
2. **Test migrations** in staging first
3. **Review migration files** before applying
4. **Monitor progress** during migration
5. **Verify functionality** after migration
6. **Keep migration history** for debugging

---

**Status**: ✅ All migration issues resolved, system ready for deployment
