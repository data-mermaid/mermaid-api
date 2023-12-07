import uuid

from api.mocks import MockRequest
from api.models import CollectRecord
from api.resources.collect_record import CollectRecordSerializer, CollectRecordViewSet
from api.resources.sync.push import apply_changes


def test_apply_changes(db_setup, serialized_tracked_collect_record, profile1, project1):
    request = MockRequest(profile=profile1)

    serialized_collect_record = serialized_tracked_collect_record["updates"][0]
    serialized_collect_record["data"]["protocol"] = "fishbelt"

    assert apply_changes(request, CollectRecordSerializer, serialized_collect_record)
    cr = CollectRecord.objects.get(id=serialized_collect_record["id"])
    assert cr.data["protocol"] == "fishbelt"

    serialized_collect_record["_deleted"] = True
    assert apply_changes(request, CollectRecordSerializer, serialized_collect_record)
    assert CollectRecord.objects.filter(id=serialized_collect_record["id"]).exists() is False

    new_collect_record = {
        "id": str(uuid.uuid4()),
        "profile": str(profile1.pk),
        "project": str(project1.pk),
        "data": dict(),
    }
    assert apply_changes(request, CollectRecordSerializer, new_collect_record)
    assert CollectRecord.objects.filter(id=new_collect_record["id"]).exists() is True
