from datetime import date

import pytest
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from api.mocks import MockRequest
from api.models import (
    AuthUser,
    Management,
    Profile,
    Project,
    ProjectProfile,
    SampleEvent,
    Site,
)
from api.utils import tokenutils

# PROJECT


@pytest.fixture
def project1(fish_family1, fish_family2, fish_family3, fish_family4):
    project = Project.objects.create(
        name="Test Project 1",
        status=Project.OPEN,
        data={
            "settings": {
                "fishFamilySubset": [
                    str(fish_family1.pk),
                    str(fish_family2.pk),
                    str(fish_family3.pk),
                    str(fish_family4.pk),
                ]
            }
        },
    )
    project.tags.add("test", "fishy", "global")

    return project


@pytest.fixture
def project2():
    return Project.objects.create(name="Test Project 2", status=Project.OPEN)


@pytest.fixture
def project3():
    return Project.objects.create(name="Test Project 3", status=Project.OPEN)


@pytest.fixture
def project4():
    return Project.objects.create(
        name="Test Project 4",
        status=Project.OPEN,
        data={
            "settings": {
                "fishFamilySubset": [
                    "343f38e9-2497-422f-bac9-576682bb97f6"  # Fake
                ]
            }
        },
    )


@pytest.fixture
def profile1():
    email = "profile1@mermaidcollect.org"
    profile = Profile.objects.create(email=email, first_name="Philip", last_name="Glass")
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    return profile


@pytest.fixture
def profile2():
    email = "profile2@mermaidcollect.org"
    profile = Profile.objects.create(email=email, first_name="Bellatrix", last_name="Lestrange")
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    return profile


@pytest.fixture
def profile3():
    email = "profile3@mermaidcollect.org"
    profile = Profile.objects.create(email=email, first_name="Garrick", last_name="Ollivander")
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    return profile


@pytest.fixture
def token1(profile1):
    auth_user = profile1.authusers.first()
    return tokenutils.create_token(auth_user.user_id)


@pytest.fixture
def token2(profile2):
    auth_user = profile2.authusers.first()
    return tokenutils.create_token(auth_user.user_id)


@pytest.fixture
def project_profile1(project1, profile1):
    return ProjectProfile.objects.create(
        project=project1, profile=profile1, role=ProjectProfile.ADMIN
    )


@pytest.fixture
def project_profile2(project1, profile2):
    return ProjectProfile.objects.create(
        project=project1, profile=profile2, role=ProjectProfile.COLLECTOR
    )


@pytest.fixture
def project_profile4(project4, profile1):
    return ProjectProfile.objects.create(
        project=project4, profile=profile1, role=ProjectProfile.ADMIN
    )


@pytest.fixture
def sample_date1():
    return date(2022, 1, 1)


@pytest.fixture
def site1(project1, country1, reef_type1, reef_exposure1, reef_zone1):
    return Site.objects.create(
        project=project1,
        name="Site 1",
        location=Point(1, 1, srid=4326),
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
    )


@pytest.fixture
def site2(project1, country1, reef_type1, reef_exposure1, reef_zone1):
    return Site.objects.create(
        project=project1,
        name="Site 2",
        location=Point(1.01, 1.01, srid=4326),
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
    )


@pytest.fixture
def site3(project1, country1, reef_type1, reef_exposure1, reef_zone1):
    return Site.objects.create(
        project=project1,
        name="Site 3",
        location=Point(-100, 100, srid=4326),
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
    )


@pytest.fixture
def management1(project1):
    return Management.objects.create(
        project=project1,
        est_year=2000,
        name="Management 1",
        notes="Hey what's up!!",
        open_access=True,
    )


@pytest.fixture
def management2(project1):
    return Management.objects.create(
        project=project1,
        est_year=2000,
        name="Management 2",
        notes="Hey what's up, from management2!!",
    )


@pytest.fixture
def sample_event1(management1, site1, sample_date1):
    return SampleEvent.objects.create(
        management=management1,
        site=site1,
        sample_date=sample_date1,
        notes="Some sample event notes for sample_event1",
    )


@pytest.fixture
def sample_event2(management2, site2, sample_date1):
    return SampleEvent.objects.create(
        management=management2,
        site=site2,
        sample_date=sample_date1,
        notes="Some sample event notes for sample_event2",
    )


@pytest.fixture
def sample_event3(management1, site1, sample_date1):
    return SampleEvent.objects.create(
        management=management1,
        site=site1,
        sample_date=sample_date1,
        notes="Some sample event notes for sample_event3",
    )


@pytest.fixture
def base_project(
    management1,
    site1,
    management2,
    site2,
    site3,
    profile1,
    profile2,
    profile3,
    project_profile1,
    project_profile2,
):
    pass


@pytest.fixture
def profile1_request(token1, profile1):
    return MockRequest(token=token1, profile=profile1)


@pytest.fixture
def api_client1(token1, project_profile1):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token1}")
    return client


@pytest.fixture
def api_client2(token2, project_profile2):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token2}")
    return client
