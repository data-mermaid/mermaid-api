from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.fixture
def me_url():
    return reverse("me-list")


def patch_me(client, data, url):
    return client.patch(url, data, format="json")


def get_me(client, url):
    return client.get(url, format="json")


def test_me_patch_updates_app_settings(db_setup, api_client1, me_url):
    response = patch_me(
        api_client1,
        {
            "app_settings": {
                "collect": {
                    "demo_project_prompt_dismissed": True,
                    "onboarding_completed": True,
                }
            }
        },
        me_url,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["app_settings"]["collect"]["demo_project_prompt_dismissed"] is True
    assert data["app_settings"]["collect"]["onboarding_completed"] is True

    # Verify persistence
    data = get_me(api_client1, me_url).json()
    assert data["app_settings"]["collect"]["demo_project_prompt_dismissed"] is True
    assert data["app_settings"]["collect"]["onboarding_completed"] is True


def test_me_patch_merges_app_settings(db_setup, api_client1, me_url):
    """Test that PATCH merges app_settings at app-level (preserves other apps)"""
    # Collect app sets its settings
    patch_me(api_client1, {"app_settings": {"collect": {"setting1": True}}}, me_url)

    # Explore app sets its settings (should preserve collect's settings)
    response = patch_me(api_client1, {"app_settings": {"explore": {"setting2": False}}}, me_url)

    assert response.status_code == 200
    data = response.json()
    # Both app settings should be present
    assert data["app_settings"]["collect"]["setting1"] is True
    assert data["app_settings"]["explore"]["setting2"] is False


def test_me_patch_updates_single_app(db_setup, api_client1, me_url):
    """Test that updating one app replaces that app's settings, not merges"""
    # Set initial collect settings with two keys
    patch_me(
        api_client1, {"app_settings": {"collect": {"setting1": True, "setting2": "old"}}}, me_url
    )

    # Update collect settings with only one key (should replace, not merge)
    response = patch_me(api_client1, {"app_settings": {"collect": {"setting1": False}}}, me_url)

    assert response.status_code == 200
    data = response.json()
    assert data["app_settings"]["collect"]["setting1"] is False
    assert "setting2" not in data["app_settings"]["collect"]


def test_me_patch_clears_single_app(db_setup, api_client1, me_url):
    """Test that a single app's settings can be cleared while preserving others"""
    patch_me(
        api_client1,
        {"app_settings": {"collect": {"setting": True}, "explore": {"other": "value"}}},
        me_url,
    )

    # Clear only collect's settings
    response = patch_me(api_client1, {"app_settings": {"collect": {}}}, me_url)

    assert response.status_code == 200
    data = response.json()
    assert data["app_settings"]["collect"] == {}
    assert data["app_settings"]["explore"]["other"] == "value"


def test_me_patch_clear_all_app_settings(db_setup, api_client1, me_url):
    """Test that all app_settings can be cleared with empty dict"""
    patch_me(
        api_client1,
        {"app_settings": {"collect": {"setting": True}, "explore": {"other": "value"}}},
        me_url,
    )

    response = patch_me(api_client1, {"app_settings": {}}, me_url)

    assert response.status_code == 200
    assert response.json()["app_settings"] == {}


@patch("api.resources.me.Auth0Users")
def test_me_patch_other_fields_preserves_app_settings(mock_auth0, db_setup, api_client1, me_url):
    """Test that updating other fields preserves app_settings"""
    patch_me(api_client1, {"app_settings": {"collect": {"setting": True}}}, me_url)

    response = patch_me(api_client1, {"first_name": "Updated"}, me_url)

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["app_settings"]["collect"]["setting"] is True
