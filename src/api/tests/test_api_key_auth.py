from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from api.auth_backends import (
    AnonymousJWTAuthentication,
    APIKeyAuthentication,
    JWTAuthentication,
)
from api.models import APIKey
from api.utils.apikeys import generate_api_key

factory = APIRequestFactory()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def key_pair(profile1):
    """An active, unexpired key and the raw token for it."""

    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile1,
        name="reporting bot",
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=timezone.now() + timedelta(days=365),
    )
    return key, raw


def _request(raw=None, header=None, path="/v1/projects/", **extra):
    if header is None and raw is not None:
        header = f"Bearer {raw}"
    if header is not None:
        extra["HTTP_AUTHORIZATION"] = header
    # DRF Request, as the backends see it at runtime
    return Request(factory.get(path, **extra))


def _authenticate(raw=None, header=None, **extra):
    return APIKeyAuthentication().authenticate(_request(raw=raw, header=header, **extra))


def test_valid_key_authenticates(key_pair, profile1):
    key, raw = key_pair
    user, auth = _authenticate(raw)

    assert user.profile == profile1
    assert isinstance(auth, APIKey)
    assert auth.pk == key.pk


@pytest.mark.parametrize(
    "header",
    [
        pytest.param("", id="no_header"),
        pytest.param("Basic dXNlcjpwYXNz", id="other_scheme"),
        pytest.param("Bearer eyJhbGciOiJIUzI1NiJ9.e30.sig", id="jwt"),
        pytest.param("Bearer not-a-key", id="unprefixed"),
        pytest.param("ApiKey mmd_local_aaaaaaaaaaaa_secret", id="old_apikey_scheme"),
    ],
)
def test_credential_that_is_not_ours_falls_through(header):
    """Only a `Bearer mmd_...` credential is ours; the rest go to the next backend."""

    assert _authenticate(header=header) is None


def test_jwt_backend_leaves_api_keys_alone(key_pair):
    """Both share `Bearer`, and JWTAuthentication runs first, so it has to pass."""

    _, raw = key_pair
    assert JWTAuthentication().authenticate(_request(raw)) is None


@pytest.mark.parametrize(
    "mangle",
    [
        pytest.param(lambda raw: raw + "x", id="wrong_secret"),
        pytest.param(lambda raw: "mmd_local_aaaaaaaaaaaa_nope", id="unknown_key_id"),
        pytest.param(lambda raw: "mmd_local_short_secret", id="bad_key_id_length"),
        pytest.param(lambda raw: "mmd_nonsense", id="prefix_only"),
        pytest.param(lambda raw: raw.replace("_local_", "_prod_", 1), id="wrong_environment"),
    ],
)
def test_bad_key_is_401(key_pair, mangle):
    _, raw = key_pair
    with pytest.raises(exceptions.AuthenticationFailed):
        _authenticate(mangle(raw))


@pytest.mark.parametrize(
    "header",
    [
        pytest.param("Bearer {raw} extra", id="trailing_junk"),
        pytest.param("Bearer", id="no_credential"),
    ],
)
def test_malformed_header_is_not_a_key(key_pair, header):
    """Not parseable as a bearer credential, so not ours to claim.

    JWTAuthentication runs first and rejects these outright, which is what
    turns them into a 401.
    """

    _, raw = key_pair
    header = header.format(raw=raw)

    assert _authenticate(header=header) is None
    with pytest.raises(exceptions.AuthenticationFailed):
        JWTAuthentication().authenticate(_request(header=header))


@pytest.mark.parametrize(
    "update",
    [
        pytest.param({"is_active": False}, id="inactive"),
        pytest.param({"revoked_at": timezone.now()}, id="revoked"),
        pytest.param({"expires_at": timezone.now() - timedelta(seconds=1)}, id="expired"),
    ],
)
def test_unusable_key_is_401(key_pair, update):
    key, raw = key_pair
    APIKey.objects.filter(pk=key.pk).update(**update)

    with pytest.raises(exceptions.AuthenticationFailed):
        _authenticate(raw)


def test_key_without_expiry_still_authenticates(key_pair, profile1):
    """expires_at=None means never; the one-year default must not be implied."""

    key, raw = key_pair
    APIKey.objects.filter(pk=key.pk).update(
        expires_at=None, created_on=timezone.now() - timedelta(days=800)
    )

    user, _ = _authenticate(raw)
    assert user.profile == profile1


def test_key_in_query_string_is_ignored(key_pair):
    """A key in the URL would land in nginx, ALB and Sentry logs."""

    _, raw = key_pair
    assert (
        APIKeyAuthentication().authenticate(_request(path=f"/v1/projects/?api_key={raw}")) is None
    )
    assert (
        APIKeyAuthentication().authenticate(_request(path=f"/v1/projects/?access_token={raw}"))
        is None
    )


def test_secret_comparison_is_constant_time(key_pair):
    _, raw = key_pair
    with patch("api.utils.apikeys.hmac.compare_digest", return_value=True) as mock_compare:
        _authenticate(raw)
    mock_compare.assert_called_once()


def test_last_used_is_throttled(key_pair):
    key, raw = key_pair
    _authenticate(raw, REMOTE_ADDR="10.0.0.1")

    key.refresh_from_db()
    first_used = key.last_used_at
    assert first_used is not None
    assert key.last_used_ip == "10.0.0.1"

    # same throttle window: no second write
    _authenticate(raw, REMOTE_ADDR="10.0.0.2")
    key.refresh_from_db()
    assert key.last_used_at == first_used
    assert key.last_used_ip == "10.0.0.1"

    # window expired
    cache.clear()
    _authenticate(raw, REMOTE_ADDR="10.0.0.2")
    key.refresh_from_db()
    assert key.last_used_at > first_used
    assert key.last_used_ip == "10.0.0.2"


def test_last_used_write_does_not_touch_updated_on(key_pair):
    key, raw = key_pair
    updated_on = key.updated_on

    _authenticate(raw)

    key.refresh_from_db()
    assert key.updated_on == updated_on


def test_failed_auth_is_logged_without_the_secret(key_pair, caplog):
    _, raw = key_pair
    with pytest.raises(exceptions.AuthenticationFailed):
        _authenticate(raw + "x")

    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "[apikey.failed_auth]" in logged
    assert "reason=bad_secret" in logged
    assert raw not in logged
    assert raw.rsplit("_", 1)[-1] not in logged


def test_anonymous_backend_fails_closed_on_bad_key(key_pair):
    """A public endpoint must 401 a bad key, not serve public data anonymously."""

    _, raw = key_pair
    with pytest.raises(exceptions.AuthenticationFailed):
        AnonymousJWTAuthentication().authenticate(_request(raw + "x"))


def test_anonymous_backend_accepts_valid_key(key_pair, profile1):
    _, raw = key_pair
    user, auth = AnonymousJWTAuthentication().authenticate(_request(raw))

    assert user.profile == profile1
    assert isinstance(auth, APIKey)


def test_anonymous_backend_still_allows_anonymous(key_pair):
    user, auth = AnonymousJWTAuthentication().authenticate(_request())

    assert user.is_anonymous
    assert auth is None
