import uuid

from api.models import CollectRecord
from api.resources.collect_record import CollectRecordSerializer
from api.resources.sync.push import apply_changes, check_for_revision_conflicts
from api.mocks import MockRequest


def test_check_for_revision_conflicts(db_setup, serialized_tracked_collect_record):
    serialized_collect_record = serialized_tracked_collect_record["updates"][0]
    checks = check_for_revision_conflicts([serialized_collect_record])
    assert checks[serialized_collect_record["id"]].has_conflict is False

    serialized_collect_record = serialized_tracked_collect_record["updates"][0]
    serialized_collect_record["_last_revision_num"] = 2
    checks = check_for_revision_conflicts([serialized_collect_record])
    assert checks[serialized_collect_record["id"]].has_conflict is True

    new_collect_record = {"id": "508665bb-0f67-42e9-af52-6e500b52100f"}
    checks = check_for_revision_conflicts([new_collect_record])
    assert checks[new_collect_record["id"]].has_conflict is False


def test_apply_changes(db_setup, serialized_tracked_collect_record, profile1, project1):
    serialized_collect_record = serialized_tracked_collect_record["updates"][0]
    serialized_collect_record["data"]["protocol"] = "fishbelt"

    request = MockRequest(profile=profile1)
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
        "data": dict()
    }
    assert apply_changes(request, CollectRecordSerializer, new_collect_record)
    assert CollectRecord.objects.filter(id=new_collect_record["id"]).exists() is True
