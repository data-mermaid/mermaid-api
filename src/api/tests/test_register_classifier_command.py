from django.core.management import call_command

from api.models import Classifier

_MANIFEST = {
    "schema_version": 1,
    "task": "pyspacer_mlp_classifier",
    "input_dim": 1280,
    "config": {"patch_size": 224},
    "trained_with": {"torch": "2.8.0", "sklearn": "1.5.2", "pyspacer": "0.12.0"},
}


def test_command_registers_version(stub_manifest, benthic_attribute_1):
    stub_manifest({**_MANIFEST, "classes": [f"{benthic_attribute_1.pk}::"]})
    call_command("register_classifier", "v9")
    classifier = Classifier.objects.get(version="v9")
    assert classifier.config == {"patch_size": 224}
    assert classifier.benthic_attribute_growth_forms.count() == 1


def test_command_dry_run_writes_nothing(stub_manifest, benthic_attribute_1):
    stub_manifest({**_MANIFEST, "classes": [f"{benthic_attribute_1.pk}::"]})
    call_command("register_classifier", "v9", "--dry-run")
    assert not Classifier.objects.filter(version="v9").exists()
