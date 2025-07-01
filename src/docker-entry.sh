#!/bin/sh
set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput

# exec "$@"
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program gunicorn app.wsgi \
  --bind 0.0.0.0:8081 \
  --timeout 120 \
  --workers 2 \
  --threads 4 \
  --worker-class gthread \
  --access-logfile "-" \
  --error-logfile "-" \
  --worker-tmp-dir /dev/shm
