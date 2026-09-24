"""Validates the Lambda classify path's settings and pinned Classifier row outside
Django's check registry.

`src/docker-entry.sh` runs `migrate` before `gunicorn`, and `migrate` runs every
registered check regardless of tags; registering this one would couple an
API-wide startup failure to a misconfiguration that only affects classification.
The image worker calls check_inference_settings() and
ensure_pinned_classifier_registered() directly instead.
"""

from django.conf import settings
from django.core.checks import Error
from django.db import connection, transaction

from api.models import Classifier

# `local` and test runs leave these settings unset by design; only a deployed
# environment is expected to have them configured.
ENFORCED_ENVIRONMENTS = ("dev", "prod")

# Arbitrary constant key for the Postgres advisory lock that serializes registration.
CLASSIFIER_REGISTRATION_LOCK = 7_302_451


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


def ensure_pinned_classifier_registered():
    """Register INFERENCE_CLASSIFIER_VERSION from its model.json if no row exists yet.

    An existing row is left untouched: v1 predates model.json and cannot be
    re-registered, and a corrected manifest is re-applied with `register_classifier`.
    Raises ClassifierRegistrationError when a missing row cannot be registered.
    """
    version = settings.INFERENCE_CLASSIFIER_VERSION
    # Concurrently starting image workers would otherwise race on BA+GF rows with a
    # NULL growth form, which the unique constraint treats as distinct.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CLASSIFIER_REGISTRATION_LOCK])
        if Classifier.objects.filter(version=version).exists():
            return
        Classifier.register(version)
