"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os

import django
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

# Django runs its system checks for `manage.py` commands only, so nothing under
# gunicorn would notice a failing one - `api.checks.check_api_key_environment`
# among them, which is what stops the API from minting keys under an ENV label
# that will not verify later. Without this, a bad ENV boots a healthy container
# and then 500s on every API-key request. Running the checks here turns that into
# a worker that refuses to start, so the deployment fails its health check
# instead. `call_command("check")` raises SystemCheckError on any Error-level
# result and queries no database.
django.setup()
call_command("check")

application = get_wsgi_application()
