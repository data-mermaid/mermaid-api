import uuid

from django.urls import reverse

from api.models import CollectRecord


def test_owner_read_edit_collect_record(
    db_setup, api_client1, api_client2, collect_record4
):
    url = reverse(
        "collectrecords-detail",
        args=[str(collect_record4.project.pk), str(collect_record4.pk)],
    )

    response = api_client1.get(url, None, format="json")
    response_data = response.json()

    assert response.status_code == 200

    response_data["data"]["some_key"] = 123
    response = api_client1.put(url, response_data, format="json")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["data"]["some_key"] == 123

    response = api_client1.delete(url, None, format="json")
    assert response.status_code == 204


def test_non_owner_read_edit_collect_record(
    db_setup, api_client1, api_client2, collect_record4, project1
):
    url = reverse(
        "collectrecords-detail",
        args=[str(collect_record4.project.pk), str(collect_record4.pk)],
    )

    response = api_client1.get(url, None, format="json")
    response_data = response.json()

    response_data["data"]["some_key"] = "some_data"
    response = api_client2.put(url, response_data, format="json")

    assert response.status_code == 403

    response = api_client2.delete(url, None, format="json")
    assert response.status_code == 403

    response = api_client2.get(url, None, format="json")
    assert response.status_code == 403

    url = reverse("collectrecords-list", args=[str(project1.pk)])
    response = api_client2.get(url, None, format="json")
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["count"] == 0


def test_create_collect_record(db_setup, api_client2, project1, profile2):
    url = reverse("collectrecords-list", args=[str(project1.pk)])

    data = {
        "id": str(uuid.uuid4()),
        "data": {},
        "project": str(project1.pk),
        "profile": str(profile2.pk),
    }
    response = api_client2.post(url, data, format="json")
    response_data = response.json()
    print(f"response_data: {response_data}")

    assert response.status_code == 201
    assert CollectRecord.objects.filter(id=response_data["id"]).exists()
