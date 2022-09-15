#!/bin/sh
set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput

# exec "$@"
gunicorn app.wsgi --bind 0.0.0.0:80 --timeout 300 --workers 3
