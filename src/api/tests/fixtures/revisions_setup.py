import pytest

from rest_framework.test import APIClient

from api.models import CollectRecord, Revision
from api.resources.collect_record import CollectRecordViewSet
from api.resources.project import ProjectViewSet
from api.resources.sync.pull import get_serialized_records


@pytest.fixture
def collect_record_revision_with_updates(db_setup, project1, profile1):
    collect_record = CollectRecord.objects.create(
        project=project1, profile=profile1, data=dict()
    )

    collect_record.save()

    CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    rev_rec = Revision.objects.get(record_id=collect_record.id)

    # Populate the rev_rec instance before deleting
    rev_rec.id

    collect_record.delete()

    return rev_rec


@pytest.fixture
def serialized_tracked_collect_record(db_setup, collect_record_revision_with_updates):
    rev = collect_record_revision_with_updates
    return get_serialized_records(
        CollectRecordViewSet,
        revision_num=rev.revision_num,
        project=rev.project_id,
        profile=rev.profile_id
    )


@pytest.fixture
def serialized_tracked_project1(db_setup, project1):
    rev = Revision.objects.filter(table_name="project").order_by("-revision_num")[0]
    return get_serialized_records(
        ProjectViewSet,
        revision_num=None,
        project=rev.project_id,
        profile=rev.profile_id
    )


@pytest.fixture
def serialized_tracked_project2(db_setup, project2):
    rev = Revision.objects.filter(table_name="project").order_by("-revision_num")[0]
    return get_serialized_records(
        ProjectViewSet,
        revision_num=None,
        project=rev.project_id,
        profile=rev.profile_id
    )

@pytest.fixture
def api_client1(token1, project_profile1):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token1}")
    return client
