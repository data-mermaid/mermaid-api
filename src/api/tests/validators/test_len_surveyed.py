from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import LenSurveyedValidator


def _get_validator():
    return LenSurveyedValidator(
        len_surveyed_path="data.fishbelt_transect.len_surveyed",
    )


def test_len_surveyed_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_len_surveyed_validator_invalid_low(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["len_surveyed"] = 9
    result = validator(record)
    assert result.status == WARN
    assert result.code == LenSurveyedValidator.LEN_SURVEYED_OUT_OF_RANGE


def test_len_surveyed_validator_invalid_high(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["len_surveyed"] = 101
    result = validator(record)
    assert result.status == WARN
    assert result.code == LenSurveyedValidator.LEN_SURVEYED_OUT_OF_RANGE


def test_len_surveyed_validator_invalid_null(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["len_surveyed"] = None
    result = validator(record)
    assert result.status == ERROR


def test_len_surveyed_validator_invalid_empty_str(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["len_surveyed"] = ""
    result = validator(record)
    assert result.status == ERROR
