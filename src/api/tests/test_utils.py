from api.utils import get_subclasses
from api.models import SampleUnit, BenthicTransect, QuadratTransect, QuadratCollection


def test_get_subclasses():
    subclasses = list(get_subclasses(SampleUnit))
    assert BenthicTransect in subclasses
    assert QuadratTransect in subclasses
    assert QuadratCollection in subclasses
