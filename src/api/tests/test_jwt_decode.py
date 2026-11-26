"""Token decoding in api.utils.auth0utils (PyJWT, replacing python-jose; card 2263).

RS256 tokens are signed with a throwaway RSA key and the JWKS fetch is stubbed,
so these run offline.
"""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from api.utils import auth0utils, tokenutils

KID = "test-kid"
AUDIENCE = "spa-client-id"
DOMAIN = "tenant.example.auth0.com"


@pytest.fixture
def rsa_key(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update(kid=KID, use="sig")
    monkeypatch.setattr(auth0utils, "get_jwks", lambda: {KID: jwk})
    # auth0utils reads `from app import settings`, so patch that module.
    monkeypatch.setattr(auth0utils.settings, "SPA_ADMIN_CLIENT_ID", AUDIENCE)
    monkeypatch.setattr(auth0utils.settings, "AUTH0_DOMAIN", DOMAIN)
    return key


def _rs256(key, kid=KID, **claims):
    payload = {
        "sub": "auth0|abc",
        "aud": AUDIENCE,
        "iss": f"https://{DOMAIN}/",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        **claims,
    }
    payload = {k: v for k, v in payload.items() if v is not None}  # None drops a claim
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": kid})


def test_decode_rsa_valid(rsa_key):
    assert auth0utils.decode(_rs256(rsa_key))["sub"] == "auth0|abc"


def test_decode_rsa_expired(rsa_key):
    with pytest.raises(AuthenticationFailed, match="token is expired"):
        auth0utils.decode_rsa(_rs256(rsa_key, exp=int(time.time()) - 10))


@pytest.mark.parametrize(
    "claims",
    [{"aud": "someone-else"}, {"iss": "https://evil.example.com/"}, {"aud": None}],
    ids=["wrong-aud", "wrong-iss", "missing-aud"],
)
def test_decode_rsa_bad_claims(rsa_key, claims):
    with pytest.raises(AuthenticationFailed, match="incorrect claims"):
        auth0utils.decode_rsa(_rs256(rsa_key, **claims))


def test_decode_rsa_wrong_signing_key(rsa_key):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(ValidationError):
        auth0utils.decode_rsa(_rs256(other))


def test_decode_rsa_unknown_kid(rsa_key):
    with pytest.raises(ValidationError):
        auth0utils.decode_rsa(_rs256(rsa_key, kid="nope"))


def test_decode_rsa_rejects_hs256_signed_with_public_key(rsa_key):
    # Classic alg confusion: an HS256 token keyed with the RSA public key must fail.
    # PyJWT refuses to mint this, so sign it by hand the way an attacker would.
    pub = jwt.algorithms.RSAAlgorithm.to_jwk(rsa_key.public_key()).encode()

    def b64(raw):
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    body = b64(json.dumps({"sub": "auth0|abc", "aud": AUDIENCE}).encode())
    sig = b64(hmac.new(pub, header + b"." + body, hashlib.sha256).digest())
    token = b".".join([header, body, sig])
    with pytest.raises(ValidationError):
        auth0utils.decode_rsa(token)


def test_hs256_roundtrip():
    token = tokenutils.create_token("auth0|abc")
    assert auth0utils.get_token_algorithm(token) == "HS256"
    assert auth0utils.is_hs_token(token) is True
    assert auth0utils.decode_hs(token)["sub"] == "auth0|abc"


def test_decode_hs_bad_signature():
    token = jwt.encode(
        {"sub": "auth0|abc", "aud": auth0utils.settings.MERMAID_API_AUDIENCE},
        "not-the-signing-secret-but-long-enough-for-hmac",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationFailed):
        auth0utils.decode_hs(token)


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c", b"not.a.jwt"])
def test_is_hs_token_rejects_malformed(token):
    assert auth0utils.is_hs_token(token) is False


@pytest.mark.django_db
def test_get_unverified_profile_ignores_expiry_and_signature(profile1, token1):
    # MockRequest relies on this: it reads the profile from a token it minted itself.
    assert auth0utils.get_unverified_profile(token1) == profile1
    expired = jwt.encode(
        {"sub": profile1.authusers.first().user_id, "exp": int(time.time()) - 10},
        "some-other-key-that-is-long-enough",
        algorithm="HS256",
    )
    assert auth0utils.get_unverified_profile(expired) == profile1
