# 🔧 Fix: "relation 'triage_vitals' already exists"

## Problem

Migration fails with:
```
psycopg2.errors.DuplicateTable: relation "triage_vitals" already exists
```

**Cause:** Multiple migrations are trying to create the same table `triage_vitals`.

## Quick Fix (Option 1): Modify Migration File

The migration `b6cd6bc9ce08_add_encounters.py` is trying to create `triage_vitals` but it already exists. 

**Fix the migration file:**

```bash
# Edit the migration file
nano migrations/versions/b6cd6bc9ce08_add_encounters.py
```

Change the `upgrade()` function to check if table exists first:

```python
def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'triage_vitals' not in existing_tables:
        op.create_table('triage_vitals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('recorded_by_id', sa.Integer(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('blood_pressure', sa.String(length=50), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_triage_vitals_id'), 'triage_vitals', ['id'], unique=False)
```

Then re-run migrations:
```bash
alembic upgrade head
```

## Quick Fix (Option 2): Drop Table and Re-run

If you don't want to modify the migration file:

```bash
# 1. Drop the existing triage_vitals table
sudo -u postgres psql -d lhims << EOF
DROP TABLE IF EXISTS triage_vitals CASCADE;
\q
EOF

# 2. Continue migrations
alembic upgrade head
```

## Quick Fix (Option 3): Remove Table Creation from Migration

Since `triage_vitals` was already created in an earlier migration, remove it from `b6cd6bc9ce08`:

```bash
# Edit migration file
nano migrations/versions/b6cd6bc9ce08_add_encounters.py
```

Change `upgrade()` to:
```python
def upgrade() -> None:
    """Upgrade schema."""
    # triage_vitals was already created in migration 72e2dc0c34b9
    # No need to create it again
    pass
```

Then continue:
```bash
alembic upgrade head
```

## Recommended Solution

**Option 1** (check if table exists) is safest as it handles both cases. The migration file has been updated in the codebase.

After fixing, run:
```bash
alembic upgrade head
```

## Verify Fix

After migrations complete:

```bash
# Check tables exist
sudo -u postgres psql -d lhims -c "\dt" | grep triage_vitals

# Check migration status
alembic current

# Verify all tables
sudo -u postgres psql -d lhims -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

