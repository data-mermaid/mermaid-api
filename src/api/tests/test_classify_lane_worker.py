import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from api.models import Annotation, ClassificationStatus, Classifier, Image, Point
from api.utils import classification, inference, q
from api.utils.classification import _classify_image, classify_image_job
from api.utils.inference import InferenceError, LambdaClassificationResult

PINNED = {"INFERENCE_CLASSIFIER_VERSION": "v2"}
THRESHOLDS = {"CLASSIFIED_THRESHOLD": 0.5, "AUTOCONFIRM_THRESHOLD": 1.0}


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


@pytest.fixture
def classifier_v2():
    return Classifier.objects.create(
        name="Test classifier", version="v2", config={"patch_size": 144}
    )


def _stub_lambda(monkeypatch, predictions, feature_vector_name=None, captured_points=None):
    """Stand in for the inference Lambda, optionally recording the points it is sent."""

    def fake_classify_via_lambda(image, points):
        if captured_points is not None:
            captured_points.extend(points)
        return LambdaClassificationResult(
            point_predictions=predictions, feature_vector_name=feature_vector_name
        )

    monkeypatch.setattr(classification, "classify_via_lambda", fake_classify_via_lambda)


def _statuses(image):
    return set(image.statuses.values_list("status", flat=True))


@override_settings(**PINNED, **THRESHOLDS)
def test_classifies_an_image_and_completes(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    _stub_lambda(monkeypatch, [(11, 22, [(f"{benthic_attribute_1.pk}::", 0.9)])])

    _classify_image(image.pk)

    point = Point.objects.get(image=image)
    assert (point.row, point.column) == (11, 22)
    annotation = Annotation.objects.get(point=point)
    assert annotation.benthic_attribute_id == benthic_attribute_1.pk
    assert annotation.classifier_id == classifier_v2.pk
    assert ClassificationStatus.COMPLETED in _statuses(image)
    assert ClassificationStatus.FAILED not in _statuses(image)


@override_settings(**PINNED, **THRESHOLDS)
def test_records_the_feature_vector_name_on_the_image_row(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    _stub_lambda(
        monkeypatch,
        [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])],
        feature_vector_name=f"{image.id}_featurevector",
    )

    _classify_image(image.pk)

    assert Image.objects.get(pk=image.pk).feature_vector_file.name == f"{image.id}_featurevector"


@override_settings(**PINNED, **THRESHOLDS)
def test_leaves_the_feature_vector_unset_when_the_lambda_wrote_none(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    _stub_lambda(
        monkeypatch, [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])], feature_vector_name=None
    )

    _classify_image(image.pk)

    assert not Image.objects.get(pk=image.pk).feature_vector_file
    assert ClassificationStatus.COMPLETED in _statuses(image)


@override_settings(**PINNED)
def test_inference_error_fails_the_job_with_its_message(monkeypatch, image, classifier_v2):
    def raise_inference_error(image, points):
        raise InferenceError("Lambda said no")

    monkeypatch.setattr(classification, "classify_via_lambda", raise_inference_error)

    _classify_image(image.pk)

    failed = image.statuses.filter(status=ClassificationStatus.FAILED).first()
    assert failed is not None
    assert failed.message == "Lambda said no"
    assert Point.objects.filter(image=image).count() == 0


@override_settings(**PINNED, **THRESHOLDS)
def test_attributes_points_and_annotations_to_the_profile(
    monkeypatch, image, classifier_v2, benthic_attribute_1, profile1
):
    _stub_lambda(monkeypatch, [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])])

    _classify_image(image.pk, profile_id=profile1.pk)

    point = Point.objects.get(image=image)
    assert point.created_by_id == profile1.pk
    assert point.updated_by_id == profile1.pk
    annotation = Annotation.objects.get(point=point)
    assert annotation.created_by_id == profile1.pk
    assert annotation.updated_by_id == profile1.pk


@override_settings(**PINNED)
def test_generates_the_requested_number_of_points(monkeypatch, image, classifier_v2):
    captured_points = []
    _stub_lambda(monkeypatch, [], captured_points=captured_points)

    _classify_image(image.pk, num_points=9)

    # generate_points lays out ceil(sqrt(9)) = 3 points per side.
    assert len(captured_points) == 9


@override_settings(**PINNED, INFERENCE_DEFAULT_NUM_POINTS=9)
def test_defaults_the_number_of_points_to_the_setting(monkeypatch, image, classifier_v2):
    captured_points = []
    _stub_lambda(monkeypatch, [], captured_points=captured_points)

    _classify_image(image.pk)

    assert len(captured_points) == 9


@override_settings(**PINNED, **THRESHOLDS)
def test_reclassifying_replaces_rather_than_duplicates_points(
    monkeypatch, image, classifier_v2, benthic_attribute_1, benthic_attribute_3
):
    stale_point = Point.objects.create(image=image, row=99, column=99)
    Annotation.objects.create(
        point=stale_point,
        benthic_attribute=benthic_attribute_3,
        classifier=classifier_v2,
        score=50,
        is_machine_created=True,
    )
    _stub_lambda(monkeypatch, [(11, 22, [(f"{benthic_attribute_1.pk}::", 0.9)])])

    _classify_image(image.pk)

    points = list(Point.objects.filter(image=image))
    assert len(points) == 1
    assert (points[0].row, points[0].column) == (11, 22)
    assert not Point.objects.filter(pk=stale_point.pk).exists()
    assert Annotation.objects.filter(point__image=image).count() == 1


@override_settings(INFERENCE_CLASSIFIER_VERSION="v-missing", **THRESHOLDS)
def test_fails_when_no_classifier_matches_the_pinned_version(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    _stub_lambda(monkeypatch, [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])])

    _classify_image(image.pk)

    assert Point.objects.filter(image=image).count() == 0
    failed = image.statuses.filter(status=ClassificationStatus.FAILED).first()
    assert failed is not None
    assert "v-missing" in failed.message


@override_settings(**PINNED, INFERENCE_LAMBDA_PYSPACER="", AWS_REGION="us-east-1")
def test_fails_when_the_lambda_name_is_unset(monkeypatch, image, classifier_v2):
    # The real lane runs here: botocore rejects an empty FunctionName client-side and
    # invoke_pyspacer turns that into an InferenceError. Reset the cached client so the
    # AWS_REGION override applies and no client built here outlives the test.
    monkeypatch.setattr(inference, "_lambda_client", None)

    _classify_image(image.pk)

    assert Point.objects.filter(image=image).count() == 0
    failed = image.statuses.filter(status=ClassificationStatus.FAILED).first()
    assert failed is not None
    assert "Lambda invoke failed" in failed.message


@override_settings(TESTING=False)
def test_classify_image_job_enqueues_with_a_visibility_timeout(monkeypatch, image, profile1):
    enqueued = []

    class RecordingQueue:
        def __init__(self, name, *args, **kwargs):
            self.name = name

        def add_job(self, job, delay=None):
            enqueued.append(job)

    monkeypatch.setattr(q, "Queue", RecordingQueue)

    classify_image_job(image.pk, profile_id=profile1.pk, num_points=9)

    assert len(enqueued) == 1
    job = enqueued[0]
    # The Lambda's own timeout is 600s; a shorter visibility timeout redelivers the
    # message while the first attempt is still running.
    assert job.visibility_timeout >= 600
    assert job.kwargs == {
        "image_record_id": image.pk,
        "profile_id": profile1.pk,
        "num_points": 9,
    }
