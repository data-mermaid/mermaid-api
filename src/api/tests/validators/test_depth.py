from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, WARN, DepthValidator


def _get_validator():
    return DepthValidator(
        depth_path="data.fishbelt_transect.depth",
    )


def test_depth_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_depth_validator_invalid(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["depth"] = 0
    result = validator(record)
    assert result.status == WARN
    assert result.code == DepthValidator.INVALID_DEPTH

    record["data"]["fishbelt_transect"]["depth"] = ""
    result = validator(record)
    assert result.status == WARN
    assert result.code == DepthValidator.INVALID_DEPTH

    record["data"]["fishbelt_transect"]["depth"] = None
    result = validator(record)
    assert result.status == WARN
    assert result.code == DepthValidator.INVALID_DEPTH


def test_depth_validator_max_depth(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["depth"] = 100
    result = validator(record)
    assert result.status == WARN
    assert result.code == DepthValidator.EXCEED_MAX_DEPTH
