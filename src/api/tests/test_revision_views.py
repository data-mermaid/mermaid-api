import uuid

from api.models import CollectRecord, Project, Revision


def test_pull_view(
    db_setup, collect_record_revision_with_updates, api_client1, country1, country2
):
    rec_rev = collect_record_revision_with_updates

    data = {
        "collect_records": {
            "last_revision": rec_rev.revision_num,
            "project": rec_rev.project_id,
        },
        "choices": {},
        "projects": {
            "last_revision": None,
            "project": rec_rev.project_id,
        }
    }

    request = api_client1.post("/v1/pull/", data, format="json")
    response_data = request.json()
    revision = Revision.objects.get(record_id=collect_record_revision_with_updates.record_id)

    assert len(response_data["collect_records"]["updates"]) == 1
    assert len(response_data["collect_records"]["deletes"]) == 1
    assert response_data["collect_records"]["last_revision_num"] == revision.revision_num

    assert len(response_data["choices"]["updates"]["countries"]["data"]) == 2

    assert len(response_data["projects"]["updates"]) == 1

    data = {
        "collect_records": {
            "last_revision": response_data["collect_records"]["last_revision_num"],
            "project": rec_rev.project_id,
        },
        "choices": {},
    }

    request = api_client1.post("/v1/pull/", data, format="json")
    response_data2 = request.json()
    assert response_data2["collect_records"]["last_revision_num"] == response_data["collect_records"]["last_revision_num"]


def test_pull_view_invalid_source_type(db_setup, api_client1):
    data = {"invalid_source_type": {}}

    request = api_client1.post("/v1/pull/", data, format="json")
    assert request.status_code == 400


def test_push_view_readonly(db_setup, api_client1):
    data = {"choices": [{"id": "def"}]}

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()
    assert response_data["choices"][0]["status_code"] == 405
    assert "read-only" in response_data["choices"][0]["message"]

    data = {"choices": [{"id": "def"}]}
    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()
    assert response_data["choices"][0]["status_code"] == 405
    assert "read-only" in response_data["choices"][0]["message"]


def test_push_view_conflict(db_setup, serialized_tracked_collect_record, api_client1):
    protocol = "fishbelt"

    col_rec = serialized_tracked_collect_record["updates"][0]
    col_rec["data"]["protocol"] = protocol

    data = {"collect_records": [col_rec]}

    request = api_client1.post("/v1/push/", data, format="json")

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()
    assert response_data["collect_records"][0]["status_code"] == 409

    # Force push (bypass conflict)
    request = api_client1.post("/v1/push/?force=true", data, format="json")
    response_data = request.json()
    assert response_data["collect_records"][0]["status_code"] == 200


def test_push_view_invalid_record(
    db_setup,
    api_client1,
    project1,
):
    new_id = str(uuid.uuid4())
    data = {
        "project_sites": [
            {"name": "My Test Site", "project": str(project1.id), "id": new_id}
        ],
    }

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()

    assert response_data["project_sites"][0]["status_code"] == 400


def test_push_view_create(db_setup, api_client1):
    api_client1

    new_id = str(uuid.uuid4())
    project = {"id": new_id, "name": "my new project"}

    data = {
        "projects": [project],
    }

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()
    assert response_data["projects"][0]["status_code"] == 201
    assert Project.objects.filter(id=new_id).exists()


def test_push_view_update(
    db_setup,
    serialized_tracked_collect_record,
    serialized_tracked_project1,
    api_client1,
):
    protocol = "fishbelt"
    new_project_name = "Revision Project Test"

    col_rec = serialized_tracked_collect_record["updates"][0]
    col_rec["data"]["protocol"] = protocol

    project = serialized_tracked_project1
    project["name"] = new_project_name

    data = {
        "collect_records": [col_rec],
        "projects": [project],
    }

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()
    collect_record_id = col_rec["id"]
    project_id = project["id"]

    assert response_data["collect_records"][0]["status_code"] == 200
    assert (
        CollectRecord.objects.get(id=collect_record_id).data.get("protocol") == protocol
    )

    assert response_data["projects"][0]["status_code"] == 200
    assert Project.objects.get(id=project_id).name == new_project_name


def test_push_view_delete(db_setup, serialized_tracked_collect_record, api_client1):
    col_rec = serialized_tracked_collect_record["updates"][0]
    col_rec["_deleted"] = True
    data = {
        "collect_records": [col_rec],
    }

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()

    assert response_data["collect_records"][0]["status_code"] == 204
    assert CollectRecord.objects.filter(id=col_rec["id"]).exists() is False

    request = api_client1.post("/v1/push/", data, format="json")
    assert response_data["collect_records"][0]["status_code"] == 204


def test_push_view_wrong_source_type(db_setup, api_client1):
    data = {"fake_source_type": [{"id": "I'm a fake"}]}

    request = api_client1.post("/v1/push/", data, format="json")

    assert request.status_code == 400


def test_push_view_wrong_permission(db_setup, api_client1, serialized_tracked_project2):
    
    data = {
        "projects": [serialized_tracked_project2],
    }

    request = api_client1.post("/v1/push/", data, format="json")
    response_data = request.json()

    assert response_data["projects"][0]["status_code"] == 403
