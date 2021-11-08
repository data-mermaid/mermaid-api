import pytest

from api.models import FishFamily, FishGenus, FishGroupTrophic, FishSpecies


@pytest.fixture
def fish_group_trophic_1():
    return FishGroupTrophic.objects.create(name="omnivore")


@pytest.fixture
def fish_family1():
    return FishFamily.objects.create(name="Fish Family 1")


@pytest.fixture
def fish_family2():
    return FishFamily.objects.create(name="Fish Family 2")


@pytest.fixture
def fish_family3():
    return FishFamily.objects.create(name="Fish Family 3")


@pytest.fixture
def fish_family4():
    return FishFamily.objects.create(name="Clown Fish Family")


@pytest.fixture
def fish_genus1(fish_family1):
    return FishGenus.objects.create(name="Fish Genus 1", family=fish_family1)


@pytest.fixture
def fish_genus2(fish_family2):
    return FishGenus.objects.create(name="Fish Genus 2", family=fish_family2)


@pytest.fixture
def fish_genus3(fish_family3):
    return FishGenus.objects.create(name="Fish Genus 3", family=fish_family3)


@pytest.fixture
def fish_genus4(fish_family4):
    return FishGenus.objects.create(name="Clown Fish Genus", family=fish_family4)


@pytest.fixture
def fish_species1(fish_genus1, fish_group_trophic_1, region1, region3):
    fs = FishSpecies.objects.create(
        name="Fish Species 1",
        genus=fish_genus1,
        biomass_constant_a=0.010000,
        biomass_constant_b=3.010000,
        biomass_constant_c=1.0,
        trophic_group=fish_group_trophic_1,
        max_length=41,
    )
    fs.regions.add(region1)
    fs.regions.add(region3)

    return fs


@pytest.fixture
def fish_species2(fish_genus2, region2):
    fs = FishSpecies.objects.create(
        name="Fish Species 2",
        genus=fish_genus2,
        biomass_constant_a=0.020000,
        biomass_constant_b=3.020000,
        biomass_constant_c=1.0,
        max_length=32,
    )
    fs.regions.add(region2)

    return fs


@pytest.fixture
def fish_species3(fish_genus3, region2, region3):
    fs = FishSpecies.objects.create(
        name="Fish Species 3",
        genus=fish_genus3,
        biomass_constant_a=0.030000,
        biomass_constant_b=3.030000,
        biomass_constant_c=1.0,
        max_length=55,
    )
    fs.regions.add(region2)
    fs.regions.add(region3)

    return fs


@pytest.fixture
def fish_species4(fish_genus3, region2):
    fs = FishSpecies.objects.create(
        name="Fish Species 4",
        genus=fish_genus3,
        biomass_constant_a=0.01,
        biomass_constant_b=3.06,
        biomass_constant_c=1.0,
        max_length=21,
    )
    fs.regions.add(region2)

    return fs


@pytest.fixture
def all_test_fish_attributes(
    fish_species1, fish_species2, fish_species3, fish_species4
):
    pass
