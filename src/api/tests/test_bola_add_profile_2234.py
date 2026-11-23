"""
Regression test for Trello card 2234 (closed by the get_project_pk fix, card 2249).

An admin of one project could grant themselves ADMIN on any other project by
naming their own project in the request body (passing the admin check) while the
URL named the victim project (where the membership row was written). With the URL
authoritative, a mismatched body project is rejected.
"""

from django.urls import reverse

from api.models import ProjectProfile


def test_cannot_add_profile_to_other_project_via_body_override(
    db_setup, api_client1, project1, project_profile1, project2, profile1
):
    # api_client1 is ADMIN of project1, not a member of project2.
    url = reverse("project-add-profile", args=[str(project2.pk)])
    response = api_client1.post(
        url,
        {"email": profile1.email, "role": ProjectProfile.ADMIN, "project": str(project1.pk)},
        format="json",
    )
    assert response.status_code not in (200, 201)
    assert not ProjectProfile.objects.filter(project=project2, profile=profile1).exists()


def test_admin_can_add_profile_to_own_project(
    db_setup, api_client1, project1, project_profile1, profile2
):
    url = reverse("project-add-profile", args=[str(project1.pk)])
    response = api_client1.post(
        url,
        {"email": profile2.email, "role": ProjectProfile.READONLY},
        format="json",
    )
    assert response.status_code == 200
    assert ProjectProfile.objects.filter(project=project1, profile=profile2).exists()
