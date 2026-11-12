#!/bin/bash
set -e

# Postgres readiness is handled by the Compose healthcheck (local) and by Cloud SQL (production).
if [ "$ENVIRONMENT" = "production" ]; then
    # The production image (plan.md §3.4, §11.2): static files were collected when it was built, and migrations run
    # as their own job before traffic moves (`migrate`), never at a web instance's start.
    case "${1:-web}" in
        web)
            echo "Starting production server..."
            # Cloud Run's front end is the only way in, so its X-Forwarded-Proto is trusted from any address.
            exec gunicorn backend.wsgi:application --bind :${PORT:-8000} --workers 2 --threads 4 \
                --timeout 60 --access-logfile - --logger-class backend.gunicorn_log.TokenSafeLogger \
                --forwarded-allow-ips '*'
            ;;
        worker)
            # The job worker (§3.4, O.3.3). A Cloud Run service must answer on $PORT, so an empty folder is served
            # there while the worker runs; the service is internal and takes no traffic (deploy/README.md).
            mkdir -p /tmp/worker-port
            python -m http.server "${PORT:-8000}" --bind 0.0.0.0 --directory /tmp/worker-port >/dev/null 2>&1 &
            exec python manage.py run_worker
            ;;
        migrate)
            # The migrations job, before traffic moves: the release gate's `check --deploy`, then migrate (§11.3).
            python manage.py check --deploy --fail-level WARNING
            exec python manage.py migrate --noinput
            ;;
        *)
            exec "$@"
            ;;
    esac
else
    echo "Starting development server..."
    python manage.py migrate
    exec python manage.py runserver 0.0.0.0:8000
fi
