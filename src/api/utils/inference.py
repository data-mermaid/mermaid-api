import json
import logging
from operator import itemgetter
from typing import NamedTuple

from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionError as BotoConnectionError,
    HTTPClientError,
    IncompleteReadError,
)
from django.conf import settings
from mermaid_inference_contract import (
    ErrorEnvelope,
    PyspacerRequest,
    S3Location,
    Traceparent,
    __version__ as CONTRACT_VERSION,
    format_traceparent,
    new_traceparent,
    parse_classify_response,
)
from opentelemetry import trace as otel_trace
from pydantic import ValidationError

from ..models.classification import get_image_storage_config

logger = logging.getLogger(__name__)

# Must stay above the Lambda's own timeout (InferenceSettings.timeout_minutes,
# iac/settings/settings.py, 600s) or botocore aborts a slower synchronous invoke
# client-side before the function itself does.
_LAMBDA_READ_TIMEOUT = 660

_lambda_client = None

# Lambda's own throttling and transient-infrastructure error codes for a synchronous
# invoke; botocore surfaces these as a ClientError, not one of the transient
# BotoCoreError subclasses below.
_RETRYABLE_CLIENT_ERROR_CODES = frozenset(
    {
        "TooManyRequestsException",
        # Returned while a container-image function's optimized image rebuilds after
        # idleness ("Lambda is initializing your function. It will be ready to invoke
        # shortly.").
        "CodeArtifactUserPendingException",
        "EC2ThrottledException",  # in botocore's own _THROTTLED_ERROR_CODES set
        "ServiceException",  # Lambda's internal 500
        # The ENI-not-ready 502 family a function hits on scale-up.
        "ResourceNotReadyException",
        "ENILimitReachedException",
        "SubnetIPAddressLimitReachedException",
    }
)
# Mirrors botocore's own transient set (TransientRetryableChecker's
# _TRANSIENT_EXCEPTION_CLS is (ConnectionError, HTTPClientError)), which subsumes
# ConnectionClosedError — an HTTPClientError a leaf enumeration missed.
# IncompleteReadError is a direct BotoCoreError outside both bases.
_RETRYABLE_BOTOCORE_EXCEPTIONS = (BotoConnectionError, HTTPClientError, IncompleteReadError)

# An Unhandled FunctionError covers both a Lambda timeout and a crash (e.g. a
# cold-start OOM kill); "signal:" isolates a kill signal from an image that exits
# at INIT with a plain status code, which is permanent until rolled back.
_RETRYABLE_UNHANDLED_ERROR_MARKERS = ("Task timed out", "Runtime exited with error: signal:")


class InferenceError(Exception):
    """Raised when the inference Lambda invocation fails or returns an error envelope.

    `retryable` marks failures where a fresh invoke might succeed — a Lambda throttle,
    a client-side timeout, or an envelope that opts in explicitly — so the caller can
    let SQS redeliver the job instead of failing the image permanently. `error_code`
    carries an ErrorEnvelope's code for failures raised from one, and is None otherwise.
    """

    def __init__(self, message, *, retryable=False, error_code=None):
        super().__init__(message)
        self.retryable = retryable
        self.error_code = error_code


def _function_error_is_retryable(function_error: str, detail: str) -> bool:
    """True for an Unhandled FunctionError whose decoded detail names a timeout or a
    runtime crash — both transient on this 10 GB/600s, cold-start-heavy function.

    A Handled FunctionError is the function's own raised exception and never matches.
    """
    return function_error == "Unhandled" and any(
        marker in detail for marker in _RETRYABLE_UNHANDLED_ERROR_MARKERS
    )


def _wrap_validation_error(context: str, err: ValidationError) -> InferenceError:
    """Bound a pydantic ValidationError to a short InferenceError message.

    The raw error can run to thousands of characters for a many-point response, and
    _classify_image writes an InferenceError's message into a user-visible status field.
    """
    return InferenceError(
        f"pyspacer inference: {context} ({err.error_count()} validation error(s))"
    )


class LambdaClassificationResult(NamedTuple):
    point_predictions: list
    feature_vector_name: str | None


def get_lambda_client():
    """Return a boto3 Lambda client, built once per process and reused after."""
    global _lambda_client
    if _lambda_client is None:
        session = Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        _lambda_client = session.client(
            "lambda",
            config=Config(
                connect_timeout=10,
                read_timeout=_LAMBDA_READ_TIMEOUT,
                # "max_attempts" counts retries, not total attempts: botocore enforces
                # max_attempts + 1 total tries. 1 retry here means 2 total invokes, each
                # a fresh, non-idempotent Lambda execution — see INFERENCE_JOB_VISIBILITY_TIMEOUT.
                retries={"max_attempts": 1, "mode": "standard"},
            ),
        )
    return _lambda_client


def invoke_pyspacer(payload: dict) -> dict:
    """Invoke the pyspacer inference Lambda synchronously and return its parsed payload.

    Raises InferenceError if the invoke call itself fails, the response payload cannot
    be read (a botocore/client error, e.g. throttling or a read timeout), or the
    function crashed (FunctionError present). A business failure is NOT a
    FunctionError — it comes back as a normal payload (ErrorEnvelope), handled by
    the caller.
    """
    client = get_lambda_client()
    try:
        response = client.invoke(
            FunctionName=settings.INFERENCE_LAMBDA_PYSPACER,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        raw = response["Payload"].read()
        if response.get("FunctionError"):
            function_error = response["FunctionError"]
            detail = raw.decode("utf-8", errors="replace")[:500]
            raise InferenceError(
                f"Lambda FunctionError ({function_error}): {detail}",
                retryable=_function_error_is_retryable(function_error, detail),
            )
        return json.loads(raw)
    except (BotoCoreError, ClientError) as err:
        # A ClientError's .response is always a dict; a BotoCoreError subclass such as
        # ReadTimeoutError sets it to None, so "or {}" covers both. This also catches
        # ResponseStreamingError/IncompleteReadError from the payload read above.
        error_response = getattr(err, "response", None) or {}
        code = error_response.get("Error", {}).get("Code", type(err).__name__)
        retryable = code in _RETRYABLE_CLIENT_ERROR_CODES or isinstance(
            err, _RETRYABLE_BOTOCORE_EXCEPTIONS
        )
        raise InferenceError(
            f"invoke_pyspacer: Lambda invoke failed ({code})", retryable=retryable
        ) from err


def _storage_key(config, name: str) -> str:
    """Storage key for `name` under a storage config's location prefix.

    Every configured `s3_path` (IMAGE_S3_PATH, IMAGE_S3_PATH_TEST) ends in "/"; an
    unvalidated environment override without one silently doubles the prefix into the
    joined key instead of raising.
    """
    return f"{config['s3_path']}{name}"


def feature_vector_name(image) -> str:
    """Name for image's feature vector.

    Must match the Django FileField name exactly, so a queryset update can record the
    Lambda-written key directly (relative to the bucket's S3Storage `location` prefix).
    """
    return f"{image.id}_featurevector"


def feature_vector_final_location(image, name: str) -> S3Location:
    """Return the S3 location for image's feature vector named `name`: image's own
    storage bucket, at the prefix get_image_storage_config resolves for it.
    """
    config = get_image_storage_config(image.image_bucket)
    return S3Location(bucket=config["bucket"], key=_storage_key(config, name))


def build_pyspacer_request(image, points, traceparent, feature_vector_output=None) -> dict:
    config = get_image_storage_config(image.image_bucket)
    request = PyspacerRequest(
        classifier_type="pyspacer",
        image=S3Location(bucket=config["bucket"], key=_storage_key(config, image.image.name)),
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


def classify_via_lambda(image, points) -> LambdaClassificationResult:
    """Invoke the pyspacer Lambda for an image and return normalized point predictions.

    Raises InferenceError on an ErrorEnvelope payload, a malformed envelope or
    response, a classifier-version drift mismatch, or a contract-version mismatch. A
    feature vector the Lambda did not write where requested does not fail the job:
    points and annotations are the product, and nothing in src/ reads feature-vector
    bytes back.
    """
    tracer = otel_trace.get_tracer("api.inference")
    with tracer.start_as_current_span("pyspacer.classify_via_lambda"):
        traceparent = _current_traceparent()
        logger.info("pyspacer inference invoke", extra={"traceparent": traceparent})
        name = feature_vector_name(image)
        requested_output = feature_vector_final_location(image, name)
        payload = invoke_pyspacer(
            build_pyspacer_request(
                image, points, traceparent, feature_vector_output=requested_output
            )
        )

        if "error_code" in payload:
            try:
                envelope = ErrorEnvelope.model_validate(payload)
            except ValidationError as err:
                # extra="forbid" means a field or ErrorCode member the function side
                # added first fails validation here rather than being ignored; the
                # envelope's own contract_version names that condition precisely,
                # so check it before reporting the vaguer "malformed" fallback.
                served = payload.get("contract_version")
                if served and served != CONTRACT_VERSION:
                    raise InferenceError(
                        f"Contract version mismatch: Lambda reported {served!r}, "
                        f"API has {CONTRACT_VERSION!r} — pin mermaid-inference-contract "
                        "to the deployed image's tag"
                    ) from err
                raise _wrap_validation_error("malformed error envelope", err) from err
            logger.error(
                f"pyspacer inference error envelope for image {image.id}: "
                f"error_code={envelope.error_code.value} traceparent={traceparent}",
                extra={"traceparent": traceparent, "error_code": envelope.error_code.value},
            )
            raise InferenceError(
                envelope.message,
                retryable=envelope.retryable,
                error_code=envelope.error_code.value,
            )

        try:
            response = parse_classify_response(payload)
        except ValidationError as err:
            raise _wrap_validation_error("malformed response", err) from err

        expected = settings.INFERENCE_CLASSIFIER_VERSION
        if expected and response.classifier_version != expected:
            logger.error(
                f"pyspacer classifier version drift for image {image.id}: "
                f"served {response.classifier_version!r}, expected {expected!r} "
                f"traceparent={traceparent}",
                extra={"traceparent": traceparent},
            )
            # Retryable: ApiStack and InferenceStack deploy independently, so a version
            # bump has a redelivery window before both sides agree; a genuine permanent
            # mismatch retries to the DLQ and alarms instead of failing silently.
            raise InferenceError(
                f"Classifier version drift: Lambda served {response.classifier_version!r}, "
                f"expected {expected!r}",
                retryable=True,
            )

        installed = CONTRACT_VERSION
        if response.contract_version and response.contract_version != installed:
            logger.error(
                f"pyspacer contract version mismatch for image {image.id}: "
                f"Lambda reported {response.contract_version!r}, API has {installed!r} "
                f"traceparent={traceparent}",
                extra={"traceparent": traceparent},
            )
            raise InferenceError(
                f"Contract version mismatch: Lambda reported {response.contract_version!r}, "
                f"API has {installed!r} — pin mermaid-inference-contract to the deployed image's tag"
            )

        matched_name = None
        if response.feature_vector_output == requested_output:
            matched_name = name
        else:
            logger.warning(
                f"pyspacer did not write the requested feature vector for image {image.id}"
            )

        return LambdaClassificationResult(
            point_predictions=response_to_point_predictions(response),
            feature_vector_name=matched_name,
        )
