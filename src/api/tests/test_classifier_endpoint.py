import pytest
from django.test import override_settings
from django.urls import reverse

from api.models import Classifier


@pytest.fixture
def classifiers():
    return [
        Classifier.objects.create(name="a", version="v1", config={"patch_size": 224}),
        Classifier.objects.create(name="b", version="v2", config={"patch_size": 224}),
    ]


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_filter_by_version(client, classifiers):
    url = reverse("classifier-list")
    resp = client.get(url, {"version": "v2"})
    assert resp.status_code == 200
    results = resp.json()["results"] if isinstance(resp.json(), dict) else resp.json()
    versions = [c["version"] for c in results]
    assert versions == ["v2"]


@override_settings(INFERENCE_CLASSIFIER_VERSION="v2")
def test_is_default_flag_matches_setting(client, classifiers):
    url = reverse("classifier-list")
    resp = client.get(url)
    results = resp.json()["results"] if isinstance(resp.json(), dict) else resp.json()
    by_version = {c["version"]: c["is_default"] for c in results}
    assert by_version["v2"] is True
    assert by_version["v1"] is False
