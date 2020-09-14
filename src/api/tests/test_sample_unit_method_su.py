from django.urls import reverse


def _call(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    data = response.json()
    return data["count"], data["results"], response


def test_beltfish_su_view(
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
):
    url = reverse("beltfishmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[1]["site_name"] == site2.name

    biomass_kgha_1 = sum(
        [obs_belt_fish1_1_biomass, obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass]
    )

    biomass_kgha_1_other = sum([obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass])

    assert round(data[0]["biomass_kgha"], 1) == round(biomass_kgha_1, 1)
    assert round(data[0]["biomass_kgha_by_trophic_group"]["other"], 1) == round(
        biomass_kgha_1_other, 1
    )
    assert round(data[0]["biomass_kgha_by_trophic_group"]["omnivore"], 1) == round(
        obs_belt_fish1_1_biomass, 1
    )

    biomass_kgha_2 = sum(
        [obs_belt_fish2_1_biomass, obs_belt_fish2_2_biomass, obs_belt_fish2_3_biomass]
    )

    transect_2_biomass = round(biomass_kgha_2, 1)
    assert round(data[1]["biomass_kgha"], 1) == transect_2_biomass


def test_benthicpit_su_view(
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
        "benthicpitmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[1]["site_name"] == site2.name

    assert data[0]["percent_cover_by_benthic_category"]["Macroalgae"] == 20.0
    assert data[0]["percent_cover_by_benthic_category"]["Hard coral"] == 60.0
    assert data[0]["percent_cover_by_benthic_category"]["Rock"] == 20.0

    assert data[1]["percent_cover_by_benthic_category"]["Hard coral"] == 60.0
    assert data[1]["percent_cover_by_benthic_category"]["Rock"] == 40.0


def test_benthiclit_su_view(
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
        "benthiclitmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[1]["site_name"] == site2.name

    assert data[0]["percent_cover_by_benthic_category"]["Macroalgae"] == 16.92
    assert data[0]["percent_cover_by_benthic_category"]["Hard coral"] == 60.0
    assert data[0]["percent_cover_by_benthic_category"]["Rock"] == 23.08

    assert data[1]["percent_cover_by_benthic_category"]["Hard coral"] == 58.46
    assert data[1]["percent_cover_by_benthic_category"]["Rock"] == 41.54


def test_habitatcomplexity_su_view(
    client, db_setup, project1, token1, habitat_complexity_project, all_choices, site1,
):
    url = reverse(
        "habitatcomplexitymethod-sampleunit-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[0]["site_name"] == site1.name
    assert data[0]["score_avg"] == 2.0


def test_bleachingqc_su_view(
    client, db_setup, project1, token1, bleaching_project, all_choices, site1,
):
    url = reverse(
        "bleachingqcsmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk)
    )
    count, data, response = _call(client, token1, url)

    assert count == 1
    assert data[0]["site_name"] == site1.name
    assert data[0]["count_total"] == 500
    assert data[0]["count_genera"] == 4
    assert data[0]["percent_normal"] == 5.0
    assert data[0]["percent_pale"] == 24.0
    assert data[0]["percent_bleached"] == 71.0
    assert data[0]["quadrat_count"] == 5
    assert data[0]["percent_hard_avg"] == 59.0
    assert data[0]["percent_soft_avg"] == 19.6
    assert data[0]["percent_algae_avg"] == 20.4
