import os

import pytest
from api.ingest import utils
from api.models import (  # CollectRecord,
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BLEACHINGQC_PROTOCOL,
    FISHBELT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    Profile,
    Project,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_data_dir = os.path.join(BASE_DIR, "tests/ingest_data/")


@pytest.fixture
def fishbelt_file(db):
    return open(os.path.join(csv_data_dir, "fishbelt.csv"))


def test_fishbelt_ingest(
    fishbelt_file,
    project1,
    profile1,
    all_project1,
    all_test_fish,
    belt_transect_width_5m,
    fish_size_bin_1,
    tide2,
    current2,
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
    fishbelt_transect = new_record.data.get("fishbelt_transect")
    observations = new_record.data["obs_belt_fishes"]

    assert fishbelt_transect.get("current") == str(current2.id)
    assert fishbelt_transect.get("tide") == str(tide2.id)

    assert len(observations) == 6
    assert observations[2].get("size") == 20
    assert observations[2].get("count") == 1
