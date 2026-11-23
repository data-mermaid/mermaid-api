"""
Regression test for Trello card 2238.

PATCH /v1/me/ let a user change their own email with no confirmation and no ownership
check. Email now is read-only on the endpoint; other fields still update.

Note: this closes the self-service email-change route. The deeper account-takeover
chain (Auth0 identity auto-linked to an existing profile by email with no
email_verified check, auth_backends/auth0utils.get_user_info) is a separate,
auth-tenant-validated change and is flagged on the card, not included here.
"""

from unittest.mock import patch

from api.models import Profile


@patch("api.resources.me.MeViewSet._sync_auth0_metadata")
def test_patch_me_cannot_change_email(_sync, db_setup, api_client1, profile1):
    original = profile1.email
    response = api_client1.patch(
        "/v1/me/",
        {"email": "attacker@evil.example", "first_name": "Zed"},
        format="json",
    )
    assert response.status_code == 200
    profile1.refresh_from_db()
    assert profile1.email == original
    # A non-PII, editable field still changes.
    assert profile1.first_name == "Zed"


@patch("api.resources.me.MeViewSet._sync_auth0_metadata")
def test_me_response_never_echoes_submitted_email(_sync, db_setup, api_client1, profile1):
    response = api_client1.patch("/v1/me/", {"email": "attacker@evil.example"}, format="json")
    assert response.status_code == 200
    assert response.json()["email"] == profile1.email
    assert Profile.objects.filter(email="attacker@evil.example").exists() is False
