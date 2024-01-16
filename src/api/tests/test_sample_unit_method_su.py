import pytest
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
    obs_belt_fish2_4_biomass,
    fishbelt_transect1,
    fishbelt_transect2,
    update_summary_cache,
):
    url = reverse("beltfishmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, _ = _call(client, token1, url)

    assert count == 2
    n = 0
    for record in data:
        if record["sample_unit_ids"][0] == str(fishbelt_transect1.pk):
            biomass_kgha_1 = sum(
                [obs_belt_fish1_1_biomass, obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass]
            )

            biomass_kgha_1_other = sum([obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass])

            assert record["biomass_kgha"] == pytest.approx(biomass_kgha_1, 0.1)
            assert record["biomass_kgha_trophic_group"]["other"] == pytest.approx(
                biomass_kgha_1_other, 0.1
            )
            assert record["biomass_kgha_trophic_group"]["omnivore"] == pytest.approx(
                obs_belt_fish1_1_biomass, 0.1
            )

            biomass_kgha_2 = sum(
                [obs_belt_fish2_1_biomass, obs_belt_fish2_2_biomass, obs_belt_fish2_3_biomass]
            )

            assert data[1]["biomass_kgha"] == pytest.approx(biomass_kgha_2, 0.1)

            fish_family_biomass_0 = record["biomass_kgha_fish_family"]
            assert fish_family_biomass_0["Fish Family 1"] == pytest.approx(
                obs_belt_fish1_1_biomass, 0.1
            )
            assert fish_family_biomass_0["Fish Family 2"] == pytest.approx(
                obs_belt_fish1_2_biomass, 0.1
            )
            assert fish_family_biomass_0["Fish Family 3"] == pytest.approx(
                obs_belt_fish1_3_biomass, 0.1
            )

            fish_family_biomass_1 = data[1]["biomass_kgha_fish_family"]
            fish_family_2_biomass = sum([obs_belt_fish2_1_biomass, obs_belt_fish2_4_biomass])
            assert fish_family_biomass_1["Fish Family 1"] == pytest.approx(
                obs_belt_fish2_3_biomass, 0.1
            )
            assert fish_family_biomass_1["Fish Family 2"] == pytest.approx(
                fish_family_2_biomass, 0.1
            )
            assert fish_family_biomass_1["Fish Family 3"] == pytest.approx(
                obs_belt_fish2_2_biomass, 0.1
            )
            n += 1

        elif record["sample_unit_ids"][0] == str(fishbelt_transect2.pk):
            assert record["site_name"] == site2.name
            n += 1

    if n != count:
        assert False, f"Wrong number of sample units, {n} should be {count}"


def test_benthicpit_su_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_pit_project,
    all_choices,
    benthic_transect1,
    benthic_transect1_2,
    benthic_transect2,
    management2,
    profile2,
    update_summary_cache,
):
    url = reverse("benthicpitmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, _ = _call(client, token1, url)

    assert count == 3
    n = 0
    for record in data:
        print(record["sample_unit_ids"])
        if record["sample_unit_ids"][0] == str(benthic_transect1.pk):
            assert record["percent_cover_benthic_category"]["Macroalgae"] == 20.0
            assert record["percent_cover_benthic_category"]["Hard coral"] == 60.0
            assert record["percent_cover_benthic_category"]["Rock"] == 20.0
            n += 1
        elif record["sample_unit_ids"][0] == str(benthic_transect1_2.pk):
            assert record["percent_cover_benthic_category"]["Macroalgae"] == 60.0
            assert record["percent_cover_benthic_category"]["Hard coral"] == 40.0
            n += 1
        elif record["sample_unit_ids"][0] == str(benthic_transect2.pk):
            assert record["percent_cover_benthic_category"]["Hard coral"] == 60.0
            assert record["percent_cover_benthic_category"]["Rock"] == 40.0
            n += 1

    if n != count:
        assert False, f"Wrong number of sample units, {n} should be {count}"


def test_benthiclit_su_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_lit_project,
    benthic_transect1,
    benthic_transect2,
    all_choices,
    site2,
    management2,
    profile2,
    update_summary_cache,
):
    url = reverse("benthiclitmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, _ = _call(client, token1, url)

    assert count == 2
    n = 0
    for record in data:
        if record["sample_unit_ids"][0] == str(benthic_transect1.pk):
            assert record["percent_cover_benthic_category"]["Macroalgae"] == 16.92
            assert record["percent_cover_benthic_category"]["Hard coral"] == 60.0
            assert record["percent_cover_benthic_category"]["Rock"] == 23.08
            n += 1
        elif record["sample_unit_ids"][0] == str(benthic_transect2.pk):
            assert record["site_name"] == site2.name
            assert record["percent_cover_benthic_category"]["Hard coral"] == 58.46
            assert record["percent_cover_benthic_category"]["Rock"] == 41.54
            n += 1

    if n != count:
        assert False, f"Wrong number of sample units, {n} should be {count}"


def test_habitatcomplexity_su_view(
    client,
    db_setup,
    project1,
    token1,
    habitat_complexity_project,
    benthic_transect1,
    benthic_transect2,
    all_choices,
    site1,
    update_summary_cache,
):
    url = reverse("habitatcomplexitymethod-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, _ = _call(client, token1, url)

    assert count == 2
    n = 0
    for record in data:
        if record["sample_unit_ids"][0] == str(benthic_transect1.pk):
            assert record["site_name"] == site1.name
            assert record["score_avg"] == 2.0
            n += 1
        elif record["sample_unit_ids"][0] == str(benthic_transect2.pk):
            n += 1

    if n != count:
        assert False, f"Wrong number of sample units, {n} should be {count}"


def test_bleachingqc_su_view(
    client,
    db_setup,
    project1,
    token1,
    bleaching_project,
    quadrat_collection1,
    all_choices,
    site1,
    update_summary_cache,
):
    url = reverse("bleachingqcsmethod-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, _ = _call(client, token1, url)

    assert count == 1
    n = 0
    for record in data:
        if record["sample_unit_ids"][0] == str(quadrat_collection1.pk):
            assert record["site_name"] == site1.name
            assert record["count_total"] == 500
            assert record["count_genera"] == 4
            assert record["percent_normal"] == 5.0
            assert record["percent_pale"] == 24.0
            assert record["percent_bleached"] == 71.0
            assert record["quadrat_count"] == 5
            assert record["percent_hard_avg"] == 59.0
            assert record["percent_soft_avg"] == 19.6
            assert record["percent_algae_avg"] == 20.4
            n += 1

    if n != count:
        assert False, f"Wrong number of sample units, {n} should be {count}"
