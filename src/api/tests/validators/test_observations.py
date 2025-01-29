from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import OK, WARN
from api.submission.validations.validators import ObservationCountValidator


def _get_validator():
    return ObservationCountValidator(observations_path="data.obs_belt_fishes")


def test_observation_count_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_observation_count_invalid_min(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["obs_belt_fishes"] = record["data"]["obs_belt_fishes"][0:3]
    result = validator(record)
    assert result.status == WARN
    assert result.code == ObservationCountValidator.TOO_FEW_OBS


def test_observation_count_invalid_max(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    for _ in range(201):
        record["data"]["obs_belt_fishes"] += record["data"]["obs_belt_fishes"][0]
    result = validator(record)
    assert result.status == WARN
    assert result.code == ObservationCountValidator.TOO_MANY_OBS
