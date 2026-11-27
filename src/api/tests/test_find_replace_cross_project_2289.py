"""Card 2289: find_and_replace must not load the replacement object from another project.

Before the fix, `_find_and_replace_objs` loaded the `replace` object globally, so an admin of
project A could name a site/management in project B as the replacement: A's note was written onto
the B object and the A source object was deleted, with no B membership. The fix scopes the
replacement lookup to the URL project.
"""

from django.urls import reverse

from api.models import Site


def test_find_replace_rejects_cross_project_replacement(
    api_client1, project1, project2, site1, country1, reef_type1, reef_exposure1, reef_zone1
):
    # api_client1 is ADMIN of project1 only. Victim site lives in project2 (no membership).
    victim = Site.objects.create(
        project=project2,
        name="Victim Site",
        location=site1.location,
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
        notes="victim original",
    )

    url = reverse("project-find-and-replace-sites", args=[str(project1.pk)])
    response = api_client1.put(
        url, {"find": [str(site1.pk)], "replace": str(victim.pk)}, format="json"
    )

    assert response.status_code == 400, response.content
    victim.refresh_from_db()
    assert victim.notes == "victim original"  # B site untouched
    assert Site.objects.filter(pk=site1.pk).exists()  # A source not deleted


def test_find_replace_same_project_still_works(api_client1, project1, site1, site2):
    # Control: a same-project replacement is unaffected by the fix.
    site1.notes = "keep me"
    site1.save()
    url = reverse("project-find-and-replace-sites", args=[str(project1.pk)])
    response = api_client1.put(
        url, {"find": [str(site2.pk)], "replace": str(site1.pk)}, format="json"
    )

    assert response.status_code == 200, response.content
    assert not Site.objects.filter(pk=site2.pk).exists()  # find source removed
    assert Site.objects.filter(pk=site1.pk).exists()  # replacement kept
