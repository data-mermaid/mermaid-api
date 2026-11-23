"""
Regression tests for Trello card 2236.

`?showall` dropped the project-membership filter on ProjectViewSet.get_queryset for
every method. On a write method that let get_object() resolve a project the caller
is not a member of; combined with the body `project` override it allowed a
cross-project modify/delete. Two defences:

- card 2249 makes get_project_pk URL-authoritative (a mismatched body is rejected);
- this change restricts `?showall` to safe (read) methods.
"""

import json

from django.urls import reverse


def test_showall_does_not_widen_write_scope(
    db_setup, api_client1, project1, project_profile1, project2
):
    # api_client1 is admin of project1, not a member of project2.
    url = reverse("project-detail", args=[str(project2.pk)]) + "?showall"
    response = api_client1.patch(url, {"name": "pwned-2236"}, format="json")
    assert response.status_code not in (200, 201)
    project2.refresh_from_db()
    assert project2.name != "pwned-2236"


def test_showall_write_with_body_override_denied(
    db_setup, api_client1, project1, project_profile1, project2
):
    url = reverse("project-detail", args=[str(project2.pk)]) + "?showall"
    response = api_client1.generic(
        "PATCH",
        url,
        data=json.dumps({"project": str(project1.pk), "name": "pwned-2236b"}),
        content_type="application/json",
    )
    assert response.status_code not in (200, 201)
    project2.refresh_from_db()
    assert project2.name != "pwned-2236b"


def test_showall_read_still_lists_all_projects(
    db_setup, api_client1, project1, project_profile1, project2
):
    url = reverse("project-list") + "?showall"
    response = api_client1.get(url, format="json")
    assert response.status_code == 200
    body = response.json()
    rows = body["results"] if isinstance(body, dict) and "results" in body else body
    ids = {row["id"] for row in rows}
    assert str(project2.pk) in ids
