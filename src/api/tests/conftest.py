import pytest
from django.contrib.gis.geos import Point
from django.db import connection

from api.models import (
    AuthUser,
    BeltTransectWidth,
    BeltTransectWidthCondition,
    Country,
    Current,
    FishFamily,
    FishGenus,
    FishSizeBin,
    FishSpecies,
    HabitatComplexityScore,
    Management,
    ManagementParty,
    Profile,
    Project,
    ProjectProfile,
    ReefExposure,
    ReefSlope,
    ReefType,
    ReefZone,
    Site,
    Tide,
    Visibility,
)


@pytest.fixture
def db_setup(db):
    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


# PROJECT

@pytest.fixture
def project1(db):
    return Project.objects.create(name="Test Project 1", status=Project.TEST)


@pytest.fixture
def profile1(db):
    email = "profile1@mermaidcollect.org"
    profile = Profile.objects.create(
        email=email, first_name="Philip", last_name="Glass"
    )
    AuthUser.objects.create(profile=profile, user_id=f"test|{email}")

    return profile


@pytest.fixture
def project_profile1(db, project1, profile1):
    return ProjectProfile.objects.create(
        project=project1, profile=profile1, role=ProjectProfile.ADMIN
    )


@pytest.fixture
def site1(db, project1, country1, reef_type1, reef_exposure1, reef_zone1):
    return Site.objects.get_or_create(
        project=project1,
        name="Site 1",
        location=Point(1, 1, srid=4326),
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
    )


@pytest.fixture
def management1(db, project1):
    return Management.objects.get_or_create(
        project=project1, est_year=2000, name="Management 1", notes="Hey what's up!!",
    )


@pytest.fixture
def all_project1(db, project1, profile1, project_profile1, site1, management1):
    pass


# CHOICES

@pytest.fixture
def country1(db):
    return Country.objects.create(iso="AL", name="Atlantis")


@pytest.fixture
def country2(db):
    return Country.objects.create(iso="CA", name="Canada")


@pytest.fixture
def country3(db):
    return Country.objects.create(iso="US", name="United States")


@pytest.fixture
def reef_type1(db):
    return ReefType.objects.create(name="reeftype1")


@pytest.fixture
def reef_type2(db):
    return ReefType.objects.create(name="reeftype2")


@pytest.fixture
def reef_type3(db):
    return ReefType.objects.create(name="reeftype3")


@pytest.fixture
def reef_zone1(db):
    return ReefZone.objects.create(name="reefzone1")


@pytest.fixture
def reef_zone2(db):
    return ReefZone.objects.create(name="reefzone2")


@pytest.fixture
def reef_zone3(db):
    return ReefZone.objects.create(name="reefzone3")


@pytest.fixture
def reef_exposure1(db):
    return ReefExposure.objects.create(name="reefexposure1", val=1)


@pytest.fixture
def reef_exposure2(db):
    return ReefExposure.objects.create(name="reefexposure2", val=2)


@pytest.fixture
def reef_exposure3(db):
    return ReefExposure.objects.create(name="reefexposure3", val=3)


@pytest.fixture
def visibility1(db):
    return Visibility.objects.create(name="Near", val=1)


@pytest.fixture
def visibility2(db):
    return Visibility.objects.create(name="Mid", val=2)


@pytest.fixture
def visibility3(db):
    return Visibility.objects.create(name="Far", val=3)


@pytest.fixture
def tide1(db):
    return Tide.objects.create(name="Low")


@pytest.fixture
def tide2(db):
    return Tide.objects.create(name="High")


@pytest.fixture
def reef_slope1(db):
    return ReefSlope.objects.create(name="flat", val=1)


@pytest.fixture
def reef_slope2(db):
    return ReefSlope.objects.create(name="slope", val=2)


@pytest.fixture
def reef_slope3(db):
    return ReefSlope.objects.create(name="wall", val=3)


@pytest.fixture
def belt_transect_width_2m(db):
    return BeltTransectWidth.objects.create(name="2m")


@pytest.fixture
def belt_transect_width_5m(db):
    return BeltTransectWidth.objects.create(name="5m")


@pytest.fixture
def belt_transect_width_condition1(db, belt_transect_width_2m):
    return BeltTransectWidthCondition.objects.create(
        belttransectwidth=belt_transect_width_2m, val=2
    )


@pytest.fixture
def belt_transect_width_condition2(db, belt_transect_width_5m):
    return BeltTransectWidthCondition.objects.create(
        belttransectwidth=belt_transect_width_5m, val=5
    )


@pytest.fixture
def fish_size_bin_1(db):
    return FishSizeBin.objects.create(val="1")


@pytest.fixture
def fish_size_bin_5(db):
    return FishSizeBin.objects.create(val="5")


@pytest.fixture
def fish_size_bin_10(db):
    return FishSizeBin.objects.create(val="10")


@pytest.fixture
def habitat_complexity_score1(db):
    return HabitatComplexityScore.objects.create(name="no vertical relief", val=1)


@pytest.fixture
def habitat_complexity_score2(db):
    return HabitatComplexityScore.objects.create(name="low", val=2)


@pytest.fixture
def habitat_complexity_score3(db):
    return HabitatComplexityScore.objects.create(name="exceptionally complex", val=3)


@pytest.fixture
def managment_party1(db):
    return ManagementParty.objects.create(name="Government")


@pytest.fixture
def managment_party2(db):
    return ManagementParty.objects.create(name="NGO")


@pytest.fixture
def managment_party3(db):
    return ManagementParty.objects.create(name="Private Sector")


@pytest.fixture
def current1(db):
    return Current.objects.create(name="Weak", val=1)


@pytest.fixture
def current2(db):
    return Current.objects.create(name="Moderate", val=2)


@pytest.fixture
def current3(db):
    return Current.objects.create(name="Strong", val=3)


@pytest.fixture
def all_choices(db, 
    country1,
    country2,
    country3,
    reef_type1,
    reef_type2,
    reef_type3,
    reef_zone1,
    reef_zone2,
    reef_zone3,
    reef_exposure1,
    reef_exposure2,
    reef_exposure3,
    visibility1,
    visibility2,
    visibility3,
    tide1,
    tide2,
    reef_slope1,
    reef_slope2,
    reef_slope3,
    belt_transect_width_2m,
    belt_transect_width_5m,
    belt_transect_width_condition1,
    belt_transect_width_condition2,
    fish_size_bin_1,
    fish_size_bin_5,
    fish_size_bin_10,
    habitat_complexity_score1,
    habitat_complexity_score2,
    habitat_complexity_score3,
    managment_party1,
    managment_party2,
    managment_party3,
    current1,
    current2,
    current3
):
    pass



## FAMILY


@pytest.fixture
def fish_family1(db):
    return FishFamily.objects.create(name="Fish Family 1")


@pytest.fixture
def fish_family2(db):
    return FishFamily.objects.create(name="Fish Family 2")


@pytest.fixture
def fish_family3(db):
    return FishFamily.objects.create(name="Fish Family 3")


## GENUS


@pytest.fixture
def fish_genus1(db, fish_family1):
    return FishGenus.objects.create(name="Fish Genus 1", family=fish_family1)


@pytest.fixture
def fish_genus2(db, fish_family2):
    return FishGenus.objects.create(name="Fish Genus 2", family=fish_family2)


@pytest.fixture
def fish_genus3(db, fish_family3):
    return FishGenus.objects.create(name="Fish Genus 3", family=fish_family3)


## SPECIES


@pytest.fixture
def fish_species1(db, fish_genus1):
    return FishSpecies.objects.create(
        name="Fish Species 1",
        genus=fish_genus1,
        biomass_constant_a=0.010000,
        biomass_constant_b=3.010000,
        biomass_constant_c=1.0,
    )


@pytest.fixture
def fish_species2(db, fish_genus2):
    return FishSpecies.objects.create(
        name="Fish Species 2",
        genus=fish_genus2,
        biomass_constant_a=0.020000,
        biomass_constant_b=3.020000,
        biomass_constant_c=1.0,
    )


@pytest.fixture
def fish_species3(db, fish_genus3):
    return FishSpecies.objects.create(
        name="Fish Species 3",
        genus=fish_genus3,
        biomass_constant_a=0.030000,
        biomass_constant_b=3.030000,
        biomass_constant_c=1.0,
    )


@pytest.fixture
def all_test_fish(
    db,
    fish_family1,
    fish_family2,
    fish_family3,
    fish_genus1,
    fish_genus2,
    fish_genus3,
    fish_species1,
    fish_species2,
    fish_species3,
):
    pass
