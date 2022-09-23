#!/bin/sh
set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput

# exec "$@"
gunicorn app.wsgi \
  --bind 0.0.0.0:8081 \
  --timeout 300 \
  --workers 1 \
  --access-logfile "-" \
  --error-logfile "-" 
