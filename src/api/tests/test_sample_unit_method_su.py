from django.urls import reverse


def _call(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    data = response.json()
    return data["count"], data["results"], response


def test_beltfish_su_csv_view(
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
    url = reverse("beltfish-sampleunit-list", kwargs=dict(project_pk=project1.pk))
    count, data, response = _call(client, token1, url)

    assert count == 2
    assert data[1]["site_name"] == site2.name

    biomass_kgha_1 = sum(
        [obs_belt_fish1_1_biomass, obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass,]
    )

    biomass_kgha_1_other = sum([obs_belt_fish1_2_biomass, obs_belt_fish1_3_biomass,])

    assert round(data[0]["biomass_kgha"], 1) == round(biomass_kgha_1, 1)
    assert round(data[0]["biomass_kgha_by_trophic_group"]["other"], 1) == round(
        biomass_kgha_1_other, 1
    )
    assert round(data[0]["biomass_kgha_by_trophic_group"]["omnivore"], 1) == round(
        obs_belt_fish1_1_biomass, 1
    )

    biomass_kgha_2 = sum(
        [obs_belt_fish2_1_biomass, obs_belt_fish2_2_biomass, obs_belt_fish2_3_biomass,]
    )

    transect_2_biomass = round(biomass_kgha_2, 1)
    assert round(data[1]["biomass_kgha"], 1) == transect_2_biomass
