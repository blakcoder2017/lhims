# 🔄 LHIMS Migration Troubleshooting Quick Reference

Quick reference guide for fixing common migration errors when deploying on a new computer.

---

## 🚨 Quick Fixes

### Error: "Could not connect to server"

```bash
# 1. Check .env file
cat .env | grep SQLALCHEMY_DATABASE_URL

# 2. Test database connection
sudo -u postgres psql -d lhims -U lhims_user

# 3. Check PostgreSQL is running
sudo systemctl status postgresql
```

### Error: "ModuleNotFoundError: No module named 'app'"

```bash
# 1. Ensure you're in project directory
cd /opt/lhims  # or your project path

# 2. Activate virtual environment
source venv/bin/activate

# 3. Verify Python path
which python  # Should show venv/bin/python

# 4. Test import
python -c "from app.db.database import Base; print('OK')"
```

### Error: "Multiple heads detected"

```bash
# Merge heads
alembic merge -m "merge_heads" heads
alembic upgrade head
```

### Error: "relation already exists"

```bash
# Option 1: Drop and recreate (WARNING: Data loss!)
sudo -u postgres psql -d lhims -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head

# Option 2: Stamp as complete (if tables match)
alembic stamp head
```

---

## ✅ Pre-Migration Checklist

Before running migrations, verify:

- [ ] In project root directory (`/opt/lhims` or your path)
- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] `.env` file exists and has `SQLALCHEMY_DATABASE_URL`
- [ ] PostgreSQL is running
- [ ] Database `lhims` exists
- [ ] User `lhims_user` has permissions
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `migrations/` directory exists with `versions/` subdirectory

---

## 🔍 Diagnostic Commands

```bash
# Check current directory
pwd

# Check virtual environment
which python
which alembic

# Check environment variables
python -c "from app.core.config import settings; print(settings.SQLALCHEMY_DATABASE_URL)"

# Check database connection
python -c "from app.db.database import engine; engine.connect(); print('OK')"

# Check migration status
alembic current
alembic heads
alembic history

# Check migration files
ls -la migrations/versions/ | wc -l
```

---

## 🔄 Complete Reset (Last Resort)

If nothing works, perform complete reset:

```bash
# 1. Backup (if data exists)
sudo -u postgres pg_dump lhims > backup.sql

# 2. Drop and recreate database
sudo -u postgres psql << EOF
DROP DATABASE lhims;
CREATE DATABASE lhims;
GRANT ALL PRIVILEGES ON DATABASE lhims TO lhims_user;
\c lhims
GRANT ALL ON SCHEMA public TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO lhims_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO lhims_user;
\q
EOF

# 3. Run migrations
cd /opt/lhims
source venv/bin/activate
alembic upgrade head
```

---

## 📞 Common Error Messages

| Error | Solution |
|-------|----------|
| `could not connect to server` | Check `.env`, PostgreSQL running, database exists |
| `ModuleNotFoundError` | Activate venv, check PYTHONPATH, reinstall deps |
| `Multiple heads detected` | Run `alembic merge heads` then `alembic upgrade head` |
| `relation already exists` | Drop schema or use `alembic stamp head` |
| `permission denied` | Grant permissions to `lhims_user` |
| `FileNotFoundError: migrations` | Check current directory, verify `migrations/` exists |

---

For detailed solutions, see the **Migration Troubleshooting** section in `DETAILED_DEPLOYMENT_GUIDE.md`.

