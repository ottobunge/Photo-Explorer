#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h postgres -U postgres -q; do
    sleep 1
done
echo "PostgreSQL is ready."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Execute the main command
exec "$@"
