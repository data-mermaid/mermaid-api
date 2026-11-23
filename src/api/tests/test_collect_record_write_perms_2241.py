"""
Regression tests for Trello card 2241.

cr_permissions was [ProjectDataPermission & CollectRecordOwner], i.e. membership only.
So a READONLY member could create/update/submit their own collect records, and any
member could write on a LOCKED project. Writes now require COLLECTOR/ADMIN role on an
open project; reads stay open to members.
"""

from django.urls import reverse

from api.models import Project, ProjectProfile


def _list_url(project):
    return reverse("collectrecords-list", kwargs={"project_pk": str(project.pk)})


def _payload(project, profile):
    return {"project": str(project.pk), "profile": str(profile.pk), "data": {}}


def test_readonly_member_cannot_create_collect_record(db_setup, api_client3, project1, profile3):
    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.READONLY)
    response = api_client3.post(_list_url(project1), _payload(project1, profile3), format="json")
    assert response.status_code == 403


def test_readonly_member_can_read(db_setup, api_client3, project1, profile3):
    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.READONLY)
    response = api_client3.get(_list_url(project1), format="json")
    assert response.status_code == 200


def test_collector_can_create_on_open_project(db_setup, api_client3, project1, profile3):
    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.COLLECTOR)
    response = api_client3.post(_list_url(project1), _payload(project1, profile3), format="json")
    assert response.status_code == 201


def test_collector_cannot_write_on_locked_project(db_setup, api_client3, project1, profile3):
    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.COLLECTOR)
    project1.status = Project.LOCKED
    project1.save()
    response = api_client3.post(_list_url(project1), _payload(project1, profile3), format="json")
    assert response.status_code == 403
