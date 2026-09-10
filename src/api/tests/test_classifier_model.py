import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from api.models import Classifier


def test_version_is_unique():
    Classifier.objects.create(name="a", version="dup", config={"patch_size": 224})
    with pytest.raises(IntegrityError):
        Classifier.objects.create(name="b", version="dup", config={"patch_size": 224})


def test_saving_pyspacer_classifier_without_patch_size_is_rejected():
    with pytest.raises(IntegrityError):
        Classifier.objects.create(name="c7", version="v7", classifier_type="pyspacer", config={})


def test_saving_non_pyspacer_classifier_without_patch_size_is_allowed():
    classifier = Classifier.objects.create(
        name="c8", version="v8", classifier_type="segmentation", config={}
    )
    assert classifier.pk is not None


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


def test_full_clean_rejects_non_object_config():
    c = Classifier(name="c6", version="v6", classifier_type="pyspacer", config=224)
    with pytest.raises(ValidationError) as exc_info:
        c.full_clean()
    assert "config" in exc_info.value.message_dict
