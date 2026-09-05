import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from api.models import Annotation, ClassificationStatus, Classifier, Image, Point
from api.utils import classification as clf


@pytest.fixture
def classifier():
    return Classifier.objects.create(name="t", version="v2", config={"patch_size": 224})


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


@override_settings(INFERENCE_LAMBDA_PYSPACER="fn", INFERENCE_CLASSIFIER_VERSION="v2")
def test_lambda_lane_writes_annotations(monkeypatch, classifier, benthic_attribute_1, image):
    ba1 = str(benthic_attribute_1.pk)
    monkeypatch.setattr(
        clf,
        "classify_via_lambda",
        lambda img, points: [(1, 2, [(ba1, 0.8)])],
    )
    clf.classify_image_job(image.pk, num_points=10)

    assert Point.objects.filter(image=image).count() == 1
    anno = Annotation.objects.get(point__image=image)
    assert str(anno.benthic_attribute_id) == ba1
    assert anno.classifier_id == classifier.id
    status = ClassificationStatus.objects.filter(image=image).order_by("-created_on").first()
    assert status.status == ClassificationStatus.COMPLETED


@override_settings(INFERENCE_LAMBDA_PYSPACER="fn", INFERENCE_CLASSIFIER_VERSION="v2")
def test_lambda_lane_error_sets_failed(monkeypatch, classifier, image):
    def _boom(img, points):
        raise clf.InferenceError("kaboom")

    monkeypatch.setattr(clf, "classify_via_lambda", _boom)
    clf.classify_image_job(image.pk, num_points=10)

    status = ClassificationStatus.objects.filter(image=image).order_by("-created_on").first()
    assert status.status == ClassificationStatus.FAILED
    assert "kaboom" in (status.message or "")


@override_settings(INFERENCE_LAMBDA_PYSPACER="", INFERENCE_CLASSIFIER_VERSION="")
def test_empty_toggle_uses_legacy_lane(monkeypatch, image):
    called = {"lambda": False, "in_process": False}
    monkeypatch.setattr(
        clf, "classify_via_lambda", lambda *a, **k: called.__setitem__("lambda", True) or []
    )
    monkeypatch.setattr(
        clf, "_classify_in_process", lambda *a, **k: called.__setitem__("in_process", True)
    )
    clf.classify_image_job(image.pk)
    assert called == {"lambda": False, "in_process": True}


@override_settings(INFERENCE_LAMBDA_PYSPACER="fn", INFERENCE_CLASSIFIER_VERSION="v2")
def test_num_points_threaded_to_generate_points(monkeypatch, classifier, image):
    seen = {}
    monkeypatch.setattr(clf, "generate_points", lambda img, n: seen.setdefault("n", n) or [(1, 2)])
    monkeypatch.setattr(clf, "classify_via_lambda", lambda img, points: [])
    clf.classify_image_job(image.pk, num_points=7)
    assert seen["n"] == 7
