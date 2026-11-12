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
  --worker-class app.gunicorn_worker.ObservableThreadWorker \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --access-logfile "-" \
  --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" "%({x-forwarded-for}i)s"' \
  --error-logfile "-" \
  --worker-tmp-dir /dev/shm
