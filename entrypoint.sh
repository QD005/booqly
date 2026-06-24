#!/bin/sh
# ── entrypoint.sh ────────────────────────────────────────────────────────────
# Wait for PostgreSQL to be ready before starting Django

echo "⏳ Waiting for PostgreSQL..."

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done

echo "✅ PostgreSQL is ready!"

# Run migrations automatically
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Execute the command passed to the container
exec "$@"
