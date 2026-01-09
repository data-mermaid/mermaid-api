from django.urls import reverse

from api.models import ProfileAppSettings


def get_settings_id(api_client):
    response = api_client.get(reverse("me-list"), format="json")
    return response.json()["app_settings"]["id"]


def test_profile_app_settings_auto_create_via_me(db_setup, api_client1, profile1):
    assert not ProfileAppSettings.objects.filter(profile=profile1).exists()

    response = api_client1.get(reverse("me-list"), format="json")

    assert response.status_code == 200
    assert "app_settings" in response.json()
    assert response.json()["app_settings"]["demo_project_prompt_dismissed"] is False
    assert ProfileAppSettings.objects.filter(profile=profile1).exists()


def test_profile_app_settings_list(db_setup, api_client1, profile1):
    assert not ProfileAppSettings.objects.filter(profile=profile1).exists()

    response = api_client1.get(reverse("profileappsettings-list"), format="json")

    assert response.status_code == 200
    assert response.json() == []

    ProfileAppSettings.objects.create(profile=profile1)

    response = api_client1.get(reverse("profileappsettings-list"), format="json")
    assert len(response.json()) == 1
    assert response.json()[0]["demo_project_prompt_dismissed"] is False


def test_profile_app_settings_create_idempotent(db_setup, api_client1, profile1):
    response1 = api_client1.post(reverse("profileappsettings-list"), format="json")
    assert response1.status_code == 201
    assert response1.json()["demo_project_prompt_dismissed"] is False
    assert ProfileAppSettings.objects.filter(profile=profile1).exists()
    settings_id = response1.json()["id"]

    response2 = api_client1.post(reverse("profileappsettings-list"), format="json")
    assert response2.status_code == 200
    assert response2.json()["id"] == settings_id


def test_profile_app_settings_patch(db_setup, api_client1):
    settings_id = get_settings_id(api_client1)
    url = reverse("profileappsettings-detail", kwargs={"pk": settings_id})

    response = api_client1.patch(url, {"demo_project_prompt_dismissed": True}, format="json")

    assert response.status_code == 200
    assert response.json()["demo_project_prompt_dismissed"] is True


def test_profile_app_settings_in_me_endpoint(db_setup, api_client1):
    settings_id = get_settings_id(api_client1)
    settings_url = reverse("profileappsettings-detail", kwargs={"pk": settings_id})

    api_client1.patch(settings_url, {"demo_project_prompt_dismissed": True}, format="json")

    response = api_client1.get(reverse("me-list"), format="json")
    assert response.json()["app_settings"]["demo_project_prompt_dismissed"] is True


def test_profile_app_settings_cannot_access_other_users(db_setup, api_client1, api_client2):
    other_user_settings_id = get_settings_id(api_client2)
    settings_url = reverse("profileappsettings-detail", kwargs={"pk": other_user_settings_id})

    assert api_client1.get(settings_url, format="json").status_code == 404
    assert (
        api_client1.patch(
            settings_url, {"demo_project_prompt_dismissed": True}, format="json"
        ).status_code
        == 404
    )
    assert (
        api_client1.put(
            settings_url, {"demo_project_prompt_dismissed": True}, format="json"
        ).status_code
        == 404
    )
    assert api_client1.delete(settings_url, format="json").status_code == 404
