import hashlib

import pytest
from django.core.exceptions import ImproperlyConfigured

from api.checks import check_api_key_environment
from api.utils.apikeys import (
    KEY_ID_LENGTH,
    generate_api_key,
    get_environment_label,
    hash_secret,
    parse_api_key,
    secret_matches,
)


def test_generate_round_trips_through_parse():
    key_id, secret_hash, raw = generate_api_key("prod")
    env, parsed_id, secret = parse_api_key(raw)

    assert env == "prod"
    assert parsed_id == key_id
    assert len(key_id) == KEY_ID_LENGTH
    assert secret_matches(secret, secret_hash)


def test_generated_key_id_has_no_underscore():
    """An underscore in key_id would make the token ambiguous to parse."""

    for _ in range(50):
        key_id, _hash, raw = generate_api_key("prod")
        assert "_" not in key_id
        assert parse_api_key(raw)[1] == key_id


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

    raw = "mmd_prod_abc123def456_aa_bb_cc"
    env, key_id, secret = parse_api_key(raw)

    assert (env, key_id, secret) == ("prod", "abc123def456", "aa_bb_cc")
    assert hash_secret(secret) == hashlib.sha256(b"aa_bb_cc").hexdigest()


@pytest.mark.parametrize(
    "raw",
    [
        "",
        None,
        "mmd_prod_abc123def456",
        "mmd_prod__secret",
        "xxx_prod_abc123def456_secret",
        "mmd__abc123def456_secret",
        "mmd_prod_short_secret",
        "mmd_prod_waytoolongkeyid_secret",
        b"mmd_prod_abc123def456_secret",
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


def test_startup_check_passes_for_a_known_environment(settings):
    settings.ENVIRONMENT = "prod"
    assert check_api_key_environment(None) == []


def test_startup_check_flags_an_unknown_environment(settings):
    """ENV is free text, so a typo would mint keys under a label that stops
    verifying the moment the typo is fixed. The check catches it at startup."""

    settings.ENVIRONMENT = "produciton"
    errors = check_api_key_environment(None)

    assert [error.id for error in errors] == ["api.E001"]
    assert "produciton" in errors[0].msg
