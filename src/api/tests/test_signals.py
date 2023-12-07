import uuid

from django.urls import reverse

from api.models import Project


def test_set_created_by(client, profile1, token1):
    url = reverse("project-list")
    response = client.post(
        url,
        data={"id": str(uuid.uuid4()), "name": "Test Project"},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 201
    assert Project.objects.get(id=response.data["id"]).created_by.id == profile1.id
