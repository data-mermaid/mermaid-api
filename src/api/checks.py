"""Validates the Lambda classify path's settings outside Django's check registry.

`src/docker-entry.sh` runs `migrate` before `gunicorn`, and `migrate` runs every
registered check regardless of tags; registering this one would couple an
API-wide startup failure to a misconfiguration that only affects classification.
Callers call check_inference_settings() directly instead.
"""

from django.conf import settings
from django.core.checks import Error

# `local` and test runs leave these settings unset by design; only a deployed
# environment is expected to have them configured.
ENFORCED_ENVIRONMENTS = ("dev", "prod")


def check_inference_settings(app_configs=None, **kwargs):
    """Return an Error for each classify-path setting missing in a deployed environment."""
    if settings.ENVIRONMENT not in ENFORCED_ENVIRONMENTS:
        return []

    errors = []
    if not settings.INFERENCE_LAMBDA_PYSPACER:
        errors.append(
            Error(
                "INFERENCE_LAMBDA_PYSPACER is not set.",
                hint="Set INFERENCE_LAMBDA_PYSPACER to the pyspacer Lambda's function name.",
                id="api.E001",
            )
        )
    if not settings.INFERENCE_CLASSIFIER_VERSION:
        errors.append(
            Error(
                "INFERENCE_CLASSIFIER_VERSION is not set.",
                hint="Set INFERENCE_CLASSIFIER_VERSION to the active classifier version.",
                id="api.E002",
            )
        )
    return errors
