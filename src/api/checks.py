from django.conf import settings
from django.core.checks import Error
from django.db import connection, transaction

from api.models import Classifier

# `src/docker-entry.sh` runs `migrate` before `gunicorn`, and `migrate` runs every
# registered check regardless of tags; registering the checks below would couple
# an API-wide startup failure to a misconfiguration that only affects
# classification. The image worker calls check_inference_settings() and
# ensure_live_classifiers_registered() directly instead, so they are deliberately
# left out of Django's check registry.

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
    functions = settings.INFERENCE_PYSPACER_FUNCTIONS
    if not functions or not isinstance(functions, dict):
        errors.append(
            Error(
                "INFERENCE_PYSPACER_FUNCTIONS is empty or not a valid JSON object.",
                hint=(
                    "Set INFERENCE_PYSPACER_FUNCTIONS to a JSON object mapping each live "
                    "classifier version to its pyspacer Lambda function name."
                ),
                id="api.E002",
            )
        )
    active = settings.INFERENCE_CLASSIFIER_VERSION
    if not active:
        errors.append(
            Error(
                "INFERENCE_CLASSIFIER_VERSION is not set.",
                hint="Set INFERENCE_CLASSIFIER_VERSION to the active classifier version.",
                id="api.E003",
            )
        )
    elif isinstance(functions, dict) and functions and active not in functions:
        errors.append(
            Error(
                f"INFERENCE_CLASSIFIER_VERSION {active!r} is not a key of "
                "INFERENCE_PYSPACER_FUNCTIONS.",
                hint="Add the active version to INFERENCE_PYSPACER_FUNCTIONS.",
                id="api.E004",
            )
        )
    return errors


def ensure_live_classifiers_registered():
    """Register each version in INFERENCE_PYSPACER_FUNCTIONS from its model.json if no row exists.

    An existing row is left untouched: v1 predates model.json and cannot be
    re-registered, and a corrected manifest is re-applied with `register_classifier`.
    Raises ClassifierRegistrationError when a missing row cannot be registered.
    """
    versions = list(settings.INFERENCE_PYSPACER_FUNCTIONS)
    # Concurrently starting image workers would otherwise race on BA+GF rows with a
    # NULL growth form, which the unique constraint treats as distinct.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CLASSIFIER_REGISTRATION_LOCK])
        existing = set(
            Classifier.objects.filter(version__in=versions).values_list("version", flat=True)
        )
        for version in versions:
            if version not in existing:
                Classifier.register(version)
