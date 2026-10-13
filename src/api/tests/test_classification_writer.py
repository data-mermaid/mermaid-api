from django.test import override_settings

from api.models import Annotation, Image, Point
from api.utils.classification import _write_classification_results

# A label scores 0..1; anything at or above CLASSIFIED_THRESHOLD is written, and
# anything at or above AUTOCONFIRM_THRESHOLD is written confirmed.
THRESHOLDS = {"CLASSIFIED_THRESHOLD": 0.5, "AUTOCONFIRM_THRESHOLD": 1.0}


@override_settings(**THRESHOLDS)
def test_writes_points_and_thresholded_annotations(
    image,
    classifier_v2,
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

    _write_classification_results(image, predictions, classifier_v2)

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
        (benthic_attribute_1.pk, growth_form1.pk, 100, True, True, classifier_v2.pk),
        (benthic_attribute_3.pk, None, 60, False, True, classifier_v2.pk),
    ]


@override_settings(**THRESHOLDS)
def test_keeps_only_the_three_highest_scoring_labels(
    image,
    classifier_v2,
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

    _write_classification_results(image, predictions, classifier_v2)

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
def test_skips_a_label_carrying_no_benthic_attribute(image, classifier_v2, growth_form1):
    predictions = [(1, 2, [(f"::{growth_form1.pk}", 0.9)])]

    _write_classification_results(image, predictions, classifier_v2)

    point = Point.objects.get(image=image)
    assert point.annotations.count() == 0


@override_settings(**THRESHOLDS)
def test_writes_nothing_when_the_image_row_is_gone(image, classifier_v2, benthic_attribute_1):
    image_id = image.pk
    predictions = [(1, 2, [(f"{benthic_attribute_1.pk}::", 0.9)])]
    Image.objects.filter(pk=image_id).delete()

    _write_classification_results(image, predictions, classifier_v2)

    assert Point.objects.filter(image_id=image_id).count() == 0
    assert Annotation.objects.filter(point__image_id=image_id).count() == 0
