import pytest

from api.models import CollectRecord


@pytest.fixture
def collect_record1(db_setup, project1, profile1):
    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )


@pytest.fixture
def collect_record2(db_setup, project1, profile1):
    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )


@pytest.fixture
def collect_record3(db_setup, project1, profile1):
    return CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )