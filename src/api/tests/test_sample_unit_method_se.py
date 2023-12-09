import pytest
from django.urls import reverse


def _call(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    data = response.json()
    return data["count"], data["results"], response


def test_beltfish_se_view(
    client,
    db_setup,
    project1,
    token1,
    belt_fish_project,
    sample_event1,
    sample_event2,
    all_choices,
    site2,
    management2,
    profile2,
    obs_belt_fish1_1_biomass,
    obs_belt_fish1_2_biomass,
    obs_belt_fish1_3_biomass,
    obs_belt_fish2_1_biomass,
    obs_belt_fish2_2_biomass,
    obs_belt_fish2_3_biomass,
    obs_belt_fish2_4_biomass,
    update_summary_cache,
):
    url = reverse(
        "beltfishmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, _ = _call(client, token1, url)

    biomass_kgha_1 = sum(
        [obs_belt_fish1_1_biomass, obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass]
    )

    assert count == 2
    n = 0
    for record in data:
        if record["id"] == str(sample_event1.pk):
            assert record["sample_unit_count"] == 1
            assert record["depth_avg"] == 8.0
            assert record["biomass_kgha_avg"] == pytest.approx(biomass_kgha_1, 0.1)
            assert record["biomass_kgha_trophic_group_avg"]["omnivore"] == pytest.approx(obs_belt_fish1_1_biomass, 0.1)

            fish_family_biomass_avg_0 = record["biomass_kgha_fish_family_avg"]
            assert fish_family_biomass_avg_0["Fish Family 1"] == pytest.approx(obs_belt_fish1_1_biomass, 0.1)
            assert fish_family_biomass_avg_0["Fish Family 2"] == pytest.approx(obs_belt_fish1_2_biomass, 0.1)
            assert fish_family_biomass_avg_0["Fish Family 3"] == pytest.approx(obs_belt_fish1_3_biomass, 0.1)

            fish_family_biomass_avg_1 = data[1]["biomass_kgha_fish_family_avg"]
            fish_family_2_biomass = sum([obs_belt_fish2_1_biomass, obs_belt_fish2_4_biomass])
            assert fish_family_biomass_avg_1["Fish Family 1"] == pytest.approx(obs_belt_fish2_3_biomass, 0.1)
            assert fish_family_biomass_avg_1["Fish Family 2"] == pytest.approx(fish_family_2_biomass, 0.1)
            assert fish_family_biomass_avg_1["Fish Family 3"] == pytest.approx(obs_belt_fish2_2_biomass, 0.1)
            n += 1
        elif record["id"] == str(sample_event2.pk):
            n += 1
    
    if n != count:
        assert False, f"Wrong number of sample events, {n} should be {count}"
            

def test_benthicpit_se_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_pit_project,
    sample_event1,
    sample_event2,
    all_choices,
    site2,
    management2,
    profile2,
    update_summary_cache,
):
    url = reverse(
        "benthicpitmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, _ = _call(client, token1, url)

    assert count == 2
    n = 0
    for record in data:
        if record["id"] == str(sample_event1.pk):
            assert record["sample_unit_count"] == 2
            assert record["depth_avg"] == 6.5
            assert record["depth_sd"] == 2.12
            assert record["percent_cover_benthic_category_avg"]["Macroalgae"] == 40.0
            assert record["percent_cover_benthic_category_sd"]["Macroalgae"] == 28.28
            assert record["percent_cover_benthic_category_avg"]["Hard coral"] == 50.0
            assert record["percent_cover_benthic_category_sd"]["Hard coral"] == 14.14
            assert record["percent_cover_benthic_category_avg"]["Rock"] == 10.0
            assert record["percent_cover_benthic_category_sd"]["Rock"] == 14.14
            n += 1
        elif record["id"] == str(sample_event2.pk):
            assert record["percent_cover_benthic_category_avg"]["Hard coral"] == 60.0
            assert record["percent_cover_benthic_category_avg"]["Rock"] == 40.0
            n += 1
    
    if n != count:
        assert False, f"Wrong number of sample events, {n} should be {count}"


def test_benthiclit_se_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_lit_project,
    sample_event1,
    sample_event2,
    all_choices,
    site2,
    management2,
    profile2,
    update_summary_cache,
):
    url = reverse(
        "benthiclitmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, _ = _call(client, token1, url)

    assert count == 2
    n = 0
    for record in data:
        if record["id"] == str(sample_event1.pk):
            assert record["percent_cover_benthic_category_avg"]["Macroalgae"] == 16.92
            assert record["percent_cover_benthic_category_avg"]["Hard coral"] == 60.0
            assert record["percent_cover_benthic_category_avg"]["Rock"] == 23.08
            n += 1
        elif record["id"] == str(sample_event2.pk):
            assert record["percent_cover_benthic_category_avg"]["Hard coral"] == 58.46
            assert record["percent_cover_benthic_category_avg"]["Rock"] == 41.54
            n += 1
    
    if n != count:
        assert False, f"Wrong number of sample events, {n} should be {count}"


def test_habitatcomplexity_se_view(
    client,
    db_setup,
    project1,
    token1,
    habitat_complexity_project,
    sample_event1,
    sample_event2,
    all_choices,
    site1,
    update_summary_cache,
):
    url = reverse(
        "habitatcomplexitymethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, _ = _call(client, token1, url)

    assert count == 2
    n = 0
    for record in data:
        if record["id"] == str(sample_event1.pk):
            assert record["score_avg_avg"] == 2.0
            n += 1
        elif record["id"] == str(sample_event2.pk):
            n += 1
    
    if n != count:
        assert False, f"Wrong number of sample events, {n} should be {count}"


def test_bleachingqc_se_view(
    client,
    db_setup,
    project1,
    token1,
    bleaching_project,
    sample_event1,
    all_choices,
    site1,
    update_summary_cache,
):
    url = reverse(
        "bleachingqcsmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, _ = _call(client, token1, url)

    assert count == 1
    n = 0
    for record in data:
        if record["id"] == str(sample_event1.pk):
            assert record["count_total_avg"] == 500
            assert record["count_genera_avg"] == 4
            assert record["percent_normal_avg"] == 5.0
            assert record["percent_pale_avg"] == 24.0
            assert record["percent_bleached_avg"] == 71.0
            assert record["quadrat_count_avg"] == 5
            assert record["percent_hard_avg_avg"] == 59.0
            assert record["percent_soft_avg_avg"] == 19.6
            assert record["percent_algae_avg_avg"] == 20.4
            n += 1
    
    if n != count:
        assert False, f"Wrong number of sample events, {n} should be {count}"
