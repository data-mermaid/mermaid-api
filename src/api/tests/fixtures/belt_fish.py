import pytest

from api.models import BeltFish, FishBeltTransect, ObsBeltFish, Observer


@pytest.fixture
def fishbelt_transect1(
    db,
    sample_event1,
    current1,
    reef_slope1,
    relative_depth1,
    fish_size_bin_1,
    tide1,
    visibility1,
    belt_transect_width_2m,
):
    return FishBeltTransect.objects.create(
        sample_event=sample_event1,
        current=current1,
        reef_slope=reef_slope1,
        relative_depth=relative_depth1,
        size_bin=fish_size_bin_1,
        tide=tide1,
        visibility=visibility1,
        width=belt_transect_width_2m,
        depth=5,
        len_surveyed=50,
        sample_time="11:00:00",
    )


@pytest.fixture
def fishbelt_transect2(
    db,
    sample_event2,
    current2,
    reef_slope2,
    relative_depth2,
    fish_size_bin_5,
    tide2,
    visibility2,
    belt_transect_width_2m,
):
    return FishBeltTransect.objects.create(
        sample_event=sample_event2,
        current=current2,
        reef_slope=reef_slope2,
        relative_depth=relative_depth2,
        size_bin=fish_size_bin_5,
        tide=tide2,
        visibility=visibility2,
        width=belt_transect_width_2m,
        depth=2,
        len_surveyed=10,
        sample_time="10:00:00",
    )


@pytest.fixture
def belt_fish1(db, fishbelt_transect1):
    return BeltFish.objects.create(transect=fishbelt_transect1)


@pytest.fixture
def belt_fish2(db, fishbelt_transect2):
    return BeltFish.objects.create(transect=fishbelt_transect2)


@pytest.fixture
def observer1(db, belt_fish1, profile1):
    return Observer.objects.create(transectmethod=belt_fish1, profile=profile1)


@pytest.fixture
def observer2(db, belt_fish2, profile2):
    return Observer.objects.create(transectmethod=belt_fish2, profile=profile2)


@pytest.fixture
def obs_belt_fish1_1(db, belt_fish1, fish_species1):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish1, fish_attribute=fish_species1, size=10.0, count=5
    )


@pytest.fixture
def obs_belt_fish1_2(db, belt_fish2, fish_species2):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish2, fish_attribute=fish_species2, size=10.0, count=10
    )


@pytest.fixture
def obs_belt_fish1_3(db, belt_fish1, fish_species3):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish1, fish_attribute=fish_species3, size=10.0, count=23
    )


@pytest.fixture
def obs_belt_fish2_1(db, belt_fish2, fish_species2):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish2, fish_attribute=fish_species2, size=20.0, count=11
    )


@pytest.fixture
def obs_belt_fish2_2(db, belt_fish2, fish_species3):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish2, fish_attribute=fish_species3, size=20.0, count=17
    )


@pytest.fixture
def obs_belt_fish2_3(db, belt_fish2, fish_species1):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish2, fish_attribute=fish_species1, size=20.0, count=3
    )


@pytest.fixture
def belt_fish_project(
    db,
    obs_belt_fish1_1,
    obs_belt_fish1_2,
    obs_belt_fish1_3,
    obs_belt_fish2_1,
    obs_belt_fish2_2,
    obs_belt_fish2_3,
    observer1,
    observer2,
    project_profile1,
    project_profile2,
):
    pass
