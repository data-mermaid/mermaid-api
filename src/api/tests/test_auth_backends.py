from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from api.auth_backends import JWTAuthentication
from api.exceptions import Auth0ServiceUnavailable
from api.models.base import Profile


def test_validate_profile_stale_refresh_survives_auth0_outage(profile1):
    """A transient Auth0 failure during the >24h picture refresh must not 503
    an already-authenticated user; the cached profile is returned unchanged."""
    user_id = f"test|{profile1.email}"
    profile1.picture_url = "https://old.example/pic.png"
    profile1.save()
    # bypass auto_now to make the profile stale (>1 day)
    Profile.objects.filter(pk=profile1.pk).update(
        updated_on=timezone.now() - timedelta(days=2)
    )

    with patch(
        "api.auth_backends.get_user_info", side_effect=Auth0ServiceUnavailable()
    ) as mock_info:
        result = JWTAuthentication()._validate_profile({"sub": user_id})

    mock_info.assert_called_once_with(user_id)
    assert result.pk == profile1.pk
    profile1.refresh_from_db()
    assert profile1.picture_url == "https://old.example/pic.png"
    # updated_on bumped so the next request backs off instead of re-failing
    assert (timezone.now() - profile1.updated_on).total_seconds() < 60
