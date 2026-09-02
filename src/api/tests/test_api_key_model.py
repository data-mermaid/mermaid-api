import pytest

from api.models import APIKey


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
    from django.db import IntegrityError

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
