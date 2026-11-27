"""
Regression test for Trello card 2249, the case a reviewer confirmed on the belt fish
DELETE route.

An admin of project A sent DELETE /projects/B/beltfishtransectmethods/<B's record>/
with the body {"project": A}. The permission check ran against A, while the queryset
used the URL project B, so B's submitted record was deleted.
"""

from django.urls import reverse

from api.models import BeltFish, Project, ProjectProfile


def test_admin_of_other_project_cannot_delete_via_body_project(
    db_setup, api_client3, profile3, belt_fish1, belt_fish_project, project1
):
    attacker_project = Project.objects.create(name="attacker-2249")
    ProjectProfile.objects.create(
        project=attacker_project, profile=profile3, role=ProjectProfile.ADMIN
    )
    url = reverse(
        "beltfishtransectmethod-detail",
        kwargs={"project_pk": str(project1.pk), "pk": str(belt_fish1.pk)},
    )
    response = api_client3.delete(url, {"project": str(attacker_project.pk)}, format="json")
    assert response.status_code == 403
    assert BeltFish.objects.filter(pk=belt_fish1.pk).exists()
