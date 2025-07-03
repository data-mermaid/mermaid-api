import pytest
from django.core.files import File

from api.models import (
    BENTHICPQT_PROTOCOL,
    Annotation,
    Classifier,
    CollectRecord,
    Image,
    Point,
)
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import OK, WARN
from api.submission.validations.validators import ImageCountValidator


@pytest.fixture
def classifier():
    return Classifier.objects.create(
        name="Test",
        version="v1",
        patch_size=128,
        num_points=2,
    )


@pytest.fixture
def image_collect_record(project1, profile1):
    return CollectRecord.objects.create(
        project=project1,
        profile=profile1,
        data={
            "image_classification": True,
            "protocol": BENTHICPQT_PROTOCOL,
            "quadrat_transect": {"num_quadrats": 1},
        },
    )


@pytest.fixture
def image_collect_record_serialized(image_collect_record):
    return CollectRecordSerializer(instance=image_collect_record).data


@pytest.fixture
def image_file():
    return File(open("api/tests/data/test_image.jpg", "rb"), name="test_image.jpg")


@pytest.fixture
def image1(image_collect_record, image_file):
    return Image.objects.create(collect_record_id=image_collect_record.pk, image=image_file)


@pytest.fixture
def image2(image_collect_record, image_file):
    return Image.objects.create(collect_record_id=image_collect_record.pk, image=image_file)


@pytest.fixture
def points(image1, image2):
    return [
        Point.objects.create(row=1, column=1, image=image1),
        Point.objects.create(row=5, column=5, image=image1),
        Point.objects.create(row=1, column=1, image=image2),
        Point.objects.create(row=5, column=5, image=image2),
    ]


@pytest.fixture
def annotations(
    classifier,
    points,
    benthic_attribute_1,
    benthic_attribute_2,
    benthic_attribute_3,
    benthic_attribute_4,
):
    return [
        Annotation.objects.create(
            point=points[0],
            benthic_attribute=benthic_attribute_1,
            classifier=classifier,
            score=0.8,
            is_confirmed=True,
            is_machine_created=True,
        ),
        Annotation.objects.create(
            point=points[1],
            benthic_attribute=benthic_attribute_2,
            classifier=classifier,
            score=0.7,
            is_confirmed=True,
            is_machine_created=True,
        ),
        Annotation.objects.create(
            point=points[2],
            benthic_attribute=benthic_attribute_3,
            classifier=classifier,
            score=0.9,
            is_confirmed=True,
            is_machine_created=True,
        ),
        Annotation.objects.create(
            point=points[3],
            benthic_attribute=benthic_attribute_4,
            classifier=classifier,
            score=0.56,
            is_confirmed=False,
            is_machine_created=True,
        ),
    ]


def test_image_count_validator(image_collect_record_serialized, annotations, image1, image2):
    # Invalid
    validator = ImageCountValidator(num_quadrats_path="data.quadrat_transect.num_quadrats")
    result = validator(image_collect_record_serialized)
    assert result.status == WARN
    assert result.code == ImageCountValidator.DIFFERENT_NUMBER_OF_IMAGES

    # Valid
    image_collect_record_serialized["data"]["quadrat_transect"]["num_quadrats"] = 2
    result = validator(image_collect_record_serialized)
    assert result.status == OK
    assert result.code is None
