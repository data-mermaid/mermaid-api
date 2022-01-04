import pytest
from django.urls import reverse

from api.models import Project
from tools.management.commands.update_summary_sample_events import (
    Command as UpdateSampleEvents,
)


@pytest.fixture
def update_summary_sample_events():
    for project in Project.objects.all():
        UpdateSampleEvents().update_project_summary_sample_event(project.pk)


@pytest.fixture
def obs_benthic_pit1_benthic_category_avgs(
    obs_benthic_pit1_1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    obs_benthic_pit1_4,
    obs_benthic_pit1_5,
):
    obs = [
        obs_benthic_pit1_1,
        obs_benthic_pit1_2,
        obs_benthic_pit1_3,
        obs_benthic_pit1_4,
        obs_benthic_pit1_5,
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
    update_summary_sample_events,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_benthic_category_avgs,
    obs_benthic_pit1_3,
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
    assert benthicpit["sample_unit_count"] == 1

    biomass = (
        obs_belt_fish1_1_biomass + obs_belt_fish1_2_biomass + obs_belt_fish1_3_biomass
    )
    assert pytest.approx(biomass, 0.1) == beltfish["biomass_kgha_avg"]

    origin = obs_benthic_pit1_3.attribute.origin.name
    assert benthicpit["percent_cover_by_benthic_category_avg"][origin] == obs_benthic_pit1_benthic_category_avgs[origin]
