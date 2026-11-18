import pytest

from api.models import BenthicTransect, HabitatComplexity, Observer
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, ValidationRunner, habitat_complexity
from api.submission.validations.validators import (
    DuplicateValidator,
    IntervalSizeValidator,
    UniqueBenthicTransectValidator,
)


def _get_validator():
    return UniqueBenthicTransectValidator(
        protocol_path="data.protocol",
        label_path="data.benthic_transect.label",
        number_path="data.benthic_transect.number",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        depth_path="data.benthic_transect.depth",
        observers_path="data.observers",
    )


@pytest.fixture()
def existing_benthic_transect(db, sample_event1, profile1):
    benthic_transect = BenthicTransect.objects.create(
        sample_event=sample_event1, number=2, depth=1, len_surveyed=100
    )
    habitat_complexity = HabitatComplexity.objects.create(transect=benthic_transect)
    observer = Observer.objects.create(transectmethod=habitat_complexity, profile=profile1)

    return observer


def test_habcomp_validator_ok(valid_habitat_complexity_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_habcomp_validator_data_invalid(valid_habitat_complexity_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["benthic_transect"]["number"] = None

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.INVALID_DATA


def test_habcomp_validator_duplicate_invalid(
    valid_habitat_complexity_collect_record, existing_benthic_transect
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.DUPLICATE_BENTHIC_TRANSECT


def _result_codes(runner):
    codes = []

    def _walk(node):
        if isinstance(node, dict):
            if "code" in node and "status" in node:
                codes.append(node["code"])
                return
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(runner.to_dict()["results"])
    return codes


def _validate_habcomp(collect_record, request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    runner.validate(collect_record, habitat_complexity.habcomp_validations, request=request)
    return _result_codes(runner)


def test_habcomp_interval_size_zero_no_duplicates(
    valid_habitat_complexity_collect_record,
    habitat_complexity_score2,
    habitat_complexity_score3,
    profile1_request,
):
    record = valid_habitat_complexity_collect_record
    record.data["interval_size"] = 0
    observations = record.data["obs_habitat_complexities"][:3]
    for obs in observations:
        obs["interval"] = 5
    observations[1]["score"] = str(habitat_complexity_score2.id)
    observations[2]["score"] = str(habitat_complexity_score3.id)
    record.data["obs_habitat_complexities"] = observations
    record.save()

    codes = _validate_habcomp(record, profile1_request)
    assert IntervalSizeValidator.INVALID_INTERVAL_SIZE in codes
    assert DuplicateValidator.DUPLICATE_VALUES not in codes


def test_habcomp_identical_rows_duplicate(
    valid_habitat_complexity_collect_record, profile1_request
):
    record = valid_habitat_complexity_collect_record
    observations = record.data["obs_habitat_complexities"]
    observations[1]["interval"] = observations[0]["interval"]
    record.save()

    codes = _validate_habcomp(record, profile1_request)
    assert DuplicateValidator.DUPLICATE_VALUES in codes
