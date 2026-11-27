"""
Regression tests for Trello card 2257 (sync push authorization gaps).

H7: a push authorized against the body `project` but wrote the record named by `id`,
    with no check that the record belonged to that project -> cross-tenant write/delete.
H8/M2: the push permission check carried no record id and no real method, so
    CollectRecordOwner was skipped and collector/role guards never fired -> a member
    could edit/delete another member's collect record (and a READONLY member could
    write).
"""

from api.mocks import MockRequest
from api.models import CollectRecord, ProjectProfile, Site
from api.resources.psite import PSiteViewSet

# -- H7: apply_changes refuses a record from another project --


def test_apply_changes_update_rejects_wrong_project(db_setup, site1, project1, project2, profile1):
    from api.resources.sync.push import apply_changes

    request = MockRequest(profile=profile1)
    record = {
        "id": str(site1.pk),  # site1 belongs to project1
        "project": str(project2.pk),  # but the push claims project2
        "_last_revision_num": 1,
        "name": "moved",
    }
    # force=True skips the revision-conflict check so we exercise the project guard.
    status_code, _, _ = apply_changes(request, PSiteViewSet.serializer_class, record, force=True)
    assert status_code == 403
    site1.refresh_from_db()
    assert site1.project_id == project1.pk


def test_apply_changes_delete_rejects_wrong_project(db_setup, site1, project1, project2, profile1):
    from api.resources.sync.push import apply_changes

    request = MockRequest(profile=profile1)
    record = {"id": str(site1.pk), "project": str(project2.pk), "_deleted": True}
    status_code, _, _ = apply_changes(request, PSiteViewSet.serializer_class, record)
    assert status_code == 403
    assert Site.objects.filter(pk=site1.pk).exists()


def test_apply_changes_delete_allows_matching_project(db_setup, site1, project1, profile1):
    from api.resources.sync.push import apply_changes

    request = MockRequest(profile=profile1)
    record = {"id": str(site1.pk), "project": str(project1.pk), "_deleted": True}
    status_code, _, _ = apply_changes(request, PSiteViewSet.serializer_class, record)
    assert status_code == 204
    assert not Site.objects.filter(pk=site1.pk).exists()


# -- H8 / M2: push permission check runs CollectRecordOwner with the real method --


def test_push_readonly_cannot_delete_other_members_collect_record(
    db_setup, api_client3, project1, profile1, profile3, collect_record1
):
    # collect_record1 is owned by profile1 on project1; profile3 is READONLY there.
    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.READONLY)
    payload = {
        "collect_records": [
            {
                "id": str(collect_record1.pk),
                "project": str(project1.pk),
                "profile": str(profile1.pk),
                "_deleted": True,
            }
        ]
    }
    response = api_client3.post("/v1/push/", payload, format="json")
    assert response.status_code == 200
    result = response.json()["collect_records"][0]
    assert result["status_code"] == 403
    assert CollectRecord.objects.filter(pk=collect_record1.pk).exists()


def test_apply_changes_project_delete_rejects_body_project_mismatch(
    db_setup, project1, project2, profile1
):
    # The permission check authorizes the body `project` (project1); the record id
    # names project2. The delete must not go through for project2.
    from api.models import Project
    from api.resources.project import ProjectViewSet
    from api.resources.sync.push import apply_changes

    request = MockRequest(profile=profile1)
    record = {"id": str(project2.pk), "project": str(project1.pk), "_deleted": True}
    status_code, _, _ = apply_changes(request, ProjectViewSet.serializer_class, record)
    assert status_code == 403
    assert Project.objects.filter(pk=project2.pk).exists()


def test_apply_changes_accepts_uppercase_project_uuid(db_setup, site1, project1, profile1):
    from api.resources.sync.push import apply_changes

    request = MockRequest(profile=profile1)
    record = {"id": str(site1.pk), "project": str(project1.pk).upper(), "_deleted": True}
    status_code, _, _ = apply_changes(request, PSiteViewSet.serializer_class, record)
    assert status_code == 204


def test_push_malformed_collect_record_id_fails_only_that_record(
    db_setup, api_client1, project1, profile1
):
    payload = {
        "collect_records": [
            {
                "id": "not-a-uuid",
                "project": str(project1.pk),
                "profile": str(profile1.pk),
                "_deleted": True,
            }
        ]
    }
    response = api_client1.post("/v1/push/", payload, format="json")
    assert response.status_code == 200
    assert response.json()["collect_records"][0]["status_code"] == 400
