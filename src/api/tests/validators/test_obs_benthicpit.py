from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    ERROR,
    OK,
    WARN,
    AllAttributesSameCategoryValidator,
    BenthicIntervalObservationCountValidator,
    ListRequiredValidator,
)


def _get_validator():
    return BenthicIntervalObservationCountValidator(
        len_surveyed_path="data.benthic_transect.len_surveyed",
        interval_size_path="data.interval_size",
        observations_path="data.obs_benthic_pits",
    )


def test_benthicpit_attributes_differentcats(valid_benthic_pit_collect_record):
    validator = AllAttributesSameCategoryValidator(obs_benthic_path="data.obs_benthic_pits")
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_attributes_allsamecat(valid_benthic_pit_collect_record, benthic_attribute_2):
    validator = AllAttributesSameCategoryValidator(obs_benthic_path="data.obs_benthic_pits")
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    observations = [
        dict(attribute=str(benthic_attribute_2.id), interval=5),
        dict(attribute=str(benthic_attribute_2.id), interval=10),
        dict(attribute=str(benthic_attribute_2.id), interval=15),
    ]
    record["data"]["obs_benthic_pits"] = observations

    result = validator(record)
    assert result.status == WARN
    assert result.code == AllAttributesSameCategoryValidator.ALL_SAME_CATEGORY

    record["data"]["obs_benthic_pits"][0]["attribute"] = ""
    record["data"]["obs_benthic_pits"][1]["attribute"] = ""
    result = validator(record)
    assert result.status == OK


def test_benthicpit_obs_required_fields(valid_benthic_pit_collect_record):
    validator = ListRequiredValidator(
        list_path="data.obs_benthic_pits",
        path="attribute",
        name_prefix="attribute",
        unique_identifier_label="observation_id",
    )
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"][0]["attribute"] = ""
    result = validator(record)
    assert result[0].status == ERROR
    assert result[0].code == ListRequiredValidator.REQUIRED


def test_benthicpit_observation_count_validator_ok(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_observation_count_invalid_data(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["interval_size"] = None

    result = validator(record)
    assert result.status == ERROR
    assert result.code == BenthicIntervalObservationCountValidator.NON_POSITIVE.format(
        "interval_size"
    )


def test_benthicpit_observation_count_invalid(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"] = record["data"]["obs_benthic_pits"][0:4]

    result = validator(record)
    assert result.status == ERROR
    assert result.code == BenthicIntervalObservationCountValidator.INCORRECT_OBSERVATION_COUNT


def test_benthicpit_observation_count_valid_plusone(
    valid_benthic_pit_collect_record, benthic_attribute_4
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    additional_obs = dict(attribute=str(benthic_attribute_4.id), interval=35)
    record["data"]["obs_benthic_pits"].append(additional_obs)

    result = validator(record)
    assert result.status == OK
