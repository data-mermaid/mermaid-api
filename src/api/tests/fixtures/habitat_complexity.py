import pytest

from api.models import (
    HabitatComplexity,
    HabitatComplexityScore,
    Observer,
    ObsHabitatComplexity,
)


@pytest.fixture
def habitat_complexity1(db, benthic_transect1):
    return HabitatComplexity.objects.create(
        transect=benthic_transect1, interval_size=1, interval_start=1
    )


@pytest.fixture
def habitat_complexity2(db, benthic_transect2):
    return HabitatComplexity.objects.create(
        transect=benthic_transect2, interval_size=0.5, interval_start=0.5
    )


@pytest.fixture
def observer_habitat_complexity1(db, habitat_complexity1, profile1):
    return Observer.objects.create(transectmethod=habitat_complexity1, profile=profile1)


@pytest.fixture
def observer_habitat_complexity2(db, habitat_complexity2, profile2):
    return Observer.objects.create(transectmethod=habitat_complexity2, profile=profile2)


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
def obs_habitat_complexity1_1(db, habitat_complexity1, habitat_complexity_score1):
    return ObsHabitatComplexity.objects.create(
        habitatcomplexity=habitat_complexity1,
        interval=1,
        score=habitat_complexity_score1,
    )


@pytest.fixture
def obs_habitat_complexity1_2(db, habitat_complexity1, habitat_complexity_score2):
    return ObsHabitatComplexity.objects.create(
        habitatcomplexity=habitat_complexity1,
        interval=2,
        score=habitat_complexity_score2,
    )


@pytest.fixture
def obs_habitat_complexity1_3(db, habitat_complexity1, habitat_complexity_score3):
    return ObsHabitatComplexity.objects.create(
        habitatcomplexity=habitat_complexity1,
        interval=3,
        score=habitat_complexity_score3,
    )


@pytest.fixture
def obs_habitat_complexity2_1(db, habitat_complexity2, habitat_complexity_score2):
    return ObsHabitatComplexity.objects.create(
        habitatcomplexity=habitat_complexity2,
        interval=1,
        score=habitat_complexity_score2,
    )


@pytest.fixture
def obs_habitat_complexity2_2(db, habitat_complexity2, habitat_complexity_score3):
    return ObsHabitatComplexity.objects.create(
        habitatcomplexity=habitat_complexity2,
        interval=2,
        score=habitat_complexity_score3,
    )


@pytest.fixture
def obs_habitat_complexity2_3(db, habitat_complexity2, habitat_complexity_score1):
    return ObsHabitatComplexity.objects.create(
        habitatcomplexity=habitat_complexity2,
        interval=3,
        score=habitat_complexity_score1,
    )


@pytest.fixture
def habitat_complexity_project(
    db,
    habitat_complexity_score1,
    habitat_complexity_score2,
    habitat_complexity_score3,
    obs_habitat_complexity1_1,
    obs_habitat_complexity1_2,
    obs_habitat_complexity1_3,
    obs_habitat_complexity2_1,
    obs_habitat_complexity2_2,
    obs_habitat_complexity2_3,
    observer_habitat_complexity1,
    observer_habitat_complexity2,
    project_profile1,
    project_profile2,
):
    pass
