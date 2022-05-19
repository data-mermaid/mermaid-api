from django.urls import reverse

from api.models import Profile, ProjectProfile


def test_add_profile_new_user(
    client,
    base_project,
    project1,
    token1,
):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    email = "bill@test.com"

    assert Profile.objects.filter(email=email).exists() is False

    response = client.post(
        url,
        data={"email": email, "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )

    assert Profile.objects.filter(email=email).exists() is True

    assert response.status_code == 200


def test_add_profile_existing_user(
    client,
    base_project,
    project1,
    token1,
    profile3,
):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    email = profile3.email.title()

    profile_id = str(profile3.pk)

    response = client.post(
        url,
        data={"email": email, "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )

    assert response.status_code == 200
    assert profile_id == response.json()["profile"]


def test_add_profile_existing_project_profile(
    client,
    base_project,
    project1,
    token1,
    profile2,
):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))

    response = client.post(
        url,
        data={"email": profile2.email, "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 400


def test_project_summary(
    client,
    benthic_lit_project,
    belt_fish_project,
    project1,
    site1,
    benthic_lit1,
    collect_record4,
    profile1,
    token1,
):
    url = reverse("project-summary", kwargs=dict(pk=project1.pk))

    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert response.status_code == 200

    site1_id = str(site1.pk)
    data = response.json()

    assert ["benthiclit", "fishbelt"] == sorted(data.get("protocols"))

    site_submitted_summary = data["site_submitted_summary"]
    assert len(site_submitted_summary) == 2
    assert site1_id in site_submitted_summary

    sample_unit_methods = site_submitted_summary[site1_id]["sample_unit_methods"]
    assert "benthiclit" in sample_unit_methods
    assert "fishbelt" in sample_unit_methods

    site_collecting_summary = data["site_collecting_summary"]
    assert site1_id in site_collecting_summary
    sample_unit_methods = site_collecting_summary[site1_id]["sample_unit_methods"]
    assert "fishbelt" in sample_unit_methods
    assert str(profile1.pk) in sample_unit_methods["fishbelt"]["profile_summary"]
