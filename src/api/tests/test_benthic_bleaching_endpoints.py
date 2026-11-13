import pytest
from django.urls import reverse

from api.models import (
    BLEACHING_CATEGORY_HARD_CORAL,
    BLEACHING_STATUS_NORMAL,
    BLEACHING_STATUS_PALE,
    BenthicPITSUModel,
    Project,
)
from api.utils.summary_cache import update_summary_cache as update_cache


@pytest.fixture
def pit_bleaching(
    benthic_pit_project,
    benthic_pit1,
    benthic_pit1_2,
    obs_benthic_pit1_2,
    obs_benthic_pit1_2_3,
    obs_benthic_pit1_2_4,
):
    # SU1 (benthic_pit1): 1 hard coral point with a status (pale); its other hard coral has none.
    # SU2 (benthic_pit1_2): 2 hard coral points, both normal.
    for benthic_pit in (benthic_pit1, benthic_pit1_2):
        benthic_pit.include_bleaching = True
        benthic_pit.save()
    obs_benthic_pit1_2.bleaching_status = BLEACHING_STATUS_PALE
    obs_benthic_pit1_2.save()
    for obs in (obs_benthic_pit1_2_3, obs_benthic_pit1_2_4):
        obs.bleaching_status = BLEACHING_STATUS_NORMAL
        obs.save()
    for project in Project.objects.all():
        update_cache(project.pk, skip_test_project=False, skip_cached_files=True)
    return benthic_pit1.transect.sample_event


def _results(api_client, name, sample_event, params=None):
    url = reverse(name, kwargs=dict(project_pk=sample_event.site.project_id))
    response = api_client.get(url, params, format="json")
    assert response.status_code == 200
    return [r for r in response.json()["results"] if r["sample_event_id"] == str(sample_event.pk)]


def test_benthicpit_obs_bleaching_status(db_setup, api_client1, pit_bleaching, obs_benthic_pit1_2):
    records = _results(api_client1, "benthicpitmethod-obs-list", pit_bleaching)
    pale = next(r for r in records if r["id"] == str(obs_benthic_pit1_2.pk))

    assert pale["bleaching_status"] == BLEACHING_STATUS_PALE
    assert pale["bleaching_status_name"] == "pale"

    filtered = _results(
        api_client1,
        "benthicpitmethod-obs-list",
        pit_bleaching,
        {"bleaching_status": f"{BLEACHING_STATUS_PALE}"},
    )
    assert [r["id"] for r in filtered] == [str(obs_benthic_pit1_2.pk)]


def test_benthicpit_su_bleaching(
    db_setup, api_client1, pit_bleaching, benthic_pit1, benthic_pit1_2
):
    records = _results(api_client1, "benthicpitmethod-sampleunit-list", pit_bleaching)
    su1 = next(r for r in records if str(benthic_pit1.transect_id) in r["sample_unit_ids"])
    su2 = next(r for r in records if str(benthic_pit1_2.transect_id) in r["sample_unit_ids"])

    assert su1["bleaching_hard_coral_points"] == 1
    assert su1["percent_bleached_hard_coral"]["pale"] == 100.0
    assert su1["percent_bleached_hard_coral"]["bleached"] == 100.0
    assert su1["bleaching_soft_coral_points"] is None
    assert su1["percent_bleached_soft_coral"] is None
    assert "percent_bleached_total_coral" not in su1
    assert su2["bleaching_hard_coral_points"] == 2
    assert su2["percent_bleached_hard_coral"]["normal"] == 100.0
    # Raw per-status amounts are stored for SE pooling but not exposed
    assert "bleaching_status_amounts" not in su1


def test_benthicpit_su_bleaching_status_amounts(
    db_setup, api_client1, pit_bleaching, benthic_pit1, benthic_pit1_2
):
    su1 = BenthicPITSUModel.objects.get(sample_unit_ids__contains=[str(benthic_pit1.transect_id)])
    su2 = BenthicPITSUModel.objects.get(sample_unit_ids__contains=[str(benthic_pit1_2.transect_id)])

    hard1 = su1.bleaching_status_amounts[BLEACHING_CATEGORY_HARD_CORAL]
    assert hard1["pale"] == 1
    assert hard1["normal"] == 0
    assert "bleached" not in hard1
    assert su2.bleaching_status_amounts[BLEACHING_CATEGORY_HARD_CORAL]["normal"] == 2

    url = reverse(
        "benthicpitmethod-sampleunit-geojson",
        kwargs=dict(project_pk=pit_bleaching.site.project_id),
    )
    response = api_client1.get(url)
    assert response.status_code == 200
    for feature in response.json()["features"]:
        assert "bleaching_status_amounts" not in feature["properties"]


def test_benthicpit_se_bleaching_pooled(db_setup, api_client1, pit_bleaching):
    (se,) = _results(api_client1, "benthicpitmethod-sampleevent-list", pit_bleaching)

    assert se["bleaching_sample_unit_count"] == 2
    assert se["bleaching_hard_coral_sample_unit_count"] == 2
    assert se["bleaching_soft_coral_sample_unit_count"] == 0
    assert se["bleaching_hard_coral_points"] == 3
    assert se["bleaching_soft_coral_points"] is None
    hard = se["percent_bleached_hard_coral"]
    assert hard["pale"] == 33.33
    assert hard["normal"] == 66.67
    assert "bleached" not in hard
    assert se["percent_bleached_soft_coral"] is None
    assert "percent_bleached_hard_coral_sd" not in se
    assert "percent_bleached_hard_coral_avg" not in se
