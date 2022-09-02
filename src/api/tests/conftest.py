import pytest
from django.db import connection
from django.conf import settings

from api.models.view_models import model_view_migrations
from api.models import revisions
from .fixtures import *


@pytest.fixture(autouse=True)
def db_setup(db):
    with connection.cursor() as cursor:
        # https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-DATABASE-TEST
        db_name = settings.DATABASES["default"]["NAME"]
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        cursor.execute(f"ALTER DATABASE {db_name} SET jit TO false;")
        cursor.execute(model_view_migrations.forward_sql())
        cursor.execute(revisions.forward_sql)
