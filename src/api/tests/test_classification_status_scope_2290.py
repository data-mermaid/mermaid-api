"""Card 2290: nested classification status reads must be scoped to the URL project.

ClassificationStatusViewSet.get_queryset returned the whole ClassificationStatus table (and the
entire table for ?showall), so a member of any project could read other projects' classification
statuses through their own project's route. The fix scopes get_queryset to the URL project.
"""

from django.urls import reverse
from rest_framework.test import APIClient

from api.models import ClassificationStatus, ProjectProfile


def test_classification_statuses_scoped_to_url_project(image, project2, profile3, token3):
    # `image` belongs to a collect record in project1. Its status is project1 data.
    status = ClassificationStatus.objects.create(image=image, message="project1-sentinel")

    # Attacker is admin of project2 only.
    ProjectProfile.objects.create(project=project2, profile=profile3, role=ProjectProfile.ADMIN)
    attacker = APIClient()
    attacker.credentials(HTTP_AUTHORIZATION=f"Bearer {token3}")

    url = reverse("status-list", args=[str(project2.pk)])
    resp = attacker.get(url)
    assert resp.status_code == 200, resp.content
    ids = [row["id"] for row in resp.json()["results"]]
    assert str(status.pk) not in ids  # project1 status not visible via project2 route
    assert ids == []  # project2 has no images/statuses

    resp_all = attacker.get(url + "?showall")
    assert resp_all.status_code == 200, resp_all.content
    assert [row["id"] for row in resp_all.json()["results"]] == []  # showall stays project-scoped


def test_classification_status_visible_to_own_project(image, api_client1, project1):
    # Control: the owning project's member still sees the status.
    status = ClassificationStatus.objects.create(image=image, message="own")
    url = reverse("status-list", args=[str(project1.pk)])
    resp = api_client1.get(url)
    assert resp.status_code == 200, resp.content
    ids = [row["id"] for row in resp.json()["results"]]
    assert str(status.pk) in ids
