import logging

import pytest
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from api.resources.base import PointFieldValidated


@pytest.mark.parametrize(
    "value",
    [
        "not a point",
        [10, -20],
        {"type": "Pointy", "coordinates": [10, -20]},
        {"type": "Polygon", "coordinates": [10, -20]},
        {"type": "LineString", "coordinates": [10, -20]},
        {"type": "MultiPoint", "coordinates": [10, -20]},
        {"type": "GeometryCollection", "coordinates": [10, -20]},
        {"type": "Feature", "coordinates": [10, -20]},
        {"type": None, "coordinates": [10, -20]},
        {"coordinates": [10, -20]},
        {"type": "Point", "coordinates": "x"},
        {"type": "Point", "coordinates": ["a", -20]},
        {"type": "Point", "coordinates": [True, False]},
        {"type": "Point", "coordinates": [10, True]},
        {"type": "Point", "coordinates": 5},
        {"type": "Point", "coordinates": {"a": 1, "b": 2}},
    ],
)
def test_invalid_point_rejected_without_gdal_errors(value, caplog):
    with caplog.at_level(logging.DEBUG, logger="django.contrib.gis"):
        with pytest.raises(ValidationError):
            PointFieldValidated().to_internal_value(value)
    assert not [r for r in caplog.records if r.name.startswith("django.contrib.gis")]


@pytest.mark.parametrize("geom_type", ["Point", "point"])
def test_valid_point_accepted(geom_type):
    point = PointFieldValidated().to_internal_value({"type": geom_type, "coordinates": [10.5, -20]})
    assert (point.x, point.y) == (10.5, -20)


def test_site_post_with_non_point_type_returns_400(
    api_client1, project1, country1, reef_type1, reef_zone1, reef_exposure1, caplog
):
    url = reverse("psite-list", kwargs=dict(project_pk=project1.pk))
    payload = {
        "name": "Bad point site",
        "project": str(project1.pk),
        "country": str(country1.pk),
        "reef_type": str(reef_type1.pk),
        "reef_zone": str(reef_zone1.pk),
        "exposure": str(reef_exposure1.pk),
        "location": {"type": "Polygon", "coordinates": [10, -20]},
    }
    with caplog.at_level(logging.DEBUG, logger="django.contrib.gis"):
        resp = api_client1.post(url, payload, format="json")

    assert resp.status_code == 400
    assert "location" in resp.json()
    assert not [r for r in caplog.records if r.name.startswith("django.contrib.gis")]
