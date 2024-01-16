from datetime import timedelta

from django.utils import timezone

from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import ERROR, OK, WARN, SampleDateValidator


def _get_validator():
    return SampleDateValidator(
        sample_date_path="data.sample_event.sample_date",
        sample_time_path="data.fishbelt_transect.sample_time",
        site_path="data.sample_event.site",
    )


def test_sample_date_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_sample_date_validator_invalid_sample_date(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["sample_event"]["sample_date"] = ""
    result = validator(record)
    assert result.status == ERROR
    assert result.code == SampleDateValidator.INVALID_SAMPLE_DATE


def test_sample_date_validator_future_date(valid_collect_record):
    validator = _get_validator()

    record = CollectRecordSerializer(instance=valid_collect_record).data
    future_date = timezone.now() + timedelta(days=10)
    record["data"]["sample_event"]["sample_date"] = f"{future_date:%Y-%m-%d}"
    result = validator(record)
    assert result.status == WARN
    assert result.code == SampleDateValidator.FUTURE_SAMPLE_DATE
