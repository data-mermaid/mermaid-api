"""C8: rejected API keys are counted, and a caller past the limit gets 429.

A 256-bit secret is not guessable, so the point of the limit is not to stop a
brute force from succeeding. It is to stop a client with a bad credential from
spending a database lookup and a hash on every retry, and to make the attempt
visible instead of drowning the log.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from api.auth_backends import APIKeyAuthentication
from api.models import APIKey
from api.utils.apikeys import generate_api_key
from api.utils.ratelimit import FailureRateLimiter

factory = APIRequestFactory()

LIMIT = APIKeyAuthentication.failure_limiter.limit


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def frozen_window():
    """Pin the window so a test that straddles a wall-clock minute cannot flake."""

    with patch("api.utils.ratelimit.time.time", return_value=1_800_000_000.0):
        yield


@pytest.fixture
def key_pair(profile1):
    key_id, secret_hash, raw = generate_api_key()
    key = APIKey.objects.create(
        profile=profile1,
        name="reporting bot",
        key_id=key_id,
        secret_hash=secret_hash,
        expires_at=timezone.now() + timedelta(days=365),
    )
    return key, raw


def _authenticate(raw, ip="10.0.0.1"):
    request = Request(factory.get("/v1/projects/", REMOTE_ADDR=ip))
    request.META["HTTP_AUTHORIZATION"] = f"Bearer {raw}"
    return APIKeyAuthentication().authenticate(request)


def _fail_n(raw, n, ip="10.0.0.1"):
    """Present a bad key `n` times, expecting a 401 each time."""

    for _ in range(n):
        with pytest.raises(exceptions.AuthenticationFailed):
            _authenticate(raw, ip=ip)


# ── the limiter itself ───────────────────────────────────────────────


def test_limiter_blocks_at_the_limit():
    limiter = FailureRateLimiter("test", limit=3, window=60)

    for expected in (1, 2, 3):
        assert limiter.retry_after("ip", "1.2.3.4") is None
        assert limiter.record_failure("ip", "1.2.3.4") == expected

    wait = limiter.retry_after("ip", "1.2.3.4")
    assert wait is not None
    assert 0 < wait <= 60


def test_limiter_separates_identifiers_and_scopes():
    limiter = FailureRateLimiter("test", limit=1, window=60)
    limiter.record_failure("ip", "1.2.3.4")

    assert limiter.retry_after("ip", "1.2.3.4") is not None
    assert limiter.retry_after("ip", "5.6.7.8") is None
    # A value that could appear as either kind must not pool its failures.
    assert limiter.retry_after("key_id", "1.2.3.4") is None


def test_limiter_window_rolls_over():
    limiter = FailureRateLimiter("test", limit=1, window=60)
    with patch("api.utils.ratelimit.time.time", return_value=1_800_000_000.0):
        limiter.record_failure("ip", "1.2.3.4")
        assert limiter.retry_after("ip", "1.2.3.4") is not None

    with patch("api.utils.ratelimit.time.time", return_value=1_800_000_060.0):
        assert limiter.retry_after("ip", "1.2.3.4") is None


def test_limiter_reset_clears_the_count():
    limiter = FailureRateLimiter("test", limit=1, window=60)
    limiter.record_failure("ip", "1.2.3.4")
    limiter.reset("ip", "1.2.3.4")

    assert limiter.retry_after("ip", "1.2.3.4") is None


# ── the backend ──────────────────────────────────────────────────────


def test_ip_is_throttled_after_the_limit(key_pair):
    _, raw = key_pair
    _fail_n(raw + "x", LIMIT)

    with pytest.raises(exceptions.Throttled) as excinfo:
        _authenticate(raw + "x")
    assert excinfo.value.wait is not None


def test_throttled_ip_is_throttled_even_with_a_good_key(key_pair):
    """The check runs before the lookup, so being over the limit costs the
    caller the rest of the minute whatever they present next."""

    _, raw = key_pair
    _fail_n(raw + "x", LIMIT)

    with pytest.raises(exceptions.Throttled):
        _authenticate(raw)


def test_other_ips_are_unaffected(key_pair, profile1):
    """The failures come from an unknown key id, so only the address is over
    the limit; the good key still works from anywhere else."""

    _, raw = key_pair
    _fail_n("mmd_local_aaaaaaaaaaaa_nope", LIMIT, ip="10.0.0.1")

    user, auth = _authenticate(raw, ip="10.0.0.2")
    assert user.profile == profile1
    assert isinstance(auth, APIKey)


def test_key_id_is_throttled_across_ips(key_pair):
    """One bad key rotating through hosts is one incident, so the key id is
    counted separately from the address that presented it."""

    _, raw = key_pair
    for i in range(LIMIT):
        _fail_n(raw + "x", 1, ip=f"10.1.0.{i}")

    # A fresh address, so only the key_id counter can be over the limit.
    with pytest.raises(exceptions.Throttled):
        _authenticate(raw, ip="10.1.1.1")


def test_malformed_keys_count_against_the_ip(key_pair):
    """A key too mangled to name a key_id can only be counted against the IP."""

    _, raw = key_pair
    _fail_n("mmd_not-a-key", LIMIT)

    with pytest.raises(exceptions.Throttled):
        _authenticate(raw)


def test_successful_requests_are_not_throttled(key_pair, profile1):
    _, raw = key_pair
    for _ in range(LIMIT + 5):
        user, _auth = _authenticate(raw)
        assert user.profile == profile1


def test_throttling_is_logged_without_the_secret(key_pair, caplog):
    _, raw = key_pair
    _fail_n(raw + "x", LIMIT)
    caplog.clear()

    with pytest.raises(exceptions.Throttled):
        _authenticate(raw + "x")

    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "[apikey.rate_limited]" in logged
    assert "scope=ip" in logged
    assert raw.rsplit("_", 1)[-1] not in logged


def test_throttled_request_returns_429(db, key_pair):
    """End to end: an exception raised in an authentication class still has to
    come back as a 429 with Retry-After, not a 500."""

    _, raw = key_pair
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}x")
    url = reverse("project-list")

    for _ in range(LIMIT):
        assert client.get(url).status_code == 401

    response = client.get(url)
    assert response.status_code == 429
    assert response.has_header("Retry-After")
