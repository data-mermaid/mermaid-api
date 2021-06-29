from django import urls


def test_filter_benthicattributes_by_region(
    db_setup, api_client1, all_test_benthic_attributes, all_regions, region1, region2, region3
):
    request = api_client1.get(
        "/v1/benthicattributes/",
        {"regions": str(region2.id)},
        format="json"
    )
    response_data = request.json()
    assert response_data["count"] == 5

    regions = [
        str(region1.id),
        str(region3.id),
    ]
    request = api_client1.get(
        "/v1/benthicattributes/",
        {"regions": ",".join(regions)},
        format="json"
    )
    response_data = request.json()
    assert response_data["count"] == 7
