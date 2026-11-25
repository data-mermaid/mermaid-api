"""
Regression tests for Trello card 2240.

The global /v1/sites/ (and /v1/managements/) endpoints returned every non-test project's
rows to any logged-in user, ignoring membership and data policy - leaking site GPS of
PRIVATE projects. The queryset is now limited to projects with a non-PRIVATE policy plus
the caller's own projects.
"""

from django.urls import reverse

from api.models import Project
from api.utils.project import DATA_POLICY_FIELDS


def _make_private(project):
    for field in DATA_POLICY_FIELDS:
        setattr(project, field, Project.PRIVATE)
    project.save()


def _ids(response):
    data = response.json()
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    return {row["id"] for row in rows}


def test_non_member_sees_public_project_site(db_setup, api_client3, project1, site1):
    # project1 defaults to PUBLIC_SUMMARY policies.
    response = api_client3.get(reverse("site-list"), format="json")
    assert response.status_code == 200
    assert str(site1.pk) in _ids(response)


def test_non_member_cannot_see_private_project_site(db_setup, api_client3, project1, site1):
    _make_private(project1)
    response = api_client3.get(reverse("site-list"), format="json")
    assert response.status_code == 200
    assert str(site1.pk) not in _ids(response)


def test_member_sees_own_private_project_site(
    db_setup, api_client1, project1, project_profile1, site1
):
    _make_private(project1)
    response = api_client1.get(reverse("site-list"), format="json")
    assert response.status_code == 200
    assert str(site1.pk) in _ids(response)
