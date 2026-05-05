#!/bin/sh
set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput

# exec "$@"
gunicorn app.wsgi \
  --bind 0.0.0.0:8081 \
  --timeout 120 \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile "-" \
  --error-logfile "-" \
  --worker-tmp-dir /dev/shm
