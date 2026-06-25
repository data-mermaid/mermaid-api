from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from api.auth_backends import JWTAuthentication
from api.exceptions import Auth0ServiceUnavailable
from api.models.base import AuthUser, Profile


@pytest.mark.django_db
def test_validate_profile_stale_refresh_survives_auth0_outage():
    """A transient Auth0 failure during the >24h picture refresh must not 503
    an already-authenticated user; the cached profile is returned unchanged."""
    user_id = "auth0|stale-refresh"
    profile = Profile.objects.create(
        email="stale@example.com", picture_url="https://old.example/pic.png"
    )
    AuthUser.objects.create(profile=profile, user_id=user_id)
    # bypass auto_now to make the profile stale (>1 day)
    Profile.objects.filter(pk=profile.pk).update(
        updated_on=timezone.now() - timedelta(days=2)
    )

    with patch(
        "api.auth_backends.get_user_info", side_effect=Auth0ServiceUnavailable()
    ) as mock_info:
        result = JWTAuthentication()._validate_profile({"sub": user_id})

    mock_info.assert_called_once_with(user_id)
    assert result.pk == profile.pk
    profile.refresh_from_db()
    assert profile.picture_url == "https://old.example/pic.png"
