import pytest
from django.urls import reverse
from rest_framework import status


@pytest.fixture
def obs_benthic_pit1_benthic_category_avgs(
    obs_benthic_pit1_1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    obs_benthic_pit1_4,
    obs_benthic_pit1_5,
    obs_benthic_pit1_2_1,
    obs_benthic_pit1_2_2,
    obs_benthic_pit1_2_3,
    obs_benthic_pit1_2_4,
    obs_benthic_pit1_2_5,
):
    obs = [
        obs_benthic_pit1_1,
        obs_benthic_pit1_2,
        obs_benthic_pit1_3,
        obs_benthic_pit1_4,
        obs_benthic_pit1_5,
        obs_benthic_pit1_2_1,
        obs_benthic_pit1_2_2,
        obs_benthic_pit1_2_3,
        obs_benthic_pit1_2_4,
        obs_benthic_pit1_2_5,
    ]
    avgs = {}
    for ob in obs:
        key = ob.attribute.origin.name
        if key not in avgs:
            avgs[key] = 0

        avgs[key] += 1

    for key in avgs:
        avgs[key] = float(avgs[key]) / len(obs) * 100.0

    return avgs


def test_summary_sample_event(
    db_setup,
    api_client1,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_benthic_category_avgs,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("summarysampleevent-list")

    request = api_client1.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 2

    assert "beltfish" in response_data["results"][0]["protocols"]
    assert "benthicpit" in response_data["results"][0]["protocols"]

    beltfish = response_data["results"][0]["protocols"]["beltfish"]
    benthicpit = response_data["results"][0]["protocols"]["benthicpit"]

    assert beltfish["sample_unit_count"] == 1
    assert benthicpit["sample_unit_count"] == 2

    biomass = obs_belt_fish1_1_biomass + obs_belt_fish1_2_biomass + obs_belt_fish1_3_biomass
    assert pytest.approx(biomass, 0.1) == beltfish["biomass_kgha_avg"]

    origin = obs_benthic_pit1_3.attribute.origin.name
    assert (
        benthicpit["percent_cover_benthic_category_avg"][origin]
        == obs_benthic_pit1_benthic_category_avgs[origin]
    )


def test_summary_sample_event_fields_param_invalid(api_client_public):
    # percent_cover_benthic_category_avg is nested inside protocols JSON, not a
    # top-level field on SummarySampleEventModel, so it should be rejected with 400.
    url = reverse("summarysampleevent-list")
    response = api_client_public.get(
        url,
        {"fields": "latitude,longitude,percent_cover_benthic_category_avg"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "percent_cover_benthic_category_avg" in response.json()["fields"]


def test_summary_sample_event_fields_param_valid(api_client_public):
    # Valid top-level fields should return 200 (even with empty results).
    url = reverse("summarysampleevent-list")
    response = api_client_public.get(
        url,
        {"fields": "latitude,longitude,sample_date,data_policy_benthicpit"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.json()
