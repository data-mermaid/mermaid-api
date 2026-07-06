def test_fish_species_notes(db_setup, api_client1, fish_species1):
    """GET /v1/fishspecies/{id}/ includes the notes field."""
    response = api_client1.get(f"/v1/fishspecies/{fish_species1.pk}/", format="json")
    assert response.status_code == 200
    assert response.json()["notes"] == fish_species1.notes


def test_fish_grouping_empty_attributes_returns_zero_aggs(
    db_setup, all_test_fish_attributes, region1, region2
):
    from api.models import FishGrouping

    grouping = FishGrouping.objects.create(name="Empty Grouping")
    grouping.regions.add(region1, region2)

    aggs = grouping._get_attribute_aggs()

    assert aggs["biomass_constant_a"] == 0
    assert aggs["biomass_constant_b"] == 0
    assert aggs["biomass_constant_c"] == 0
    assert aggs["max_length"] is None


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
