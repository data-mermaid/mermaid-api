"""Generation and parsing of MERMAID API keys.

A key is presented to the API as::

    mmd_<env>_<key_id>_<secret>

It travels in ``Authorization: Bearer <key>``, the same scheme as an Auth0
access token; the ``mmd_`` prefix is what tells the two apart.

``key_id`` identifies the ``APIKey`` row and is safe to log. ``secret`` is 256
bits of CSPRNG output; only its SHA-256 digest is stored. A plain, unsalted
digest is used deliberately: the secret has enough entropy that a slow password
hash would add latency to every request without making guessing any less
impossible. See the "Hash, do not encrypt" decision in the API key plan.
"""

import hashlib
import hmac
import logging
import re
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

# Issuing and retiring a credential is an audit trail, not debug chatter, so it
# is logged at INFO through a logger of its own. settings.LOGGING keeps the
# `api` logger and its console handler at WARNING in production, which would
# otherwise drop every one of these lines (C8).
AUDIT_LOGGER_NAME = "api.apikeys"
audit_logger = logging.getLogger(AUDIT_LOGGER_NAME)

PREFIX = "mmd"
KEY_ID_LENGTH = 12
SECRET_BYTES = 32
# key_id must not contain "_": the token is split on underscores, and the secret
# (url-safe base64) may contain them, so only the id has to stay unambiguous.
KEY_ID_ALPHABET = string.ascii_letters + string.digits
KEY_ID_RE = re.compile(rf"^[A-Za-z0-9]{{{KEY_ID_LENGTH}}}$")

# settings.ENVIRONMENT goes into the key verbatim. It is validated because ENV
# is free text (settings.ENVIRONMENT = os.environ.get("ENV") or "local"): a typo
# would mint keys under a label that stops verifying once the typo is fixed.
ENVIRONMENTS = ("local", "dev", "prod")

# A key with no expiry is a credential nobody has to think about again, so it
# is an explicit choice at creation. Everything that omits an expiry gets this
# lifetime instead.
DEFAULT_LIFETIME_DAYS = 365


def default_expires_at(now=None):
    """Expiry for a key whose creator did not choose one."""

    now = now or timezone.now()
    return now + timedelta(days=DEFAULT_LIFETIME_DAYS)


def get_environment_label(environment=None):
    """Return the environment label for a key, rejecting unknown values."""

    environment = environment if environment is not None else settings.ENVIRONMENT
    if environment not in ENVIRONMENTS:
        raise ImproperlyConfigured(
            f"Cannot issue or verify API keys: unknown ENVIRONMENT {environment!r}. "
            f"Expected one of {', '.join(ENVIRONMENTS)}."
        )
    return environment


def hash_secret(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def secret_matches(secret, secret_hash):
    """Constant-time comparison, so a wrong secret leaks no timing signal."""

    return hmac.compare_digest(hash_secret(secret), secret_hash)


def generate_api_key(env=None):
    """Return ``(key_id, secret_hash, raw_key)``. The raw key is never stored."""

    env = env if env is not None else get_environment_label()
    key_id = "".join(secrets.choice(KEY_ID_ALPHABET) for _ in range(KEY_ID_LENGTH))
    secret = secrets.token_urlsafe(SECRET_BYTES)
    raw = f"{PREFIX}_{env}_{key_id}_{secret}"
    return key_id, hash_secret(secret), raw


def log_key_created(key, actor, replaces=None):
    """Audit line for a minted credential (C8).

    The counterpart of `APIKey.revoke`'s line. Together they answer "which
    credentials existed, for whom, and for how long" from the logs alone. The
    raw key and the hash are never part of it.
    """

    audit_logger.info(
        "[apikey.created] key_id=%s profile=%s actor=%s expires_at=%s replaces=%s",
        key.key_id,
        key.profile_id,
        actor,
        key.expires_at.isoformat() if key.expires_at else "never",
        replaces.key_id if replaces else "none",
    )


def looks_like_api_key(raw):
    """True when a bearer credential is a MERMAID API key rather than a JWT.

    The prefix is the whole discriminator between the two credentials that
    share the `Bearer` scheme. It only claims the token for the API key
    backend; whether the rest of it is well formed is `parse_api_key`'s job,
    and a token claimed here fails closed rather than falling through to JWT.
    """

    return isinstance(raw, str) and raw.startswith(f"{PREFIX}_")


def parse_api_key(raw):
    """Return ``(env, key_id, secret)``, raising ``ValueError`` on a bad shape.

    The secret may itself contain no underscores (``token_urlsafe`` emits
    ``-`` and ``_``), so the split is bounded and the remainder is the secret.
    """

    if not raw or not isinstance(raw, str):
        raise ValueError("empty API key")

    parts = raw.split("_", 3)
    if len(parts) != 4:
        raise ValueError("malformed API key")

    prefix, env, key_id, secret = parts
    if prefix != PREFIX:
        raise ValueError("malformed API key")
    if not env or not key_id or not secret:
        raise ValueError("malformed API key")
    if not KEY_ID_RE.match(key_id):
        raise ValueError("malformed API key")

    return env, key_id, secret
