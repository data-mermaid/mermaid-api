from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    ERROR,
    OK,
    WARN,
    BleachingPercentValidator,
)


def _get_validator():
    return BleachingPercentValidator(
        obs_quadrat_benthic_percent_path="data.obs_quadrat_benthic_percent",
        observation_percent_paths=[
            "percent_hard",
            "percent_soft",
            "percent_algae",
        ],
    )


def test_bleaching_percent_validator_ok(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_bleaching_percent_validator_invalid(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data

    record["data"]["obs_quadrat_benthic_percent"][0]["percent_hard"] = -101
    results = validator(record)

    assert results[0].status == ERROR
    assert results[0].code == BleachingPercentValidator.INVALID_PERCENT

    record["data"]["obs_quadrat_benthic_percent"][0]["percent_hard"] = 101
    results = validator(record)

    assert results[0].status == ERROR
    assert results[0].code == BleachingPercentValidator.INVALID_TOTAL_PERCENT

    record["data"]["obs_quadrat_benthic_percent"][0]["percent_hard"] = ""
    results = validator(record)

    assert results[0].status == WARN
    assert results[0].code == BleachingPercentValidator.VALUE_NOT_SET
