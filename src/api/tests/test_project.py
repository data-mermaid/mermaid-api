import pytest
from django.urls import reverse

from api.models import ProjectProfile


def test_add_profile_new(
    client,
    base_project,
    project1,
    token1,
):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))

    response = client.post(
        url,
        data={"email": "bill@test.com", "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 200


def test_add_profile_new(
    client,
    base_project,
    project1,
    token1,
    profile2,
):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))

    response = client.post(
        url,
        data={"email": profile2.email, "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 400
