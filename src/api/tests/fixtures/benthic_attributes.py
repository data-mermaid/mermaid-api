import pytest

from api.models import BenthicAttribute, GrowthForm


@pytest.fixture
def benthic_attribute_1(db):
    return BenthicAttribute.objects.create(name="Macroalgae")


@pytest.fixture
def benthic_attribute_2(db):
    return BenthicAttribute.objects.create(name="Hard coral")


@pytest.fixture
def benthic_attribute_3(db):
    return BenthicAttribute.objects.create(name="Rock")


@pytest.fixture
def benthic_attribute_4(db):
    return BenthicAttribute.objects.create(name="Sand")


@pytest.fixture
def benthic_attribute_1a(db, benthic_attribute_1):
    return BenthicAttribute.objects.create(
        name="Red Fleshy Algae", parent=benthic_attribute_1
    )


@pytest.fixture
def benthic_attribute_2a(db, benthic_attribute_2):
    return BenthicAttribute.objects.create(
        name="Acroporidae", parent=benthic_attribute_2
    )


@pytest.fixture
def benthic_attribute_2b(db, benthic_attribute_2):
    return BenthicAttribute.objects.create(name="Faviidae", parent=benthic_attribute_2)


@pytest.fixture
def benthic_attribute_2a1(db, benthic_attribute_2a):
    return BenthicAttribute.objects.create(
        name="Astreopora", parent=benthic_attribute_2a
    )


@pytest.fixture
def benthic_attribute_2b1(db, benthic_attribute_2b):
    return BenthicAttribute.objects.create(
        name="Erythrastrea", parent=benthic_attribute_2b
    )


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
):
    pass
