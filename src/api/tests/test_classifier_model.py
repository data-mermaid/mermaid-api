import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from api.models import Classifier


def test_saving_pyspacer_classifier_without_patch_size_is_rejected():
    with pytest.raises(IntegrityError):
        Classifier.objects.create(name="c7", version="v7", classifier_type="pyspacer", config={})


def test_saving_non_pyspacer_classifier_without_patch_size_is_allowed():
    classifier = Classifier.objects.create(
        name="c8", version="v8", classifier_type="segmentation", config={}
    )
    assert classifier.pk is not None


@pytest.mark.parametrize(
    "classifier_type,config",
    [
        ("pyspacer", {}),  # missing the required patch_size key
        ("pyspacer", 224),  # non-object config
        ("pyspacer", {"patch_size": "224"}),  # patch_size must be an int
        ("segmentation", 224),  # non-object config, even with no schema for the type
        ("segmentation", []),
    ],
)
def test_full_clean_rejects_invalid_config(classifier_type, config):
    c = Classifier(name="c", version="v-invalid", classifier_type=classifier_type, config=config)
    with pytest.raises(ValidationError) as exc_info:
        c.full_clean()
    assert "config" in exc_info.value.message_dict
