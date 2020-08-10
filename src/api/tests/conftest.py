import pytest
from django.db import connection

from api.models.view_models import model_view_migrations
from .fixtures import *


@pytest.fixture
def db_setup(db):
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute(model_view_migrations.forward_sql())
