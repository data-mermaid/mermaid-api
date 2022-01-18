from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    ERROR,
    OK,
    WARN,
    AllEqualValidator,
    ListRequiredValidator,
    RequiredValidator,
)


def _get_validator():
    return RequiredValidator(
        path="data.sample_event.site",
    )


def _get_list_required_validator():
    return ListRequiredValidator(
        list_path="data.obs_belt_fishes",
        path="fish_attribute",
        name_prefix="fish_attribute",
    )


def _get_all_equal_validator():
    return AllEqualValidator(
        path="data.obs_belt_fishes",
        ignore_keys=["id"]
    )


def test_required_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_required_validator_invalid(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["sample_event"]["site"] = ""

    result = validator(record)
    assert result.status == ERROR


def test_list_required_validator_ok(valid_collect_record):
    validator = _get_list_required_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_list_required_validator_invalid(valid_collect_record):
    validator = _get_list_required_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][1]["fish_attribute"] = ""
    record["data"]["obs_belt_fishes"][2]["fish_attribute"] = None

    results = validator(record)

    assert results[1].status == ERROR
    assert results[1].code == ListRequiredValidator.REQUIRED
    assert results[2].status == ERROR
    assert results[2].code == ListRequiredValidator.REQUIRED


def test_all_equal_validator_ok(valid_collect_record):
    validator = _get_all_equal_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_required_validator_invalid(valid_collect_record):
    validator = _get_all_equal_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    for obs in record["data"]["obs_belt_fishes"]:
        obs["fish_attribute"] = "1"
        obs["count"] = "1"
        obs["size"] = "1"

    result = validator(record)
    assert result.status == WARN
