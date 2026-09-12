import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from api.models import Annotation, Classifier, Image, Point
from api.utils.classification import _write_classification_results

# A label scores 0..1; anything at or above CLASSIFIED_THRESHOLD is written, and
# anything at or above AUTOCONFIRM_THRESHOLD is written confirmed.
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
def classifier():
    return Classifier.objects.create(
        name="Test classifier", version="v2", config={"patch_size": 144}
    )


@override_settings(**THRESHOLDS)
def test_writes_points_and_thresholded_annotations(
    image,
    classifier,
    benthic_attribute_1,
    benthic_attribute_3,
    benthic_attribute_4,
    growth_form1,
):
    predictions = [
        (
            10,
            20,
            [
                (f"{benthic_attribute_1.pk}::{growth_form1.pk}", 1.0),
                (f"{benthic_attribute_3.pk}::", 0.6),
                (f"{benthic_attribute_4.pk}::", 0.4),
            ],
        )
    ]

    _write_classification_results(image, predictions, classifier)

    point = Point.objects.get(image=image)
    assert (point.row, point.column) == (10, 20)

    annotations = point.annotations.order_by("-score")
    assert [
        (
            annotation.benthic_attribute_id,
            annotation.growth_form_id,
            annotation.score,
            annotation.is_confirmed,
            annotation.is_machine_created,
            annotation.classifier_id,
        )
        for annotation in annotations
    ] == [
        (benthic_attribute_1.pk, growth_form1.pk, 100, True, True, classifier.pk),
        (benthic_attribute_3.pk, None, 60, False, True, classifier.pk),
    ]


@override_settings(**THRESHOLDS)
def test_empty_growth_form_segment_writes_a_null_growth_form(
    image, classifier, benthic_attribute_1
):
    predictions = [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])]

    _write_classification_results(image, predictions, classifier)

    annotation = Annotation.objects.get(point__image=image)
    assert annotation.benthic_attribute_id == benthic_attribute_1.pk
    assert annotation.growth_form_id is None


@override_settings(**THRESHOLDS)
def test_keeps_only_the_three_highest_scoring_labels(
    image,
    classifier,
    benthic_attribute_1,
    benthic_attribute_2,
    benthic_attribute_3,
    benthic_attribute_4,
    benthic_attribute_1a,
):
    predictions = [
        (
            0,
            0,
            [
                (f"{benthic_attribute_4.pk}::", 0.95),
                (f"{benthic_attribute_3.pk}::", 0.9),
                (f"{benthic_attribute_2.pk}::", 0.8),
                (f"{benthic_attribute_1.pk}::", 0.7),
                (f"{benthic_attribute_1a.pk}::", 0.65),
            ],
        )
    ]

    _write_classification_results(image, predictions, classifier)

    point = Point.objects.get(image=image)
    assert [
        (annotation.benthic_attribute_id, annotation.score)
        for annotation in point.annotations.order_by("-score")
    ] == [
        (benthic_attribute_4.pk, 95),
        (benthic_attribute_3.pk, 90),
        (benthic_attribute_2.pk, 80),
    ]


@override_settings(**THRESHOLDS)
def test_skips_a_label_carrying_no_benthic_attribute(image, classifier, growth_form1):
    predictions = [(1, 2, [(f"::{growth_form1.pk}", 0.9)])]

    _write_classification_results(image, predictions, classifier)

    point = Point.objects.get(image=image)
    assert point.annotations.count() == 0


@override_settings(**THRESHOLDS)
def test_writes_nothing_when_the_image_row_is_gone(image, classifier, benthic_attribute_1):
    image_id = image.pk
    predictions = [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])]
    Image.objects.filter(pk=image_id).delete()

    _write_classification_results(image, predictions, classifier)

    assert Point.objects.filter(image_id=image_id).count() == 0
    assert Annotation.objects.filter(point__image_id=image_id).count() == 0
