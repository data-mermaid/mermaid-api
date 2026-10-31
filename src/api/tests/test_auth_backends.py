from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from api.auth_backends import AnonymousJWTAuthentication, JWTAuthentication
from api.exceptions import Auth0ServiceUnavailable
from api.models.base import Profile
from api.utils.auth0utils import QueryStringTokenRejected


def test_validate_profile_stale_refresh_survives_auth0_outage(profile1):
    """A transient Auth0 failure during the >24h picture refresh must not 503
    an already-authenticated user; the cached profile is returned unchanged."""
    user_id = f"test|{profile1.email}"
    profile1.picture_url = "https://old.example/pic.png"
    profile1.save()
    # bypass auto_now to make the profile stale (>1 day)
    Profile.objects.filter(pk=profile1.pk).update(updated_on=timezone.now() - timedelta(days=2))

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


def _request(path="/v1/projects/", **extra):
    # DRF Request, as the backends see it at runtime
    return Request(APIRequestFactory().get(path, **extra))


@pytest.mark.parametrize("backend", [JWTAuthentication, AnonymousJWTAuthentication])
def test_jwt_in_query_string_is_rejected(backend, token1, profile1):
    """A token in the URL lands in ALB, nginx and Sentry logs: refuse it, even on
    public endpoints, so the client learns to move it to the header."""
    with pytest.raises(QueryStringTokenRejected):
        backend().authenticate(_request(f"/v1/projects/?access_token={token1}"))


def test_jwt_in_authorization_header_authenticates(token1, profile1):
    user, _ = JWTAuthentication().authenticate(_request(HTTP_AUTHORIZATION=f"Bearer {token1}"))

    assert user.profile == profile1


def test_header_wins_over_query_string(token1, profile1):
    user, _ = JWTAuthentication().authenticate(
        _request("/v1/projects/?access_token=junk", HTTP_AUTHORIZATION=f"Bearer {token1}")
    )

    assert user.profile == profile1


def test_malformed_header_with_query_token_is_rejected(token1, profile1):
    with pytest.raises(exceptions.AuthenticationFailed, match="should not contain spaces"):
        JWTAuthentication().authenticate(
            _request(f"/v1/projects/?access_token={token1}", HTTP_AUTHORIZATION="Bearer a b")
        )


@pytest.mark.parametrize("path", ["/v1/me/", "/v1/projects/"])
def test_query_string_token_gets_401_over_http(path, api_client_public, token1, profile1):
    """/v1/me/ needs a login; /v1/projects/ GET is public (AnonymousJWTAuthentication)."""
    response = api_client_public.get(f"{path}?access_token={token1}")

    assert response.status_code == 401
    assert "Authorization header" in response.json()["detail"]
