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
    obs_belt_fish2_4_biomass
):
    url = reverse(
        "beltfishmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    biomass_kgha_1 = sum(
        [obs_belt_fish1_1_biomass, obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass]
    )
    biomass_kgha_1_other = sum([obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass])

    assert count == 2
    assert data[0]["sample_unit_count"] == 1
    assert data[0]["depth_avg"] == 8.0
    assert data[0]["biomass_kgha_avg"] == pytest.approx(biomass_kgha_1, 0.1)
    assert data[0]["biomass_kgha_by_trophic_group_avg"]["other"] == pytest.approx(biomass_kgha_1_other, 0.1)
    assert data[0]["biomass_kgha_by_trophic_group_avg"]["omnivore"] == pytest.approx(obs_belt_fish1_1_biomass, 0.1)

    fish_family_biomass_avg_0 = data[0]["biomass_kgha_by_fish_family_avg"]
    assert fish_family_biomass_avg_0["Fish Family 1"] == pytest.approx(obs_belt_fish1_1_biomass, 0.1)
    assert fish_family_biomass_avg_0["Fish Family 2"] == pytest.approx(obs_belt_fish1_2_biomass, 0.1)
    assert fish_family_biomass_avg_0["Fish Family 3"] == pytest.approx(obs_belt_fish1_3_biomass, 0.1)


    fish_family_biomass_avg_1 = data[1]["biomass_kgha_by_fish_family_avg"]
    fish_family_2_biomass = sum([obs_belt_fish2_1_biomass, obs_belt_fish2_4_biomass])
    assert fish_family_biomass_avg_1["Fish Family 1"] == pytest.approx(obs_belt_fish2_3_biomass, 0.1)
    assert fish_family_biomass_avg_1["Fish Family 2"] == pytest.approx(fish_family_2_biomass, 0.1)
    assert fish_family_biomass_avg_1["Fish Family 3"] == pytest.approx(obs_belt_fish2_2_biomass, 0.1)


def test_benthicpit_se_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_pit_project,
    all_choices,
    site2,
    management2,
    profile2,
):
    url = reverse(
        "benthicpitmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[0]["sample_unit_count"] == 1
    assert data[0]["depth_avg"] == 5.0
    assert data[0]["percent_cover_by_benthic_category_avg"]["Macroalgae"] == 20.0
    assert data[0]["percent_cover_by_benthic_category_avg"]["Hard coral"] == 60.0
    assert data[0]["percent_cover_by_benthic_category_avg"]["Rock"] == 20.0

    assert data[1]["percent_cover_by_benthic_category_avg"]["Hard coral"] == 60.0
    assert data[1]["percent_cover_by_benthic_category_avg"]["Rock"] == 40.0


def test_benthiclit_se_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_lit_project,
    all_choices,
    site2,
    management2,
    profile2,
):
    url = reverse(
        "benthiclitmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[0]["percent_cover_by_benthic_category_avg"]["Macroalgae"] == 16.92
    assert data[0]["percent_cover_by_benthic_category_avg"]["Hard coral"] == 60.0
    assert data[0]["percent_cover_by_benthic_category_avg"]["Rock"] == 23.08

    assert data[1]["percent_cover_by_benthic_category_avg"]["Hard coral"] == 58.46
    assert data[1]["percent_cover_by_benthic_category_avg"]["Rock"] == 41.54


def test_habitatcomplexity_se_view(
    client, db_setup, project1, token1, habitat_complexity_project, all_choices, site1,
):
    url = reverse(
        "habitatcomplexitymethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[0]["score_avg_avg"] == 2.0


def test_bleachingqc_se_view(
    client, db_setup, project1, token1, bleaching_project, all_choices, site1,
):
    url = reverse(
        "bleachingqcsmethod-sampleevent-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 1
    assert data[0]["count_total_avg"] == 500
    assert data[0]["count_genera_avg"] == 4
    assert data[0]["percent_normal_avg"] == 5.0
    assert data[0]["percent_pale_avg"] == 24.0
    assert data[0]["percent_bleached_avg"] == 71.0
    assert data[0]["quadrat_count_avg"] == 5
    assert data[0]["percent_hard_avg_avg"] == 59.0
    assert data[0]["percent_soft_avg_avg"] == 19.6
    assert data[0]["percent_algae_avg_avg"] == 20.4
