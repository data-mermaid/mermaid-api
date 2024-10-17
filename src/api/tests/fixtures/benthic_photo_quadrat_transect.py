import pytest

from api.models import (
    BenthicPhotoQuadratTransect,
    ObsBenthicPhotoQuadrat,
    Observer,
    QuadratTransect,
)


@pytest.fixture
def quadrat_transect1(
    db, sample_event1, current1, reef_slope1, relative_depth1, tide1, visibility1
):
    return QuadratTransect.objects.create(
        quadrat_size=1,
        num_quadrats=2,
        num_points_per_quadrat=100,
        quadrat_number_start=1,
        sample_event=sample_event1,
        current=current1,
        reef_slope=reef_slope1,
        relative_depth=relative_depth1,
        tide=tide1,
        visibility=visibility1,
        depth=5,
        len_surveyed=50,
        sample_time="11:00:00",
    )


@pytest.fixture
def benthic_photo_quadrat_transect1(db, quadrat_transect1):
    return BenthicPhotoQuadratTransect.objects.create(quadrat_transect=quadrat_transect1)


@pytest.fixture
def observer_benthic_photo_quadrat_transect1(benthic_photo_quadrat_transect1, profile1):
    return Observer.objects.create(transectmethod=benthic_photo_quadrat_transect1, profile=profile1)


@pytest.fixture
def obs_benthic_photo_quadrat1_1(db, benthic_photo_quadrat_transect1, benthic_attribute_1a):
    return ObsBenthicPhotoQuadrat.objects.create(
        benthic_photo_quadrat_transect=benthic_photo_quadrat_transect1,
        quadrat_number=1,
        attribute=benthic_attribute_1a,
        num_points=49,
    )


@pytest.fixture
def obs_benthic_photo_quadrat1_2(db, benthic_photo_quadrat_transect1, benthic_attribute_2a):
    return ObsBenthicPhotoQuadrat.objects.create(
        benthic_photo_quadrat_transect=benthic_photo_quadrat_transect1,
        quadrat_number=1,
        attribute=benthic_attribute_2a,
        num_points=51,
    )


@pytest.fixture
def obs_benthic_photo_quadrat1_3(
    db, benthic_photo_quadrat_transect1, benthic_attribute_2b, growth_form1
):
    return ObsBenthicPhotoQuadrat.objects.create(
        benthic_photo_quadrat_transect=benthic_photo_quadrat_transect1,
        quadrat_number=2,
        attribute=benthic_attribute_2b,
        num_points=25,
        growth_form=growth_form1,
    )


@pytest.fixture
def obs_benthic_photo_quadrat1_4(
    db, benthic_photo_quadrat_transect1, benthic_attribute_2b1, growth_form4
):
    return ObsBenthicPhotoQuadrat.objects.create(
        benthic_photo_quadrat_transect=benthic_photo_quadrat_transect1,
        quadrat_number=2,
        attribute=benthic_attribute_2b1,
        num_points=25,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_photo_quadrat1_5(
    db, benthic_photo_quadrat_transect1, benthic_attribute_3, growth_form4
):
    return ObsBenthicPhotoQuadrat.objects.create(
        benthic_photo_quadrat_transect=benthic_photo_quadrat_transect1,
        quadrat_number=2,
        attribute=benthic_attribute_3,
        num_points=50,
        growth_form=growth_form4,
    )


@pytest.fixture
def benthic_photo_quadrat_transect_project(
    db,
    all_life_histories,
    obs_benthic_photo_quadrat1_1,
    obs_benthic_photo_quadrat1_2,
    obs_benthic_photo_quadrat1_3,
    obs_benthic_photo_quadrat1_4,
    obs_benthic_photo_quadrat1_5,
    observer_benthic_photo_quadrat_transect1,
    project_profile1,
    project_profile2,
):
    pass
