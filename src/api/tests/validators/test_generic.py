from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    ERROR,
    OK,
    WARN,
    AllEqualValidator,
    DuplicateValidator,
    ListPositiveIntegerValidator,
    ListRequiredValidator,
    PositiveIntegerValidator,
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


def test_duplicate_validator_ok(valid_bleaching_qc_collect_record):
    validator = DuplicateValidator(
        list_path="data.obs_quadrat_benthic_percent",
        key_paths=["quadrat_number"],
    )
    record = CollectRecordSerializer(instance=valid_bleaching_qc_collect_record).data
    result = validator(record)
    assert result.status == OK

    validator = DuplicateValidator(
        list_path="data.obs_colonies_bleached",
        key_paths=["attribute", "growth_form"],
    )
    record = CollectRecordSerializer(instance=valid_bleaching_qc_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_duplicate_validator_invalid(valid_bleaching_qc_collect_record):
    record = valid_bleaching_qc_collect_record

    validator = DuplicateValidator(
        list_path="data.obs_quadrat_benthic_percent",
        key_paths=["quadrat_number"],
    )
    record.data["obs_quadrat_benthic_percent"][0]["quadrat_number"] = 1
    record.data["obs_quadrat_benthic_percent"][1]["quadrat_number"] = 1
    result = validator(CollectRecordSerializer(instance=record).data)

    assert result.status == ERROR
    assert result.code == DuplicateValidator.DUPLICATE_VALUES

    validator = DuplicateValidator(
        list_path="data.obs_colonies_bleached",
        key_paths=["attribute", "growth_form"],
    )

    obs_colonies_bleached = record.data["obs_colonies_bleached"][0]
    record.data["obs_colonies_bleached"][1]["attribute"] = obs_colonies_bleached["attribute"]
    record.data["obs_colonies_bleached"][1]["growth_form"] = obs_colonies_bleached["growth_form"]
    result = validator(CollectRecordSerializer(instance=record).data)

    assert result.status == ERROR
    assert result.code == DuplicateValidator.DUPLICATE_VALUES


def test_list_positive_integer_validator_ok(valid_bleaching_qc_collect_record):
    validator = ListPositiveIntegerValidator(
        list_path="data.obs_quadrat_benthic_percent",
        key_path="quadrat_number",
    )
    record = CollectRecordSerializer(instance=valid_bleaching_qc_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_list_positive_integer_validator_invalid(valid_bleaching_qc_collect_record):
    validator = ListPositiveIntegerValidator(
        list_path="data.obs_quadrat_benthic_percent",
        key_path="quadrat_number",
    )
    record = CollectRecordSerializer(instance=valid_bleaching_qc_collect_record).data

    record["data"]["obs_quadrat_benthic_percent"][0]["quadrat_number"] = None

    results = validator(record)
    results[0].status = ERROR
    results[0].code = PositiveIntegerValidator.NOT_POSITIVE_INTEGER

    record["data"]["obs_quadrat_benthic_percent"][0]["quadrat_number"] = -1

    results = validator(record)
    results[0].status = ERROR
    results[0].code = PositiveIntegerValidator.NOT_POSITIVE_INTEGER
