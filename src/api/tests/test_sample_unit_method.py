import csv
# import os
from io import StringIO

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
):
    url = reverse("obstransectbeltfish-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-beltfish-obs-"
        in response._headers.get("content-disposition")[1]
    )
    assert len(rows) == 6
    assert "country_name" in fieldnames
    assert len(rows[3].keys()) == 57
    assert rows[3]["site_name"] == site2.name
    assert float(rows[3]["latitude"]) == site2.location.y
    assert float(rows[3]["longitude"]) == site2.location.x
    assert rows[3]["observers"] == profile2.full_name
    assert rows[3]["management_id"] == str(management2.id)


def test_beltfish_field_report(
    client, db_setup, project1, token1, belt_fish_project, all_choices, site2, profile2
):
    url = reverse("obstransectbeltfish-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-beltfish-obs-"
        in response._headers.get("content-disposition")[1]
    )
    assert len(rows) == 6
    assert "Country" in fieldnames
    assert len(rows[3].keys()) == 47
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
):
    url = reverse("obstransectbenthicpit-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthicpit-obs-"
        in response._headers.get("content-disposition")[1]
    )

    assert len(rows) == 10
    assert "country_name" in fieldnames
    assert len(rows[6].keys()) == 48
    assert rows[6]["site_name"] == site2.name
    assert float(rows[6]["latitude"]) == site2.location.y
    assert float(rows[6]["longitude"]) == site2.location.x
    assert rows[6]["observers"] == profile2.full_name
    assert rows[6]["management_id"] == str(management2.id)


def test_benthicpit_field_report(
    client,
    db_setup,
    project1,
    token1,
    benthic_pit_project,
    all_choices,
    site2,
    profile2,
):
    url = reverse("obstransectbenthicpit-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthicpit-obs-"
        in response._headers.get("content-disposition")[1]
    )
    assert len(rows) == 10
    assert "Country" in fieldnames
    assert len(rows[6].keys()) == 36
    assert rows[6]["Site"] == site2.name
    assert float(rows[6]["Latitude"]) == site2.location.y
    assert float(rows[6]["Longitude"]) == site2.location.x
    assert rows[6]["Observers"] == profile2.full_name


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
    obs_benthic_lit2_4,
):
    url = reverse("obstransectbenthiclit-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, url)

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthiclit-obs-"
        in response._headers.get("content-disposition")[1]
    )

    assert len(rows) == 10
    assert "country_name" in fieldnames
    assert len(rows[6].keys()) == 47
    assert rows[6]["site_name"] == site2.name
    assert float(rows[6]["latitude"]) == site2.location.y
    assert float(rows[6]["longitude"]) == site2.location.x
    assert rows[6]["observers"] == profile2.full_name
    assert rows[6]["management_id"] == str(management2.id)
    assert rows[6]["length"] == str(obs_benthic_lit2_4.length)


def test_benthiclit_field_report(
    client,
    db_setup,
    project1,
    token1,
    benthic_lit_project,
    all_choices,
    site2,
    profile2,
    obs_benthic_lit2_4,
):
    url = reverse("obstransectbenthiclit-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows, response = _get_rows(client, token1, f"{url}?field_report=true")

    assert response.has_header("Content-Disposition")
    assert (
        "test_project_1-benthiclit-obs-"
        in response._headers.get("content-disposition")[1]
    )
    assert len(rows) == 10
    assert "Country" in fieldnames
    assert len(rows[6].keys()) == 37
    assert rows[6]["Site"] == site2.name
    assert float(rows[6]["Latitude"]) == site2.location.y
    assert float(rows[6]["Longitude"]) == site2.location.x
    assert rows[6]["Observers"] == profile2.full_name
    assert rows[6]["LIT (cm)"] == str(obs_benthic_lit2_4.length)


# def test_benthiclit_csv_view(
#     client,
#     db_setup,
#     project1,
#     token1,
#     benthic_lit_project,
#     all_choices,
#     site2,
#     profile2,
# ):
#     url = reverse("obstransectbenthiclit-csv", kwargs=dict(project_pk=project1.pk))
#     fieldnames, rows = _get_rows(client, token1, url)

#     assert len(rows) == 6
#     assert "Country" in fieldnames

#     assert rows[3]["Site"] == site2.name
#     assert float(rows[3]["Latitude"]) == site2.location.y
#     assert float(rows[3]["Longitude"]) == site2.location.x
#     assert rows[3]["Observer"] == profile2.full_name


# def test_habitatcomplexity_csv_view(
#     client,
#     db_setup,
#     project1,
#     token1,
#     habitat_complexity_project,
#     all_choices,
#     site2,
#     profile2,
# ):
#     url = reverse("obshabitatcomplexity-csv", kwargs=dict(project_pk=project1.pk))
#     fieldnames, rows = _get_rows(client, token1, url)

#     assert len(rows) == 6
#     assert "Country" in fieldnames

#     assert rows[3]["Site"] == site2.name
#     assert float(rows[3]["Latitude"]) == site2.location.y
#     assert float(rows[3]["Longitude"]) == site2.location.x
#     assert rows[3]["Observer"] == profile2.full_name


# def test_bleaching_colonies_bleached_csv_view(
#     client,
#     db_setup,
#     project1,
#     token1,
#     bleaching_project,
#     all_choices,
#     site2,
#     profile2,
# ):
#     url = reverse("obscoloniesbleached-csv", kwargs=dict(project_pk=project1.pk))
#     fieldnames, rows = _get_rows(client, token1, url)

#     assert len(rows) == 6
#     assert "Country" in fieldnames

#     assert rows[3]["Site"] == site2.name
#     assert float(rows[3]["Latitude"]) == site2.location.y
#     assert float(rows[3]["Longitude"]) == site2.location.x
#     assert rows[3]["Observer"] == profile2.full_name


# def test_bleaching_quadrat_benthic_percent_csv_view(
#     client,
#     db_setup,
#     project1,
#     token1,
#     bleaching_project,
#     all_choices,
#     site2,
#     profile2,
# ):
#     url = reverse("obsquadratbenthicpercent-csv", kwargs=dict(project_pk=project1.pk))
#     fieldnames, rows = _get_rows(client, token1, url)

#     assert len(rows) == 6
#     assert "Country" in fieldnames

#     assert rows[3]["Site"] == site2.name
#     assert float(rows[3]["Latitude"]) == site2.location.y
#     assert float(rows[3]["Longitude"]) == site2.location.x
#     assert rows[3]["Observer"] == profile2.full_name
