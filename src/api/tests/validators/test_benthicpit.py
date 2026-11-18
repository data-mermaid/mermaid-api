import pytest

from api.models import BenthicPIT, BenthicTransect, Observer
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, ValidationRunner, benthic_pit
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
        sample_event=sample_event1, number=1, depth=1, len_surveyed=30
    )
    benthicpit = BenthicPIT.objects.create(
        transect=benthic_transect, interval_size=5, interval_start=5
    )
    observer = Observer.objects.create(transectmethod=benthicpit, profile=profile1)

    return observer


def test_benthicpit_validator_ok(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_validator_data_invalid(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["benthic_transect"]["depth"] = None

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.INVALID_DATA


def test_benthicpit_validator_duplicate_invalid(
    valid_benthic_pit_collect_record, existing_benthic_transect
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

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


def _validate_benthicpit(collect_record, request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    runner.validate(collect_record, benthic_pit.benthic_pit_validations, request=request)
    return _result_codes(runner)


def test_benthicpit_interval_size_zero_no_duplicates(
    valid_benthic_pit_collect_record, benthic_attribute_4, growth_form1, profile1_request
):
    record = valid_benthic_pit_collect_record
    record.data["interval_size"] = 0
    # Same interval on every row (as the webapp generates with size 0); rows differ otherwise
    observations = record.data["obs_benthic_pits"][:3]
    for obs in observations:
        obs["interval"] = 5
    observations[1]["attribute"] = str(benthic_attribute_4.id)
    observations[2]["growth_form"] = str(growth_form1.id)
    record.data["obs_benthic_pits"] = observations
    record.save()

    codes = _validate_benthicpit(record, profile1_request)
    assert IntervalSizeValidator.INVALID_INTERVAL_SIZE in codes
    assert DuplicateValidator.DUPLICATE_VALUES not in codes


def test_benthicpit_identical_rows_duplicate(
    valid_benthic_pit_collect_record, growth_form1, profile1_request
):
    record = valid_benthic_pit_collect_record
    observations = record.data["obs_benthic_pits"]
    observations[1]["interval"] = observations[0]["interval"]
    observations[0]["growth_form"] = str(growth_form1.id)
    observations[1]["growth_form"] = str(growth_form1.id)
    record.save()

    codes = _validate_benthicpit(record, profile1_request)
    assert DuplicateValidator.DUPLICATE_VALUES in codes
