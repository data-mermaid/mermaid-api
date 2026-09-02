import pytest

from api.models.classification import (
    CONFIG_SCHEMAS,
    TASK_TO_CLASSIFIER_TYPE,
    PyspacerConfig,
)


def test_pyspacer_config_accepts_patch_size():
    cfg = PyspacerConfig(patch_size=224)
    assert cfg.patch_size == 224
    assert cfg.model_dump() == {"patch_size": 224}


def test_pyspacer_config_rejects_missing_patch_size():
    with pytest.raises(Exception):
        PyspacerConfig()


def test_pyspacer_config_rejects_extra_fields():
    with pytest.raises(Exception):
        PyspacerConfig(patch_size=224, unexpected="x")


def test_registry_and_task_map():
    assert CONFIG_SCHEMAS["pyspacer"] is PyspacerConfig
    assert TASK_TO_CLASSIFIER_TYPE["pyspacer_mlp_classifier"] == "pyspacer"
