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
def test_classifies_an_image_and_completes(monkeypatch, image, classifier_v2, benthic_attribute_1):
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


@override_settings(**PINNED, **THRESHOLDS)
def test_relocates_the_feature_vector_before_recording_it(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    """The row is only updated once relocate_feature_vector confirms the object
    exists at its final key — never from the Lambda's response alone."""
    _stub_lambda(
        monkeypatch,
        [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])],
        feature_vector_name=f"{image.id}_featurevector",
    )
    seen = []

    def fake_relocate(img, name):
        seen.append(Image.objects.get(pk=img.pk).feature_vector_file.name)
        return True

    monkeypatch.setattr(classification, "relocate_feature_vector", fake_relocate)

    _classify_image(image.pk)

    assert seen == [""]  # column still unset when relocation runs
    assert Image.objects.get(pk=image.pk).feature_vector_file.name == f"{image.id}_featurevector"


@override_settings(**PINNED, **THRESHOLDS)
def test_leaves_the_feature_vector_unset_when_relocation_fails(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    """A failed relocation must not point feature_vector_file at a key that was
    never written to its final bucket, and must not fail the classification: point
    predictions are the product, the feature vector is not."""
    _stub_lambda(
        monkeypatch,
        [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])],
        feature_vector_name=f"{image.id}_featurevector",
    )
    monkeypatch.setattr(classification, "relocate_feature_vector", lambda img, name: False)

    _classify_image(image.pk)

    assert not Image.objects.get(pk=image.pk).feature_vector_file
    assert ClassificationStatus.COMPLETED in _statuses(image)
    assert ClassificationStatus.FAILED not in _statuses(image)


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


@override_settings(**PINNED)
def test_fatal_classification_failure_logs_the_processing_error_marker(
    monkeypatch, image, classifier_v2, caplog
):
    """The CloudWatch metric filter in iac/stacks/constructs/alerts.py alarms on this
    literal marker on the image worker's log group; a fatal failure that never logs
    it is invisible to that alarm."""

    def raise_inference_error(image, points):
        raise InferenceError("Lambda said no")

    monkeypatch.setattr(classification, "classify_via_lambda", raise_inference_error)

    # "api" is configured with propagate=False (see app/settings.py LOGGING), so
    # caplog's root-attached handler never observes records from api.utils.classification
    # unless attached directly to that logger.
    classification.logger.addHandler(caplog.handler)
    try:
        _classify_image(image.pk)
    finally:
        classification.logger.removeHandler(caplog.handler)

    assert "[classify.processing_error]" in caplog.text


@override_settings(**PINNED)
def test_retryable_classification_failure_omits_the_processing_error_marker(
    monkeypatch, image, classifier_v2, caplog
):
    """A retryable failure already has the SQS DLQ alarm behind it; marking it here
    too would fire the permanent-failure alarm on a throttle or cold-start blip."""

    def raise_retryable_inference_error(image, points):
        raise InferenceError("Lambda throttled", retryable=True)

    monkeypatch.setattr(classification, "classify_via_lambda", raise_retryable_inference_error)

    classification.logger.addHandler(caplog.handler)
    try:
        with pytest.raises(InferenceError):
            _classify_image(image.pk)
    finally:
        classification.logger.removeHandler(caplog.handler)

    assert "[classify.processing_error]" not in caplog.text


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


@override_settings(**PINNED, **THRESHOLDS)
def test_reclassifying_skips_an_image_with_reviewed_points(
    monkeypatch, image, classifier_v2, benthic_attribute_1, benthic_attribute_3
):
    reviewed_point = Point.objects.create(image=image, row=99, column=99)
    reviewed_annotation = Annotation.objects.create(
        point=reviewed_point,
        benthic_attribute=benthic_attribute_3,
        classifier=classifier_v2,
        score=50,
        is_machine_created=True,
        is_confirmed=True,
    )
    _stub_lambda(monkeypatch, [(11, 22, [(f"{benthic_attribute_1.pk}::", 0.9)])])

    _classify_image(image.pk)

    assert Point.objects.filter(pk=reviewed_point.pk).exists()
    assert Annotation.objects.filter(pk=reviewed_annotation.pk).exists()
    assert Point.objects.filter(image=image).count() == 1
    assert ClassificationStatus.COMPLETED in _statuses(image)


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
