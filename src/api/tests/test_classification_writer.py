import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from api.models import Annotation, Classifier, Image, Point
from api.utils.classification import (
    _legacy_point_predictions,
    _write_classification_results,
)


@pytest.fixture
def classifier():
    return Classifier.objects.create(name="t", version="v-writer", config={"patch_size": 224})


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


def test_legacy_point_predictions_ranks_descending():
    label_ids = ["a::", "b::"]
    score_sets = [(1, 2, [0.1, 0.9])]
    out = _legacy_point_predictions(label_ids, score_sets)
    assert out == [(1, 2, [("b::", 0.9), ("a::", 0.1)])]


@override_settings(CLASSIFIED_THRESHOLD=0.5, AUTOCONFIRM_THRESHOLD=1.0)
def test_writer_creates_points_and_thresholded_annotations(
    classifier, benthic_attribute_1, benthic_attribute_2, image
):
    ba1, ba2 = str(benthic_attribute_1.pk), str(benthic_attribute_2.pk)
    # point (10,20): ba1 above threshold (0.8), ba2 below (0.2) -> 1 annotation
    point_predictions = [(10, 20, [(f"{ba1}", 0.8), (f"{ba2}", 0.2)])]

    _write_classification_results(image, point_predictions, classifier, profile=None)

    points = list(Point.objects.filter(image=image))
    assert len(points) == 1 and (points[0].row, points[0].column) == (10, 20)
    annos = list(Annotation.objects.filter(point=points[0]))
    assert len(annos) == 1
    assert str(annos[0].benthic_attribute_id) == ba1
    assert annos[0].growth_form_id is None
    assert annos[0].score == pytest.approx(80.0)
    assert annos[0].is_confirmed is False  # 0.8 < AUTOCONFIRM_THRESHOLD (1.0)
    assert annos[0].is_machine_created is True


@override_settings(CLASSIFIED_THRESHOLD=0.5, AUTOCONFIRM_THRESHOLD=1.0)
def test_writer_empty_growth_form_label_maps_to_none(classifier, benthic_attribute_1, image):
    ba1 = str(benthic_attribute_1.pk)
    # Trailing-separator label "ba::" -> split yields gf_id == "" which the writer's
    # `gf_id = gf_id or None` guard must convert to a None FK (an empty string would
    # otherwise break the growth_form_id FK write).
    point_predictions = [(10, 20, [(f"{ba1}::", 0.8)])]

    _write_classification_results(image, point_predictions, classifier, profile=None)

    points = list(Point.objects.filter(image=image))
    assert len(points) == 1
    annos = list(Annotation.objects.filter(point=points[0]))
    assert len(annos) == 1
    assert str(annos[0].benthic_attribute_id) == ba1
    assert annos[0].growth_form_id is None
    assert annos[0].score == pytest.approx(80.0)
    assert annos[0].is_confirmed is False
    assert annos[0].is_machine_created is True
