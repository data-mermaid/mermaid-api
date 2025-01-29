from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import (
    BleachingObsValidator,
    ColonyCountValidator,
)


def _get_count_validator():
    return ColonyCountValidator(
        obs_colonies_bleached_path="data.obs_colonies_bleached",
        observation_count_normal_path="count_normal",
        observation_count_pale_path="count_pale",
        observation_count_20_path="count_20",
        observation_count_50_path="count_50",
        observation_count_80_path="count_80",
        observation_count_100_path="count_100",
        observation_count_dead_path="count_dead",
    )


def _get_values_validator():
    return BleachingObsValidator(
        obs_path="data.obs_colonies_bleached",
        observation_field_paths=[
            "count_normal",
            "count_pale",
            "count_20",
            "count_50",
            "count_80",
            "count_100",
            "count_dead",
        ],
    )


def test_colony_count_validator_ok(valid_bleaching_qc_collect_record):
    validator = _get_count_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_colony_count_validator_data_invalid(valid_bleaching_qc_collect_record):
    validator = _get_count_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data

    record["data"]["obs_colonies_bleached"][0]["count_20"] = 601
    result = validator(record)
    assert result.status == WARN
    assert result.code == ColonyCountValidator.EXCEED_TOTAL_COLONIES


def test_colony_values_validator_ok(valid_bleaching_qc_collect_record):
    validator = _get_values_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    results = validator(record)
    assert results[0].status == OK


def test_colony_values_validator_blanks(valid_bleaching_qc_collect_record):
    validator = _get_values_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data

    record["data"]["obs_colonies_bleached"][0]["count_pale"] = 1001
    results = validator(record)
    assert results[0].status == ERROR
    assert results[0].code == BleachingObsValidator.INVALID_TOTAL

    record["data"]["obs_colonies_bleached"][0]["count_pale"] = None
    record["data"]["obs_colonies_bleached"][0]["count_80"] = None
    results = validator(record)
    assert results[0].status == ERROR
    assert results[0].context["invalid_paths"] == ["count_pale", "count_80"]
