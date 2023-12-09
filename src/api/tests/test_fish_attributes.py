def test_filter_fish_species_by_region(
    db_setup, api_client1, all_test_fish_attributes, all_regions, region1, region2, region3
):
    request = api_client1.get("/v1/fishspecies/", {"regions": str(region2.id)}, format="json")
    response_data = request.json()
    assert response_data["count"] == 3

    regions = [
        str(region1.id),
        str(region3.id),
    ]
    request = api_client1.get("/v1/fishspecies/", {"regions": ",".join(regions)}, format="json")
    response_data = request.json()
    assert response_data["count"] == 2


def test_filter_fish_genera_by_region(
    db_setup, api_client1, all_test_fish_attributes, all_regions, region1, region2, region3
):
    request = api_client1.get("/v1/fishgenera/", {"regions": str(region2.id)}, format="json")
    response_data = request.json()
    assert response_data["count"] == 2

    regions = [
        str(region1.id),
        str(region3.id),
    ]
    request = api_client1.get("/v1/fishgenera/", {"regions": ",".join(regions)}, format="json")
    response_data = request.json()
    assert response_data["count"] == 2


def test_filter_fish_families_by_region(
    db_setup, api_client1, all_test_fish_attributes, all_regions, region1, region2, region3
):
    request = api_client1.get("/v1/fishfamilies/", {"regions": str(region2.id)}, format="json")
    response_data = request.json()
    assert response_data["count"] == 2

    regions = [
        str(region1.id),
        str(region3.id),
    ]
    request = api_client1.get("/v1/fishfamilies/", {"regions": ",".join(regions)}, format="json")
    response_data = request.json()
    assert response_data["count"] == 2
