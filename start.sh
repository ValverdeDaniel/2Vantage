#!/bin/bash
set -e

# Postgres readiness is handled by the Compose healthcheck (local) and by Cloud SQL (production).
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Starting production server..."
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    exec gunicorn backend.wsgi:application --bind :${PORT:-8000} --workers 2 --threads 4 \
        --timeout 60 --access-logfile -
else
    echo "Starting development server..."
    python manage.py migrate
    exec python manage.py runserver 0.0.0.0:8000
fi
