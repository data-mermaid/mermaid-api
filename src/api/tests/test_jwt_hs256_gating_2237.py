"""
Regression tests for Trello card 2237.

decode() picks the verification algorithm from the token's own header. An HS256 token
is verified with the symmetric MERMAID_API_SIGNING_SECRET, which is only meant for
local/CI test tokens. On a deployed environment that lets a leaked secret forge any
identity. HS256 is now accepted only where ALLOW_HS256_TOKENS is true (non dev/prod).
"""

import pytest
from rest_framework.exceptions import AuthenticationFailed

from api.utils import auth0utils, tokenutils

# auth0utils reads `from app import settings`, so override the module attribute, not
# django.conf.settings (the pytest `settings` fixture would not reach it).


def test_hs256_accepted_when_allowed(db, monkeypatch):
    monkeypatch.setattr("app.settings.ALLOW_HS256_TOKENS", True)
    token = tokenutils.create_token("auth0|victim")
    payload = auth0utils.decode(token)
    assert payload["sub"] == "auth0|victim"


def test_hs256_rejected_when_not_allowed(db, monkeypatch):
    # Simulate a deployed environment.
    monkeypatch.setattr("app.settings.ALLOW_HS256_TOKENS", False)
    token = tokenutils.create_token("auth0|victim")
    with pytest.raises(AuthenticationFailed):
        auth0utils.decode(token)
