import copy
import uuid

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from api.models import CollectRecord, Project
from api.resources.collect_record import CollectRecordSerializer
from api.submission.utils import (
    SUCCESS_STATUS,
    VALIDATION_ERROR_STATUS,
    submit_collect_records,
    validate_collect_record,
    write_collect_record,
)
from api.submission.validations.statuses import ERROR, OK, WARN
from api.utils import Testing
from api.utils.related import defer_project_updated_on

COLLECT_RECORD_FIXTURES = [
    "valid_collect_record",
    "valid_benthic_pit_collect_record",
    "valid_benthic_lit_collect_record",
    "valid_habitat_complexity_collect_record",
    "valid_bleaching_qc_collect_record",
    "valid_belt_invert_collect_record",
]

# Fields that must stay unique within a sample unit.
UNIQUE_OBS_FIELDS = ("interval", "quadrat_number")


def _scaled_copy(collect_record, factor):
    """
    A new collect record with each list of observations repeated `factor` times.
    Intervals and quadrat numbers continue from the original ones, and the
    transect is lengthened to match, so the record stays valid.
    """
    data = copy.deepcopy(collect_record.data)
    for key, observations in data.items():
        if not key.startswith("obs_") or not isinstance(observations, list):
            continue

        offsets = {
            field: max(obs[field] for obs in observations)
            for field in UNIQUE_OBS_FIELDS
            if observations and observations[0].get(field) is not None
        }
        scaled = []
        for n in range(factor):
            for obs in copy.deepcopy(observations):
                for field, offset in offsets.items():
                    obs[field] = obs[field] + n * offset
                if n > 0 and obs.get("id"):
                    obs["id"] = str(uuid.uuid4())
                if n > 0 and isinstance(obs.get("size"), (int, float)):
                    # Belt invert flags repeated (attribute, size) pairs as duplicates.
                    obs["size"] = obs["size"] + n * 0.1
                scaled.append(obs)
        data[key] = scaled

    for transect_key in ("benthic_transect", "fishbelt_transect", "belt_transect"):
        transect = data.get(transect_key)
        if transect and transect.get("len_surveyed"):
            transect["len_surveyed"] = transect["len_surveyed"] * factor

    return CollectRecord.objects.create(
        project=collect_record.project,
        profile=collect_record.profile,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data,
    )


def _count_dry_write_queries(collect_record, request):
    with CaptureQueriesContext(connection) as queries:
        status, result = write_collect_record(collect_record, request, dry_run=True)
    assert status == SUCCESS_STATUS, result
    return len(queries)


def _project_updates(queries):
    return [q for q in queries.captured_queries if q["sql"].startswith('UPDATE "project"')]


@pytest.mark.parametrize("collect_record_fixture", COLLECT_RECORD_FIXTURES)
def test_dry_write_queries_do_not_scale_with_observations(
    request, collect_record_fixture, profile1_request
):
    collect_record = request.getfixturevalue(collect_record_fixture)
    record_1x = _scaled_copy(collect_record, 1)
    record_3x = _scaled_copy(collect_record, 3)

    with Testing():
        # The first write loads some lookups once per process; leave it out.
        _count_dry_write_queries(record_1x, profile1_request)
        count_1x = _count_dry_write_queries(record_1x, profile1_request)
        count_3x = _count_dry_write_queries(record_3x, profile1_request)

    assert count_3x == count_1x


@pytest.mark.parametrize("collect_record_fixture", COLLECT_RECORD_FIXTURES)
def test_validate_queries_do_not_scale_with_observations(request, collect_record_fixture, profile1):
    collect_record = request.getfixturevalue(collect_record_fixture)
    record_1x = _scaled_copy(collect_record, 1)
    record_3x = _scaled_copy(collect_record, 3)

    counts = []
    statuses = []
    with Testing():
        validate_collect_record(profile1, record_1x, CollectRecordSerializer)
        for record in (record_1x, record_3x):
            with CaptureQueriesContext(connection) as queries:
                output = validate_collect_record(profile1, record, CollectRecordSerializer)
            # Errors skip the dry write; the other validations still run.
            assert output["status"] in (OK, WARN, ERROR)
            counts.append(len(queries))
            statuses.append(output["status"])
            # At most one project save, from the dry write.
            assert len(_project_updates(queries)) <= 1

    assert counts[0] == counts[1], statuses


def test_submit_updates_project_once(valid_collect_record, profile1):
    project_updated_on = Project.objects.get(id=valid_collect_record.project_id).updated_on

    with Testing(), CaptureQueriesContext(connection) as queries:
        output = submit_collect_records(
            profile1, [str(valid_collect_record.id)], CollectRecordSerializer
        )

    assert output[str(valid_collect_record.id)]["status"] == OK
    # One when the write ends, one from deleting the collect record.
    assert len(_project_updates(queries)) == 2
    assert Project.objects.get(id=valid_collect_record.project_id).updated_on > project_updated_on


def test_bleaching_duplicate_quadrat_number_message(
    valid_bleaching_qc_collect_record, profile1_request
):
    data = valid_bleaching_qc_collect_record.data
    data["obs_quadrat_benthic_percent"][1]["quadrat_number"] = data["obs_quadrat_benthic_percent"][
        0
    ]["quadrat_number"]
    valid_bleaching_qc_collect_record.save()

    with Testing():
        status, result = write_collect_record(
            valid_bleaching_qc_collect_record, profile1_request, dry_run=True
        )

    assert status == VALIDATION_ERROR_STATUS
    assert result == {"non_field_errors": ["Duplicate quadrat numbers"]}


def test_deferred_project_updated_on_saves_each_project_once(site1, project2):
    project1 = site1.project
    before = {p.pk: p.updated_on for p in Project.objects.filter(pk__in=[project1.pk, project2.pk])}

    with CaptureQueriesContext(connection) as queries:
        with defer_project_updated_on():
            site1.save()
            site1.save()
            site1.project = project2
            site1.save()
            assert _project_updates(queries) == []

    assert len(_project_updates(queries)) == 2
    for project in Project.objects.filter(pk__in=[project1.pk, project2.pk]):
        assert project.updated_on > before[project.pk]


def test_deferred_project_updated_on_skips_save_on_error(site1):
    with CaptureQueriesContext(connection) as queries, pytest.raises(ValueError):
        with defer_project_updated_on():
            site1.save()
            raise ValueError

    assert _project_updates(queries) == []
