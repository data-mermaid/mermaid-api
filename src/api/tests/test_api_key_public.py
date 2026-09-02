"""C2/C9: public endpoints fail closed.

`AnonymousJWTAuthentication` serves a caller with no credentials as
`AnonymousUser`. A bad API key is a credential, not the absence of one, so it
has to 401 there too. Falling through to anonymous would hand a misconfigured
client public data and leave nobody a 401 to notice.
"""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import APIKey, Project
from api.utils.apikeys import generate_api_key


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def key_pair(profile1):
    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile1,
        name="public reader bot",
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=timezone.now() + timedelta(days=365),
    )
    return key, raw


def _client(raw=None):
    client = APIClient()
    if raw is not None:
        client.credentials(HTTP_AUTHORIZATION=f"ApiKey {raw}")
    return client


# GET endpoints an unauthenticated caller may reach, with the status each one
# gives that caller. Anonymous is never 401 here; a bad key always is.
PUBLIC_ENDPOINTS = [
    pytest.param(lambda p: reverse("project-list"), 200, id="project_list"),
    # Detail is a 404 for a caller with no credentials (the anonymous queryset
    # is empty), which is still not a 401 - authentication ran and passed.
    pytest.param(
        lambda p: reverse("project-detail", kwargs=dict(pk=p.pk)), 404, id="project_detail"
    ),
    pytest.param(
        lambda p: reverse("projectsummarysampleevents-list"), 200, id="summary_sample_events"
    ),
    # sample-unit-method SE view: public at the default PUBLIC_SUMMARY policy
    pytest.param(
        lambda p: reverse("benthicpitmethod-sampleevent-list", args=[str(p.pk)]),
        200,
        id="benthicpit_sampleevent",
    ),
]


@pytest.mark.parametrize("url_for,anonymous_status", PUBLIC_ENDPOINTS)
def test_public_endpoint_rejects_a_bad_key(db_setup, key_pair, project1, url_for, anonymous_status):
    _, raw = key_pair

    response = _client(raw + "x").get(url_for(project1), format="json")

    assert response.status_code == 401


@pytest.mark.parametrize("url_for,anonymous_status", PUBLIC_ENDPOINTS)
def test_public_endpoint_serves_an_anonymous_caller(db_setup, project1, url_for, anonymous_status):
    """The control: with no Authorization header these endpoints answer without
    a 401, so the 401 above comes from the bad key and not from the endpoint."""

    response = _client().get(url_for(project1), format="json")

    assert response.status_code == anonymous_status


def test_public_endpoint_accepts_a_valid_key(db_setup, key_pair, project1, project_profile1):
    _, raw = key_pair

    response = _client(raw).get(reverse("project-list"), format="json")

    assert response.status_code == 200
    assert {r["id"] for r in response.json()["results"]} == {str(project1.pk)}


def test_revoked_key_does_not_fall_back_to_public_data(db_setup, key_pair, project1):
    """The most likely real failure: a key that used to work is revoked and the
    client keeps sending it. It must break loudly, not silently degrade to the
    public view of the same endpoint."""

    key, raw = key_pair
    key.revoke("manual")

    assert _client(raw).get(reverse("project-list"), format="json").status_code == 401


def test_private_project_stays_private_for_a_bad_key(db_setup, api_client_public, project3):
    """project3 sets data_policy_benthicpit=PRIVATE. Unauthenticated is a 403;
    a bad key is a 401 - the credential is rejected before the policy is read."""

    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project3.pk)])

    assert api_client_public.get(url, format="json").status_code == 403
    assert _client("mmd_local_aaaaaaaaaaaa_nope").get(url, format="json").status_code == 401


def test_key_sees_public_summary_data_for_a_project_it_is_not_in(db_setup, profile1, project1):
    """Membership decides member-level access; it does not take away what any
    caller may read. profile1 is not a member of project1, so its key reads
    project1 at the public level like anyone else."""

    key_id, secret_hash, raw = generate_api_key()
    APIKey.objects.create(
        profile=profile1,
        name="non-member bot",
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=timezone.now() + timedelta(days=365),
    )

    url = reverse("benthicpitmethod-sampleevent-list", args=[str(project1.pk)])
    assert project1.data_policy_benthicpit == Project.PUBLIC_SUMMARY
    assert _client(raw).get(url, format="json").status_code == 200
