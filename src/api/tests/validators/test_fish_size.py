from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, ERROR, WARN, FishSizeValidator


def _get_validator():
    return FishSizeValidator(
        observations_path="data.obs_belt_fishes",
        observation_fish_attribute_path="fish_attribute",
        observation_size_path="size",
    )


def test_fish_size_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_fish_count_validator_invalid(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["size"] = 20000

    results = validator(record)
    assert results[0].status == WARN
    assert results[0].code == FishSizeValidator.MAX_FISH_SIZE


def test_fish_count_validator_error(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["size"] = ""

    results = validator(record)
    assert results[0].status == ERROR
