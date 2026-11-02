from unittest.mock import patch

import pytest
from django.urls import reverse

from api.models import Profile, ProjectProfile
from api.utils import normalize_email

WJ = "⁠"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (f"{WJ}user@gmail.com", "user@gmail.com"),
        (f"{WJ}{WJ}{WJ}user@gmail.com", "user@gmail.com"),
        ("​user@gmail.com﻿", "user@gmail.com"),
        ("  user@gmail.com \n", "user@gmail.com"),
        ("user＠gmail.com", "user@gmail.com"),  # full-width @
        ("User@Example.org", "User@Example.org"),  # case preserved
        ("françois@blueventures.org", "françois@blueventures.org"),
        ("e\u200d\u0301@x.com", "\u00e9@x.com"),  # recomposed after stripping ZWJ
        ("\u00b4x@y.com", "\u0301x@y.com"),  # NFKC-introduced space is stripped
        (None, None),
    ],
)
def test_normalize_email(raw, expected):
    assert normalize_email(raw) == expected


@pytest.mark.parametrize(
    "raw", ["e\u200d\u0301@x.com", f"{WJ}user@gmail.com", "user\uff20gmail.com", "a\u00a0b@x.com"]
)
def test_normalize_email_is_idempotent(raw):
    once = normalize_email(raw)
    assert normalize_email(once) == once


def test_profile_save_normalizes_email(db):
    profile = Profile.objects.create(email=f"{WJ}saved@test.com")
    assert profile.email == "saved@test.com"
    profile.refresh_from_db()
    assert profile.email == "saved@test.com"


def test_profile_save_normalizes_changed_email(db):
    profile = Profile.objects.create(email="before@test.com")
    profile = Profile.objects.get(pk=profile.pk)
    profile.email = f"{WJ}after@test.com"
    profile.save()
    profile.refresh_from_db()
    assert profile.email == "after@test.com"


def test_profile_save_refreshes_email_snapshot(db):
    profile = Profile.objects.create(email=f"{WJ}snap@test.com")
    assert profile._loaded_email == "snap@test.com"
    profile.email = f"{WJ}snap2@test.com"
    profile.save()
    assert profile._loaded_email == "snap2@test.com"
    profile.first_name = "x"
    profile.save(update_fields=["first_name"])
    assert profile._loaded_email == "snap2@test.com"


def test_profile_save_leaves_untouched_legacy_email(db):
    """Saving a legacy dirty row without changing its email must not collide
    with its clean twin on the unique constraint."""
    Profile.objects.create(email="twin@test.com")
    legacy = Profile.objects.create(email="placeholder@test.com")
    Profile.objects.filter(pk=legacy.pk).update(email=f"{WJ}twin@test.com")

    legacy = Profile.objects.get(pk=legacy.pk)
    legacy.first_name = "Legacy"
    legacy.save()
    legacy.save(update_fields=["updated_on"])
    legacy.refresh_from_db()
    assert legacy.email == f"{WJ}twin@test.com"
    assert legacy.first_name == "Legacy"


def test_add_profile_strips_invisible_chars(client, base_project, project1, token1):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    response = client.post(
        url,
        data={"email": f"{WJ}Pasted@Test.com", "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 200
    assert Profile.objects.filter(email="pasted@test.com").exists()
    assert not Profile.objects.filter(email__contains=WJ).exists()


def test_add_profile_matches_existing_user_despite_invisible_chars(
    client, base_project, project1, token1, profile3
):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    response = client.post(
        url,
        data={"email": f"{WJ}{WJ}{profile3.email}", "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 200
    assert response.json()["profile"] == str(profile3.pk)


@pytest.mark.parametrize("email", [WJ, " ", "not-an-email"])
def test_add_profile_rejects_empty_or_invalid(client, base_project, project1, token1, email):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    response = client.post(
        url,
        data={"email": email, "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 400


@patch("api.resources.me.Auth0Users")
def test_me_patch_normalizes_email_before_auth0_sync(mock_auth0, db_setup, api_client1):
    response = api_client1.patch(reverse("me-list"), {"email": f"{WJ}me@test.com"}, format="json")
    assert response.status_code == 200
    assert response.json()["email"] == "me@test.com"
    for call in mock_auth0.return_value.update.call_args_list:
        assert call.args[0]["user_metadata"]["email"] == "me@test.com"


@patch("api.utils.auth0utils.Auth0ManagementAPI")
@patch("api.utils.auth0utils.Auth0UserInfo")
def test_get_user_info_normalizes_email(mock_userinfo, _mock_mgmt):
    from api.utils.auth0utils import get_user_info

    ui = mock_userinfo.return_value.get_userinfo.return_value
    ui.user_metadata = {}
    ui.email = f"{WJ}auth0@test.com"
    assert get_user_info("auth0|abc")["email"] == "auth0@test.com"

    # metadata email that is only invisible chars falls back to ui.email
    ui.user_metadata = {"email": WJ}
    assert get_user_info("auth0|abc")["email"] == "auth0@test.com"
