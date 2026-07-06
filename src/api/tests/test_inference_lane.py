import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from api.models import Image
from api.utils import inference
from api.utils.inference import InferenceError, classify_via_lambda


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
