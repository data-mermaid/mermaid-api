echo "Create Database, if not exists"
# createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME
echo "SELECT 'CREATE DATABASE mermaid' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mermaid')\gexec" | psql -h $DB_HOST -p $DB_PORT -U $DB_USER

# set -e

echo "Starting Django Migrations"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "Run Gunicorn Server"
gunicorn app.wsgi --bind 0.0.0.0:8080