from decimal import Decimal

import pytest

from api.models import (
    SUPERUSER_APPROVED,
    BeltInvert,
    InvertBeltTransect,
    InvertBeltTransectWidth,
    InvertClass,
    InvertFamily,
    InvertGenus,
    InvertGroupOfInterest,
    InvertOrder,
    InvertSizeBin,
    InvertSpecies,
    ObsBeltInvert,
    Observer,
)


@pytest.fixture
def invert_belt_transect_width_1m(db):
    return InvertBeltTransectWidth.objects.create(val=1, name="1m")


@pytest.fixture
def invert_belt_transect_width_2m(db):
    return InvertBeltTransectWidth.objects.create(val=2, name="2m")


@pytest.fixture
def invert_size_bin_1(db):
    return InvertSizeBin.objects.create(val="1")


@pytest.fixture
def invert_size_bin_2(db):
    return InvertSizeBin.objects.create(val="2")


@pytest.fixture
def invert_group_of_interest_1(db):
    return InvertGroupOfInterest.objects.create(name="Sea urchins", status=SUPERUSER_APPROVED)


@pytest.fixture
def invert_group_of_interest_2(db):
    return InvertGroupOfInterest.objects.create(
        name="Crown-of-thorns starfish (COTS)", status=SUPERUSER_APPROVED
    )


@pytest.fixture
def invert_class_1(db):
    return InvertClass.objects.create(name="Echinoidea", status=SUPERUSER_APPROVED)


@pytest.fixture
def invert_order_1(db, invert_class_1):
    return InvertOrder.objects.create(
        name="Camarodonta",
        invert_class=invert_class_1,
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_family_1(db, invert_order_1):
    return InvertFamily.objects.create(
        name="Strongylocentrotidae",
        order=invert_order_1,
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_genus_1(db, invert_family_1, invert_group_of_interest_1):
    return InvertGenus.objects.create(
        name="Strongylocentrotus",
        family=invert_family_1,
        group_of_interest=invert_group_of_interest_1,
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_genus_2(db, invert_family_1, invert_group_of_interest_2):
    # Second genus in invert_family_1, mapped to a different GoI than invert_genus_1.
    # Used to test equal-split GoI attribution for family-level observations.
    return InvertGenus.objects.create(
        name="Acanthaster",
        family=invert_family_1,
        group_of_interest=invert_group_of_interest_2,
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_genus_3(db, invert_family_1, invert_group_of_interest_1):
    # Third genus in invert_family_1, same GoI as invert_genus_1. Makes the family
    # 2:1 across GoI_1 vs GoI_2 so that equal-split (1/2 each) and genus-proportion
    # (2/3 vs 1/3) produce different numbers — allowing tests to discriminate them.
    return InvertGenus.objects.create(
        name="Paracentrotus",
        family=invert_family_1,
        group_of_interest=invert_group_of_interest_1,
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_species_1(db, invert_genus_1):
    return InvertSpecies.objects.create(
        name="purpuratus",
        genus=invert_genus_1,
        max_length=8,
        max_length_type="test diameter",
        notes="Purple sea urchin",
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_goi_attribute_1(db, invert_group_of_interest_1):
    # InvertGroupOfInterest is now an InvertAttribute subclass; the fixture
    # returns the GoI record, which IS the attribute.
    return invert_group_of_interest_1


@pytest.fixture
def all_test_invert_attributes(
    invert_goi_attribute_1,
    invert_class_1,
    invert_order_1,
    invert_family_1,
    invert_genus_1,
    invert_species_1,
):
    return [
        invert_goi_attribute_1,
        invert_class_1,
        invert_order_1,
        invert_family_1,
        invert_genus_1,
        invert_species_1,
    ]


@pytest.fixture
def invert_belt_transect1(
    db,
    sample_event1,
    current1,
    reef_slope1,
    relative_depth1,
    tide1,
    visibility1,
    invert_belt_transect_width_1m,
    invert_size_bin_1,
):
    return InvertBeltTransect.objects.create(
        sample_event=sample_event1,
        current=current1,
        reef_slope=reef_slope1,
        relative_depth=relative_depth1,
        tide=tide1,
        visibility=visibility1,
        width=invert_belt_transect_width_1m,
        size_bin=invert_size_bin_1,
        depth=5,
        len_surveyed=50,
        number=1,
    )


@pytest.fixture
def belt_invert1(db, invert_belt_transect1, profile1, project_profile1):
    beltinvert = BeltInvert.objects.create(transect=invert_belt_transect1)
    Observer.objects.create(transectmethod=beltinvert, profile=profile1, rank=1)
    return beltinvert


@pytest.fixture
def belt_invert1_with_obs(db, belt_invert1, invert_genus_1):
    ObsBeltInvert.objects.create(
        beltinvert=belt_invert1,
        invert_attribute=invert_genus_1,
        count=3,
        size=Decimal("2.5"),
    )
    return belt_invert1


@pytest.fixture
def belt_invert1_with_goi_obs(
    db, belt_invert1, invert_genus_1, invert_genus_2, invert_genus_3, invert_family_1
):
    # invert_genus_1 and invert_genus_3 -> GoI 1 ("Sea urchins"); invert_genus_2 ->
    # GoI 2 ("COTS"). All three are in invert_family_1, giving a 2:1 genus ratio.
    # Equal-split sees 2 distinct GoIs → weight 0.5 each (density 1600/1000).
    # Genus-proportion would give weights 2/3 vs 1/3 (density ~1933/~667) — so the
    # assertions below only pass under equal-split, catching a regression to the old logic.
    # invert_genus_3 is not directly observed; it exists only to set the 2:1 ratio.
    ObsBeltInvert.objects.create(
        beltinvert=belt_invert1,
        invert_attribute=invert_genus_1,
        count=3,
        size=Decimal("2.5"),
    )
    ObsBeltInvert.objects.create(
        beltinvert=belt_invert1,
        invert_attribute=invert_family_1,
        count=10,
        size=Decimal("3.0"),
    )
    return belt_invert1
