import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from api.models import APIKey
from api.utils.apikeys import parse_api_key


@pytest.fixture
def api_key1(profile1):
    key = APIKey.objects.create(
        profile=profile1,
        name="reporting bot",
        id=uuid.UUID("0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11"),
        secret_hash="0" * 64,
    )
    return key


def test_api_key_str_does_not_leak_hash(api_key1):
    assert str(api_key1) == "reporting bot [0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11]"
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


def test_api_key_deleted_with_profile(api_key1, profile1):
    profile1.delete()
    assert APIKey.objects.filter(pk=api_key1.pk).exists() is False


def test_usable_for_matches_is_usable(api_key1, profile1, profile2):
    """The queryset the caps count with has to agree with the per-row property."""

    now = timezone.now()
    live = APIKey.objects.create(
        profile=profile1,
        name="live",
        secret_hash="1" * 64,
        expires_at=now + timedelta(days=1),
    )
    expired = APIKey.objects.create(
        profile=profile1,
        name="expired",
        secret_hash="2" * 64,
        expires_at=now - timedelta(days=1),
    )
    inactive = APIKey.objects.create(
        profile=profile1,
        name="inactive",
        secret_hash="3" * 64,
        is_active=False,
    )
    revoked = APIKey.objects.create(
        profile=profile1,
        name="revoked",
        secret_hash="4" * 64,
    )
    revoked.revoke("test")
    other = APIKey.objects.create(
        profile=profile2,
        name="other",
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


def test_issue_uses_the_key_id_as_the_primary_key(profile1):
    """The id in the raw key is the row's pk, so the backend can look it up directly."""

    key, raw = APIKey.issue(profile=profile1, name="issued", expires_at=None, actor="tester")

    assert parse_api_key(raw)[1] == str(key.pk)
    assert APIKey.objects.get(pk=parse_api_key(raw)[1]) == key
