import uuid

from api.mocks import MockRequest
from api.models import CollectRecord, ProjectProfile
from api.resources.collect_record import CollectRecordSerializer
from api.resources.project_profile import ProjectProfileSerializer
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


def test_sync_push_blocks_deleting_last_admin(
    db_setup, project_profile1, project_profile2, profile1
):
    # project_profile1 is the only ADMIN; project_profile2 is COLLECTOR
    request = MockRequest(profile=profile1)
    record = {"id": str(project_profile1.pk), "_deleted": True, "_last_revision_num": 1}

    status_code, msg, _ = apply_changes(request, ProjectProfileSerializer, record)

    assert status_code == 400
    assert "Last admin" in msg
    assert ProjectProfile.objects.filter(pk=project_profile1.pk).exists()


def test_sync_push_blocks_downgrading_last_admin_role(
    db_setup, project_profile1, project_profile2, profile1
):
    # project_profile1 is the only ADMIN; attempt to change role to COLLECTOR via PUT
    request = MockRequest(profile=profile1)
    record = {
        "id": str(project_profile1.pk),
        "_last_revision_num": 1,
        "project": str(project_profile1.project_id),
        "profile": str(project_profile1.profile_id),
        "role": ProjectProfile.COLLECTOR,
    }

    status_code, msg, _ = apply_changes(request, ProjectProfileSerializer, record, force=True)

    assert status_code == 400
    assert "Last admin" in msg
    project_profile1.refresh_from_db()
    assert project_profile1.role == ProjectProfile.ADMIN


def test_sync_push_allows_downgrading_admin_when_another_admin_exists(
    db_setup, project_profile1, project_profile2, profile1, project1
):
    # Promote project_profile2 to ADMIN first, then downgrade project_profile1
    project_profile2.role = ProjectProfile.ADMIN
    project_profile2.save()

    request = MockRequest(profile=profile1)
    record = {
        "id": str(project_profile1.pk),
        "_last_revision_num": 1,
        "project": str(project_profile1.project_id),
        "profile": str(project_profile1.profile_id),
        "role": ProjectProfile.COLLECTOR,
    }

    status_code, _, _ = apply_changes(request, ProjectProfileSerializer, record, force=True)

    assert status_code == 200
    project_profile1.refresh_from_db()
    assert project_profile1.role == ProjectProfile.COLLECTOR
