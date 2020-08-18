import csv

# import os
from io import StringIO, BytesIO

import pytest
from django.urls import reverse

# from api.models import (
#     BeltFish,
    
#     BenthicPITObsView,
#     BenthicLIT,
#     BenthicPIT,
#     BleachingQuadratCollection,
#     HabitatComplexity,
#     ObsBenthicLIT,
#     ObsBenthicPIT,
#     ObsColoniesBleached,
#     ObsHabitatComplexity,
#     ObsQuadratBenthicPercent,
#     ProjectProfile,
# )
# from ..resources import fieldreport


def _get_rows(client, token, url):
    response = client.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")
    f = StringIO(b"".join(response.streaming_content).decode("utf-8"))
    reader = csv.DictReader(f, delimiter=",")
    fieldnames = reader.fieldnames
    return fieldnames, list(reader)


def test_beltfish_csv_view(
    client, db_setup, project1, token1, belt_fish_project, all_choices, site2, profile2
):
    url = reverse("obstransectbeltfish-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows = _get_rows(client, token1, url)

    assert len(rows) == 6
    assert "Country" in fieldnames

    assert rows[3]["Site"] == site2.name
    assert float(rows[3]["Latitude"]) == site2.location.y
    assert float(rows[3]["Longitude"]) == site2.location.x
    assert rows[3]["Observer"] == profile2.full_name


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
):
    url = reverse("obstransectbenthicpit-csv", kwargs=dict(project_pk=project1.pk))
    fieldnames, rows = _get_rows(client, token1, url)

    bf = BenthicPITObsView.objects.all().order_by(
        "site_name", "sample_date", "transect_number", "label", "interval"
    )

    for row, b in zip(rows, bf):
        print(b.site_name)
        print(row["Site"])
        print("==")

    assert len(rows) == 10
    assert "Country" in fieldnames

    assert rows[6]["Site"] == site2.name
    assert float(rows[6]["Latitude"]) == site2.location.y
    assert float(rows[6]["Longitude"]) == site2.location.x
    assert rows[6]["Observer"] == profile2.full_name


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
