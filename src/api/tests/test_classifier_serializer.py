from api.models import Classifier
from api.resources.classification.classifier import ClassifierSerializer


def test_serializer_exposes_type_and_config_not_num_points():
    c = Classifier.objects.create(
        name="c", version="v1", classifier_type="pyspacer", config={"patch_size": 224}
    )
    data = ClassifierSerializer(instance=c).data
    assert data["version"] == "v1"
    assert data["classifier_type"] == "pyspacer"
    assert data["config"] == {"patch_size": 224}
    assert "benthic_attribute_growth_forms" in data
    assert "num_points" not in data


def test_serializer_exposes_exact_field_set():
    c = Classifier.objects.create(name="c2", version="v2")
    data = ClassifierSerializer(instance=c).data
    assert set(data.keys()) == {
        "id",
        "name",
        "version",
        "classifier_type",
        "config",
        "description",
        "benthic_attribute_growth_forms",
        "is_default",
        "created_on",
        "updated_on",
    }
