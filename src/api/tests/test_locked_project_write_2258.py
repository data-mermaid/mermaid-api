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
