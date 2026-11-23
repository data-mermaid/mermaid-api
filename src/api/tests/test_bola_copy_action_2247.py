"""
Regression tests for Trello card 2247.

The `copy` action looked up the source record by id with no project filter, cloned
it into the caller's project, and returned its full data. A collector of any one
project could clone (and read) any other project's site/management records,
including GPS location. The fix only copies from a project the caller belongs to.
"""

import pytest
from django.urls import reverse

from api.models import Project, ProjectProfile, Site


@pytest.fixture
def attacker_admin_project(db, profile3):
    project = Project.objects.create(name="attacker-2247")
    ProjectProfile.objects.create(project=project, profile=profile3, role=ProjectProfile.ADMIN)
    return project


def test_copy_cannot_read_other_projects_site(
    db_setup, api_client3, attacker_admin_project, site1, project1
):
    # site1 belongs to project1; profile3 is not a member of project1.
    before = Site.objects.filter(project=attacker_admin_project).count()
    url = reverse("psite-copy", args=[str(attacker_admin_project.pk)])
    response = api_client3.post(url, {"original_ids": [str(site1.pk)]}, format="json")
    assert response.status_code == 403
    assert Site.objects.filter(project=attacker_admin_project).count() == before


def test_copy_within_own_project_allowed(db_setup, api_client1, project1, project_profile1, site1):
    before = Site.objects.filter(project=project1).count()
    url = reverse("psite-copy", args=[str(project1.pk)])
    response = api_client1.post(url, {"original_ids": [str(site1.pk)]}, format="json")
    assert response.status_code == 200
    assert Site.objects.filter(project=project1).count() == before + 1
