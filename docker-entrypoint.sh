#!/bin/bash
set -e

echo "=========================================="
echo "LHIMS Docker Entrypoint"
echo "=========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD="${POSTGRES_PASSWORD}" psql -h db -U "${POSTGRES_USER:-lhims_user}" -d "${POSTGRES_DB:-lhims}" -c '\q' 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Seed initial data if needed (optional)
# Uncomment if you want to run seed scripts automatically
# if [ ! -f /app/.seed_complete ]; then
#     echo "Seeding initial data..."
#     python scripts/seed_permissions.py || true
#     python scripts/seed_admin.py || true
#     touch /app/.seed_complete
# fi

# Execute the main command
echo "Starting application..."
exec "$@"

