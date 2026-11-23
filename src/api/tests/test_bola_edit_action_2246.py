"""
Regression tests for Trello card 2246.

The sample-unit-method `edit` action loaded the record by id with no project scope,
then deleted it and returned it as an editable collect record. An admin of any one
project could therefore delete and exfiltrate another project's submitted method by
its id alone. The fix scopes the lookup to the URL project.
"""

import pytest
from django.urls import reverse

from api.models import BeltFish, Project, ProjectProfile


@pytest.fixture
def attacker_admin_project(db, profile3):
    # profile3 is an ADMIN of a throwaway project and nothing else here.
    project = Project.objects.create(name="attacker-2246")
    ProjectProfile.objects.create(project=project, profile=profile3, role=ProjectProfile.ADMIN)
    return project


def test_edit_cannot_delete_other_projects_method(
    db_setup, api_client3, attacker_admin_project, belt_fish1, belt_fish_project
):
    # belt_fish1 belongs to belt_fish_project, not to the attacker's project.
    url = reverse(
        "beltfishtransectmethod-edit",
        kwargs={"project_pk": str(attacker_admin_project.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client3.put(url, {}, format="json")
    assert response.status_code == 404
    assert BeltFish.objects.filter(pk=belt_fish1.pk).exists()


def test_edit_works_for_owning_project_admin(
    db_setup, api_client1, project1, project_profile1, belt_fish1, belt_fish_project
):
    # belt_fish1 belongs to project1; api_client1 is its admin.
    assert belt_fish1.transect.sample_event.site.project_id == project1.pk
    url = reverse(
        "beltfishtransectmethod-edit",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client1.put(url, {}, format="json")
    assert response.status_code == 200
    assert not BeltFish.objects.filter(pk=belt_fish1.pk).exists()


# The `owner` field looked the id up as a Project, so it never matched and the collect
# record always went to the caller. It must resolve to a member of the URL project.


def test_edit_assigns_collect_record_to_requested_owner(
    db_setup,
    api_client1,
    project1,
    project_profile1,
    project_profile2,
    profile2,
    belt_fish1,
    belt_fish_project,
):
    from api.models import CollectRecord

    url = reverse(
        "beltfishtransectmethod-edit",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client1.put(url, {"owner": str(profile2.pk)}, format="json")
    assert response.status_code == 200
    assert CollectRecord.objects.get(pk=response.json()["id"]).profile_id == profile2.pk


def test_edit_ignores_owner_who_is_not_a_project_member(
    db_setup,
    api_client1,
    project1,
    project_profile1,
    profile1,
    profile3,
    belt_fish1,
    belt_fish_project,
):
    from api.models import CollectRecord

    url = reverse(
        "beltfishtransectmethod-edit",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client1.put(url, {"owner": str(profile3.pk)}, format="json")
    assert response.status_code == 200
    assert CollectRecord.objects.get(pk=response.json()["id"]).profile_id == profile1.pk
