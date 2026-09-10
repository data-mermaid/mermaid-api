from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from api.models import APIKey
from api.utils.apikeys import KEY_ID_ISSUE_ATTEMPTS, generate_api_key, hash_secret


@pytest.fixture
def api_key1(profile1):
    key = APIKey.objects.create(
        profile=profile1,
        name="reporting bot",
        key_id="abc123def456",
        secret_hash="0" * 64,
    )
    return key


def test_api_key_str_does_not_leak_hash(api_key1):
    assert str(api_key1) == "reporting bot [abc123def456]"
    assert api_key1.secret_hash not in str(api_key1)


def test_api_key_has_no_raw_secret_field():
    field_names = {f.name for f in APIKey._meta.get_fields()}
    assert "secret" not in field_names
    assert "secret_hash" in field_names


def test_api_key_carries_no_scope_or_role_of_its_own():
    """The key is its profile's access. A field here that narrowed or widened
    that would be a second permission system to keep in step with the first."""

    field_names = {f.name for f in APIKey._meta.get_fields()}
    assert "projects" not in field_names
    assert "role" not in field_names


def test_api_key_defaults(api_key1, profile1):
    assert api_key1.is_active is True
    # no expiry, revocation or usage until something sets them
    assert api_key1.expires_at is None
    assert api_key1.revoked_at is None
    assert api_key1.revoked_reason == ""
    assert api_key1.last_used_at is None
    assert api_key1.last_used_ip is None
    assert list(profile1.api_keys.all()) == [api_key1]


def test_api_key_id_is_unique(api_key1, profile1):
    with pytest.raises(IntegrityError):
        APIKey.objects.create(
            profile=profile1,
            name="duplicate",
            key_id=api_key1.key_id,
            secret_hash="1" * 64,
        )


def test_api_key_deleted_with_profile(api_key1, profile1):
    profile1.delete()
    assert APIKey.objects.filter(pk=api_key1.pk).exists() is False


def test_usable_for_matches_is_usable(api_key1, profile1, profile2):
    """The queryset the caps count with has to agree with the per-row property."""

    now = timezone.now()
    live = APIKey.objects.create(
        profile=profile1,
        name="live",
        key_id="live00000001",
        secret_hash="1" * 64,
        expires_at=now + timedelta(days=1),
    )
    expired = APIKey.objects.create(
        profile=profile1,
        name="expired",
        key_id="expd00000001",
        secret_hash="2" * 64,
        expires_at=now - timedelta(days=1),
    )
    inactive = APIKey.objects.create(
        profile=profile1,
        name="inactive",
        key_id="inac00000001",
        secret_hash="3" * 64,
        is_active=False,
    )
    revoked = APIKey.objects.create(
        profile=profile1,
        name="revoked",
        key_id="revk00000001",
        secret_hash="4" * 64,
    )
    revoked.revoke("test")
    other = APIKey.objects.create(
        profile=profile2,
        name="other",
        key_id="othr00000001",
        secret_hash="5" * 64,
    )

    usable = set(APIKey.usable_for(profile1))
    # api_key1 has no expiry, so it is usable too
    assert usable == {api_key1, live}
    for key in (expired, inactive, revoked, other):
        assert key not in usable
    for key in (api_key1, live):
        assert key.is_usable is True
    for key in (expired, inactive, revoked):
        assert key.is_usable is False


def _fixed_key(key_id):
    """A `generate_api_key` stand-in that hands back a chosen key_id."""

    return key_id, hash_secret(f"secret-{key_id}"), f"mmd_local_{key_id}_secret-{key_id}"


def test_issue_retries_a_colliding_key_id(api_key1, profile1):
    """A key_id the unique constraint rejects is redrawn, not surfaced as a 500."""

    draws = [_fixed_key(api_key1.key_id), _fixed_key("fresh0000001")]
    with patch("api.models.base.generate_api_key", side_effect=draws) as generate:
        key, raw = APIKey.issue(
            profile=profile1,
            name="retried",
            expires_at=None,
            actor="tester",
        )

    assert generate.call_count == 2
    assert key.key_id == "fresh0000001"
    assert raw.endswith("_fresh0000001_secret-fresh0000001")
    assert APIKey.objects.filter(profile=profile1, name="retried").count() == 1
    # The failed insert was savepointed, so the enclosing transaction is still
    # usable: an unrolled-back IntegrityError would break this query.
    assert APIKey.objects.filter(key_id=api_key1.key_id).count() == 1


def test_issue_gives_up_after_the_attempt_ceiling(api_key1, profile1):
    """Retrying is defense in depth, not an unbounded loop."""

    draws = [_fixed_key(api_key1.key_id)] * KEY_ID_ISSUE_ATTEMPTS
    with patch("api.models.base.generate_api_key", side_effect=draws) as generate:
        with pytest.raises(IntegrityError):
            APIKey.issue(
                profile=profile1,
                name="doomed",
                expires_at=None,
                actor="tester",
            )

    assert generate.call_count == KEY_ID_ISSUE_ATTEMPTS
    assert APIKey.objects.filter(name="doomed").exists() is False


def test_issue_does_not_retry_an_unrelated_integrity_error(profile1):
    """Only a key_id clash is worth another draw; anything else fails the same
    way every time, so retrying it would just triple the latency of the 500."""

    with patch("api.models.base.generate_api_key", wraps=generate_api_key) as generate:
        with patch.object(
            APIKey.objects.__class__, "create", side_effect=IntegrityError("profile_id fkey")
        ):
            with pytest.raises(IntegrityError):
                APIKey.issue(
                    profile=profile1,
                    name="unrelated",
                    expires_at=None,
                    actor="tester",
                )

    assert generate.call_count == 1
