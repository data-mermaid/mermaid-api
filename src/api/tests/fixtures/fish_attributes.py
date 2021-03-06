import pytest

from api.models import FishFamily, FishGenus, FishGroupTrophic, FishSpecies


@pytest.fixture
def fish_group_trophic_1(db):
    return FishGroupTrophic.objects.create(name="omnivore")


@pytest.fixture
def fish_family1(db):
    return FishFamily.objects.create(name="Fish Family 1")


@pytest.fixture
def fish_family2(db):
    return FishFamily.objects.create(name="Fish Family 2")


@pytest.fixture
def fish_family3(db):
    return FishFamily.objects.create(name="Fish Family 3")


@pytest.fixture
def fish_genus1(db, fish_family1):
    return FishGenus.objects.create(name="Fish Genus 1", family=fish_family1)


@pytest.fixture
def fish_genus2(db, fish_family2):
    return FishGenus.objects.create(name="Fish Genus 2", family=fish_family2)


@pytest.fixture
def fish_genus3(db, fish_family3):
    return FishGenus.objects.create(name="Fish Genus 3", family=fish_family3)


@pytest.fixture
def fish_species1(db, fish_genus1, fish_group_trophic_1):
    return FishSpecies.objects.create(
        name="Fish Species 1",
        genus=fish_genus1,
        biomass_constant_a=0.010000,
        biomass_constant_b=3.010000,
        biomass_constant_c=1.0,
        trophic_group = fish_group_trophic_1
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
def all_test_fish_attributes(
    db, fish_species1, fish_species2, fish_species3,
):
    pass
