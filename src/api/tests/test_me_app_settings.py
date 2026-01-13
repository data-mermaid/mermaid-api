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


def test_me_patch_updates_state_fields(db_setup, api_client1, me_url):
    """Test that collect_state and explore_state can be updated independently"""
    # Update collect_state
    response = patch_me(
        api_client1,
        {
            "collect_state": {
                "demo_project_prompt_dismissed": True,
                "onboarding_completed": True,
            }
        },
        me_url,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["collect_state"]["demo_project_prompt_dismissed"] is True
    assert data["collect_state"]["onboarding_completed"] is True

    # Update explore_state (should not affect collect_state)
    response = patch_me(
        api_client1,
        {
            "explore_state": {
                "filters": {"status": "open"},
                "view_mode": "grid",
            }
        },
        me_url,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["explore_state"]["filters"]["status"] == "open"
    assert data["explore_state"]["view_mode"] == "grid"
    # collect_state should still be present
    assert data["collect_state"]["demo_project_prompt_dismissed"] is True
    assert data["collect_state"]["onboarding_completed"] is True

    # Verify persistence
    data = get_me(api_client1, me_url).json()
    assert data["collect_state"]["demo_project_prompt_dismissed"] is True
    assert data["collect_state"]["onboarding_completed"] is True
    assert data["explore_state"]["filters"]["status"] == "open"
    assert data["explore_state"]["view_mode"] == "grid"


def test_me_patch_replaces_state_field(db_setup, api_client1, me_url):
    """Test that updating a state field replaces it entirely (all or nothing)"""
    # Set initial collect_state with two keys
    patch_me(api_client1, {"collect_state": {"setting1": True, "setting2": "old"}}, me_url)

    # Update collect_state with only one key (should replace entire field)
    response = patch_me(api_client1, {"collect_state": {"setting1": False}}, me_url)

    assert response.status_code == 200
    data = response.json()
    assert data["collect_state"]["setting1"] is False
    # setting2 should be gone since we replaced the entire field
    assert "setting2" not in data["collect_state"]


def test_me_patch_clears_state_field(db_setup, api_client1, me_url):
    """Test that a state field can be cleared independently"""
    # Set both state fields
    patch_me(
        api_client1,
        {"collect_state": {"setting": True}, "explore_state": {"other": "value"}},
        me_url,
    )

    # Clear only collect_state
    response = patch_me(api_client1, {"collect_state": {}}, me_url)

    assert response.status_code == 200
    data = response.json()
    assert data["collect_state"] == {}
    # explore_state should be unaffected
    assert data["explore_state"]["other"] == "value"


@patch("api.resources.me.Auth0Users")
def test_me_patch_other_fields_preserves_state(mock_auth0, db_setup, api_client1, me_url):
    """Test that updating other fields preserves state fields"""
    patch_me(
        api_client1,
        {"collect_state": {"setting": True}, "explore_state": {"other": "value"}},
        me_url,
    )

    response = patch_me(api_client1, {"first_name": "Updated"}, me_url)

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    # Both state fields should be preserved
    assert data["collect_state"]["setting"] is True
    assert data["explore_state"]["other"] == "value"
