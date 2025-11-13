import copy

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from api.models import Annotation, Classifier, Image, Point


@pytest.fixture
def classifier():
    return Classifier.objects.create(name="Test classifier", version="v0", patch_size=144)


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
def point(image):
    return Point.objects.create(
        image=image,
        row=0,
        column=0,
    )


@pytest.fixture
def annotations(classifier, point, benthic_attribute_1, benthic_attribute_2, benthic_attribute_3):
    return [
        Annotation.objects.create(
            classifier=classifier,
            point=point,
            benthic_attribute=benthic_attribute_1,
            growth_form=None,
            score=4,
            is_confirmed=False,
            is_machine_created=True,
        ),
        Annotation.objects.create(
            classifier=classifier,
            point=point,
            benthic_attribute=benthic_attribute_2,
            growth_form=None,
            score=80,
            is_confirmed=True,
            is_machine_created=True,
        ),
        Annotation.objects.create(
            classifier=classifier,
            point=point,
            benthic_attribute=benthic_attribute_3,
            growth_form=None,
            score=1,
            is_confirmed=False,
            is_machine_created=True,
        ),
    ]


def test_create_user_defined_annotation(
    db_setup,
    api_client1,
    project1,
    image,
    point,
    annotations,
    benthic_attribute_4,
    growth_form1,
):
    url_kwargs = {
        "project_pk": str(project1.pk),
        "pk": str(image.pk),
    }
    url = reverse("image-detail", kwargs=url_kwargs)
    request = api_client1.get(url, format="json")
    assert request.status_code == 200

    data = request.json()

    bad_data = copy.deepcopy(data)
    bad_data["points"][0]["annotations"].append(
        {
            "point": str(point.pk),
            "benthic_attribute": str(benthic_attribute_4.pk),
            "growth_form": None,
            "classifier": None,
            "is_confirmed": True,
        }
    )

    # Test two annotations with is_confirmed
    request = api_client1.patch(url, bad_data, format="json")
    assert request.status_code == 400

    good_data = copy.deepcopy(bad_data)

    # Only have one is_confirmed
    for annotation in good_data["points"][0]["annotations"]:
        annotation["is_confirmed"] = False

    good_data["points"][0]["annotations"][-1]["is_confirmed"] = True

    request = api_client1.patch(url, data, format="json")
    assert request.status_code == 200


def test_two_user_defined_annotation(
    db_setup,
    api_client1,
    project1,
    image,
    point,
    annotations,
    benthic_attribute_4,
    growth_form1,
):
    url_kwargs = {
        "project_pk": str(project1.pk),
        "pk": str(image.pk),
    }
    url = reverse("image-detail", kwargs=url_kwargs)
    request = api_client1.get(url, format="json")
    assert request.status_code == 200

    data = request.json()

    data["points"][0]["annotations"].append(
        {
            "point": str(point.pk),
            "benthic_attribute": str(benthic_attribute_4.pk),
            "growth_form": str(growth_form1.pk),
            "classifier": None,
            "is_confirmed": False,
        }
    )

    data["points"][0]["annotations"].append(
        {
            "point": str(point.pk),
            "benthic_attribute": str(benthic_attribute_4.pk),
            "growth_form": None,
            "classifier": None,
            "is_confirmed": True,
        }
    )

    request = api_client1.patch(url, data, format="json")
    data = request.json()

    assert request.status_code == 400


def test_edit_machine_annotation(
    db_setup,
    api_client1,
    project1,
    image,
    point,
    annotations,
    benthic_attribute_4,
):
    url_kwargs = {
        "project_pk": str(project1.pk),
        "pk": str(image.pk),
    }
    url = reverse("image-detail", kwargs=url_kwargs)
    request = api_client1.get(url, format="json")
    assert request.status_code == 200

    data = request.json()

    # Remove classifier
    bad_data = copy.deepcopy(data)
    bad_data["points"][0]["annotations"][0]["classifier"] = None
    request = api_client1.patch(url, bad_data, format="json")
    updated_data = request.json()

    assert request.status_code == 200
    assert updated_data["points"][0]["annotations"][0]["classifier"] is not None

    # No annotation id
    bad_data = copy.deepcopy(data)
    bad_data["points"][0]["annotations"][0]["id"] = None
    request = api_client1.patch(url, bad_data, format="json")
    updated_data = request.json()

    assert request.status_code == 400

    # Remove Point - Should be ignored because it uses parent point
    bad_data = copy.deepcopy(data)
    bad_data["points"][0]["annotations"][0]["point"] = None
    request = api_client1.patch(url, bad_data, format="json")
    updated_data = request.json()

    assert request.status_code == 200

    # Edit score - Should be ignored because it uses parent point
    bad_data = copy.deepcopy(data)
    bad_data["points"][0]["annotations"][0]["score"] = 0
    request = api_client1.patch(url, bad_data, format="json")
    updated_data = request.json()

    assert request.status_code == 200
    assert (
        updated_data["points"][0]["annotations"][0]["score"]
        == data["points"][0]["annotations"][0]["score"]
    )

    # Multiple is_confirmed
    bad_data = copy.deepcopy(data)
    bad_data["points"][0]["annotations"][0]["is_confirmed"] = True
    bad_data["points"][0]["annotations"][1]["is_confirmed"] = True
    request = api_client1.patch(url, bad_data, format="json")
    updated_data = request.json()

    assert request.status_code == 400

    # Change is_confirmed
    good_data = copy.deepcopy(data)
    anno_id_1 = good_data["points"][0]["annotations"][0]["id"]
    anno_id_2 = good_data["points"][0]["annotations"][1]["id"]
    good_data["points"][0]["annotations"][0]["is_confirmed"] = True
    good_data["points"][0]["annotations"][1]["is_confirmed"] = False
    request = api_client1.patch(url, good_data, format="json")
    updated_data = request.json()

    assert request.status_code == 200
    for anno in updated_data["points"][0]["annotations"]:
        if anno_id_1 == anno["id"]:
            assert anno["is_confirmed"] is True
        elif anno_id_2 == anno["id"]:
            assert anno["is_confirmed"] is False
