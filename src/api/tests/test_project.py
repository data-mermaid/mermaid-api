from venv import create
from django.urls import reverse

from api.models import Profile, ProjectProfile
from api.utils.project import copy_project_and_resources, create_project


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


def test_copy_project_and_resources(
    project1,
    project_profile1,
    project_profile2,
    site1,
    site2,
    site3,
    management1,
    management2
):
    project_name = "new title"
    owner_profile = project_profile1.profile
    new_project = copy_project_and_resources(owner_profile, project_name, project1.pk)

    assert new_project.pk != project1.pk
    assert new_project.name == project_name

    original_tags = [t.name for t in project1.tags.all()]
    assert new_project.tags.filter(name__in=original_tags).count() == len(original_tags)

    assert new_project.tags.count() == 3    

    assert new_project.sites.all().count() == 3
    assert new_project.management_set.count() == 2

    assert new_project.profiles.get(profile=owner_profile).role == ProjectProfile.ADMIN
    assert new_project.profiles.get(profile=project_profile2.profile).role == project_profile2.role
