#!/bin/sh


echo "Create Database, if not exists"
createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME
# echo "SELECT 'CREATE DATABASE mermaid' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec" | psql -h $DB_HOST -p $DB_PORT -U $DB_USER

# This is set AFTER the createdb command in case it fails with "database ___ already exists"
set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput

# python manage.py collectstatic --noinput

# exec "$@"
gunicorn app.wsgi --bind 0.0.0.0:8000 --timeout 300 --workers 3
