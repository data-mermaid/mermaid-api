import csv

from io import StringIO

import pytest
from django.urls import reverse


def _get_rows(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    f = StringIO(b"".join(response.streaming_content).decode("utf-8"))
    reader = csv.DictReader(f, delimiter=",")
    fieldnames = reader.fieldnames
    return fieldnames, list(reader), response


def test_beltfish_csv_view(
    client,
    db_setup,
    project1,
    token1,
    belt_fish_project,
    all_choices,
    site2,
    management2,
    profile2,
    update_summary_cache,
):
    url = reverse("beltfishmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-beltfish-obs-"
        in response.headers.get("content-disposition")
    )
    assert len(rows) == 7
    assert "country_name" in fieldnames
    assert len(rows[3].keys()) == 60
    assert rows[3]["site_name"] == site2.name
    assert float(rows[3]["latitude"]) == site2.location.y
    assert float(rows[3]["longitude"]) == site2.location.x
    assert rows[3]["observers"] == profile2.full_name
    assert rows[3]["management_id"] == str(management2.id)


def test_beltfish_field_report(
    client,
    db_setup,
    project1,
    token1,
    belt_fish_project,
    all_choices,
    site2,
    profile2,
    update_summary_cache,
):
    url = reverse("beltfishmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-beltfish-obs-"
        in response.headers.get("content-disposition")
    )
    assert len(rows) == 7
    assert "Country" in fieldnames
    assert len(rows[3].keys()) == 54
    assert rows[3]["Site"] == site2.name
    assert float(rows[3]["Latitude"]) == site2.location.y
    assert float(rows[3]["Longitude"]) == site2.location.x
    assert rows[3]["Observers"] == profile2.full_name


def test_benthicpit_csv_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_pit_project,
    all_choices,
    site2,
    profile1,
    profile2,
    management2,
    update_summary_cache,
):
    url = reverse("benthicpitmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthicpit-obs-"
        in response.headers.get("content-disposition")
    )

    assert len(rows) == 15
    assert "country_name" in fieldnames
    assert len(rows[11].keys()) == 50
    assert rows[11]["site_name"] == site2.name
    assert float(rows[11]["latitude"]) == site2.location.y
    assert float(rows[11]["longitude"]) == site2.location.x
    assert rows[11]["observers"] == profile2.full_name
    assert rows[11]["management_id"] == str(management2.id)


def test_benthicpit_field_report(
    client,
    db_setup,
    project1,
    token1,
    benthic_pit_project,
    all_choices,
    site2,
    profile2,
    update_summary_cache,
):
    url = reverse("benthicpitmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthicpit-obs-"
        in response.headers.get("content-disposition")
    )
    assert len(rows) == 15
    assert "Country" in fieldnames
    assert len(rows[11].keys()) == 42
    assert rows[11]["Site"] == site2.name
    assert float(rows[11]["Latitude"]) == site2.location.y
    assert float(rows[11]["Longitude"]) == site2.location.x
    assert rows[11]["Observers"] == profile2.full_name


def test_benthiclit_csv_view(
    client,
    db_setup,
    project1,
    token1,
    benthic_lit_project,
    all_choices,
    site2,
    profile1,
    profile2,
    management2,
    ordered_benthic_lit1_observations,
    ordered_benthic_lit2_observations,
    update_summary_cache,
):
    url = reverse("benthiclitmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    ordered_obs = list(ordered_benthic_lit1_observations) + list(
        ordered_benthic_lit2_observations
    )

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthiclit-obs-"
        in response.headers.get("content-disposition")
    )

    assert len(rows) == 10
    assert "country_name" in fieldnames
    assert len(rows[6].keys()) == 49
    assert rows[6]["site_name"] == site2.name
    assert float(rows[6]["latitude"]) == site2.location.y
    assert float(rows[6]["longitude"]) == site2.location.x
    assert rows[6]["observers"] == profile2.full_name
    assert rows[6]["management_id"] == str(management2.id)
    assert rows[6]["length"] == str(ordered_obs[6].length)


def test_benthiclit_field_report(
    client,
    db_setup,
    all_choices,
    benthic_lit_project,
    project1,
    token1,
    site2,
    profile2,
    ordered_benthic_lit1_observations,
    ordered_benthic_lit2_observations,
    update_summary_cache,
):
    url = reverse("benthiclitmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    ordered_obs = list(ordered_benthic_lit1_observations) + list(
        ordered_benthic_lit2_observations
    )

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthiclit-obs-"
        in response.headers.get("content-disposition")
    )
    assert len(rows) == 10
    assert "Country" in fieldnames
    assert len(rows[6].keys()) == 43
    assert rows[6]["Site"] == site2.name
    assert float(rows[6]["Latitude"]) == site2.location.y
    assert float(rows[6]["Longitude"]) == site2.location.x
    assert rows[6]["Observers"] == profile2.full_name
    assert rows[6]["LIT (cm)"] == str(ordered_obs[6].length)


def test_habitatcomplexity_csv_view(
    client,
    db_setup,
    project1,
    token1,
    habitat_complexity_project,
    all_choices,
    site2,
    profile2,
    obs_habitat_complexity1_1,
    update_summary_cache,
):
    url = reverse(
        "habitatcomplexitymethod-obs-csv", kwargs=dict(project_pk=project1.pk)
    )
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert len(rows) == 6
    assert "country_name" in fieldnames
    assert len(rows[3].keys()) == 48
    assert rows[3]["site_name"] == site2.name
    assert float(rows[3]["latitude"]) == site2.location.y
    assert float(rows[3]["longitude"]) == site2.location.x
    assert rows[3]["observers"] == profile2.full_name
    assert int(float(rows[3]["interval"])) == int(
        float(obs_habitat_complexity1_1.interval)
    )


def test_habitatcomplexity_field_report(
    client,
    db_setup,
    project1,
    token1,
    habitat_complexity_project,
    all_choices,
    site2,
    profile2,
    obs_habitat_complexity1_1,
    update_summary_cache,
):
    url = reverse(
        "habitatcomplexitymethod-obs-csv", kwargs=dict(project_pk=project1.pk)
    )
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert len(rows) == 6
    assert "Country" in fieldnames
    assert len(rows[3].keys()) == 41
    assert rows[3]["Site"] == site2.name
    assert float(rows[3]["Latitude"]) == site2.location.y
    assert float(rows[3]["Longitude"]) == site2.location.x
    assert rows[3]["Observers"] == profile2.full_name
    assert int(float(rows[3]["Interval (m)"])) == int(
        float(obs_habitat_complexity1_1.interval)
    )


def test_bleaching_colonies_bleached_csv_view(
    client,
    db_setup,
    project1,
    token1,
    bleaching_project,
    all_choices,
    site1,
    profile1,
    obs_colonies_bleached1_4,
    update_summary_cache,
):
    url = reverse("coloniesbleachedmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert len(rows) == 5
    assert "country_name" in fieldnames
    assert len(rows[3].keys()) == 51
    assert rows[3]["site_name"] == site1.name
    assert float(rows[3]["latitude"]) == site1.location.y
    assert float(rows[3]["longitude"]) == site1.location.x
    assert rows[3]["observers"] == profile1.full_name
    assert rows[3]["id"] == str(obs_colonies_bleached1_4.id)


def test_bleaching_colonies_bleached_field_report(
    client,
    db_setup,
    project1,
    token1,
    bleaching_project,
    all_choices,
    site1,
    profile1,
    obs_colonies_bleached1_4,
    update_summary_cache,
):
    url = reverse("coloniesbleachedmethod-obs-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert len(rows) == 5
    assert "Country" in fieldnames
    assert len(rows[3].keys()) == 45
    assert rows[3]["Site"] == site1.name
    assert float(rows[3]["Latitude"]) == site1.location.y
    assert float(rows[3]["Longitude"]) == site1.location.x
    assert rows[3]["Observers"] == profile1.full_name
    assert rows[3]["20-50% bleached count"] == str(obs_colonies_bleached1_4.count_50)


def test_bleaching_quadrat_benthic_percent_csv_view(
    client,
    db_setup,
    project1,
    token1,
    bleaching_project,
    all_choices,
    site1,
    profile1,
    obs_quadrat_benthic_percent1_4,
    update_summary_cache,
):
    url = reverse(
        "quadratbenthicpercentmethod-obs-csv", kwargs=dict(project_pk=project1.pk)
    )
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert len(rows) == 5
    assert "country_name" in fieldnames
    assert len(rows[3].keys()) == 46
    assert rows[3]["site_name"] == site1.name
    assert float(rows[3]["latitude"]) == site1.location.y
    assert float(rows[3]["longitude"]) == site1.location.x
    assert rows[3]["observers"] == profile1.full_name
    assert rows[3]["id"] == str(obs_quadrat_benthic_percent1_4.id)


def test_bleaching_quadrat_benthic_percent_field_report(
    client,
    db_setup,
    project1,
    token1,
    bleaching_project,
    all_choices,
    site1,
    profile1,
    obs_quadrat_benthic_percent1_4,
    update_summary_cache,
):
    url = reverse(
        "quadratbenthicpercentmethod-obs-csv", kwargs=dict(project_pk=project1.pk)
    )
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert len(rows) == 5
    assert "Country" in fieldnames
    assert len(rows[3].keys()) == 40
    assert rows[3]["Site"] == site1.name
    assert float(rows[3]["Latitude"]) == site1.location.y
    assert float(rows[3]["Longitude"]) == site1.location.x
    assert rows[3]["Observers"] == profile1.full_name
    assert pytest.approx(float(rows[3]["Soft coral (% cover)"]), 1) == pytest.approx(
        obs_quadrat_benthic_percent1_4.percent_soft, 1
    )
