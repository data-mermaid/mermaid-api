import pytest

from api.models import Classifier
from api.models.classification import ClassifierRegistrationError


def _manifest(classes, config=None, task="pyspacer_mlp_classifier", schema_version=1):
    return {
        "schema_version": schema_version,
        "task": task,
        "classes": classes,
        "input_dim": 1280,
        "config": config if config is not None else {"patch_size": 224},
        "trained_with": {"torch": "2.8.0", "sklearn": "1.5.2", "pyspacer": "0.12.0"},
    }


@pytest.fixture
def stub_manifest(monkeypatch):
    """Patch the S3 JSON read; return a setter the test calls with a manifest dict."""
    holder = {}

    def fake_read_json_object(bucket, key, *args, **kwargs):
        return holder["manifest"]

    monkeypatch.setattr("api.utils.s3.read_json_object", fake_read_json_object)

    def set_manifest(manifest):
        holder["manifest"] = manifest

    return set_manifest


def test_register_populates_config_and_labels(
    stub_manifest, benthic_attribute_1, benthic_attribute_2
):
    stub_manifest(
        _manifest(
            classes=[f"{benthic_attribute_1.pk}::", f"{benthic_attribute_2.pk}::"],
            config={"patch_size": 224},
        )
    )

    classifier = Classifier.register("v9", name="Reef v9")

    assert classifier.version == "v9"
    assert classifier.classifier_type == "pyspacer"
    assert classifier.config == {"patch_size": 224}
    ba_ids = set(
        classifier.benthic_attribute_growth_forms.values_list("benthic_attribute_id", flat=True)
    )
    assert ba_ids == {benthic_attribute_1.pk, benthic_attribute_2.pk}


def test_register_is_idempotent_upsert(stub_manifest, benthic_attribute_1, benthic_attribute_2):
    stub_manifest(_manifest(classes=[f"{benthic_attribute_1.pk}::"], config={"patch_size": 224}))
    first = Classifier.register("v9")

    stub_manifest(
        _manifest(
            classes=[f"{benthic_attribute_1.pk}::", f"{benthic_attribute_2.pk}::"],
            config={"patch_size": 128},
        )
    )
    second = Classifier.register("v9")

    assert first.pk == second.pk  # updated, not duplicated
    assert Classifier.objects.filter(version="v9").count() == 1
    second.refresh_from_db()
    assert second.config == {"patch_size": 128}
    assert second.benthic_attribute_growth_forms.count() == 2


def test_register_rejects_unknown_task(stub_manifest, benthic_attribute_1):
    stub_manifest(_manifest(classes=[f"{benthic_attribute_1.pk}::"], task="nope"))
    with pytest.raises(ClassifierRegistrationError):
        Classifier.register("v9")
    assert not Classifier.objects.filter(version="v9").exists()


def test_register_rejects_invalid_config(stub_manifest, benthic_attribute_1):
    stub_manifest(_manifest(classes=[f"{benthic_attribute_1.pk}::"], config={"wrong": 1}))
    with pytest.raises(ClassifierRegistrationError):
        Classifier.register("v9")
    assert not Classifier.objects.filter(version="v9").exists()


def test_register_rejects_unknown_benthic_attribute_atomically(stub_manifest, benthic_attribute_1):
    bad = "00000000-0000-0000-0000-000000000000"
    stub_manifest(_manifest(classes=[f"{benthic_attribute_1.pk}::", f"{bad}::"]))
    with pytest.raises(ClassifierRegistrationError):
        Classifier.register("v9")
    # nothing partially applied
    assert not Classifier.objects.filter(version="v9").exists()
