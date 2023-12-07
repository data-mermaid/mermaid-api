from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, WARN, ColonyCountValidator


def _get_validator():
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


def test_colony_count_validator_ok(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_colony_count_validator_data_invalid(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data

    record["data"]["obs_colonies_bleached"][0]["count_20"] = 601
    result = validator(record)

    assert result.status == WARN
    assert result.code == ColonyCountValidator.EXCEED_TOTAL_COLONIES
