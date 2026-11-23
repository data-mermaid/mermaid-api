"""
Regression test for Trello card 2242.

With CORS_ALLOW_CREDENTIALS = True, reflecting any Origin let any website make
cookie-carrying cross-origin requests and read the responses. CORS_ALLOW_ALL_ORIGINS
is now tied to the environment: off on dev/prod (use CORS_ALLOWED_ORIGINS allow-list),
on only for local development.
"""

from django.conf import settings

from app.settings import ENVIRONMENT


def test_cors_allow_all_is_off_on_deployed_environments():
    # allow-all must follow the environment: True only outside dev/prod.
    expected = ENVIRONMENT not in ("dev", "prod")
    assert settings.CORS_ALLOW_ALL_ORIGINS is expected


def test_credentials_allowed_requires_an_allowlist_type():
    assert settings.CORS_ALLOW_CREDENTIALS is True
    # CORS_ALLOWED_ORIGINS is the explicit allow-list used when allow-all is off.
    assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
