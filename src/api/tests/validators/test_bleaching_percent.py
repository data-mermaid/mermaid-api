from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK
from api.submission.validations.validators import BleachingObsValidator


def _get_validator():
    return BleachingObsValidator(
        obs_path="data.obs_quadrat_benthic_percent",
        observation_field_paths=[
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
    assert results[0].code == BleachingObsValidator.INVALID_PERCENT

    record["data"]["obs_quadrat_benthic_percent"][0]["percent_hard"] = ""
    results = validator(record)
    assert results[0].status == ERROR
    assert results[0].code == BleachingObsValidator.INVALID_PERCENT

    record["data"]["obs_quadrat_benthic_percent"][0]["percent_hard"] = 101
    results = validator(record)
    assert results[0].status == ERROR
    assert results[0].code == BleachingObsValidator.INVALID_TOTAL
