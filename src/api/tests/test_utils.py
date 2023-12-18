from api.models import BenthicTransect, QuadratCollection, QuadratTransect, SampleUnit
from api.utils import get_subclasses


def test_get_subclasses():
    subclasses = list(get_subclasses(SampleUnit))
    assert BenthicTransect in subclasses
    assert QuadratTransect in subclasses
    assert QuadratCollection in subclasses
