"""
Regression tests for Trello card 2239.

A COLLECTOR could delete other project members (perform_destroy only blocked the last
admin). A collector may now remove only their own membership; removing another member is
an admin action.
"""

from django.urls import reverse

from api.models import ProjectProfile


def _detail_url(project, project_profile):
    return reverse("project_profile-detail", args=[str(project.pk), str(project_profile.pk)])


def test_collector_cannot_delete_another_member(
    db_setup, api_client2, project1, project_profile1, project_profile2, profile3
):
    # api_client2 (profile2) is a COLLECTOR of project1; target is another member.
    target = ProjectProfile.objects.create(
        project=project1, profile=profile3, role=ProjectProfile.READONLY
    )
    response = api_client2.delete(_detail_url(project1, target), format="json")
    assert response.status_code == 403
    assert ProjectProfile.objects.filter(pk=target.pk).exists()


def test_collector_can_remove_self(
    db_setup, api_client2, project1, project_profile1, project_profile2
):
    response = api_client2.delete(_detail_url(project1, project_profile2), format="json")
    assert response.status_code == 204
    assert not ProjectProfile.objects.filter(pk=project_profile2.pk).exists()


def test_admin_can_delete_another_member(
    db_setup, api_client1, project1, project_profile1, profile3
):
    target = ProjectProfile.objects.create(
        project=project1, profile=profile3, role=ProjectProfile.READONLY
    )
    response = api_client1.delete(_detail_url(project1, target), format="json")
    assert response.status_code == 204
    assert not ProjectProfile.objects.filter(pk=target.pk).exists()
