import logging

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from mermaid_inference_contract import parse_traceparent
from opentelemetry import trace as otel_trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from api.models import Image
from api.models.classification import get_image_storage_config
from api.utils import inference
from api.utils.inference import (
    InferenceError,
    build_pyspacer_request,
    classify_via_lambda,
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


def _ok_payload(version="v2"):
    return {
        "classifier_type": "pyspacer",
        "classifier_version": version,
        "valid_rowcol": True,
        "traceparent": None,
        "point_results": [
            {
                "row": 1,
                "col": 2,
                "scores": [
                    {"label": "ba1::", "score": 0.9},
                    {"label": "ba2::", "score": 0.1},
                ],
            },
        ],
    }


def test_build_pyspacer_request_shape(image):
    traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
    req = build_pyspacer_request(image, [(1, 2), (3, 4)], traceparent)

    config = get_image_storage_config(image.image_bucket)

    assert req["classifier_type"] == "pyspacer"
    assert req["image"]["bucket"] == config["bucket"]
    assert req["image"]["key"] == f"{config['s3_path']}{image.image.name}"
    assert req["points"] == [[1, 2], [3, 4]]
    assert req["traceparent"] == traceparent
    assert "classifier_version" not in req


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_maps_response(monkeypatch, image):
    captured_payloads = []

    def fake_invoke(payload):
        captured_payloads.append(payload)
        return _ok_payload("v2")

    monkeypatch.setattr(inference, "invoke_pyspacer", fake_invoke)
    preds = classify_via_lambda(image, [(1, 2)])
    assert preds == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]

    # The request sent to the Lambda carries a derived (well-formed) traceparent.
    assert len(captured_payloads) == 1
    parsed = parse_traceparent(captured_payloads[0]["traceparent"])
    assert parsed.trace_id and parsed.parent_id


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
    with pytest.raises(InferenceError) as exc:
        classify_via_lambda(image, [(1, 2)])
    assert "drift" in str(exc.value).lower()


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_contract_version_mismatch_raises(monkeypatch, image):
    payload = _ok_payload("v2")
    payload["contract_version"] = "9.9.9"  # != installed
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)
    with pytest.raises(InferenceError) as exc:
        classify_via_lambda(image, [(1, 2)])
    assert "contract" in str(exc.value).lower()


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_contract_version_match_ok(monkeypatch, image):
    import mermaid_inference_contract as contract

    payload = _ok_payload("v2")
    payload["contract_version"] = contract.__version__  # matches installed
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)
    preds = classify_via_lambda(image, [(1, 2)])
    assert preds == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_classify_via_lambda_missing_contract_version_tolerated(monkeypatch, image):
    payload = _ok_payload("v2")  # no contract_version key -> None (older Lambda)
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda p: payload)
    preds = classify_via_lambda(image, [(1, 2)])  # must NOT raise
    assert preds == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]


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
        with caplog.at_level(logging.INFO, logger="api.utils.inference"):
            classify_via_lambda(image, [(1, 2)])
    finally:
        inference.logger.removeHandler(caplog.handler)

    invoke_records = [r for r in caplog.records if getattr(r, "traceparent", None)]
    assert invoke_records, "expected a log record carrying the traceparent"
    parsed = parse_traceparent(invoke_records[0].traceparent)
    assert parsed.trace_id and parsed.parent_id
