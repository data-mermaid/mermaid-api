#!/bin/sh
set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput

# exec "$@"
exec opentelemetry-instrument gunicorn app.wsgi \
  --bind 0.0.0.0:8081 \
  --timeout 120 \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --access-logfile "-" \
  --error-logfile "-" \
  --worker-tmp-dir /dev/shm
