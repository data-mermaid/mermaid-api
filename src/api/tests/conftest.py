from unittest.mock import patch

import pytest
from django.conf import settings
from django.db import connection

from api.models import revisions
from api.models.summary_sample_events import ProjectSummarySampleEventView
from api.models.view_models import model_view_migrations
from .fixtures import *  # noqa: F403


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    settings.TESTING = True
    # https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-DATABASE-TEST
    db_name = settings.DATABASES["default"]["NAME"]
    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            cursor.execute(f"ALTER DATABASE {db_name} SET jit TO false;")
            cursor.execute(model_view_migrations.forward_sql())
            cursor.execute(revisions.forward_sql)
            cursor.execute(ProjectSummarySampleEventView.forward_sql)


@pytest.fixture(autouse=True)
def db_setup(db):
    pass


@pytest.fixture(autouse=True)
def _disable_s3_cache(request):
    """Disable S3 cache by default; use `s3_cache_hit` fixture to test cache-hit paths."""
    if "s3_cache_hit" not in request.fixturenames:
        with patch("api.utils.cached.exists", return_value=False):
            yield
    else:
        yield


@pytest.fixture
def s3_cache_hit():
    """Opt-in fixture to mock S3 cache as available, for testing cache-hit paths."""
    with patch("api.utils.cached.exists", return_value=True):
        yield
