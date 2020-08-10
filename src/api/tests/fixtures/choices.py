import pytest

from api.models import (
    BeltTransectWidth,
    BeltTransectWidthCondition,
    Country,
    Current,
    FishSizeBin,
    HabitatComplexityScore,
    ManagementParty,
    ReefExposure,
    ReefSlope,
    ReefType,
    ReefZone,
    RelativeDepth,
    Tide,
    Visibility,
)


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
def relative_depth1(db):
    return RelativeDepth.objects.create(name="Shallow")


@pytest.fixture
def relative_depth2(db):
    return RelativeDepth.objects.create(name="Deep")


@pytest.fixture
def all_choices(
    db,
    belt_transect_width_2m,
    belt_transect_width_5m,
    belt_transect_width_condition1,
    belt_transect_width_condition2,
    country1,
    country2,
    country3,
    current1,
    current2,
    current3,
    fish_size_bin_1,
    fish_size_bin_10,
    fish_size_bin_5,
    habitat_complexity_score1,
    habitat_complexity_score2,
    habitat_complexity_score3,
    managment_party1,
    managment_party2,
    managment_party3,
    reef_exposure1,
    reef_exposure2,
    reef_exposure3,
    reef_slope1,
    reef_slope2,
    reef_slope3,
    reef_type1,
    reef_type2,
    reef_type3,
    reef_zone1,
    reef_zone2,
    reef_zone3,
    relative_depth1,
    relative_depth2,
    tide1,
    tide2,
    visibility1,
    visibility2,
    visibility3,
):
    pass
