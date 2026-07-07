import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

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
    monkeypatch.setattr(inference, "invoke_pyspacer", lambda payload: _ok_payload("v2"))
    preds = classify_via_lambda(image, [(1, 2)])
    assert preds == [(1, 2, [("ba1::", 0.9), ("ba2::", 0.1)])]


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
