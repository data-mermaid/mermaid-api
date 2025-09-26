import uuid

import pytest
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from api.models import (
    BenthicAttribute,
    BenthicPhotoQuadratTransect,
    Image,
    Management,
    ObsBenthicPhotoQuadrat,
    QuadratTransect,
    SampleEvent,
    Site,
)


@pytest.fixture
def management_other(project3):
    return Management.objects.create(
        project=project3,
        est_year=2000,
        name="Management 3",
        notes="Hey what's up, from management other!!",
    )


@pytest.fixture
def site_other(project3, country1, reef_type1, reef_exposure1, reef_zone1):
    return Site.objects.create(
        project=project3,
        name="Site Other",
        location=Point(-100, 100, srid=4326),
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
    )


@pytest.fixture
def sample_event_other(management_other, site_other, sample_date1):
    return SampleEvent.objects.create(
        management=management_other,
        site=site_other,
        sample_date=sample_date1,
        notes="Some sample event notes for sample_event other",
    )


@pytest.fixture
def image_file():
    return SimpleUploadedFile(
        name="test_image.jpg",
        content=open("api/tests/data/test_image.jpg", "rb").read(),
        content_type="image/jpeg",
    )


@pytest.fixture
def image_bpq_project1(
    db, benthic_photo_quadrat_transect1, obs_benthic_photo_quadrat1_1, profile1, image_file
):
    image = Image.objects.create(
        name="BPQ Image Project 1",
        image=image_file,
        collect_record_id=uuid.uuid4(),
        created_by=profile1,
        updated_by=profile1,
    )

    obs = ObsBenthicPhotoQuadrat.objects.filter(
        benthic_photo_quadrat_transect=benthic_photo_quadrat_transect1
    ).first()

    if obs:
        obs.image = image
        obs.save()

    return image


@pytest.fixture
def image_bpq_project_other(
    db,
    profile3,
    sample_event_other,
    image_file,
    project_profile3,
    benthic_attribute_1a,
    benthic_attribute_2a,
):
    quadrat_transect = QuadratTransect.objects.create(
        quadrat_size=1,
        num_quadrats=1,
        num_points_per_quadrat=100,
        quadrat_number_start=1,
        sample_event=sample_event_other,
        depth=5,
        len_surveyed=50,
        sample_time="11:00:00",
    )

    benthic_pq_transect_other = BenthicPhotoQuadratTransect.objects.create(
        quadrat_transect=quadrat_transect
    )

    image_other = Image.objects.create(
        name="BPQ Image Project 3",
        image=image_file,
        collect_record_id=uuid.uuid4(),
        created_by=profile3,
        updated_by=profile3,
    )

    benthic_attr = BenthicAttribute.objects.first()

    ObsBenthicPhotoQuadrat.objects.create(
        benthic_photo_quadrat_transect=benthic_pq_transect_other,
        quadrat_number=1,
        attribute=benthic_attr,
        num_points=50,
        image=image_other,
    )

    return image_other


@pytest.fixture
def image_no_project(db, profile2):
    return Image.objects.create(name="Orphan Image", created_by=profile2, updated_by=profile2)


def test_unauthenticated_access_denied(api_client_public):
    url = reverse("images-list")
    response = api_client_public.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_user_can_list_images(
    api_client1, image_bpq_project1, benthic_photo_quadrat_transect_project
):
    url = reverse("images-list")
    response = api_client1.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "results" in data

    image_ids = [img["id"] for img in data["results"]]
    assert str(image_bpq_project1.id) in image_ids


def test_user_only_sees_accessible_images(
    api_client1,
    api_client3,
    image_bpq_project1,
    image_bpq_project_other,
    benthic_photo_quadrat_transect_project,
):
    url = reverse("images-list")

    response = api_client1.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    image_ids = [img["id"] for img in data["results"]]
    assert str(image_bpq_project1.id) in image_ids
    assert str(image_bpq_project_other.id) not in image_ids

    response3 = api_client3.get(url)
    assert response3.status_code == status.HTTP_200_OK
    data3 = response3.json()

    image_ids3 = [img["id"] for img in data3["results"]]
    assert str(image_bpq_project_other.id) in image_ids3
    assert str(image_bpq_project1.id) not in image_ids3


def test_retrieve_single_image(
    api_client1, image_bpq_project1, project1, benthic_photo_quadrat_transect_project
):
    url = reverse("images-detail", args=[str(image_bpq_project1.id)])
    response = api_client1.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == str(image_bpq_project1.id)
    assert data["name"] == image_bpq_project1.name
    assert data["project_id"] == str(project1.id)
    assert data["project_name"] == project1.name


def test_cannot_retrieve_inaccessible_image(
    api_client1, api_client3, image_bpq_project_other, benthic_attribute_1a
):
    url = reverse("images-detail", args=[str(image_bpq_project_other.id)])

    response = api_client1.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
