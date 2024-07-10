import json

import pytest
from django.urls import reverse


@pytest.fixture
def geojson_geometry():
    return {
        "coordinates": [
            [
                [30.563324839986507, 5.537690894889451],
                [31.99304270085645, 5.517440085031026],
                [31.290101817207784, 7.114308805357695],
                [30.563324839986507, 5.537690894889451],
            ]
        ],
        "type": "Polygon",
    }


@pytest.fixture
def geojson_feature_collection(geojson_geometry):
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": geojson_geometry}],
    }


def test_geometry_field_patch(
    db_setup,
    api_client_public,
    geojson_geometry,
    geojson_feature_collection,
):
    url = reverse("summarysampleevent-list")

    params = {"site_within": {"a": 1}}

    request = api_client_public.get(url, params, format="json")
    assert request.status_code == 400

    params = {"site_within": json.dumps(geojson_feature_collection)}

    request = api_client_public.get(url, params, format="json")
    assert request.status_code == 400

    params = {"site_within": 123}

    request = api_client_public.get(url, params, format="json")
    assert request.status_code == 400

    params = {"site_within": json.dumps(geojson_geometry)}

    request = api_client_public.get(url, params, format="json")
    assert request.status_code == 200
