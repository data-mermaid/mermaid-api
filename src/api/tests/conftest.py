from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection

from api.models import revisions
from api.models.classification import get_s3_image_storage
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
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            cursor.execute(f"ALTER DATABASE {db_name} SET jit TO false;")
            # ALTER DATABASE only applies to new sessions; this connection is
            # already open and is reused for the whole test session.
            cursor.execute("SET jit TO off;")
            cursor.execute(model_view_migrations.forward_sql())
            cursor.execute(revisions.forward_sql)
            cursor.execute(ProjectSummarySampleEventView.forward_sql)


@pytest.fixture(autouse=True)
def db_setup(db):
    pass


# --- Deferred attribute materialized-view refreshes ---------------------------
# Saving a fish/invert attribute (or Region) fires a signal that, under pytest,
# runs REFRESH MATERIALIZED VIEW immediately. Fixture graphs create many such
# rows (project1 alone pulls in 4 fish families), so one test could refresh
# the same view many times before its body even starts.
#
# During fixture setup we only record which views are dirty, then refresh each
# one once: before any fixture outside the pure attribute-creating modules runs
# (so it sees current views), and before the test body. Inside the test body
# and teardown, refreshes run immediately as before.

# Matched by suffix: the package prefix depends on pytest's rootdir/import mode.
_ATTRIBUTE_FIXTURE_MODULES = (
    "tests.fixtures.benthic_attributes",
    "tests.fixtures.choices",
    "tests.fixtures.fish_attributes",
    "tests.fixtures.macroinvertebrate",
)


class _ViewRefresher:
    def __init__(self):
        self.deferring = False
        self.dirty = set()

    def schedule(self, view_name):
        if self.deferring:
            self.dirty.add(view_name)
        else:
            call_command("refresh_view", view_name)

    def flush(self):
        while self.dirty:
            call_command("refresh_view", self.dirty.pop())

    def reset(self):
        self.deferring = False
        self.dirty.clear()


_view_refresher = _ViewRefresher()


@pytest.fixture(scope="session", autouse=True)
def _defer_attribute_view_refreshes():
    with patch("api.signals.attributes._schedule_refresh", _view_refresher.schedule):
        yield


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    _view_refresher.reset()
    _view_refresher.deferring = True
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef, request):
    module = getattr(fixturedef.func, "__module__", "") or ""
    if _view_refresher.dirty and not module.endswith(_ATTRIBUTE_FIXTURE_MODULES):
        _view_refresher.flush()
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    _view_refresher.flush()
    _view_refresher.deferring = False
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    _view_refresher.reset()
    return (yield)


@pytest.fixture(autouse=True)
def _disable_s3_cache(request):
    """Disable S3 cache by default; use `s3_cache_hit` fixture to test cache-hit paths."""
    if "s3_cache_hit" not in request.fixturenames:
        with patch("api.utils.cached.exists", return_value=False):
            yield
    else:
        yield


@pytest.fixture(autouse=True)
def _clear_image_storage_cache():
    """Image storages are cached per bucket; don't leak one built under another test's settings."""
    get_s3_image_storage.cache_clear()
    yield
    get_s3_image_storage.cache_clear()


@pytest.fixture
def s3_cache_hit():
    """Opt-in fixture to mock S3 cache as available, for testing cache-hit paths."""
    with patch("api.utils.cached.exists", return_value=True):
        yield
