"""
Regression test for Trello card 2251 (closed by the get_project_pk fix, card 2249).

An anonymous caller tried to read a PRIVATE project's sample-event data by putting
a different, PUBLIC project in the request body. The data-policy check read the
body project's policy (allow) while the queryset returned the URL project's
PRIVATE rows. With the URL now authoritative, a body project that differs from the
URL is rejected.
"""

import json

from django.urls import reverse


def _get_with_body(client, url, body):
    return client.generic("GET", url, data=json.dumps(body), content_type="application/json")


def test_private_se_not_readable_via_body_project_override(
    db_setup, api_client_public, project1, project3
):
    # project3 has data_policy_benthicpit = PRIVATE; project1 is PUBLIC_SUMMARY.
    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project3.pk)])
    response = _get_with_body(api_client_public, url, {"project": str(project1.pk)})
    assert response.status_code != 200


def test_private_se_still_denied_without_body(db_setup, api_client_public, project3):
    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project3.pk)])
    response = api_client_public.get(url, format="json")
    assert response.status_code != 200


def test_public_summary_se_still_readable(db_setup, api_client_public, project1):
    # Control: the legitimate anonymous summary read still works.
    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project1.pk)])
    response = api_client_public.get(url, format="json")
    assert response.status_code == 200
