import hashlib
import uuid

import pytest
from django.core.exceptions import ImproperlyConfigured

from api.utils.apikeys import (
    generate_api_key,
    get_environment_label,
    hash_secret,
    looks_like_api_key,
    parse_api_key,
    secret_matches,
)


def test_generate_round_trips_through_parse():
    key_id, secret_hash, raw = generate_api_key("prod")
    env, parsed_id, secret = parse_api_key(raw)

    assert env == "prod"
    assert parsed_id == str(key_id)
    assert isinstance(key_id, uuid.UUID)
    assert secret_matches(secret, secret_hash)


def test_generated_key_id_has_no_underscore():
    """An underscore in key_id would make the token ambiguous to parse."""

    for _ in range(50):
        key_id, _hash, raw = generate_api_key("prod")
        assert "_" not in str(key_id)
        assert parse_api_key(raw)[1] == str(key_id)


def test_secret_is_not_recoverable_from_the_stored_value():
    _key_id, secret_hash, raw = generate_api_key("prod")
    secret = parse_api_key(raw)[2]

    assert secret not in secret_hash
    assert secret_hash == hashlib.sha256(secret.encode()).hexdigest()
    assert len(secret_hash) == 64


def test_secrets_are_unique():
    raws = {generate_api_key("prod")[2] for _ in range(100)}
    assert len(raws) == 100


def test_secret_matches_rejects_wrong_secret():
    _key_id, secret_hash, raw = generate_api_key("prod")
    secret = parse_api_key(raw)[2]

    assert secret_matches(secret, secret_hash) is True
    assert secret_matches(secret + "x", secret_hash) is False
    assert secret_matches("", secret_hash) is False


def test_secret_with_underscores_survives_parsing():
    """token_urlsafe emits "_", so the split has to stop after the key id."""

    raw = "mmd_prod_0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11_aa_bb_cc"
    env, key_id, secret = parse_api_key(raw)

    assert (env, key_id, secret) == ("prod", "0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11", "aa_bb_cc")
    assert hash_secret(secret) == hashlib.sha256(b"aa_bb_cc").hexdigest()


@pytest.mark.parametrize(
    "raw",
    [
        "",
        None,
        "mmd_prod_0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11",
        "mmd_prod__secret",
        "xxx_prod_0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11_secret",
        "mmd__0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11_secret",
        "mmd_prod_short_secret",
        "mmd_prod_0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a110_secret",
        # the hex form and upper case are valid UUIDs but not the canonical
        # form the pk is issued in
        "mmd_prod_0b6f0f8e4a524f0c9d432f8f2d6c1a11_secret",
        "mmd_prod_0B6F0F8E-4A52-4F0C-9D43-2F8F2D6C1A11_secret",
        b"mmd_prod_0b6f0f8e-4a52-4f0c-9d43-2f8f2d6c1a11_secret",
    ],
)
def test_parse_rejects_bad_shapes(raw):
    with pytest.raises(ValueError):
        parse_api_key(raw)


@pytest.mark.parametrize("environment", ["prod", "dev", "local"])
def test_environment_used_verbatim(environment):
    assert get_environment_label(environment) == environment


def test_unknown_environment_is_rejected():
    with pytest.raises(ImproperlyConfigured):
        get_environment_label("staging")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("mmd_prod_abc123def456_secret", True),
        # claimed on the prefix alone, so a bad key 401s instead of being
        # handed to the JWT decoder
        ("mmd_", True),
        ("mmd_garbage", True),
        ("eyJhbGciOiJIUzI1NiJ9.e30.sig", False),
        ("mmd", False),
        ("Mmd_prod_abc123def456_secret", False),
        ("", False),
        (None, False),
        (b"mmd_prod_abc123def456_secret", False),
    ],
)
def test_looks_like_api_key(raw, expected):
    assert looks_like_api_key(raw) is expected
