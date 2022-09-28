import datetime
import os

import pytest

from api.ingest import utils
from api.models import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    BENTHICPQT_PROTOCOL,
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
def benthiclit_file(db):
    return open(os.path.join(csv_data_dir, "benthiclit.csv"))


@pytest.fixture
def habitatcomplexity_file(db):
    return open(os.path.join(csv_data_dir, "habitatcomplexity.csv"))


@pytest.fixture
def bleaching_file(db):
    return open(os.path.join(csv_data_dir, "bleaching.csv"))


@pytest.fixture
def benthicpqt_file(db):
    return open(os.path.join(csv_data_dir, "benthicpqt.csv"))


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
    site2,
    management1,
    fish_species3,
    fish_species4,
    reef_slope1,
    relative_depth1,
    visibility1,
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

    assert new_records is not None and len(new_records) == 2

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
    assert fishbelt_transect.get("reef_slope") == str(reef_slope1.id)
    assert fishbelt_transect.get("visibility") == str(visibility1.id)
    assert fishbelt_transect.get("relative_depth") == str(relative_depth1.id)
    assert fishbelt_transect.get("notes") == "SU notes"
    assert str(fishbelt_transect.get("sample_time")) == "11:00:00"

    assert sample_event.get("site") == str(site1.id)
    assert sample_event.get("management") == str(management1.id)
    assert str(sample_event.get("sample_date")) == "2015-12-03"

    assert len(observations) == 6
    assert observations[2].get("size") == 20
    assert observations[2].get("count") == 1
    assert observations[2].get("fish_attribute") == str(fish_species3.id)

    assert new_records[1].data["obs_belt_fishes"][2]["fish_attribute"] == str(
        fish_species4.id
    )


def test_benthicpit_ingest(
    db_setup,
    benthicpit_file,
    project1,
    profile1,
    base_project,
    all_test_benthic_attributes,
    tide1,
    relative_depth1,
    benthic_attribute_2a1,
    growth_form1,
    site1,
    management1,
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

    new_record = new_records[1]
    sample_event = new_record.data.get("sample_event")
    benthic_transect = new_record.data.get("benthic_transect")
    observations = new_record.data["obs_benthic_pits"]

    assert new_record.project == project1
    assert new_record.profile == profile1

    assert benthic_transect.get("depth") == 8.0
    assert benthic_transect.get("tide") == str(tide1.id)
    assert benthic_transect.get("relative_depth") == str(relative_depth1.id)
    assert benthic_transect.get("notes") == "SU notes"

    assert sample_event.get("site") == str(site1.id)
    assert sample_event.get("management") == str(management1.id)
    assert str(sample_event.get("sample_date")) == "2011-03-31"

    assert len(observations) == 3
    assert observations[0].get("attribute") == str(benthic_attribute_2a1.id)
    assert observations[0].get("growth_form") == str(growth_form1.id)


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
    site1,
    management1,
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
    sample_event = new_record.data.get("sample_event")
    quadrat_collection = new_record.data.get("quadrat_collection")
    obs_colonies_bleached = new_record.data["obs_colonies_bleached"]

    assert new_record.project == project1
    assert new_record.profile == profile1

    assert quadrat_collection.get("tide") == str(tide1.id)
    assert quadrat_collection.get("depth") == 1.0
    assert quadrat_collection.get("quadrat_size") == 1
    assert quadrat_collection.get("visibility") == str(visibility1.id)
    assert quadrat_collection.get("current") == str(current3.id)
    assert quadrat_collection.get("relative_depth") == str(relative_depth1.id)
    assert quadrat_collection.get("notes") == "SU notes"

    assert sample_event.get("site") == str(site1.id)
    assert sample_event.get("management") == str(management1.id)
    assert str(sample_event.get("sample_date")) == "2020-05-20"

    assert len(obs_colonies_bleached) == 2
    assert obs_colonies_bleached[0]["attribute"] == str(benthic_attribute_2a1.id)
    assert obs_colonies_bleached[0]["growth_form"] == str(growth_form4.id)
    assert obs_colonies_bleached[1]["attribute"] == str(benthic_attribute_2.id)

    obs_quadrat_benthic_percent = new_record.data["obs_quadrat_benthic_percent"]
    assert len(obs_quadrat_benthic_percent) == 4
    assert obs_quadrat_benthic_percent[3]["quadrat_number"] == 4
    assert obs_quadrat_benthic_percent[3]["percent_hard"] == 87
    assert obs_quadrat_benthic_percent[3]["percent_soft"] == None
    assert obs_quadrat_benthic_percent[3]["percent_algae"] == 13


def test_benthiclit_ingest(
    db_setup,
    benthiclit_file,
    project1,
    profile1,
    base_project,
    all_test_benthic_attributes,
    site1,
    site2,
    management1,
    management2,
    relative_depth1,
    relative_depth2,
    reef_slope2,
    reef_slope3,
    visibility1,
    visibility2,
    current1,
    current2,
    tide1,
    tide2,
    benthic_attribute_1a,
    benthic_attribute_2a1,
    benthic_attribute_2b1,
    benthic_attribute_3,
    benthic_attribute_4,
    benthic_attribute_2b,
    growth_form3,
    growth_form4,
):
    new_records, output = utils.ingest(
        protocol=BENTHICLIT_PROTOCOL,
        datafile=benthiclit_file,
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

    new_record = new_records[1]
    sample_event = new_record.data.get("sample_event")
    benthic_transect = new_record.data.get("benthic_transect")
    observations = new_record.data["obs_benthic_lits"]

    assert new_record.project == project1
    assert new_record.profile == profile1
    assert str(new_record.data.get("observers")[0]["profile"]) == str(profile1.id)

    assert benthic_transect.get("depth") == 5.0
    assert benthic_transect.get("tide") == str(tide2.id)
    assert benthic_transect.get("relative_depth") == str(relative_depth2.id)
    assert benthic_transect.get("sample_time") == datetime.time(8, 0)
    assert benthic_transect.get("number") == 2
    assert benthic_transect.get("reef_slope") == str(reef_slope3.id)
    assert benthic_transect.get("notes") == "SU notes"

    assert sample_event.get("site") == str(site2.id)
    assert sample_event.get("management") == str(management2.id)
    assert str(sample_event.get("sample_date")) == "2020-02-22"

    assert len(observations) == 5
    assert observations[0].get("attribute") == str(benthic_attribute_3.id)
    assert observations[0].get("growth_form") is None
    assert observations[0].get("length") == 322


def test_habitatcomplexity_ingest(
    db_setup,
    habitatcomplexity_file,
    project1,
    profile1,
    base_project,
    all_test_benthic_attributes,
    site1,
    site2,
    management1,
    management2,
    relative_depth1,
    relative_depth2,
    reef_slope2,
    reef_slope3,
    visibility1,
    visibility2,
    current1,
    current2,
    tide1,
    tide2,
    habitat_complexity_score1,
    habitat_complexity_score2,
    habitat_complexity_score3,
):
    new_records, output = utils.ingest(
        protocol=HABITATCOMPLEXITY_PROTOCOL,
        datafile=habitatcomplexity_file,
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
    sample_event = new_record.data.get("sample_event")
    benthic_transect = new_record.data.get("benthic_transect")
    observations = new_record.data["obs_habitat_complexities"]

    assert new_record.project == project1
    assert new_record.profile == profile1
    assert str(new_record.data.get("observers")[0]["profile"]) == str(profile1.id)

    assert benthic_transect.get("depth") == 5.0
    assert benthic_transect.get("tide") == str(tide2.id)
    assert benthic_transect.get("relative_depth") == str(relative_depth2.id)
    assert benthic_transect.get("sample_time") == datetime.time(8, 0)
    assert benthic_transect.get("number") == 2
    assert benthic_transect.get("reef_slope") == str(reef_slope3.id)
    assert benthic_transect.get("notes") == "SU notes"

    assert sample_event.get("site") == str(site2.id)
    assert sample_event.get("management") == str(management2.id)
    assert str(sample_event.get("sample_date")) == "2020-02-22"

    assert len(observations) == 5
    assert observations[0].get("interval") == 0.5
    assert observations[0].get("score") == str(habitat_complexity_score3.id)


def test_benthicpqt_ingest(
    benthicpqt_file,
    project1,
    profile1,
    base_project,
    all_test_benthic_attributes,
    site1,
    site2,
    management1,
    management2,
    relative_depth1,
    relative_depth2,
    reef_slope1,
    visibility1,
    current3,
    tide1,
    tide2,
    growth_form1,
):
    new_records, _ = utils.ingest(
        protocol=BENTHICPQT_PROTOCOL,
        datafile=benthicpqt_file,
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
    obs = new_record.data["obs_benthic_photo_quadrats"]

    assert new_record.data["sample_event"]["sample_date"] == datetime.date(2009, 4, 15)
    assert new_record.data["quadrat_transect"]["depth"] == 4
    assert new_record.data["quadrat_transect"]["len_surveyed"] == 50
    assert new_record.data["quadrat_transect"]["num_quadrats"] == 7
    assert new_record.data["quadrat_transect"]["number"] == 1
    assert new_record.data["quadrat_transect"]["num_points_per_quadrat"] == 100
    assert new_record.data["quadrat_transect"]["visibility"] == str(visibility1.id)
    assert new_record.data["quadrat_transect"]["quadrat_size"] == 0.5
    assert new_record.data["quadrat_transect"]["notes"] == "SU notes"

    assert len(obs) == 24
    assert obs[-1]["num_points"] == 100
    assert sum(o.get("num_points") or 0 for o in obs) == 700
    assert obs[1]["growth_form"] == str(growth_form1.id)

    new_records[1].data["quadrat_transect"]["reef_slope"] = str(reef_slope1.id)
    new_records[1].data["quadrat_transect"]["relative_depth"] = str(relative_depth2.id)
    new_records[1].data["quadrat_transect"]["num_quadrats"] = 2
