import pytest
from django.test import override_settings

from api.models import Annotation, ClassificationStatus, Image, Point
from api.utils import classification, q
from api.utils.classification import _classify_image, classify_image_job
from api.utils.inference import InferenceError, LambdaClassificationResult

PINNED = {"INFERENCE_CLASSIFIER_VERSION": "v2"}
THRESHOLDS = {"CLASSIFIED_THRESHOLD": 0.5, "AUTOCONFIRM_THRESHOLD": 1.0}


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
def test_records_the_feature_vector_name_the_lambda_wrote(
    monkeypatch, image, classifier_v2, benthic_attribute_1
):
    """The Lambda writes each feature vector straight to its final key; the row
    records that same name with no relocation step in between."""
    _stub_lambda(
        monkeypatch,
        [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])],
        feature_vector_name=f"{image.id}_featurevector",
    )

    _classify_image(image.pk)

    assert Image.objects.get(pk=image.pk).feature_vector_file.name == f"{image.id}_featurevector"


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


@pytest.mark.parametrize(
    "num_points, expected",
    [
        pytest.param(9, 9, id="explicit_arg"),
        pytest.param(None, 9, id="falls_back_to_setting"),
    ],
)
@override_settings(**PINNED, INFERENCE_DEFAULT_NUM_POINTS=9)
def test_generates_the_requested_number_of_points(
    monkeypatch, image, classifier_v2, num_points, expected
):
    captured_points = []
    _stub_lambda(monkeypatch, [], captured_points=captured_points)

    _classify_image(image.pk, num_points=num_points)

    # generate_points lays out ceil(sqrt(n)) points per side.
    assert len(captured_points) == expected


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


@override_settings(TESTING=False)
def test_classify_image_job_enqueues_with_a_visibility_timeout(monkeypatch, image):
    enqueued = []

    class RecordingQueue:
        def __init__(self, name, *args, **kwargs):
            self.name = name

        def add_job(self, job, delay=None):
            enqueued.append(job)

    monkeypatch.setattr(q, "Queue", RecordingQueue)

    classify_image_job(image.pk, num_points=9)

    assert len(enqueued) == 1
    job = enqueued[0]
    assert job.kwargs == {
        "image_record_id": image.pk,
        "num_points": 9,
    }
