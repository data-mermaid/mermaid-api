from datetime import timedelta

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Classifier


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def pinned_classifier():
    # Backdated so recency alone would point `Classifier.latest()` at
    # `newer_classifier` instead - the two rows must stay distinguishable
    # by pin, not by creation order.
    classifier = Classifier.objects.create(
        name="pinned", version="v1", config={"patch_size": 224}
    )
    Classifier.objects.filter(pk=classifier.pk).update(
        created_on=timezone.now() - timedelta(days=1)
    )
    classifier.refresh_from_db()
    return classifier


@pytest.fixture
def newer_classifier():
    return Classifier.objects.create(name="newer", version="v2", config={"patch_size": 224})


@override_settings(INFERENCE_CLASSIFIER_VERSION="v1")
def test_is_default_reflects_pinned_version_not_latest(
    api_client, pinned_classifier, newer_classifier
):
    response = api_client.get(reverse("classifier-list"))
    assert response.status_code == 200

    is_default_by_version = {row["version"]: row["is_default"] for row in response.json()["results"]}
    assert is_default_by_version == {"v1": True, "v2": False}


def test_version_query_param_returns_only_matching_row(
    api_client, pinned_classifier, newer_classifier
):
    response = api_client.get(reverse("classifier-list"), {"version": "v2"})
    assert response.status_code == 200

    results = response.json()["results"]
    assert [row["version"] for row in results] == ["v2"]
