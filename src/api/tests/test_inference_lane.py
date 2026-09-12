from unittest.mock import MagicMock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from mermaid_inference_contract import (
    PointResult,
    PointScore,
    PyspacerResponse,
    S3Location,
    __version__ as CONTRACT_VERSION,
    parse_traceparent,
)
from opentelemetry import trace as otel_trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from api.models import Image
from api.tests.test_image_bucket_routing import STORAGE_SETTINGS
from api.utils import inference
from api.utils.inference import (
    InferenceError,
    build_pyspacer_request,
    classify_via_lambda,
    feature_vector_location,
    response_to_point_predictions,
)

# The deployed handler always emits every PyspacerResponse field; this default mirrors
# that, so a test only overrides the one field its scenario is actually about.
_DEFAULT_FEATURE_VECTOR_OUTPUT = S3Location(
    bucket="prod-bucket", key="mermaid/default_featurevector"
)


@pytest.fixture
def image(valid_benthic_pq_transect_collect_record):
    with open("api/tests/data/test_image.jpg", "rb") as f:
        content = f.read()

    image_file = SimpleUploadedFile(
        name="test_image.jpg", content=content, content_type="image/jpeg"
    )

    return Image.objects.create(
        collect_record_id=valid_benthic_pq_transect_collect_record.pk,
        image=image_file,
        name="Test image",
    )


def _ok_payload(
    version="v2",
    feature_vector_output=_DEFAULT_FEATURE_VECTOR_OUTPUT,
    contract_version=CONTRACT_VERSION,
):
    return PyspacerResponse(
        classifier_type="pyspacer",
        classifier_version=version,
        valid_rowcol=True,
        point_results=[
            PointResult(
                row=1,
                col=2,
                scores=[
                    PointScore(label="ba1::", score=0.9),
                    PointScore(label="ba2::", score=0.1),
                ],
            ),
        ],
        feature_vector_output=feature_vector_output,
        traceparent=None,
        contract_version=contract_version,
    ).model_dump(mode="json")


# --- build_pyspacer_request ---


@override_settings(**STORAGE_SETTINGS)
@pytest.mark.parametrize(
    "bucket,expected_key",
    [
        ("prod-bucket", "mermaid/abc123.png"),
        ("test-bucket", "mermaid-production-test/abc123.png"),
    ],
)
def test_build_pyspacer_request_image_key(bucket, expected_key):
    image = MagicMock()
    image.image_bucket = bucket
    image.image.name = "abc123.png"
    traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

    req = build_pyspacer_request(image, [(1, 2), (3, 4)], traceparent)

    assert req["classifier_type"] == "pyspacer"
    assert req["image"] == {"bucket": bucket, "key": expected_key}
    assert req["points"] == [[1, 2], [3, 4]]
    assert req["traceparent"] == traceparent


@override_settings(**STORAGE_SETTINGS)
def test_build_pyspacer_request_feature_vector_output():
    image = MagicMock()
    image.id = "abc123"
    image.image_bucket = "prod-bucket"
    image.image.name = "abc123.png"
    traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

    _, feature_vector_output = feature_vector_location(image)
    req = build_pyspacer_request(
        image, [(1, 2)], traceparent, feature_vector_output=feature_vector_output
    )

    assert req["feature_vector_output"] == {
        "bucket": "prod-bucket",
        "key": "mermaid/abc123_featurevector",
    }


# --- classify_via_lambda ---


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
@override_settings(**STORAGE_SETTINGS)
def test_classify_via_lambda_maps_response(monkeypatch, image):
    captured_payloads = []
    # Hand-written, not computed via feature_vector_location(image): the image fixture
    # has no image_bucket set, so get_image_storage_config resolves the default (prod)
    # bucket/prefix from STORAGE_SETTINGS above.
    requested_location = S3Location(bucket="prod-bucket", key=f"mermaid/{image.id}_featurevector")

    def fake_invoke(payload):
        captured_payloads.append(payload)
        return _ok_payload("v2", feature_vector_output=requested_location)

    monkeypatch.setattr(inference, "invoke_pyspacer", fake_invoke)
    result = classify_via_lambda(image, [(1, 2)])
    assert result.point_predictions == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]
    assert result.feature_vector_name == f"{image.id}_featurevector"

    # The request sent to the Lambda carries a derived (well-formed) traceparent.
    assert len(captured_payloads) == 1
    parsed = parse_traceparent(captured_payloads[0]["traceparent"])
    assert parsed.trace_id and parsed.parent_id


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_returns_no_feature_vector_name_when_response_echoes_none(
    monkeypatch, image
):
    payload = _ok_payload("v2", feature_vector_output=None)  # no feature vector written
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)

    result = classify_via_lambda(image, [(1, 2)])

    assert result.feature_vector_name is None
    assert result.point_predictions == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_raises_on_error_envelope(monkeypatch, image):
    envelope = {"error_code": "processing_error", "message": "kaboom", "retryable": False}
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda payload: envelope)
    with pytest.raises(InferenceError) as exc:
        classify_via_lambda(image, [(1, 2)])
    assert "kaboom" in str(exc.value)


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_drift_guard(monkeypatch, image):
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda payload: _ok_payload("v3"))
    with pytest.raises(InferenceError) as excinfo:
        classify_via_lambda(image, [(1, 2)])
    assert "drift" in str(excinfo.value).lower()
    # Retryable: ApiStack and InferenceStack deploy independently; on a version bump
    # SQS redelivers after the visibility timeout and the image classifies correctly.
    assert excinfo.value.retryable is True


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_contract_version_mismatch_raises(monkeypatch, image):
    payload = _ok_payload("v2")
    payload["contract_version"] = "9.9.9"  # != installed
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)
    with pytest.raises(InferenceError) as excinfo:
        classify_via_lambda(image, [(1, 2)])
    assert "contract" in str(excinfo.value).lower()
    # Non-retryable: contract skew is a configuration error that redelivery cannot fix;
    # it should fail once and alarm instead of looping to the DLQ.
    assert excinfo.value.retryable is False


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_contract_version_match_ok(monkeypatch, image):
    import mermaid_inference_contract as contract

    payload = _ok_payload("v2")
    payload["contract_version"] = contract.__version__  # matches installed
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)
    result = classify_via_lambda(image, [(1, 2)])
    assert result.point_predictions == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_missing_contract_version_tolerated(monkeypatch, image):
    payload = _ok_payload("v2", contract_version=None)  # older Lambda: no contract_version
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)
    result = classify_via_lambda(image, [(1, 2)])  # must NOT raise
    assert result.point_predictions == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]


def test_current_traceparent_uses_valid_span_context(monkeypatch):
    """_current_traceparent() derives trace_id/parent_id from a valid active span."""
    trace_id = 0x0AF7651916CD43DD8448EB211C80319C
    span_id = 0xB7AD6B7169203331
    span_context = SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    monkeypatch.setattr(
        inference.otel_trace,
        "get_current_span",
        lambda: NonRecordingSpan(span_context),
    )

    traceparent = inference._current_traceparent()

    parsed = parse_traceparent(traceparent)
    assert parsed.trace_id == format(trace_id, "032x")
    assert parsed.parent_id == format(span_id, "016x")
    assert parsed.flags == "01"


def test_current_traceparent_falls_back_without_valid_span(monkeypatch):
    """With no valid active span, _current_traceparent() still returns a well-formed id."""
    monkeypatch.setattr(inference.otel_trace, "get_current_span", lambda: otel_trace.INVALID_SPAN)

    traceparent = inference._current_traceparent()

    parsed = parse_traceparent(traceparent)  # raises ValueError if malformed
    assert parsed.trace_id != "0" * 32
    assert parsed.parent_id != "0" * 16


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_logs_traceparent_at_invoke(monkeypatch, image, caplog):
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda payload: _ok_payload("v2"))

    # The "api" logger is configured with propagate=False (see app/settings.py LOGGING),
    # so caplog's root-attached handler never observes records from api.utils.inference
    # unless we attach it directly to that logger.
    inference.logger.addHandler(caplog.handler)
    try:
        classify_via_lambda(image, [(1, 2)])
    finally:
        inference.logger.removeHandler(caplog.handler)

    invoke_records = [r for r in caplog.records if getattr(r, "traceparent", None)]
    assert invoke_records, "expected a log record carrying the traceparent"
    parsed = parse_traceparent(invoke_records[0].traceparent)
    assert parsed.trace_id and parsed.parent_id


# --- response_to_point_predictions ---


def test_response_to_point_predictions_ranks_descending():
    response = PyspacerResponse(
        classifier_type="pyspacer",
        classifier_version="v2",
        valid_rowcol=True,
        point_results=[
            PointResult(
                row=1,
                col=2,
                scores=[
                    PointScore(label="low", score=0.1),
                    PointScore(label="high", score=0.9),
                    PointScore(label="mid", score=0.5),
                ],
            )
        ],
    )

    predictions = response_to_point_predictions(response)

    assert predictions == [(1, 2, [("high", 0.9), ("mid", 0.5), ("low", 0.1)])]
