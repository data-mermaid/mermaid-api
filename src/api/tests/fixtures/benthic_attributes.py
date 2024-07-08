import pytest

from api.models import BenthicAttribute, BenthicLifeHistory, GrowthForm


@pytest.fixture
def benthic_attribute_1(db, region1, region2):
    ba = BenthicAttribute.objects.create(name="Macroalgae")
    ba.regions.add(region1)
    ba.regions.add(region2)

    return ba


@pytest.fixture
def benthic_attribute_2(db, region2, region3):
    ba = BenthicAttribute.objects.create(name="Hard coral")
    ba.regions.add(region2)
    ba.regions.add(region3)

    return ba


@pytest.fixture
def benthic_attribute_3(db, region1, region2, region3):
    ba = BenthicAttribute.objects.create(name="Rock")
    ba.regions.add(region1)
    ba.regions.add(region2)
    ba.regions.add(region3)

    return ba


@pytest.fixture
def benthic_attribute_4(db, region1, region2, region3):
    ba = BenthicAttribute.objects.create(name="Sand")
    ba.regions.add(region1)
    ba.regions.add(region2)
    ba.regions.add(region3)

    return ba


@pytest.fixture
def benthic_attribute_1a(db, benthic_attribute_1, region3):
    ba = BenthicAttribute.objects.create(name="Red Fleshy Algae", parent=benthic_attribute_1)
    ba.regions.add(region3)

    return ba


@pytest.fixture
def benthic_attribute_2a(db, benthic_attribute_2, region2):
    ba = BenthicAttribute.objects.create(name="Acroporidae", parent=benthic_attribute_2)
    ba.regions.add(region2)

    return ba


@pytest.fixture
def benthic_attribute_2b(db, benthic_attribute_2, region3):
    ba = BenthicAttribute.objects.create(name="Faviidae", parent=benthic_attribute_2)
    ba.regions.add(region3)

    return ba


@pytest.fixture
def benthic_attribute_2a1(db, benthic_attribute_2a):
    return BenthicAttribute.objects.create(name="Astreopora", parent=benthic_attribute_2a)


@pytest.fixture
def benthic_attribute_2b1(db, benthic_attribute_2b, region1, region3):
    ba = BenthicAttribute.objects.create(name="Erythrastrea", parent=benthic_attribute_2b)
    ba.regions.add(region1)
    ba.regions.add(region3)

    return ba


@pytest.fixture
def growth_form1(db):
    return GrowthForm.objects.create(name="massive")


@pytest.fixture
def growth_form2(db):
    return GrowthForm.objects.create(name="plates or tables")


@pytest.fixture
def growth_form3(db):
    return GrowthForm.objects.create(name="digitate")


@pytest.fixture
def growth_form4(db):
    return GrowthForm.objects.create(name="branching")


@pytest.fixture
def life_histories(db):
    BenthicLifeHistory.objects.create(name="N/A")
    BenthicLifeHistory.objects.create(name="competitive")
    BenthicLifeHistory.objects.create(name="generalist")
    BenthicLifeHistory.objects.create(name="stress-tolerant")
    BenthicLifeHistory.objects.create(name="weedy")

    return BenthicLifeHistory.objects.all()


@pytest.fixture
def all_test_benthic_attributes(
    db,
    benthic_attribute_1,
    benthic_attribute_1a,
    benthic_attribute_2,
    benthic_attribute_2a,
    benthic_attribute_2a1,
    benthic_attribute_2b,
    benthic_attribute_2b1,
    benthic_attribute_3,
    benthic_attribute_4,
    growth_form1,
    growth_form2,
    growth_form3,
    growth_form4,
    life_histories,
):
    pass
