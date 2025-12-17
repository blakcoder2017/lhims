# 🔧 Fix: Only alembic_version Table Created

## Problem

After running `alembic upgrade head`, only the `alembic_version` table exists, but no application tables were created.

**Current state:**
- `alembic current` shows: `a6285dd03420 (head)`
- Only `alembic_version` table exists
- No application tables (users, patients, etc.)

**Root Cause:** The database was stamped with a revision (`a6285dd03420`) that doesn't exist in your migration files. This prevents migrations from running.

## Diagnosis

This usually means:
1. Migrations were "stamped" instead of actually run
2. Migration files exist but don't contain table creation code
3. Models aren't being imported properly in migrations

## Solution 1: Check Migration Files Content

```bash
# 1. Check if migration files have actual table creation code
grep -l "create_table\|op.create_table" migrations/versions/*.py | head -5

# 2. Check the head migration file
cat migrations/versions/*a6285dd03420*.py

# 3. Check for initial/base migration
ls -la migrations/versions/ | head -10
```

## Solution 2: Reset and Re-run Migrations (RECOMMENDED)

**This is the fix for revision `a6285dd03420` not found:**

```bash
# 1. Clear the alembic_version table (removes the bad revision)
sudo -u postgres psql -d lhims << EOF
DELETE FROM alembic_version;
\q
EOF

# 2. Check what the actual head revision is
alembic heads
# Should show the actual head revision from your migration files

# 3. Check migration history
alembic history | head -5
alembic history | tail -5

# 4. Run migrations from the beginning (now they will actually execute)
cd /opt/lhims  # or your project path
source venv/bin/activate
alembic upgrade head

# 5. Verify tables were created
sudo -u postgres psql -d lhims -c "\dt"
# Should now show many tables!
```

## Solution 3: Verify Models Are Imported

```bash
# Test if models can be imported
cd /opt/lhims  # or your project path
source venv/bin/activate

python << EOF
from app.models import *
from app.db.database import Base
print("Models imported successfully")
print(f"Base metadata: {Base.metadata}")
print(f"Tables: {list(Base.metadata.tables.keys())}")
EOF
```

If this fails, models aren't being imported correctly.

## Solution 4: Check Migration Environment

```bash
# Check migrations/env.py imports models correctly
cat migrations/env.py | grep -A 5 "from app.models"

# Should see:
# from app.models import *
# from app.db.database import Base
# target_metadata = Base.metadata
```

## Solution 5: Find Actual Head and Stamp (Alternative)

If you want to keep the database but fix the revision:

```bash
# 1. Find the actual head revision from your migration files
alembic heads
# Note the revision ID (e.g., '446dc4c3cf37')

# 2. Clear the bad revision
sudo -u postgres psql -d lhims -c "DELETE FROM alembic_version;"

# 3. Stamp with the actual head (if tables already exist)
alembic stamp head

# OR run migrations if tables don't exist
alembic upgrade head
```

## Solution 6: Force Recreate All Tables

If migrations aren't working, you can create tables directly:

```bash
# WARNING: This will drop all existing data!

# 1. Drop and recreate database
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

# 2. Clear alembic version
# (Database is fresh, so no version table exists yet)

# 3. Run migrations
cd /opt/lhims
source venv/bin/activate
alembic upgrade head

# 4. Verify tables created
sudo -u postgres psql -d lhims -c "\dt"
```

## Solution 6: Check Migration Chain

```bash
# Check if migration chain is complete
alembic history --verbose

# Check what the head migration should create
alembic show head

# Check current state
alembic current
```

## Solution 7: Manual Table Creation (Last Resort)

If migrations still don't work:

```bash
# Create tables directly from models
python << EOF
from app.db.database import engine, Base
from app.models import *
Base.metadata.create_all(bind=engine)
print("Tables created directly from models")
EOF

# Then stamp database
alembic stamp head
```

## Verification

After fixing, verify:

```bash
# 1. Check tables exist
sudo -u postgres psql -d lhims -c "\dt" | wc -l
# Should show 30+ tables

# 2. Check specific tables
sudo -u postgres psql -d lhims -c "\d users"
sudo -u postgres psql -d lhims -c "\d patients"

# 3. Test application
python -c "from app.db.database import SessionLocal; db = SessionLocal(); db.close(); print('OK')"
```

## Most Likely Cause

The migration files might be empty or the models aren't being imported in `migrations/env.py`. Check:

1. `migrations/env.py` has: `from app.models import *`
2. Migration files have actual `op.create_table()` calls
3. Models are properly defined in `app/models/`

