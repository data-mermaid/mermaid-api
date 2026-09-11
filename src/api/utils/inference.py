import json
import logging
from operator import itemgetter
from typing import NamedTuple

from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from mermaid_inference_contract import (
    PyspacerRequest,
    S3Location,
    Traceparent,
    __version__ as CONTRACT_VERSION,
    format_traceparent,
    new_traceparent,
    parse_classify_response,
)
from opentelemetry import trace as otel_trace

from ..models.classification import Classifier, get_image_storage_config

logger = logging.getLogger(__name__)

# The Lambda's own timeout is 600s; botocore's 60s read_timeout default would
# abort a slower synchronous invoke client-side before the function itself does.
_LAMBDA_READ_TIMEOUT = 660

_lambda_client = None


class InferenceError(Exception):
    """Raised when the inference Lambda invocation fails or returns an error envelope."""


class LambdaClassificationResult(NamedTuple):
    point_predictions: list
    feature_vector_name: str | None


def get_lambda_client(aws_access_key_id=None, aws_secret_access_key=None):
    """Return a boto3 Lambda client, built once per process and reused after."""
    global _lambda_client
    if _lambda_client is None:
        session = Session(
            aws_access_key_id=aws_access_key_id or settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        _lambda_client = session.client(
            "lambda",
            config=Config(
                connect_timeout=10,
                read_timeout=_LAMBDA_READ_TIMEOUT,
                retries={"max_attempts": 5, "mode": "standard"},
            ),
        )
    return _lambda_client


def invoke_pyspacer(payload: dict) -> dict:
    """Invoke the pyspacer inference Lambda synchronously and return its parsed payload.

    Raises InferenceError if the invoke call itself fails (a botocore/client error,
    e.g. throttling) or the function crashed (FunctionError present). A business
    failure is NOT a FunctionError — it comes back as a normal payload (ErrorEnvelope),
    handled by the caller.
    """
    client = get_lambda_client()
    try:
        response = client.invoke(
            FunctionName=settings.INFERENCE_LAMBDA_PYSPACER,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as err:
        code = getattr(err, "response", {}).get("Error", {}).get("Code", type(err).__name__)
        raise InferenceError(f"invoke_pyspacer: Lambda invoke failed ({code})") from err

    raw = response["Payload"].read()
    if response.get("FunctionError"):
        detail = raw.decode("utf-8", errors="replace")[:500]
        raise InferenceError(f"Lambda FunctionError ({response['FunctionError']}): {detail}")
    return json.loads(raw)


def feature_vector_location(image) -> tuple[str, S3Location]:
    """Name/location pair for an image's feature vector.

    `name` matches the Django FileField name the in-process pyspacer path saves
    (relative to the bucket's S3Storage `location` prefix). `S3Location.key` carries
    that same prefix explicitly, since the contract has no notion of a storage-level
    location — getting this pair out of sync means the Lambda writes bytes at a key
    the FileField does not point at.
    """
    name = f"{image.id}_featurevector"
    config = get_image_storage_config(image.image_bucket)
    return name, S3Location(bucket=config["bucket"], key=f"{config['s3_path']}{name}")


def build_pyspacer_request(image, points, traceparent, feature_vector_output=None) -> dict:
    config = get_image_storage_config(image.image_bucket)
    request = PyspacerRequest(
        classifier_type="pyspacer",
        image=S3Location(bucket=config["bucket"], key=f"{config['s3_path']}{image.image.name}"),
        points=[(int(row), int(col)) for row, col in points],
        feature_vector_output=feature_vector_output,
        traceparent=traceparent,
    )
    return request.model_dump(mode="json")


def _current_traceparent() -> str:
    """W3C traceparent for the active OTEL span, or a fresh one if there is no valid span.

    OTEL span-context ids are already 128-bit trace / 64-bit span, i.e. W3C-shaped, so no
    X-Ray-format conversion is needed here; ADOT handles the X-Ray mapping at export.
    """
    ctx = otel_trace.get_current_span().get_span_context()
    if ctx.is_valid:
        return format_traceparent(
            Traceparent(
                trace_id=format(ctx.trace_id, "032x"),
                parent_id=format(ctx.span_id, "016x"),
                flags="01" if ctx.trace_flags.sampled else "00",
            )
        )
    return format_traceparent(new_traceparent())


def response_to_point_predictions(response):
    """PyspacerResponse -> normalized [(row, col, [(label, score), ...ranked])].

    Re-sorts explicitly: the contract documents descending score order, but the
    caller takes only the top 3 entries, so a silent upstream ordering regression
    would otherwise write the wrong labels with no error anywhere.
    """
    return [
        (
            pr.row,
            pr.col,
            sorted(((ps.label, ps.score) for ps in pr.scores), key=itemgetter(1), reverse=True),
        )
        for pr in response.point_results
    ]


def _resolve_active_classifier() -> Classifier:
    """The Classifier row for the version baked into the deployed inference image.

    No latest()-style fallback: that orders by created_on and could return a
    different row than the one that actually scored the points, mis-attributing
    Annotation.classifier.
    """
    version = settings.INFERENCE_CLASSIFIER_VERSION
    if not version:
        raise InferenceError("INFERENCE_CLASSIFIER_VERSION is not set")
    try:
        return Classifier.objects.get(version=version)
    except Classifier.DoesNotExist as err:
        raise InferenceError(f"No Classifier registered for version {version!r}") from err


def classify_via_lambda(image, points) -> LambdaClassificationResult:
    """Invoke the pyspacer Lambda for an image and return normalized point predictions.

    Raises InferenceError on an ErrorEnvelope payload, a classifier-version drift
    mismatch, or a contract-version mismatch. A feature vector the Lambda did not
    write where requested does not fail the job: points and annotations are the
    product, and nothing in src/ reads feature-vector bytes back.
    """
    tracer = otel_trace.get_tracer("api.inference")
    with tracer.start_as_current_span("pyspacer.classify_via_lambda"):
        traceparent = _current_traceparent()
        logger.info("pyspacer inference invoke", extra={"traceparent": traceparent})
        name, feature_vector_output = feature_vector_location(image)
        payload = invoke_pyspacer(
            build_pyspacer_request(
                image, points, traceparent, feature_vector_output=feature_vector_output
            )
        )

        if "error_code" in payload:
            logger.error(
                "pyspacer inference error envelope",
                extra={"traceparent": traceparent, "error_code": payload.get("error_code")},
            )
            raise InferenceError(payload.get("message") or "inference error")

        response = parse_classify_response(payload)

        expected = settings.INFERENCE_CLASSIFIER_VERSION
        if expected and response.classifier_version != expected:
            logger.error(
                "pyspacer classifier version drift",
                extra={"traceparent": traceparent},
            )
            raise InferenceError(
                f"Classifier version drift: Lambda served {response.classifier_version!r}, "
                f"expected {expected!r}"
            )

        installed = CONTRACT_VERSION
        if response.contract_version and response.contract_version != installed:
            logger.error(
                "pyspacer contract version mismatch",
                extra={"traceparent": traceparent},
            )
            raise InferenceError(
                f"Contract version mismatch: Lambda reported {response.contract_version!r}, "
                f"API has {installed!r} — pin mermaid-inference-contract to the deployed image's tag"
            )

        feature_vector_name = None
        if response.feature_vector_output == feature_vector_output:
            feature_vector_name = name
        else:
            logger.warning(
                f"pyspacer did not write the requested feature vector for image {image.id}"
            )

        return LambdaClassificationResult(
            point_predictions=response_to_point_predictions(response),
            feature_vector_name=feature_vector_name,
        )
