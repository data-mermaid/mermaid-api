import pytest

from api.models import BenthicLIT, ObsBenthicLIT, Observer


@pytest.fixture
def benthic_lit1(db, benthic_transect1):
    return BenthicLIT.objects.create(transect=benthic_transect1)


@pytest.fixture
def benthic_lit2(db, benthic_transect2):
    return BenthicLIT.objects.create(transect=benthic_transect2)


@pytest.fixture
def observer_benthic_lit1(db, benthic_lit1, profile1):
    return Observer.objects.create(transectmethod=benthic_lit1, profile=profile1)


@pytest.fixture
def observer_benthic_lit2(db, benthic_lit2, profile2):
    return Observer.objects.create(transectmethod=benthic_lit2, profile=profile2)


@pytest.fixture
def obs_benthic_lit1_1(db, benthic_lit1, benthic_attribute_1a):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit1, attribute=benthic_attribute_1a, length=11
    )


@pytest.fixture
def obs_benthic_lit1_2(db, benthic_lit1, benthic_attribute_2a):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit1, attribute=benthic_attribute_2a, length=12
    )


@pytest.fixture
def obs_benthic_lit1_3(db, benthic_lit1, benthic_attribute_2b, growth_form1):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit1,
        attribute=benthic_attribute_2b,
        length=13,
        growth_form=growth_form1,
    )


@pytest.fixture
def obs_benthic_lit1_4(db, benthic_lit1, benthic_attribute_2b1, growth_form4):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit1,
        attribute=benthic_attribute_2b1,
        length=14,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_lit1_5(db, benthic_lit1, benthic_attribute_3, growth_form4):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit1,
        attribute=benthic_attribute_3,
        length=15,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_lit2_1(db, benthic_lit2, benthic_attribute_2):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit2, attribute=benthic_attribute_2, length=11
    )


@pytest.fixture
def obs_benthic_lit2_2(db, benthic_lit2, benthic_attribute_3):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit2, attribute=benthic_attribute_3, length=12
    )


@pytest.fixture
def obs_benthic_lit2_3(db, benthic_lit2, benthic_attribute_2b, growth_form1):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit2,
        attribute=benthic_attribute_2b,
        length=13,
        growth_form=growth_form1,
    )


@pytest.fixture
def obs_benthic_lit2_4(db, benthic_lit2, benthic_attribute_2b1, growth_form4):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit2,
        attribute=benthic_attribute_2b1,
        length=14,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_lit2_5(db, benthic_lit2, benthic_attribute_3, growth_form4):
    return ObsBenthicLIT.objects.create(
        benthiclit=benthic_lit2,
        attribute=benthic_attribute_3,
        length=15,
        growth_form=growth_form4,
    )


@pytest.fixture
def benthic_lit_project(
    db,
    obs_benthic_lit1_1,
    obs_benthic_lit1_2,
    obs_benthic_lit1_3,
    obs_benthic_lit1_4,
    obs_benthic_lit1_5,
    obs_benthic_lit2_1,
    obs_benthic_lit2_2,
    obs_benthic_lit2_3,
    obs_benthic_lit2_4,
    obs_benthic_lit2_5,
    observer_benthic_lit1,
    observer_benthic_lit2,
):
    pass
