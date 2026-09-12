import importlib

import pytest
from django.apps import apps as django_apps

from api.models import Classifier

_migration_module = importlib.import_module("api.migrations.0134_classifier_config")
config_to_patch_size = _migration_module.config_to_patch_size


def test_config_to_patch_size_rejects_row_missing_patch_size(db_setup):
    classifier = Classifier.objects.create(
        name="seg", version="vseg", classifier_type="segmentation", config={}
    )

    with pytest.raises(RuntimeError, match=classifier.version):
        config_to_patch_size(django_apps, None)
