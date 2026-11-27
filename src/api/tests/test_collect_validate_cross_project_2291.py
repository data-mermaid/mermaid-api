"""Card 2291: validate/submit must act only on records in the URL project.

`validate_collect_records` / `submit_collect_records` selected records by id alone. An attacker who
OWNS a draft in project B (created it, then lost B membership) could still validate/submit it through
their own project A, because ProjectDataPermission passes for A and CollectRecordOwner passes on
ownership. The same id-only lookup was also a foreign-draft existence oracle. The fix scopes both
helpers to the URL project.
"""

from django.urls import reverse

from api.models import CollectRecord


def _owned_draft(project, profile):
    return CollectRecord.objects.create(
        project=project, profile=profile, data={"protocol": "fishbelt"}
    )


def test_validate_ignores_record_outside_url_project(api_client1, project1, project2, profile1):
    # profile1 is ADMIN of project1 (api_client1) and owns a draft in project2 (no membership).
    foreign = _owned_draft(project2, profile1)
    own = _owned_draft(project1, profile1)

    url = reverse("collectrecords-validate", args=[str(project1.pk)])
    response = api_client1.post(url, {"ids": [str(foreign.pk), str(own.pk)]}, format="json")

    assert response.status_code == 200, response.content
    body = response.json()
    assert str(foreign.pk) not in body  # cross-project record not processed / not revealed
    assert str(own.pk) in body  # same-project record still validated


def test_submit_reports_record_outside_url_project_as_not_found(
    api_client1, project1, project2, profile1
):
    foreign = _owned_draft(project2, profile1)

    url = reverse("collectrecords-submit", args=[str(project1.pk)])
    response = api_client1.post(url, {"ids": [str(foreign.pk)]}, format="json")

    assert response.status_code == 200, response.content
    entry = response.json().get(str(foreign.pk)) or {}
    # Scoped out of the URL project -> reported as "Not found" (not reached by submit).
    assert entry.get("message") == "Not found", entry
    # the foreign draft is untouched (still a draft in project2)
    assert CollectRecord.objects.filter(pk=foreign.pk, project=project2).exists()
