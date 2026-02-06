import uuid
from contextlib import contextmanager
from unittest.mock import patch

from django.db.models.signals import post_save, pre_save
from django.urls import reverse

from api.models import (
    BeltFish,
    BenthicAttribute,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    Profile,
    ProjectProfile,
    QuadratTransect,
    SampleEvent,
)
from api.models.classification import Annotation, Image, Point
from api.signals.classification import post_save_classification_image, pre_image_save
from api.utils.project import copy_project_and_resources


@contextmanager
def mock_demo_project(project, mock_s3=False):
    """Context manager to mock settings for demo project copy."""
    with patch("api.utils.project.settings") as mock_settings:
        mock_settings.DEMO_PROJECT_ID = str(project.pk)
        mock_settings.IMAGE_PROCESSING_BUCKET = "test-bucket"
        mock_settings.IMAGE_BUCKET_AWS_ACCESS_KEY_ID = "test-key"
        mock_settings.IMAGE_BUCKET_AWS_SECRET_ACCESS_KEY = "test-secret"

        if mock_s3:
            with patch("api.utils.project.s3_utils.copy_object") as mock_copy:
                yield mock_settings, mock_copy
        else:
            yield mock_settings


def test_add_profile_new_user(client, base_project, project1, token1):
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


def test_add_profile_existing_user(client, base_project, project1, token1, profile3):
    url = reverse("project-add-profile", kwargs=dict(pk=project1.pk))
    response = client.post(
        url,
        data={"email": profile3.email.title(), "role": ProjectProfile.COLLECTOR},
        HTTP_AUTHORIZATION=f"Bearer {token1}",
    )
    assert response.status_code == 200
    assert str(profile3.pk) == response.json()["profile"]


def test_add_profile_existing_project_profile(client, base_project, project1, token1, profile2):
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
    assert "benthiclit" in site_submitted_summary[site1_id]["sample_unit_methods"]
    assert "fishbelt" in site_submitted_summary[site1_id]["sample_unit_methods"]

    site_collecting_summary = data["site_collecting_summary"]
    assert site1_id in site_collecting_summary
    assert "fishbelt" in site_collecting_summary[site1_id]["sample_unit_methods"]
    assert (
        str(profile1.pk)
        in site_collecting_summary[site1_id]["sample_unit_methods"]["fishbelt"]["profile_summary"]
    )


def test_copy_project_and_resources(
    project1, project_profile1, project_profile2, site1, site2, site3, management1, management2
):
    owner_profile = project_profile1.profile
    new_project = copy_project_and_resources(owner_profile, "new title", project1)

    assert new_project.pk != project1.pk
    assert new_project.name == "new title"
    assert new_project.tags.count() == 3
    assert new_project.sites.all().count() == 3
    assert new_project.management_set.count() == 2
    assert new_project.profiles.get(profile=owner_profile).role == ProjectProfile.ADMIN
    assert new_project.profiles.get(profile=project_profile2.profile).role == project_profile2.role


def test_copy_demo_project_copies_collect_records(
    project1, project_profile1, site1, management1, profile1, collect_record4
):
    owner_profile = project_profile1.profile

    with mock_demo_project(project1):
        new_project = copy_project_and_resources(owner_profile, "demo copy", project1)

    assert new_project.collect_records.count() == 1
    new_cr = new_project.collect_records.first()

    assert new_cr.profile == owner_profile
    assert new_cr.data["sample_event"]["site"] == str(new_project.sites.first().pk)
    assert new_cr.data["sample_event"]["management"] == str(new_project.management_set.first().pk)
    assert new_cr.data["observers"] == [{"profile": str(owner_profile.id)}]
    assert new_cr.stage == collect_record4.stage
    assert new_cr.validations is not None


def test_copy_demo_project_copies_submitted_sample_units(
    project1,
    project_profile1,
    benthic_lit_project,
    benthic_lit1,
    benthic_transect1,
    sample_event1,
    obs_benthic_lit1_1,
):
    owner_profile = project_profile1.profile
    original_counts = {
        "sample_events": SampleEvent.objects.filter(site__project=project1).count(),
        "benthic_lits": BenthicLIT.objects.filter(
            transect__sample_event__site__project=project1
        ).count(),
        "observations": ObsBenthicLIT.objects.filter(
            benthiclit__transect__sample_event__site__project=project1
        ).count(),
    }

    with mock_demo_project(project1):
        new_project = copy_project_and_resources(owner_profile, "demo copy", project1)

    assert (
        SampleEvent.objects.filter(site__project=new_project).count()
        == original_counts["sample_events"]
    )
    assert (
        BenthicLIT.objects.filter(transect__sample_event__site__project=new_project).count()
        == original_counts["benthic_lits"]
    )
    assert (
        ObsBenthicLIT.objects.filter(
            benthiclit__transect__sample_event__site__project=new_project
        ).count()
        == original_counts["observations"]
    )


def test_copy_demo_project_observers_are_new_owner(
    project1, project_profile1, belt_fish_project, belt_fish1, observer_belt_fish1
):
    owner_profile = project_profile1.profile

    with mock_demo_project(project1):
        new_project = copy_project_and_resources(owner_profile, "demo copy", project1)

    new_belt_fish = BeltFish.objects.filter(transect__sample_event__site__project=new_project)
    assert new_belt_fish.count() > 0
    for bf in new_belt_fish:
        assert list(bf.observers.values_list("profile", flat=True)) == [owner_profile.pk]


def test_copy_non_demo_project_does_not_copy_data(
    project1, project_profile1, belt_fish_project, belt_fish1, collect_record4
):
    owner_profile = project_profile1.profile
    new_project = copy_project_and_resources(owner_profile, "regular copy", project1)

    assert new_project.collect_records.count() == 0
    assert SampleEvent.objects.filter(site__project=new_project).count() == 0
    assert BeltFish.objects.filter(transect__sample_event__site__project=new_project).count() == 0


def test_copy_demo_project_copies_photo_quadrat_transects_with_images(
    db,
    project1,
    project_profile1,
    benthic_photo_quadrat_transect_project,
    benthic_photo_quadrat_transect1,
    quadrat_transect1,
    obs_benthic_photo_quadrat1_1,
    obs_benthic_photo_quadrat1_2,
):
    """Verify BenthicPhotoQuadratTransect with images is copied correctly."""
    owner_profile = project_profile1.profile

    # Disconnect image signals to create test image without actual file
    pre_save.disconnect(pre_image_save, sender=Image)
    post_save.disconnect(post_save_classification_image, sender=Image)

    try:
        # Create test image with points and annotations
        test_image = Image.objects.create(
            collect_record_id=uuid.uuid4(),
            name="test-image.jpg",
            original_image_name="original.jpg",
            original_image_width=1920,
            original_image_height=1080,
        )
        test_image.image.name = f"mermaid/{test_image.id}.jpg"
        test_image.thumbnail.name = f"mermaid/{test_image.id}_thumb.jpg"
        test_image.save()

        benthic_attr = BenthicAttribute.objects.first()
        for row, col in [(100, 200), (300, 400)]:
            point = Point.objects.create(image=test_image, row=row, column=col)
            Annotation.objects.create(
                point=point, benthic_attribute=benthic_attr, is_confirmed=True
            )

        obs_benthic_photo_quadrat1_1.image = test_image
        obs_benthic_photo_quadrat1_1.save()

        original_counts = {
            "quadrat_transects": QuadratTransect.objects.filter(
                sample_event__site__project=project1
            ).count(),
            "bpqts": BenthicPhotoQuadratTransect.objects.filter(
                quadrat_transect__sample_event__site__project=project1
            ).count(),
            "observations": ObsBenthicPhotoQuadrat.objects.filter(
                benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project=project1
            ).count(),
            "images": Image.objects.count(),
            "points": Point.objects.count(),
            "annotations": Annotation.objects.count(),
        }

        with mock_demo_project(project1, mock_s3=True) as (mock_settings, mock_copy):
            new_project = copy_project_and_resources(owner_profile, "demo copy", project1)
            assert mock_copy.call_count == 2  # image + thumbnail

        # Verify transects and observations were copied
        assert (
            QuadratTransect.objects.filter(sample_event__site__project=new_project).count()
            == original_counts["quadrat_transects"]
        )
        new_bpqts = BenthicPhotoQuadratTransect.objects.filter(
            quadrat_transect__sample_event__site__project=new_project
        )
        assert new_bpqts.count() == original_counts["bpqts"]
        assert (
            ObsBenthicPhotoQuadrat.objects.filter(
                benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project=new_project
            ).count()
            == original_counts["observations"]
        )

        # Verify observers are new owner
        for bpqt in new_bpqts:
            assert list(bpqt.observers.values_list("profile", flat=True)) == [owner_profile.pk]

        # Verify images, points, and annotations were copied
        assert Image.objects.count() == original_counts["images"] + 1
        assert Point.objects.count() == original_counts["points"] + 2
        assert Annotation.objects.count() == original_counts["annotations"] + 2

        # Verify new observation references new image with correct path
        new_obs = ObsBenthicPhotoQuadrat.objects.filter(
            benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project=new_project,
            image__isnull=False,
        ).first()
        assert new_obs.image.id != test_image.id
        assert str(new_obs.image.id) in new_obs.image.image.name
    finally:
        pre_save.connect(pre_image_save, sender=Image)
        post_save.connect(post_save_classification_image, sender=Image)
