from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from api.checks import check_inference_settings
from api.models import Classifier


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_command_enforces_inference_settings_only_in_dev(mock_run_with_reloader):
    with override_settings(
        ENVIRONMENT="dev",
        INFERENCE_PYSPACER_FUNCTIONS={},
        INFERENCE_CLASSIFIER_VERSION="",
        IMAGE_QUEUE_NAME="mermaid-local-image",
    ):
        with pytest.raises(CommandError):
            call_command("simpleq_worker", queue_name="mermaid-local-image")
    mock_run_with_reloader.assert_not_called()

    with override_settings(
        ENVIRONMENT="local",
        INFERENCE_PYSPACER_FUNCTIONS={},
        INFERENCE_CLASSIFIER_VERSION="",
        IMAGE_QUEUE_NAME="mermaid-local-image",
    ):
        call_command("simpleq_worker", queue_name="mermaid-local-image")
    mock_run_with_reloader.assert_called_once()


@pytest.mark.parametrize("functions", [{}, None])
def test_e002_when_the_function_map_is_empty_or_invalid(functions):
    with override_settings(
        ENVIRONMENT="dev",
        INFERENCE_PYSPACER_FUNCTIONS=functions,
        INFERENCE_CLASSIFIER_VERSION="v1",
    ):
        errors = check_inference_settings()

    assert [e.id for e in errors] == ["api.E002"]


def test_e004_only_when_the_active_version_is_not_in_the_map():
    functions = {"v1": "fn-v1"}
    with override_settings(
        ENVIRONMENT="dev", INFERENCE_PYSPACER_FUNCTIONS=functions, INFERENCE_CLASSIFIER_VERSION="v2"
    ):
        assert [e.id for e in check_inference_settings()] == ["api.E004"]
    with override_settings(
        ENVIRONMENT="dev", INFERENCE_PYSPACER_FUNCTIONS=functions, INFERENCE_CLASSIFIER_VERSION="v1"
    ):
        assert check_inference_settings() == []


_DEV_IMAGE_WORKER = {
    "ENVIRONMENT": "dev",
    "INFERENCE_PYSPACER_FUNCTIONS": {"v9": "fn-v9"},
    "IMAGE_QUEUE_NAME": "mermaid-local-image",
}


@pytest.fixture(autouse=True)
def worker_connection():
    # The worker closes its DB connection before handing off to the reloader;
    # closing the real one would break the test's own transaction.
    with patch("simpleq.management.commands.simpleq_worker.connection") as mock_connection:
        yield mock_connection


_MANIFEST = {
    "schema_version": 1,
    "task": "pyspacer_mlp_classifier",
    "config": {"patch_size": 224},
}


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_leaves_an_existing_pinned_row_untouched(mock_run_with_reloader, stub_manifest):
    # v1 predates model.json, so an existing row must never trigger an S3 read.
    Classifier.objects.create(name="v1", version="v1", config={"patch_size": 224})

    with override_settings(
        INFERENCE_CLASSIFIER_VERSION="v1",
        **{**_DEV_IMAGE_WORKER, "INFERENCE_PYSPACER_FUNCTIONS": {"v1": "fn-v1"}},
    ):
        call_command("simpleq_worker", queue_name="mermaid-local-image")

    assert stub_manifest.calls == []
    mock_run_with_reloader.assert_called_once()


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_registers_only_the_missing_live_versions(
    mock_run_with_reloader, stub_manifest, benthic_attribute_1
):
    existing = Classifier.objects.create(name="v1", version="v1", config={"patch_size": 224})
    stub_manifest({**_MANIFEST, "classes": [f"{benthic_attribute_1.pk}::"]})

    with override_settings(
        INFERENCE_CLASSIFIER_VERSION="v1",
        **{
            **_DEV_IMAGE_WORKER,
            "INFERENCE_PYSPACER_FUNCTIONS": {"v1": "fn-v1", "v9": "fn-v9"},
        },
    ):
        call_command("simpleq_worker", queue_name="mermaid-local-image")

    assert Classifier.objects.filter(version="v9").exists()
    assert len(stub_manifest.calls) == 1
    assert Classifier.objects.get(version="v1").pk == existing.pk
    assert Classifier.objects.get(version="v1").config == {"patch_size": 224}


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_registers_a_missing_pinned_row(
    mock_run_with_reloader, worker_connection, stub_manifest, benthic_attribute_1
):
    stub_manifest({**_MANIFEST, "classes": [f"{benthic_attribute_1.pk}::"]})

    with override_settings(INFERENCE_CLASSIFIER_VERSION="v9", **_DEV_IMAGE_WORKER):
        call_command("simpleq_worker", queue_name="mermaid-local-image")

    classifier = Classifier.objects.get(version="v9")
    assert classifier.benthic_attribute_growth_forms.count() == 1
    worker_connection.close.assert_called_once()
    mock_run_with_reloader.assert_called_once()


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_exits_when_the_pinned_row_cannot_be_registered(
    mock_run_with_reloader, stub_manifest
):
    stub_manifest({"schema_version": 99})

    with override_settings(INFERENCE_CLASSIFIER_VERSION="v9", **_DEV_IMAGE_WORKER):
        with pytest.raises(CommandError, match="v9"):
            call_command("simpleq_worker", queue_name="mermaid-local-image")

    assert not Classifier.objects.filter(version="v9").exists()
    mock_run_with_reloader.assert_not_called()


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_skips_registration_outside_the_image_queue_and_locally(
    mock_run_with_reloader, stub_manifest
):
    with override_settings(INFERENCE_CLASSIFIER_VERSION="v9", **_DEV_IMAGE_WORKER):
        call_command("simpleq_worker", queue_name="mermaid-local-general")
    with override_settings(
        INFERENCE_CLASSIFIER_VERSION="v9", **{**_DEV_IMAGE_WORKER, "ENVIRONMENT": "local"}
    ):
        call_command("simpleq_worker", queue_name="mermaid-local-image")

    assert stub_manifest.calls == []
    assert mock_run_with_reloader.call_count == 2
