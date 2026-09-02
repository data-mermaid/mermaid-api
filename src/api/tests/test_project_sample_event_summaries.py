import pytest
from django.urls import reverse

from api.models import Project
from api.models.summary_sample_events import (
    RestrictedProjectSummarySampleEvent,
    UnrestrictedProjectSummarySampleEvent,
)
from api.utils.summary_cache import update_summary_cache as _update_summary_cache


@pytest.fixture
def project1_private_policies(project1):
    project1.data_policy_beltfish = Project.PRIVATE
    project1.data_policy_benthicpit = Project.PRIVATE
    project1.save()


def test_project_se_summary_public(
    db_setup,
    project1_private_policies,
    api_client_public,
    sample_event1,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("projectsummarysampleevents-list")

    request = api_client_public.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 1

    results = response_data["results"]
    for record in results[0]["records"]:
        if record["sample_event_id"] == str(sample_event1.pk):
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
    sample_event1,
    sample_event2,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("projectsummarysampleevents-list")

    request = api_client1.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 1

    results = response_data["results"]
    records = results[0]["records"]

    assert len(records) == 2

    sample_event1_record = next(
        (r for r in records if r["sample_event_id"] == str(sample_event1.pk)), None
    )
    assert sample_event1_record is not None

    assert "beltfish" in sample_event1_record["protocols"]
    assert "benthicpit" in sample_event1_record["protocols"]

    beltfish = sample_event1_record["protocols"]["beltfish"]
    benthicpit = sample_event1_record["protocols"]["benthicpit"]

    assert beltfish["sample_unit_count"] == 1
    assert benthicpit["sample_unit_count"] == 2

    biomass = obs_belt_fish1_1_biomass + obs_belt_fish1_2_biomass + obs_belt_fish1_3_biomass
    assert pytest.approx(biomass, 0.1) == beltfish["biomass_kgha_avg"]

    # project-level records reuse SummarySampleEventSerializer, so depth_avg/depth_sd
    # should already be present without any extra wiring. sample_event1's sample units
    # are fishbelt_transect1 (depth=8), benthic_transect1 (depth=5), and
    # benthic_transect1_2 (depth=8) -- avg=7.0, sample stddev=sqrt(6/2)~=1.73.
    assert pytest.approx(7.0, 0.01) == float(sample_event1_record["depth_avg"])
    assert pytest.approx(1.73, 0.01) == float(sample_event1_record["depth_sd"])


def test_project_se_summary_authenticated_not_project(
    db_setup,
    api_client3,
    project1_private_policies,
    sample_event1,
    belt_fish_project,
    benthic_pit_project,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_benthic_pit1_3,
    update_summary_cache,
):
    url = reverse("projectsummarysampleevents-list")

    request = api_client3.get(url, None, format="json")
    response_data = request.json()
    assert response_data["count"] == 1

    results = response_data["results"]
    records = results[0]["records"]

    assert len(records) == 2
    for record in results[0]["records"]:
        if record["sample_event_id"] == str(sample_event1.pk):
            assert "beltfish" in record["protocols"]
            assert "benthicpit" in record["protocols"]

            beltfish = record["protocols"]["beltfish"]
            benthicpit = record["protocols"]["benthicpit"]

            assert beltfish["sample_unit_count"] == 1
            assert benthicpit["sample_unit_count"] == 2

            assert "biomass_kgha_avg" not in beltfish
            assert "percent_cover_benthic_category_avg" not in benthicpit


def test_project_se_summary_cleaned_up_after_project_deleted(db_setup, project1):
    project_id = project1.pk
    RestrictedProjectSummarySampleEvent.objects.create(project_id=project_id, records=[])
    UnrestrictedProjectSummarySampleEvent.objects.create(project_id=project_id, records=[])

    project1.delete()
    _update_summary_cache(project_id, skip_cached_files=True)

    assert not RestrictedProjectSummarySampleEvent.objects.filter(project_id=project_id).exists()
    assert not UnrestrictedProjectSummarySampleEvent.objects.filter(project_id=project_id).exists()
