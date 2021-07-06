import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework.test import APIClient

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
def project1(db):
    return Project.objects.create(name="Test Project 1", status=Project.TEST)


@pytest.fixture
def project2(db):
    return Project.objects.create(name="Test Project 2", status=Project.TEST)


@pytest.fixture
def project3(db):
    return Project.objects.create(name="Test Project 3", status=Project.TEST)


@pytest.fixture
def profile1(db):
    email = "profile1@mermaidcollect.org"
    profile = Profile.objects.create(
        email=email, first_name="Philip", last_name="Glass"
    )
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    return profile


@pytest.fixture
def profile2(db):
    email = "profile2@mermaidcollect.org"
    profile = Profile.objects.create(
        email=email, first_name="Bellatrix", last_name="Lestrange"
    )
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    return profile


@pytest.fixture
def token1(db, profile1):
    auth_user = profile1.authusers.first()
    return tokenutils.create_token(auth_user.user_id)


@pytest.fixture
def token2(db, profile2):
    auth_user = profile2.authusers.first()
    return tokenutils.create_token(auth_user.user_id)


@pytest.fixture
def project_profile1(db, project1, profile1):
    return ProjectProfile.objects.create(
        project=project1, profile=profile1, role=ProjectProfile.ADMIN
    )


@pytest.fixture
def project_profile2(db, project1, profile2):
    return ProjectProfile.objects.create(
        project=project1, profile=profile2, role=ProjectProfile.COLLECTOR
    )


@pytest.fixture
def site1(db, project1, country1, reef_type1, reef_exposure1, reef_zone1):
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
def site2(db, project1, country1, reef_type1, reef_exposure1, reef_zone1):
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
def management1(db, project1):
    return Management.objects.create(
        project=project1, est_year=2000, name="Management 1", notes="Hey what's up!!",
    )


@pytest.fixture
def management2(db, project1):
    return Management.objects.create(
        project=project1,
        est_year=2000,
        name="Management 2",
        notes="Hey what's up, from management2!!",
    )


@pytest.fixture
def sample_event1(db, management1, site1):
    return SampleEvent.objects.create(
        management=management1,
        site=site1,
        sample_date=timezone.now(),
        notes="Some sample event notes for sample_event1",
    )


@pytest.fixture
def sample_event2(db, management2, site2):
    return SampleEvent.objects.create(
        management=management2,
        site=site2,
        sample_date=timezone.now(),
        notes="Some sample event notes for sample_event2",
    )


@pytest.fixture
def base_project(
    db,
    management1,
    site1,
    management2,
    site2,
    profile1,
    profile2,
    project_profile1,
    project_profile2,
):
    pass


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
