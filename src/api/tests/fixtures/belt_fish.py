import pytest

from api.models import (
    BeltFish,
    BeltTransectWidth,
    BeltTransectWidthCondition,
    FishBeltTransect,
    FishSizeBin,
    ObsBeltFish,
    Observer,
)
from api.utils import calc_biomass_density


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
def observer_belt_fish1(db, belt_fish1, profile1):
    return Observer.objects.create(transectmethod=belt_fish1, profile=profile1)


@pytest.fixture
def observer_belt_fish2(db, belt_fish2, profile2):
    return Observer.objects.create(transectmethod=belt_fish2, profile=profile2)


@pytest.fixture
def obs_belt_fish1_1(db, belt_fish1, fish_species1):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish1, fish_attribute=fish_species1, size=10.0, count=5
    )


@pytest.fixture
def obs_belt_fish1_2(db, belt_fish1, fish_species2):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish1, fish_attribute=fish_species2, size=10.0, count=10
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
def obs_belt_fish2_4(db, belt_fish2, fish_species2):
    return ObsBeltFish.objects.create(
        beltfish=belt_fish2, fish_attribute=fish_species2, size=10.0, count=5
    )


@pytest.fixture
def obs_belt_fish1_1_biomass(db, obs_belt_fish1_1, belt_fish1):
    return calc_biomass_density(
        count=obs_belt_fish1_1.count,
        size=obs_belt_fish1_1.size,
        transect_len_surveyed=belt_fish1.transect.len_surveyed,
        transect_width=belt_fish1.transect.width.get_condition(obs_belt_fish1_1.size).val,
        constant_a=obs_belt_fish1_1.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish1_1.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish1_1.fish_attribute.biomass_constant_c,
    )


@pytest.fixture
def obs_belt_fish1_2_biomass(db, obs_belt_fish1_2, belt_fish1):
    return calc_biomass_density(
        count=obs_belt_fish1_2.count,
        size=obs_belt_fish1_2.size,
        transect_len_surveyed=belt_fish1.transect.len_surveyed,
        transect_width=belt_fish1.transect.width.get_condition(obs_belt_fish1_2.size).val,
        constant_a=obs_belt_fish1_2.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish1_2.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish1_2.fish_attribute.biomass_constant_c,
    )


@pytest.fixture
def obs_belt_fish1_3_biomass(db, obs_belt_fish1_3, belt_fish1):
    return calc_biomass_density(
        count=obs_belt_fish1_3.count,
        size=obs_belt_fish1_3.size,
        transect_len_surveyed=belt_fish1.transect.len_surveyed,
        transect_width=belt_fish1.transect.width.get_condition(obs_belt_fish1_3.size).val,
        constant_a=obs_belt_fish1_3.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish1_3.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish1_3.fish_attribute.biomass_constant_c,
    )


@pytest.fixture
def obs_belt_fish2_1_biomass(db, obs_belt_fish2_1, belt_fish2):
    return calc_biomass_density(
        count=obs_belt_fish2_1.count,
        size=obs_belt_fish2_1.size,
        transect_len_surveyed=belt_fish2.transect.len_surveyed,
        transect_width=belt_fish2.transect.width.get_condition(obs_belt_fish2_1.size).val,
        constant_a=obs_belt_fish2_1.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish2_1.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish2_1.fish_attribute.biomass_constant_c,
    )


@pytest.fixture
def obs_belt_fish2_2_biomass(db, obs_belt_fish2_2, belt_fish2):
    return calc_biomass_density(
        count=obs_belt_fish2_2.count,
        size=obs_belt_fish2_2.size,
        transect_len_surveyed=belt_fish2.transect.len_surveyed,
        transect_width=belt_fish2.transect.width.get_condition(obs_belt_fish2_2.size).val,
        constant_a=obs_belt_fish2_2.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish2_2.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish2_2.fish_attribute.biomass_constant_c,
    )


@pytest.fixture
def obs_belt_fish2_3_biomass(db, obs_belt_fish2_3, belt_fish2):
    return calc_biomass_density(
        count=obs_belt_fish2_3.count,
        size=obs_belt_fish2_3.size,
        transect_len_surveyed=belt_fish2.transect.len_surveyed,
        transect_width=belt_fish2.transect.width.get_condition(obs_belt_fish2_3.size).val,
        constant_a=obs_belt_fish2_3.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish2_3.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish2_3.fish_attribute.biomass_constant_c,
    )

@pytest.fixture
def obs_belt_fish2_4_biomass(db, obs_belt_fish2_4, belt_fish2):
    return calc_biomass_density(
        count=obs_belt_fish2_4.count,
        size=obs_belt_fish2_4.size,
        transect_len_surveyed=belt_fish2.transect.len_surveyed,
        transect_width=belt_fish2.transect.width.get_condition(obs_belt_fish2_4.size).val,
        constant_a=obs_belt_fish2_4.fish_attribute.biomass_constant_a,
        constant_b=obs_belt_fish2_4.fish_attribute.biomass_constant_b,
        constant_c=obs_belt_fish2_4.fish_attribute.biomass_constant_c,
    )
    


@pytest.fixture
def belt_fish_project(
    db,
    belt_transect_width_2m,
    belt_transect_width_5m,
    belt_transect_width_condition1,
    belt_transect_width_condition2,
    fish_size_bin_1,
    fish_size_bin_10,
    fish_size_bin_5,
    obs_belt_fish1_1,
    obs_belt_fish1_2,
    obs_belt_fish1_3,
    obs_belt_fish2_1,
    obs_belt_fish2_2,
    obs_belt_fish2_3,
    obs_belt_fish2_4,
    observer_belt_fish1,
    observer_belt_fish2,
    project_profile1,
    project_profile2,
):
    pass


@pytest.fixture
def obs_belt_fishes_low_biomass_invalid(fish_species4):
    fish_species_id = str(fish_species4.id)
    return [
        dict(
            count=1,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=32,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=44,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=1,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=3,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
    ]


@pytest.fixture
def obs_belt_fishes_high_biomass_invalid(fish_species4):
    fish_species_id = str(fish_species4.id)
    return [
        dict(
            count=7003,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=3200,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=4455,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=4100,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=3000,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
    ]


@pytest.fixture
def obs_belt_fishes_biomass_valid(fish_species4):
    fish_species_id = str(fish_species4.id)
    return [
        dict(
            count=2403,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=32,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=445,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=1100,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
        dict(
            count=3000,
            fish_attribute=fish_species_id,
            size=7.5,
        ),
    ]


@pytest.fixture
def obs_belt_fishes_invalid():
    return [
        dict(count=1),
        dict(count=2),
        dict(count=3),
        dict(count=1),
    ]


@pytest.fixture
def obs_belt_fishes_valid():
    return [
        dict(count=1),
        dict(count=2),
        dict(count=3),
        dict(count=1),
        dict(count=10),
    ]
