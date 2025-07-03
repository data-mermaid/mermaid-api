from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import (
    FishCountValidator,
    TotalFishCountValidator,
)


def _get_fish_count_validator():
    return FishCountValidator(
        observations_path="data.obs_belt_fishes",
        observation_count_path="count",
    )


def _get_total_fish_count_validator():
    return TotalFishCountValidator(
        observations_path="data.obs_belt_fishes",
        observation_count_path="count",
    )


def test_fish_count_validator_ok(valid_collect_record):
    validator = _get_fish_count_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_fish_count_validator_invalid(valid_collect_record):
    validator = _get_fish_count_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["count"] = None
    record["data"]["obs_belt_fishes"][1]["count"] = ""
    record["data"]["obs_belt_fishes"][2]["count"] = -1

    results = validator(record)
    for result in results[0:3]:
        assert result.status == ERROR
        assert result.code == FishCountValidator.INVALID_FISH_COUNT


def test_total_fish_count_validator_ok(valid_collect_record):
    validator = _get_total_fish_count_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_total_fish_count_validator_invalid(valid_collect_record):
    validator = _get_total_fish_count_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    for ob in record["data"]["obs_belt_fishes"]:
        ob["count"] = 0.0

    result = validator(record)
    assert result.status == WARN
    assert result.code == TotalFishCountValidator.MIN_TOTAL_FISH_COUNT
