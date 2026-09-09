import pytest
from django.core.exceptions import ValidationError
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


def test_full_clean_rejects_config_missing_required_key():
    c = Classifier(name="c3", version="v3", classifier_type="pyspacer", config={})
    with pytest.raises(ValidationError) as exc_info:
        c.full_clean()
    assert "config" in exc_info.value.message_dict


def test_full_clean_accepts_valid_config():
    c = Classifier(name="c4", version="v4", classifier_type="pyspacer", config={"patch_size": 224})
    c.full_clean()


def test_full_clean_skips_validation_for_type_with_no_schema():
    c = Classifier(name="c5", version="v5", classifier_type="segmentation", config={})
    c.full_clean()
