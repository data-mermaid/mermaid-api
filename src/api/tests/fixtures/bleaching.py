import pytest

from api.models import (
    BleachingQuadratCollection,
    ObsColoniesBleached,
    Observer,
    ObsQuadratBenthicPercent,
    QuadratCollection,
)


@pytest.fixture
def quadrat_collection1(
    db, sample_event1, current1, relative_depth1, tide1, visibility1,
):
    return QuadratCollection.objects.create(
        sample_event=sample_event1,
        current=current1,
        relative_depth=relative_depth1,
        tide=tide1,
        visibility=visibility1,
        depth=5,
        quadrat_size=1,
        sample_time="11:00:00",
    )


@pytest.fixture
def quadrat_collection2(
    db, sample_event2, current2, relative_depth1, tide1, visibility2,
):
    return QuadratCollection.objects.create(
        sample_event=sample_event2,
        current=current2,
        relative_depth=relative_depth1,
        tide=tide1,
        visibility=visibility2,
        depth=10,
        quadrat_size=1,
        sample_time="13:00:00",
    )


@pytest.fixture
def bleaching_quadrat_collection1(db, quadrat_collection1):
    return BleachingQuadratCollection.objects.create(quadrat=quadrat_collection1)


@pytest.fixture
def bleaching_quadrat_collection2(db, quadrat_collection2):
    return BleachingQuadratCollection.objects.create(quadrat=quadrat_collection2)


@pytest.fixture
def observer_bleaching_quadrat_collection1(db, bleaching_quadrat_collection1, profile1):
    return Observer.objects.create(
        transectmethod=bleaching_quadrat_collection1, profile=profile1
    )


@pytest.fixture
def observer_bleaching_quadrat_collection2(db, bleaching_quadrat_collection2, profile1):
    return Observer.objects.create(
        transectmethod=bleaching_quadrat_collection2, profile=profile1
    )


@pytest.fixture
def obs_colonies_bleached1_1(db, bleaching_quadrat_collection1, benthic_attribute_2a1):
    return ObsColoniesBleached.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        attribute=benthic_attribute_2a1,
        count_normal=10,
        count_pale=15,
        count_20=0,
        count_50=25,
        count_80=0,
        count_100=0,
        count_dead=50,
    )


@pytest.fixture
def obs_colonies_bleached1_2(db, bleaching_quadrat_collection1, benthic_attribute_2a):
    return ObsColoniesBleached.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        attribute=benthic_attribute_2a,
        count_normal=5,
        count_pale=30,
        count_20=0,
        count_50=25,
        count_80=20,
        count_100=0,
        count_dead=20,
    )


@pytest.fixture
def obs_colonies_bleached1_3(db, bleaching_quadrat_collection1, benthic_attribute_2a1):
    return ObsColoniesBleached.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        attribute=benthic_attribute_2a1,
        count_normal=10,
        count_pale=15,
        count_20=0,
        count_50=25,
        count_80=0,
        count_100=0,
        count_dead=50,
    )


@pytest.fixture
def obs_colonies_bleached1_4(db, bleaching_quadrat_collection1, benthic_attribute_2b1):
    return ObsColoniesBleached.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        attribute=benthic_attribute_2b1,
        count_normal=0,
        count_pale=30,
        count_20=0,
        count_50=50,
        count_80=0,
        count_100=0,
        count_dead=20,
    )


@pytest.fixture
def obs_colonies_bleached1_5(db, bleaching_quadrat_collection1, benthic_attribute_2b):
    return ObsColoniesBleached.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        attribute=benthic_attribute_2b,
        count_normal=0,
        count_pale=30,
        count_20=40,
        count_50=20,
        count_80=0,
        count_100=0,
        count_dead=10,
    )


@pytest.fixture
def obs_quadrat_benthic_percent1_1(
    db, bleaching_quadrat_collection1, benthic_attribute_2a1
):
    return ObsQuadratBenthicPercent.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        quadrat_number=1,
        percent_hard=90,
        percent_soft=3,
        percent_algae=2,
    )


@pytest.fixture
def obs_quadrat_benthic_percent1_2(db, bleaching_quadrat_collection1):
    return ObsQuadratBenthicPercent.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        quadrat_number=2,
        percent_hard=75,
        percent_soft=25,
        percent_algae=0,
    )


@pytest.fixture
def obs_quadrat_benthic_percent1_3(db, bleaching_quadrat_collection1):
    return ObsQuadratBenthicPercent.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        quadrat_number=3,
        percent_hard=55,
        percent_soft=15,
        percent_algae=30,
    )


@pytest.fixture
def obs_quadrat_benthic_percent1_4(db, bleaching_quadrat_collection1):
    return ObsQuadratBenthicPercent.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        quadrat_number=4,
        percent_hard=63,
        percent_soft=27,
        percent_algae=10,
    )


@pytest.fixture
def obs_quadrat_benthic_percent1_5(db, bleaching_quadrat_collection1):
    return ObsQuadratBenthicPercent.objects.create(
        bleachingquadratcollection=bleaching_quadrat_collection1,
        quadrat_number=5,
        percent_hard=12,
        percent_soft=28,
        percent_algae=60,
    )


@pytest.fixture
def bleaching_project(
    db,
    obs_colonies_bleached1_1,
    obs_colonies_bleached1_2,
    obs_colonies_bleached1_3,
    obs_colonies_bleached1_4,
    obs_colonies_bleached1_5,
    obs_quadrat_benthic_percent1_1,
    obs_quadrat_benthic_percent1_2,
    obs_quadrat_benthic_percent1_3,
    obs_quadrat_benthic_percent1_4,
    obs_quadrat_benthic_percent1_5,
    observer_bleaching_quadrat_collection1,
    observer_bleaching_quadrat_collection2,
    project_profile1,
    project_profile2,
):
    pass
