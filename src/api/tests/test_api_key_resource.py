"""Self-service API key management at /apikeys/.

A signed-in person can list, mint, rename and revoke keys that act as their
own profile, and nothing else: another person's key is invisible, a key can
never manage keys, and the secret is shown once at creation and never again.
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import APIKey
from api.resources.apikey import OWNER_REVOKED
from api.utils.apikeys import DEFAULT_LIFETIME_DAYS, generate_api_key
from .fixtures.apikeys import api_key_audit_lines


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_key(profile, name="bot", **kwargs):
    key_id, secret_hash, raw = generate_api_key()
    kwargs.setdefault("expires_at", timezone.now() + timedelta(days=30))
    key = APIKey.objects.create(
        profile=profile, name=name, key_id=key_id, secret_hash=secret_hash, **kwargs
    )
    return key, raw


def _key_client(raw):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    return client


@pytest.fixture
def own_key(profile1):
    return _make_key(profile1, name="own key")


@pytest.fixture
def other_key(profile2):
    return _make_key(profile2, name="someone else's key")


@pytest.fixture
def list_url():
    return reverse("apikey-list")


def _detail_url(key):
    return reverse("apikey-detail", kwargs={"pk": key.pk})


def _revoke_url(key):
    return reverse("apikey-revoke", kwargs={"pk": key.pk})


# --- access -----------------------------------------------------------------


def test_anonymous_is_rejected(db_setup, api_client_public, list_url):
    assert api_client_public.get(list_url).status_code == 401
    assert api_client_public.post(list_url, {"name": "x"}, format="json").status_code == 401


def test_api_key_cannot_manage_keys(db_setup, own_key, list_url):
    """A leaked key must not become an unlimited supply of keys."""

    key, raw = own_key
    client = _key_client(raw)

    assert client.get(list_url).status_code == 403
    assert client.post(list_url, {"name": "another"}, format="json").status_code == 403
    assert client.patch(_detail_url(key), {"name": "renamed"}, format="json").status_code == 403
    assert client.post(_revoke_url(key)).status_code == 403
    assert APIKey.objects.filter(profile=key.profile).count() == 1


def test_disallowed_methods(db_setup, api_client1, own_key, list_url):
    key, _ = own_key
    assert api_client1.delete(_detail_url(key)).status_code == 405
    assert api_client1.put(_detail_url(key), {"name": "x"}, format="json").status_code == 405
    assert APIKey.objects.filter(pk=key.pk).exists()


# --- read ---------------------------------------------------------------------


def test_list_only_own_keys(db_setup, api_client1, own_key, other_key, list_url):
    response = api_client1.get(list_url)
    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    result = data["results"][0]
    assert result["id"] == str(own_key[0].pk)
    assert result["key_id"] == own_key[0].key_id
    assert result["status"] == "active"
    assert "secret_hash" not in result
    assert "key" not in result


def test_retrieve_other_persons_key_is_not_found(db_setup, api_client1, other_key):
    key, _ = other_key
    assert api_client1.get(_detail_url(key)).status_code == 404
    assert api_client1.patch(_detail_url(key), {"name": "x"}, format="json").status_code == 404
    assert api_client1.post(_revoke_url(key)).status_code == 404
    key.refresh_from_db()
    assert key.revoked_at is None


@pytest.mark.parametrize(
    "attrs, expected",
    [
        pytest.param({}, "active", id="active"),
        pytest.param({"is_active": False}, "inactive", id="inactive"),
        pytest.param({"expires_at": timezone.now() - timedelta(days=1)}, "expired", id="expired"),
        pytest.param(
            {"is_active": False, "revoked_at": timezone.now(), "revoked_reason": "x"},
            "revoked",
            id="revoked",
        ),
    ],
)
def test_status_field(db_setup, api_client1, profile1, attrs, expected):
    key, _ = _make_key(profile1, **attrs)
    response = api_client1.get(_detail_url(key))
    assert response.status_code == 200
    assert response.json()["status"] == expected


def test_filters(db_setup, api_client1, profile1, list_url):
    live, _ = _make_key(profile1, name="live")
    revoked, _ = _make_key(profile1, name="dead")
    revoked.revoke("test")

    response = api_client1.get(list_url, {"revoked": "true"})
    assert [r["id"] for r in response.json()["results"]] == [str(revoked.pk)]

    response = api_client1.get(list_url, {"revoked": "false"})
    assert [r["id"] for r in response.json()["results"]] == [str(live.pk)]

    response = api_client1.get(list_url, {"is_active": "true"})
    assert [r["id"] for r in response.json()["results"]] == [str(live.pk)]

    response = api_client1.get(list_url, {"search": "dead"})
    assert [r["id"] for r in response.json()["results"]] == [str(revoked.pk)]


def test_sensitive_fields_are_never_returned(db_setup, api_client1, own_key, list_url):
    """`?fields=` must not be a way around the serializer's field list.

    The serializer leaves `secret_hash` out, but `?fields=` rebuilds the
    serializer from the requested names, so a sensitive column could be asked
    for by name. Asking for one is a 400, and the digest appears in no
    response body whatever combination is requested.
    """

    key, _ = own_key
    detail_url = _detail_url(key)

    for url in (list_url, detail_url):
        for fields in ("secret_hash", "id,secret_hash", " secret_hash , name "):
            response = api_client1.get(url, {"fields": fields})
            assert response.status_code == 400, f"{url} {fields!r}"
            assert "fields" in response.json()
            assert key.secret_hash not in response.content.decode()

    # an allowed subset still works, and still carries no digest
    response = api_client1.get(detail_url, {"fields": "id,name,key_id"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"id", "name", "key_id"}
    assert key.secret_hash not in response.content.decode()


def test_unknown_requested_fields_are_rejected(db_setup, api_client1, own_key):
    """A name the serializer does not know is a 400, not a silent empty object."""

    key, _ = own_key
    response = api_client1.get(_detail_url(key), {"fields": "id,not_a_field"})
    assert response.status_code == 400
    assert "not_a_field" in response.json()["fields"]


# --- create -------------------------------------------------------------------


def test_create_returns_working_key_once(
    db_setup, api_client1, profile1, project1, list_url, api_key_audit_logs
):
    response = api_client1.post(list_url, {"name": "reporting bot"}, format="json")
    assert response.status_code == 201
    data = response.json()

    key = APIKey.objects.get(pk=data["id"])
    assert key.profile == profile1
    assert key.created_by == profile1
    assert key.name == "reporting bot"
    assert data["key_id"] == key.key_id
    assert data["status"] == "active"
    assert "secret_hash" not in data

    raw = data["key"]
    assert raw.startswith("mmd_")
    assert key.key_id in raw
    # the raw key is not stored anywhere
    assert key.secret_hash not in raw
    assert raw not in str(APIKey.objects.filter(pk=key.pk).values().first())

    # the secret is gone from every later read
    assert "key" not in api_client1.get(_detail_url(key)).json()

    # and the key works as its owner
    key_response = _key_client(raw).get(reverse("project-detail", kwargs={"pk": project1.pk}))
    assert key_response.status_code == 200

    (line,) = api_key_audit_lines(api_key_audit_logs, "created")
    assert f"key_id={key.key_id}" in line
    assert f"profile={profile1.pk}" in line
    assert f"actor={profile1.authusers.first().user_id}" in line
    assert "mmd_" not in line
    assert key.secret_hash not in line


def test_create_defaults_expiry(db_setup, api_client1, list_url):
    before = timezone.now()
    response = api_client1.post(list_url, {"name": "bot"}, format="json")
    assert response.status_code == 201

    key = APIKey.objects.get(pk=response.json()["id"])
    expected = before + timedelta(days=DEFAULT_LIFETIME_DAYS)
    assert timedelta(0) <= key.expires_at - expected < timedelta(minutes=1)


def test_create_with_explicit_expiry(db_setup, api_client1, list_url):
    expires_at = (timezone.now() + timedelta(days=7)).replace(microsecond=0)
    response = api_client1.post(
        list_url, {"name": "bot", "expires_at": expires_at.isoformat()}, format="json"
    )
    assert response.status_code == 201
    key = APIKey.objects.get(pk=response.json()["id"])
    assert key.expires_at == expires_at


def test_create_never_expires_is_explicit(db_setup, api_client1, list_url):
    response = api_client1.post(list_url, {"name": "bot", "never_expires": True}, format="json")
    assert response.status_code == 201
    key = APIKey.objects.get(pk=response.json()["id"])
    assert key.expires_at is None

    # a null expiry without the flag still gets the default lifetime
    response = api_client1.post(list_url, {"name": "bot2", "expires_at": None}, format="json")
    assert response.status_code == 201
    assert APIKey.objects.get(pk=response.json()["id"]).expires_at is not None


def test_create_allows_expiry_up_to_the_ceiling(db_setup, api_client1, list_url):
    max_days = settings.API_KEY_MAX_LIFETIME_DAYS
    expires_at = (timezone.now() + timedelta(days=max_days - 1)).replace(microsecond=0)
    response = api_client1.post(
        list_url, {"name": "bot", "expires_at": expires_at.isoformat()}, format="json"
    )
    assert response.status_code == 201
    assert APIKey.objects.get(pk=response.json()["id"]).expires_at == expires_at


def test_create_stops_at_the_per_profile_limit(db_setup, api_client1, profile1, list_url):
    """A loop cannot leave an unbounded pile of live credentials behind."""

    for i in range(settings.API_KEY_MAX_PER_PROFILE):
        _make_key(profile1, name=f"bot{i}")

    response = api_client1.post(list_url, {"name": "one too many"}, format="json")
    assert response.status_code == 400
    assert "non_field_errors" in response.json()
    assert APIKey.objects.filter(profile=profile1).count() == settings.API_KEY_MAX_PER_PROFILE


def test_per_profile_limit_counts_only_usable_keys(db_setup, api_client1, profile1, list_url):
    """Revoked and expired keys stay for the audit trail, not against the cap."""

    for i in range(settings.API_KEY_MAX_PER_PROFILE - 1):
        _make_key(profile1, name=f"bot{i}")

    revoked, _ = _make_key(profile1, name="revoked")
    revoked.revoke("test")
    expired, _ = _make_key(profile1, name="expired")
    APIKey.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(days=1))

    response = api_client1.post(list_url, {"name": "still room"}, format="json")
    assert response.status_code == 201

    # and now the profile is at the cap
    assert api_client1.post(list_url, {"name": "no room"}, format="json").status_code == 400


def test_per_profile_limit_is_not_shared_between_profiles(
    db_setup, api_client1, profile1, profile2, list_url
):
    for i in range(settings.API_KEY_MAX_PER_PROFILE):
        _make_key(profile2, name=f"other{i}")

    response = api_client1.post(list_url, {"name": "bot"}, format="json")
    assert response.status_code == 201


@pytest.mark.parametrize(
    "payload, field",
    [
        pytest.param({}, "name", id="missing_name"),
        pytest.param({"name": ""}, "name", id="blank_name"),
        pytest.param({"name": "x" * 101}, "name", id="long_name"),
        pytest.param(
            {"name": "bot", "expires_at": (timezone.now() - timedelta(days=1)).isoformat()},
            "expires_at",
            id="past_expiry",
        ),
        pytest.param(
            {
                "name": "bot",
                "never_expires": True,
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            "expires_at",
            id="both_expiry_options",
        ),
        pytest.param(
            {
                "name": "bot",
                "expires_at": "9999-12-31T00:00:00Z",
            },
            "expires_at",
            id="expiry_past_the_ceiling",
        ),
    ],
)
def test_create_validation(db_setup, api_client1, profile1, list_url, payload, field):
    response = api_client1.post(list_url, payload, format="json")
    assert response.status_code == 400
    assert field in response.json()
    assert APIKey.objects.filter(profile=profile1).count() == 0


def test_create_ignores_ownership_and_secret_fields(
    db_setup, api_client1, profile1, profile2, list_url
):
    """The body cannot pick another owner, a key_id or a hash."""

    response = api_client1.post(
        list_url,
        {
            "name": "bot",
            "profile": str(profile2.pk),
            "key_id": "AAAAAAAAAAAA",
            "secret_hash": "0" * 64,
            "is_active": False,
            "revoked_at": None,
        },
        format="json",
    )
    assert response.status_code == 201
    key = APIKey.objects.get(pk=response.json()["id"])
    assert key.profile == profile1
    assert key.key_id != "AAAAAAAAAAAA"
    assert key.secret_hash != "0" * 64
    assert key.is_active is True


# --- update -------------------------------------------------------------------


def test_patch_renames_only(db_setup, api_client1, profile1, own_key):
    key, _ = own_key
    original_expiry = key.expires_at
    response = api_client1.patch(
        _detail_url(key),
        {
            "name": "renamed",
            "expires_at": (timezone.now() + timedelta(days=3650)).isoformat(),
            "is_active": False,
            "key_id": "BBBBBBBBBBBB",
        },
        format="json",
    )
    assert response.status_code == 200

    key.refresh_from_db()
    assert key.name == "renamed"
    assert key.expires_at == original_expiry
    assert key.is_active is True
    assert key.key_id != "BBBBBBBBBBBB"
    assert key.updated_by == profile1


# --- revoke -------------------------------------------------------------------


def test_revoke(db_setup, api_client1, profile1, project1, own_key, api_key_audit_logs):
    key, raw = own_key
    project_url = reverse("project-detail", kwargs={"pk": project1.pk})
    assert _key_client(raw).get(project_url).status_code == 200

    response = api_client1.post(_revoke_url(key))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "revoked"
    assert data["revoked_at"] is not None
    assert data["is_active"] is False

    key.refresh_from_db()
    actor = profile1.authusers.first().user_id
    assert key.revoked_reason == f"{OWNER_REVOKED}:{actor}"
    # the row survives for the audit trail
    assert APIKey.objects.filter(pk=key.pk).exists()

    # and the credential is dead on the next request
    cache.clear()
    assert _key_client(raw).get(project_url).status_code == 401

    (line,) = api_key_audit_lines(api_key_audit_logs, "revoked")
    assert f"key_id={key.key_id}" in line
    assert f"actor={actor}" in line


def test_revoke_is_idempotent(db_setup, api_client1, own_key):
    key, _ = own_key
    assert api_client1.post(_revoke_url(key)).status_code == 200
    key.refresh_from_db()
    first_revoked_at, first_reason = key.revoked_at, key.revoked_reason

    assert api_client1.post(_revoke_url(key)).status_code == 200
    key.refresh_from_db()
    assert key.revoked_at == first_revoked_at
    assert key.revoked_reason == first_reason
