"""C3: a key acts as its profile.

There is no per-key scope or role. Every request a key authenticates resolves
to `APIKey.profile`, and from there through the ordinary permission classes,
so the key reaches exactly what its owner reaches: the same projects, with the
same `ProjectProfile.role` on each, subject to the same project status and
data policy rules. These tests pin that equivalence in both directions - what
the key can do, and what it cannot.
"""

import uuid
from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.http import QueryDict
from django.urls import reverse
from rest_framework.test import APIClient

from api.mocks import MockRequest
from api.models import APIKey, Project, ProjectProfile, Site
from api.resources.sync.utils import create_view_request
from api.utils.apikeys import default_expires_at, generate_api_key


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_key(profile, name="bot"):
    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile,
        name=name,
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=default_expires_at(),
    )
    return key, raw


def _client(raw):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    return client


def _site_payload(project, country, reef_type, reef_zone, exposure):
    return {
        "id": str(uuid.uuid4()),
        "name": "Bot site",
        "project": str(project.pk),
        "country": str(country.pk),
        "reef_type": str(reef_type.pk),
        "reef_zone": str(reef_zone.pk),
        "exposure": str(exposure.pk),
        "location": {"type": "Point", "coordinates": [1.5, 1.5]},
    }


def test_key_reaches_every_project_the_profile_belongs_to(
    db_setup, profile1, project1, project2, project_profile1
):
    ProjectProfile.objects.create(project=project2, profile=profile1, role=ProjectProfile.ADMIN)
    _, raw = _make_key(profile1)
    client = _client(raw)

    for project in (project1, project2):
        url = reverse("psite-list", kwargs=dict(project_pk=project.pk))
        assert client.get(url, format="json").status_code == 200


def test_key_is_denied_a_project_the_profile_does_not_belong_to(
    db_setup, profile1, project1, project2, project_profile1
):
    """Membership is the boundary. profile1 is an ADMIN of project1 and not a
    member of project2, and the key inherits exactly that."""

    _, raw = _make_key(profile1)
    url = reverse("psite-list", kwargs=dict(project_pk=project2.pk))
    assert _client(raw).get(url, format="json").status_code == 403


def test_key_loses_a_project_when_the_membership_goes(
    db_setup, profile1, project1, project_profile1
):
    """Nothing revokes or rescopes the key here. Access follows the membership
    on the next request because the key never held a project list of its own."""

    _, raw = _make_key(profile1)
    client = _client(raw)
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))

    assert client.get(url, format="json").status_code == 200

    project_profile1.delete()

    assert _client(raw).get(url, format="json").status_code == 403


def test_collector_profile_key_can_write(db_setup, project1, profile2, project_profile2):
    """The key carries the profile's role: project_profile2 is a COLLECTOR on
    project1, so the key writes there."""

    _, raw = _make_key(profile2)
    url = reverse("collectrecords-list", args=[str(project1.pk)])
    data = {
        "id": str(uuid.uuid4()),
        "data": {},
        "project": str(project1.pk),
        "profile": str(profile2.pk),
    }
    assert _client(raw).post(url, data, format="json").status_code == 201


def test_readonly_profile_key_cannot_write(
    db_setup, project1, profile3, country1, reef_type1, reef_zone1, reef_exposure1
):
    """A READONLY member's key reads and nothing more - the role is the cap."""

    ProjectProfile.objects.create(project=project1, profile=profile3, role=ProjectProfile.READONLY)
    _, raw = _make_key(profile3, name="readonly bot")
    client = _client(raw)
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))

    assert client.get(url, format="json").status_code == 200

    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)
    assert client.post(url, payload, format="json").status_code == 403


def test_locked_project_key_cannot_write(
    db_setup,
    project1,
    profile2,
    project_profile2,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    """A LOCKED project downgrades COLLECTORs to read-only, and a key inherits
    that: the same POST that succeeded on an open project is now a 403."""

    _, raw = _make_key(profile2)
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)

    assert _client(raw).post(url, payload, format="json").status_code == 201

    project1.status = Project.LOCKED
    project1.save()

    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)
    assert _client(raw).post(url, payload, format="json").status_code == 403


def test_admin_profile_key_can_do_admin_actions(
    db_setup, base_project, project1, profile1, project_profile1
):
    _, raw = _make_key(profile1)
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    response = _client(raw).post(
        url, {"email": "bot-added@test.com", "role": ProjectProfile.COLLECTOR}, format="json"
    )
    assert response.status_code == 200


def test_project_list_matches_the_profile(
    db_setup, api_client1, profile1, project1, project2, project_profile1
):
    """The key and a JWT for the same profile see the same list."""

    _, raw = _make_key(profile1)

    key_response = _client(raw).get(reverse("project-list"), format="json")
    jwt_response = api_client1.get(reverse("project-list"), format="json")

    assert key_response.status_code == 200
    ids = {r["id"] for r in key_response.json()["results"]}
    assert ids == {r["id"] for r in jwt_response.json()["results"]}
    assert ids == {str(project1.pk)}


def test_me_works_for_a_key(db_setup, profile1, project1, project_profile1):
    _, raw = _make_key(profile1)
    response = _client(raw).get(reverse("me-list"), format="json")

    assert response.status_code == 200
    assert response.json()["id"] == str(profile1.pk)


def test_write_is_attributed_to_the_keys_profile(
    db_setup,
    project1,
    profile2,
    project_profile2,
    country1,
    reef_type1,
    reef_zone1,
    reef_exposure1,
):
    """A key request carries no JWT, so updated_by has to come from the
    profile the key resolved to rather than from the Authorization header."""

    _, raw = _make_key(profile2)
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = _site_payload(project1, country1, reef_type1, reef_zone1, reef_exposure1)
    response = _client(raw).post(url, payload, format="json")

    assert response.status_code == 201
    assert Site.objects.get(pk=response.json()["id"]).updated_by == profile2


def test_view_request_carries_the_api_key(db_setup, profile1, project1):
    """Sync builds a derived request per record, and the write attribution on
    a push depends on request.auth surviving that."""

    key, _ = _make_key(profile1)

    class _Req:
        auth = key
        user = None
        method = "GET"
        headers = {}
        META = {}
        authenticators = ()
        successful_authenticator = None

    assert create_view_request(_Req()).auth is key


def test_mock_request_keeps_the_api_key(db_setup, profile1, project1):
    """Background reports are handed a MockRequest built from the real one."""

    key, _ = _make_key(profile1)
    stub = SimpleNamespace(
        user=SimpleNamespace(profile=profile1),
        GET=QueryDict(),
        POST=QueryDict(),
        data={},
        query_params=QueryDict(),
        META={},
        auth=key,
    )

    assert MockRequest.load_request(stub).auth is key
