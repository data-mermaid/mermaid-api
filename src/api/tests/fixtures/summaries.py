import pytest

from api.models import Project
from api.utils.summary_cache import update_summary_cache as update_cache


@pytest.fixture
def update_summary_cache():
    for project in Project.objects.all():
        update_cache(project.pk, skip_test_project=False, skip_cached_files=True)
