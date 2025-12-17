# 🔧 Fix: "Can't locate revision identified by '1b61f463c8c4'"

## Quick Fix

This error means the database references a migration that doesn't exist in your files.

### Option 1: Reset Database (Recommended for Fresh Install)

```bash
# Drop and recreate database
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS lhims;
CREATE DATABASE lhims;
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;
\q
EOF

# Run migrations
cd /opt/lhims
source venv/bin/activate
alembic upgrade head
```

### Option 2: Copy Missing Migration Files

```bash
# Check what revision database thinks it's at
alembic current

# Check if migration file exists
find migrations/versions/ -name "*1b61f463c8c4*"

# If missing, copy from working computer:
# scp /path/to/source/migrations/versions/*1b61f463c8c4*.py user@new-computer:/opt/lhims/migrations/versions/
```

### Option 3: Clear Migration State

```bash
# Connect to database
sudo -u postgres psql -d lhims

# Clear version tracking
DELETE FROM alembic_version;
\q

# Stamp with head (if tables exist) or run migrations
alembic stamp head
# OR
alembic upgrade head
```

## Verify Migration Files

```bash
# Count migration files (should be 50+)
ls migrations/versions/*.py | wc -l

# List all migration files
ls migrations/versions/

# Check migration chain
alembic history
```

