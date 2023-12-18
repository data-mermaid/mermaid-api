import pytest

from api.mocks import MockRequest
from api.models import CollectRecord, Revision
from api.resources.collect_record import CollectRecordViewSet
from api.resources.sync.pull import get_serialized_records


@pytest.fixture
def collect_record_revision_with_updates(db_setup, project1, profile1):
    collect_record = CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    collect_record.save()

    CollectRecord.objects.create(project=project1, profile=profile1, data=dict())

    rev_rec = Revision.objects.get(record_id=collect_record.id)

    # Populate the rev_rec instance before deleting
    rev_rec.id

    collect_record.delete()

    return rev_rec


@pytest.fixture
def serialized_tracked_collect_record(db_setup, collect_record_revision_with_updates, profile1):
    request = MockRequest(profile=profile1)
    rev = collect_record_revision_with_updates
    return get_serialized_records(
        CollectRecordViewSet(request=request),
        profile1.pk,
        {"revision_num": rev.revision_num, "project": rev.project_id, "profile": rev.profile_id},
    )


@pytest.fixture
def serialized_tracked_project1(db_setup, project1, profile1, project_profile1):
    rev = Revision.objects.get(record_id=project1.pk)
    return {
        "_last_revision_num": rev.revision_num,
        "_modified": False,
        "_deleted": rev.deleted,
        "name": project1.name,
        "id": str(project1.id),
    }


@pytest.fixture
def serialized_tracked_project2(db_setup, project2, project_profile2):
    rev = Revision.objects.get(record_id=project2.pk)
    return {
        "_last_revision_num": rev.revision_num,
        "_modified": False,
        "_deleted": rev.deleted,
        "name": project2.name,
        "id": str(project2.id),
    }
