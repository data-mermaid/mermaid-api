import os

from datetime import datetime

import pytest
from api.ingest import utils
from api.models import (
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_data_dir = os.path.join(BASE_DIR, "tests/ingest_data/")


@pytest.fixture
def fishbelt_file(db):
    return open(os.path.join(csv_data_dir, "fishbelt.csv"))


@pytest.fixture
def benthicpit_file(db):
    return open(os.path.join(csv_data_dir, "benthicpit.csv"))


@pytest.fixture
def bleaching_file(db):
    return open(os.path.join(csv_data_dir, "bleaching.csv"))


def test_fishbelt_ingest(
    db_setup,
    fishbelt_file,
    project1,
    profile1,
    base_project,
    all_test_fish_attributes,
    belt_transect_width_5m,
    fish_size_bin_1,
    tide2,
    current2,
    site1,
    management1,
    fish_species3,
):
    new_records, output = utils.ingest(
        protocol=FISHBELT_PROTOCOL,
        datafile=fishbelt_file,
        project_id=project1.pk,
        profile_id=profile1.pk,
        request=None,
        dry_run=False,
        clear_existing=False,
        bulk_validation=False,
        bulk_submission=False,
        validation_suppressants=None,
        serializer_class=None,
    )

    assert new_records is not None and len(new_records) == 1

    new_record = new_records[0]
    sample_event = new_record.data.get("sample_event")
    fishbelt_transect = new_record.data.get("fishbelt_transect")
    observations = new_record.data["obs_belt_fishes"]

    assert new_record.project == project1
    assert new_record.profile == profile1

    assert fishbelt_transect.get("current") == str(current2.id)
    assert fishbelt_transect.get("tide") == str(tide2.id)
    assert fishbelt_transect.get("width") == str(belt_transect_width_5m.id)
    assert fishbelt_transect.get("depth") == 10

    assert sample_event.get("site") == str(site1.id)
    assert sample_event.get("management") == str(management1.id)
    assert str(sample_event.get("sample_date")) == "2015-12-03"

    assert len(observations) == 6
    assert observations[2].get("size") == 20
    assert observations[2].get("count") == 1
    assert observations[2].get("fish_attribute") == str(fish_species3.id)
    


def test_benthicpit_ingest(
    db_setup,
    benthicpit_file,
    project1,
    profile1,
    base_project,
    all_test_benthic_attributes,
    tide1,
    tide2,
    relative_depth1,
    benthic_attribute_2a,
    growth_form4,
):
    new_records, output = utils.ingest(
        protocol=BENTHICPIT_PROTOCOL,
        datafile=benthicpit_file,
        project_id=project1.pk,
        profile_id=profile1.pk,
        request=None,
        dry_run=False,
        clear_existing=False,
        bulk_validation=False,
        bulk_submission=False,
        validation_suppressants=None,
        serializer_class=None,
    )

    assert new_records is not None and len(new_records) == 2

    new_record = new_records[0]
    benthic_transect = new_record.data.get("benthic_transect")
    observations = new_record.data["obs_benthic_pits"]

    assert benthic_transect.get("tide") == str(tide2.id)

    assert len(observations) == 24
    assert observations[2].get("attribute") == str(benthic_attribute_2a.id)
    assert observations[2].get("growth_form") == str(growth_form4.id)


def test_bleaching_ingest(
    db_setup,
    bleaching_file,
    project1,
    profile1,
    base_project,
    all_test_benthic_attributes,
    tide1,
    visibility1,
    current3,
    relative_depth1,
    benthic_attribute_2,
    benthic_attribute_2a1,
    growth_form4,
):
    new_records, output = utils.ingest(
        protocol=BLEACHINGQC_PROTOCOL,
        datafile=bleaching_file,
        project_id=project1.pk,
        profile_id=profile1.pk,
        request=None,
        dry_run=False,
        clear_existing=False,
        bulk_validation=False,
        bulk_submission=False,
        validation_suppressants=None,
        serializer_class=None,
    )

    assert new_records is not None and len(new_records) == 1

    new_record = new_records[0]
    quadrat_collection = new_record.data.get("quadrat_collection")

    assert quadrat_collection.get("tide") == str(tide1.id)

    obs_colonies_bleached = new_record.data["obs_colonies_bleached"]

    assert len(obs_colonies_bleached) == 2
    assert obs_colonies_bleached[0]["attribute"] == str(benthic_attribute_2a1.id)
    assert obs_colonies_bleached[0]["growth_form"] == str(growth_form4.id)
    assert obs_colonies_bleached[1]["attribute"] == str(benthic_attribute_2.id)

    obs_quadrat_benthic_percent = new_record.data["obs_quadrat_benthic_percent"]
    assert len(obs_quadrat_benthic_percent) == 4
    assert obs_quadrat_benthic_percent[3]["quadrat_number"] == 4
    assert obs_quadrat_benthic_percent[3]["percent_hard"] == 87
    assert obs_quadrat_benthic_percent[3]["percent_soft"] == 0
    assert obs_quadrat_benthic_percent[3]["percent_algae"] == 13
