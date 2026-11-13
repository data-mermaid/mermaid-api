import pytest
from django.urls import reverse
from rest_framework import status

from api.models import BLEACHING_STATUS_NORMAL, BLEACHING_STATUS_PALE, Project
from api.utils.summary_cache import update_summary_cache as update_cache


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
    fishbelt_transect1,
    benthic_transect1,
    benthic_transect1_2,
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

    # depth_avg/depth_sd are top-level fields aggregated across sample units from
    # every protocol sharing this sample_event_id.
    depths = [
        float(fishbelt_transect1.depth),
        float(benthic_transect1.depth),
        float(benthic_transect1_2.depth),
    ]
    expected_avg = sum(depths) / len(depths)
    expected_sd = (sum((d - expected_avg) ** 2 for d in depths) / (len(depths) - 1)) ** 0.5
    assert pytest.approx(expected_avg, 0.01) == float(response_data["results"][0]["depth_avg"])
    assert pytest.approx(expected_sd, 0.01) == float(response_data["results"][0]["depth_sd"])


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


def _summary_benthicpit(api_client):
    for project in Project.objects.all():
        update_cache(project.pk, skip_test_project=False, skip_cached_files=True)

    url = reverse("summarysampleevent-list")
    response_data = api_client.get(url, None, format="json").json()
    return next(
        r["protocols"]["benthicpit"]
        for r in response_data["results"]
        if "benthicpit" in r["protocols"]
    )


def test_summary_sample_event_benthicpit_bleaching(
    db_setup,
    api_client1,
    benthic_pit_project,
    benthic_pit1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    obs_benthic_pit1_4,
):
    benthic_pit1.include_bleaching = True
    benthic_pit1.save()
    # Hard coral obs: one pale, one normal, one not assessed (excluded from the denominator)
    obs_benthic_pit1_2.bleaching_status = BLEACHING_STATUS_PALE
    obs_benthic_pit1_2.save()
    obs_benthic_pit1_3.bleaching_status = BLEACHING_STATUS_NORMAL
    obs_benthic_pit1_3.save()

    benthicpit = _summary_benthicpit(api_client1)

    assert benthicpit["bleaching_sample_unit_count"] == 1
    assert benthicpit["bleaching_hard_coral_sample_unit_count"] == 1
    assert benthicpit["bleaching_soft_coral_sample_unit_count"] == 0
    assert benthicpit["bleaching_hard_coral_points"] == 2
    hard = benthicpit["percent_bleached_hard_coral"]
    assert hard["pale"] == 50.0
    assert hard["normal"] == 50.0
    assert hard["fully bleached"] == 0.0
    # SE objects have no combined `bleached` key, and total coral is not reported
    assert "bleached" not in hard
    assert "percent_bleached_total_coral" not in benthicpit
    # No soft coral with a status: null (stripped), not 0
    assert "bleaching_soft_coral_points" not in benthicpit
    assert "percent_bleached_soft_coral" not in benthicpit


def test_summary_sample_event_benthicpit_bleaching_no_statuses(
    db_setup,
    api_client1,
    benthic_pit_project,
    benthic_pit1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    obs_benthic_pit1_4,
):
    # Bleaching was assessed but every coral status left blank: the SU still counts
    benthic_pit1.include_bleaching = True
    benthic_pit1.save()

    benthicpit = _summary_benthicpit(api_client1)

    assert benthicpit["bleaching_sample_unit_count"] == 1
    assert benthicpit["bleaching_hard_coral_sample_unit_count"] == 0
    assert "bleaching_hard_coral_points" not in benthicpit
    assert "percent_bleached_hard_coral" not in benthicpit


def test_summary_sample_event_benthicpit_bleaching_pooled(
    db_setup,
    api_client1,
    benthic_pit_project,
    benthic_pit1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
    benthic_pit1_2,
    obs_benthic_pit1_2_3,
    obs_benthic_pit1_2_4,
):
    # SU1: 1 hard coral point with a status (pale) -> 100% pale.
    # SU2: 2 hard coral points, both normal -> 100% normal.
    # Pooled: 1 of 3 points pale. A mean of SU %s would give 50%.
    for benthic_pit in (benthic_pit1, benthic_pit1_2):
        benthic_pit.include_bleaching = True
        benthic_pit.save()
    obs_benthic_pit1_2.bleaching_status = BLEACHING_STATUS_PALE
    obs_benthic_pit1_2.save()
    for obs in (obs_benthic_pit1_2_3, obs_benthic_pit1_2_4):
        obs.bleaching_status = BLEACHING_STATUS_NORMAL
        obs.save()

    benthicpit = _summary_benthicpit(api_client1)

    assert benthicpit["bleaching_sample_unit_count"] == 2
    assert benthicpit["bleaching_hard_coral_sample_unit_count"] == 2
    assert benthicpit["bleaching_hard_coral_points"] == 3
    assert benthicpit["percent_bleached_hard_coral"]["pale"] == 33.33
    assert benthicpit["percent_bleached_hard_coral"]["normal"] == 66.67
    assert "percent_bleached_hard_coral_sd" not in benthicpit


def test_summary_sample_event_benthicpit_bleaching_private(
    db_setup,
    api_client1,
    project1,
    benthic_pit_project,
    benthic_pit1,
    obs_benthic_pit1_2,
    obs_benthic_pit1_3,
):
    # Private data policy: only sample_unit_count is shown, as with other protocols
    project1.data_policy_benthicpit = Project.PRIVATE
    project1.save()
    benthic_pit1.include_bleaching = True
    benthic_pit1.save()
    obs_benthic_pit1_2.bleaching_status = BLEACHING_STATUS_PALE
    obs_benthic_pit1_2.save()
    obs_benthic_pit1_3.bleaching_status = BLEACHING_STATUS_NORMAL
    obs_benthic_pit1_3.save()

    benthicpit = _summary_benthicpit(api_client1)

    assert benthicpit["sample_unit_count"] >= 1
    for field in (
        "bleaching_sample_unit_count",
        "bleaching_hard_coral_sample_unit_count",
        "bleaching_soft_coral_sample_unit_count",
        "bleaching_hard_coral_points",
        "bleaching_soft_coral_points",
        "percent_bleached_hard_coral",
        "percent_bleached_soft_coral",
    ):
        assert field not in benthicpit
