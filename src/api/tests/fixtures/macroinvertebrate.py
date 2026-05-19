import pytest

from api.models import (
    SUPERUSER_APPROVED,
    BeltInvert,
    InvertBeltTransect,
    InvertBeltTransectWidth,
    InvertClass,
    InvertClassGroupOfInterest,
    InvertFamily,
    InvertGenus,
    InvertGroupOfInterest,
    InvertOrder,
    InvertSizeBin,
    InvertSpecies,
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
    return InvertGroupOfInterest.objects.create(name="Sea urchins")


@pytest.fixture
def invert_class_1(db):
    return InvertClass.objects.create(name="Echinoidea")


@pytest.fixture
def invert_class_goi_1(db, invert_class_1, invert_group_of_interest_1):
    return InvertClassGroupOfInterest.objects.create(
        invert_class=invert_class_1,
        group_of_interest=invert_group_of_interest_1,
        status=SUPERUSER_APPROVED,
    )


@pytest.fixture
def invert_order_1(db, invert_class_goi_1):
    return InvertOrder.objects.create(
        name="Camarodonta",
        class_goi=invert_class_goi_1,
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
def invert_genus_1(db, invert_family_1):
    return InvertGenus.objects.create(
        name="Strongylocentrotus",
        family=invert_family_1,
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
def all_test_invert_attributes(
    invert_class_goi_1, invert_order_1, invert_family_1, invert_genus_1, invert_species_1
):
    return [invert_class_goi_1, invert_order_1, invert_family_1, invert_genus_1, invert_species_1]


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
