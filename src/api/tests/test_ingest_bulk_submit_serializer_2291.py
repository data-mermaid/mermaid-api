"""Card 2291: ingest bulk submit passed arguments to submit_collect_records positionally,
so validation_suppressants landed in the serializer_class slot and bulk submit from a CSV
ingest raised TypeError inside _save_validation_output. The serializer_class must reach the
serializer_class parameter.
"""

import os
from unittest.mock import patch

import pytest

from api.ingest import utils
from api.models import FISHBELT_PROTOCOL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_data_dir = os.path.join(BASE_DIR, "tests/ingest_data/")


@pytest.fixture
def fishbelt_file(db):
    file = open(os.path.join(csv_data_dir, "fishbelt.csv"))
    yield file
    file.close()


def test_bulk_submit_passes_serializer_class_not_suppressants_2291(
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
    sentinel = object()
    with (
        patch.object(utils, "validate_collect_records", return_value={}),
        patch.object(utils, "submit_collect_records", return_value={}) as mock_submit,
    ):
        utils.ingest(
            protocol=FISHBELT_PROTOCOL,
            datafile=fishbelt_file,
            project_id=project1.pk,
            profile_id=profile1.pk,
            request=None,
            dry_run=False,
            clear_existing=False,
            bulk_validation=False,
            bulk_submission=True,
            validation_suppressants=None,
            serializer_class=sentinel,
        )

    assert mock_submit.call_count == 1
    args, kwargs = mock_submit.call_args
    # The third positional (or serializer_class kwarg) must be the serializer class, never
    # validation_suppressants.
    passed = kwargs.get("serializer_class", args[2] if len(args) > 2 else None)
    assert passed is sentinel
