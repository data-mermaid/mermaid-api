"""
Regression tests for Trello card 2258.

A project admin could PATCH a LOCKED project's status back to OPEN (and edit it), because
the admin permission path never checked is_open. CLAUDE.md says a LOCKED project takes no
writes, even for admins. perform_update now blocks API writes while the project is locked.
"""

from django.urls import reverse

from api.models import Project


def _url(project):
    return reverse("project-detail", args=[str(project.pk)])


def test_admin_cannot_unlock_locked_project(db_setup, api_client1, project1, project_profile1):
    project1.status = Project.LOCKED
    project1.save()
    response = api_client1.patch(_url(project1), {"status": Project.OPEN}, format="json")
    assert response.status_code == 403
    project1.refresh_from_db()
    assert project1.status == Project.LOCKED


def test_admin_cannot_edit_locked_project(db_setup, api_client1, project1, project_profile1):
    project1.status = Project.LOCKED
    project1.save()
    response = api_client1.patch(_url(project1), {"name": "renamed-while-locked"}, format="json")
    assert response.status_code == 403
    project1.refresh_from_db()
    assert project1.name != "renamed-while-locked"


def test_admin_can_edit_open_project(db_setup, api_client1, project1, project_profile1):
    response = api_client1.patch(_url(project1), {"name": "renamed-open"}, format="json")
    assert response.status_code == 200
    project1.refresh_from_db()
    assert project1.name == "renamed-open"


# perform_update guards the standard update path; these custom write actions bypass it.


def test_admin_cannot_add_profile_to_locked_project(
    db_setup, api_client1, project1, project_profile1
):
    project1.status = Project.LOCKED
    project1.save()
    url = reverse("project-add-profile", args=[str(project1.pk)])
    response = api_client1.post(url, {"email": "newperson@example.com"}, format="json")
    assert response.status_code == 403


def test_admin_cannot_transfer_sample_units_on_locked_project(
    db_setup, api_client1, project1, project_profile1
):
    project1.status = Project.LOCKED
    project1.save()
    url = reverse("project-transfer-sample-units", args=[str(project1.pk)])
    response = api_client1.put(url, {}, format="json")
    assert response.status_code == 403


def test_admin_cannot_find_and_replace_sites_on_locked_project(
    db_setup, api_client1, project1, project_profile1
):
    project1.status = Project.LOCKED
    project1.save()
    url = reverse("project-find-and-replace-sites", args=[str(project1.pk)])
    response = api_client1.put(
        url, {"find": [str(project1.pk)], "replace": str(project1.pk)}, format="json"
    )
    assert response.status_code == 403


# ProjectDataAdminPermission itself must refuse writes on a LOCKED project. Before, it
# only checked the admin role, so admin DELETE and the sample-unit /edit/ action wrote
# to a locked project.


def _lock(project):
    project.status = Project.LOCKED
    project.save()


def test_admin_cannot_delete_sample_unit_on_locked_project(
    db_setup, api_client1, project1, project_profile1, belt_fish1, belt_fish_project
):
    from api.models import BeltFish

    _lock(project1)
    url = reverse(
        "beltfishtransectmethod-detail",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client1.delete(url)
    assert response.status_code == 403
    assert BeltFish.objects.filter(pk=belt_fish1.pk).exists()


def test_admin_cannot_edit_sample_unit_on_locked_project(
    db_setup, api_client1, project1, project_profile1, belt_fish1, belt_fish_project
):
    from api.models import BeltFish

    _lock(project1)
    url = reverse(
        "beltfishtransectmethod-edit",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client1.put(url, {}, format="json")
    assert response.status_code == 403
    assert BeltFish.objects.filter(pk=belt_fish1.pk).exists()


def test_admin_can_still_read_sample_unit_on_locked_project(
    db_setup, api_client1, project1, project_profile1, belt_fish1, belt_fish_project
):
    _lock(project1)
    url = reverse(
        "beltfishtransectmethod-detail",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    assert api_client1.get(url).status_code == 200
