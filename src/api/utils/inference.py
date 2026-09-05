import json
import logging

import boto3
import mermaid_inference_contract
from django.conf import settings
from mermaid_inference_contract import (
    PyspacerRequest,
    S3Location,
    Traceparent,
    format_traceparent,
    new_traceparent,
    parse_classify_response,
)
from opentelemetry import trace as otel_trace

from api.models.classification import get_image_storage_config

logger = logging.getLogger(__name__)


class InferenceError(Exception):
    """Raised when the inference Lambda invocation fails or returns an error envelope."""


def get_lambda_client(aws_access_key_id=None, aws_secret_access_key=None):
    session = boto3.session.Session(
        aws_access_key_id=aws_access_key_id or settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    return session.client("lambda")


def invoke_pyspacer(payload: dict) -> dict:
    """Invoke the pyspacer inference Lambda synchronously and return its parsed payload.

    Raises InferenceError if the function crashed (FunctionError present). A business
    failure is NOT a FunctionError — it comes back as a normal payload (ErrorEnvelope),
    handled by the caller.
    """
    client = get_lambda_client()
    response = client.invoke(
        FunctionName=settings.INFERENCE_LAMBDA_PYSPACER,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    raw = response["Payload"].read()
    if response.get("FunctionError"):
        detail = raw.decode("utf-8", errors="replace")[:500]
        raise InferenceError(f"Lambda FunctionError ({response['FunctionError']}): {detail}")
    return json.loads(raw)


def build_pyspacer_request(image, points, traceparent) -> dict:
    config = get_image_storage_config(image.image_bucket)
    request = PyspacerRequest(
        classifier_type="pyspacer",
        image=S3Location(bucket=config["bucket"], key=f"{config['s3_path']}{image.image.name}"),
        points=[(int(row), int(col)) for row, col in points],
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
    """PyspacerResponse -> normalized [(row, col, [(label, score), ...ranked])]."""
    return [
        (pr.row, pr.col, [(ps.label, ps.score) for ps in pr.scores])
        for pr in response.point_results
    ]


def classify_via_lambda(image, points):
    """Invoke the pyspacer Lambda for an image and return normalized point predictions.

    Raises InferenceError on an ErrorEnvelope payload, a classifier-version drift
    mismatch, or a contract-version mismatch.
    """
    tracer = otel_trace.get_tracer("api.inference")
    with tracer.start_as_current_span("pyspacer.classify_via_lambda"):
        traceparent = _current_traceparent()
        logger.info("pyspacer inference invoke", extra={"traceparent": traceparent})
        payload = invoke_pyspacer(build_pyspacer_request(image, points, traceparent))

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

        installed = mermaid_inference_contract.__version__
        if response.contract_version and response.contract_version != installed:
            logger.error(
                "pyspacer contract version mismatch",
                extra={"traceparent": traceparent},
            )
            raise InferenceError(
                f"Contract version mismatch: Lambda reported {response.contract_version!r}, "
                f"API has {installed!r} — pin mermaid-inference-contract to the deployed image's tag"
            )

        return response_to_point_predictions(response)
