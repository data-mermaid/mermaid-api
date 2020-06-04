import requests
from collections import namedtuple

CORAL_ATLAS_API = "https://integration.allencoralatlas.org/mapping/querypoint"

CoralAtlasDataPoint = namedtuple(
    "CoralAtlasDataPoint", "x y benthic geomorphic reeftype"
)


class CoralAtlasAPIException(Exception):
    pass


def to_geojson_collection(points):
    features = []
    for coords in points:
        features.append(
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Point", "coordinates": coords},
            }
        )

    return {"type": "FeatureCollection", "features": features}


def parse_feature(feature):
    return CoralAtlasDataPoint(
        feature.get("lng"),
        feature.get("lat"),
        feature.get("benthic"),
        feature.get("geomorphic"),
        feature.get("reeftype"),
    )


def get_data_points(points):
    geojson_payload = to_geojson_collection(points)
    resp = requests.post(f"{CORAL_ATLAS_API}?geometries=false", json=geojson_payload)
    status_code = resp.status_code

    if status_code != 200:
        raise CoralAtlasAPIException(resp.text)

    features = (resp.json() or {}).get("data") or []
    return [parse_feature(feature) for feature in features]
