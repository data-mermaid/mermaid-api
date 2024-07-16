import pytest

from api.models import BenthicPIT, ObsBenthicPIT, Observer


@pytest.fixture
def benthic_pit1(db, benthic_transect1):
    return BenthicPIT.objects.create(
        transect=benthic_transect1,
        interval_size=1,
        interval_start=1,
    )


@pytest.fixture
def benthic_pit1_2(db, benthic_transect1_2):
    return BenthicPIT.objects.create(
        transect=benthic_transect1_2,
        interval_size=1,
        interval_start=1,
    )


@pytest.fixture
def benthic_pit2(db, benthic_transect2):
    return BenthicPIT.objects.create(
        transect=benthic_transect2,
        interval_size=0.5,
        interval_start=0.5,
    )


@pytest.fixture
def observer_benthic_pit1(db, benthic_pit1, profile1):
    return Observer.objects.create(transectmethod=benthic_pit1, profile=profile1)


@pytest.fixture
def observer_benthic_pit1_2(db, benthic_pit1_2, profile1):
    return Observer.objects.create(transectmethod=benthic_pit1_2, profile=profile1)


@pytest.fixture
def observer_benthic_pit2(db, benthic_pit2, profile2):
    return Observer.objects.create(transectmethod=benthic_pit2, profile=profile2)


@pytest.fixture
def obs_benthic_pit1_1(db, benthic_pit1, benthic_attribute_1a):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1, attribute=benthic_attribute_1a, interval=1
    )


@pytest.fixture
def obs_benthic_pit1_2(db, benthic_pit1, benthic_attribute_2a):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1, attribute=benthic_attribute_2a, interval=2
    )


@pytest.fixture
def obs_benthic_pit1_3(db, benthic_pit1, benthic_attribute_2b, growth_form1):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1,
        attribute=benthic_attribute_2b,
        interval=3,
        growth_form=growth_form1,
    )


@pytest.fixture
def obs_benthic_pit1_4(db, benthic_pit1, benthic_attribute_2b1, growth_form4):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1,
        attribute=benthic_attribute_2b1,
        interval=4,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_pit1_5(db, benthic_pit1, benthic_attribute_3, growth_form4):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1,
        attribute=benthic_attribute_3,
        interval=5,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_pit1_2_1(db, benthic_pit1_2, benthic_attribute_1a):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1_2, attribute=benthic_attribute_1a, interval=1
    )


@pytest.fixture
def obs_benthic_pit1_2_2(db, benthic_pit1_2, benthic_attribute_1a):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1_2, attribute=benthic_attribute_1a, interval=2
    )


@pytest.fixture
def obs_benthic_pit1_2_3(db, benthic_pit1_2, benthic_attribute_2b, growth_form1):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1_2,
        attribute=benthic_attribute_2b,
        interval=3,
        growth_form=growth_form1,
    )


@pytest.fixture
def obs_benthic_pit1_2_4(db, benthic_pit1_2, benthic_attribute_2b, growth_form4):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1_2,
        attribute=benthic_attribute_2b,
        interval=4,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_pit1_2_5(db, benthic_pit1_2, benthic_attribute_1a, growth_form4):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit1_2,
        attribute=benthic_attribute_1a,
        interval=5,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_pit2_1(db, benthic_pit2, benthic_attribute_2):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit2, attribute=benthic_attribute_2, interval=1
    )


@pytest.fixture
def obs_benthic_pit2_2(db, benthic_pit2, benthic_attribute_3):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit2, attribute=benthic_attribute_3, interval=2
    )


@pytest.fixture
def obs_benthic_pit2_3(db, benthic_pit2, benthic_attribute_2b, growth_form1):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit2,
        attribute=benthic_attribute_2b,
        interval=3,
        growth_form=growth_form1,
    )


@pytest.fixture
def obs_benthic_pit2_4(db, benthic_pit2, benthic_attribute_2b1, growth_form4):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit2,
        attribute=benthic_attribute_2b1,
        interval=4,
        growth_form=growth_form4,
    )


@pytest.fixture
def obs_benthic_pit2_5(db, benthic_pit2, benthic_attribute_3, growth_form4):
    return ObsBenthicPIT.objects.create(
        benthicpit=benthic_pit2,
        attribute=benthic_attribute_3,
        interval=5,
        growth_form=growth_form4,
    )


@pytest.fixture
def benthic_pit_project(
    db,
    all_life_histories,
    obs_benthic_pit1_1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    obs_benthic_pit1_4,
    obs_benthic_pit1_5,
    obs_benthic_pit1_2_1,
    obs_benthic_pit1_2_2,
    obs_benthic_pit1_2_3,
    obs_benthic_pit1_2_4,
    obs_benthic_pit1_2_5,
    obs_benthic_pit2_1,
    obs_benthic_pit2_2,
    obs_benthic_pit2_3,
    obs_benthic_pit2_4,
    obs_benthic_pit2_5,
    observer_benthic_pit1,
    observer_benthic_pit1_2,
    observer_benthic_pit2,
    project_profile1,
    project_profile2,
):
    pass
