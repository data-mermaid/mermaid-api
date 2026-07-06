import pytest
from django.db import IntegrityError

from api.models import Classifier


def test_classifier_defaults_and_config_property():
    c = Classifier.objects.create(name="c1", version="v1", config={"patch_size": 224})
    c.refresh_from_db()
    assert c.classifier_type == "pyspacer"
    assert c.config == {"patch_size": 224}
    assert c.patch_size == 224


def test_config_defaults_to_empty_dict():
    c = Classifier.objects.create(name="c2", version="v2")
    assert c.config == {}
    assert c.patch_size is None


def test_version_is_unique():
    Classifier.objects.create(name="a", version="dup")
    with pytest.raises(IntegrityError):
        Classifier.objects.create(name="b", version="dup")
