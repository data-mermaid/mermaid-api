from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings


@patch("simpleq.management.commands.simpleq_worker.run_with_reloader")
def test_worker_command_enforces_inference_settings_only_in_dev(mock_run_with_reloader):
    with override_settings(
        ENVIRONMENT="dev",
        INFERENCE_LAMBDA_PYSPACER="",
        INFERENCE_CLASSIFIER_VERSION="",
        IMAGE_QUEUE_NAME="mermaid-local-image",
    ):
        with pytest.raises(CommandError):
            call_command("simpleq_worker", queue_name="mermaid-local-image")
    mock_run_with_reloader.assert_not_called()

    with override_settings(
        ENVIRONMENT="local",
        INFERENCE_LAMBDA_PYSPACER="",
        INFERENCE_CLASSIFIER_VERSION="",
        IMAGE_QUEUE_NAME="mermaid-local-image",
    ):
        call_command("simpleq_worker", queue_name="mermaid-local-image")
    mock_run_with_reloader.assert_called_once()
