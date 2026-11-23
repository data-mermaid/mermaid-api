"""
Regression test for Trello card 2254 (closed by the get_project_pk fix, card 2249).

A member of one project could read another project's submitted images and
classification statuses by naming their own project in the request body while the
URL named the victim project. The ProjectData* permissions resolved the project
from the body; the queryset returned the URL project's rows. With the URL
authoritative, a mismatched body project is rejected.
"""

import json

from django.urls import reverse


def _get_with_body(client, url, body):
    return client.generic("GET", url, data=json.dumps(body), content_type="application/json")


def test_cannot_read_other_project_images_via_body_override(
    db_setup, api_client1, project1, project_profile1, project2
):
    # api_client1 is a member of project1, not of project2.
    url = reverse("image-list", args=[str(project2.pk)])
    response = _get_with_body(api_client1, url, {"project": str(project1.pk)})
    assert response.status_code != 200


def test_member_can_list_own_project_images(db_setup, api_client1, project1, project_profile1):
    url = reverse("image-list", args=[str(project1.pk)])
    response = api_client1.get(url, format="json")
    assert response.status_code == 200
