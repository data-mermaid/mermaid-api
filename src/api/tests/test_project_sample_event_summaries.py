import pytest
from django.urls import reverse


def test_project_se_summary_public(
    db_setup,
    api_client_public,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("projectsummarysampleevent-list")

    request = api_client_public.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 1

    results = response_data["results"]
    record = results[0]["records"][0]

    assert "beltfish" in record["protocols"]
    assert "benthicpit" in record["protocols"]

    beltfish = record["protocols"]["beltfish"]
    benthicpit = record["protocols"]["benthicpit"]

    assert beltfish["sample_unit_count"] == 1
    assert benthicpit["sample_unit_count"] == 2

    assert "biomass_kgha_avg" not in beltfish
    assert "percent_cover_benthic_category_avg" not in benthicpit


def test_project_se_summary_authenticated(
    db_setup,
    api_client1,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("projectsummarysampleevent-list")

    request = api_client1.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 1

    results = response_data["results"]
    records = results[0]["records"]

    assert len(records) == 2

    record = results[0]["records"][0]

    assert "beltfish" in record["protocols"]
    assert "benthicpit" in record["protocols"]

    beltfish = record["protocols"]["beltfish"]
    benthicpit = record["protocols"]["benthicpit"]

    assert beltfish["sample_unit_count"] == 1
    assert benthicpit["sample_unit_count"] == 2

    biomass = obs_belt_fish1_1_biomass + obs_belt_fish1_2_biomass + obs_belt_fish1_3_biomass
    assert pytest.approx(biomass, 0.1) == beltfish["biomass_kgha_avg"]


def test_project_se_summary_authenticated_not_project(
    db_setup,
    api_client3,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("projectsummarysampleevent-list")

    request = api_client3.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 1

    results = response_data["results"]
    records = results[0]["records"]

    assert len(records) == 2

    record = results[0]["records"][0]

    assert "beltfish" in record["protocols"]
    assert "benthicpit" in record["protocols"]

    beltfish = record["protocols"]["beltfish"]
    benthicpit = record["protocols"]["benthicpit"]

    assert beltfish["sample_unit_count"] == 1
    assert benthicpit["sample_unit_count"] == 2

    assert "biomass_kgha_avg" not in beltfish
    assert "percent_cover_benthic_category_avg" not in benthicpit
