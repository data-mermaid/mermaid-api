from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    AllAttributesSameCategoryValidator,
    BenthicPITObservationCountValidator,
    ERROR,
    OK,
    WARN,
)


def _get_validator():
    return BenthicPITObservationCountValidator(
        len_surveyed_path="data.benthic_transect.len_surveyed",
        interval_size_path="data.interval_size",
        obs_benthicpits_path="data.obs_benthic_pits",
    )


def test_benthicpit_attributes_differentcats(valid_benthic_pit_collect_record):
    validator = AllAttributesSameCategoryValidator(
        obs_benthicpits_path="data.obs_benthic_pits"
    )
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_attributes_allsamecat(
    valid_benthic_pit_collect_record, benthic_attribute_2
):
    validator = AllAttributesSameCategoryValidator(
        obs_benthicpits_path="data.obs_benthic_pits"
    )
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    observations = [
        dict(attribute=str(benthic_attribute_2.id), interval=5),
        dict(attribute=str(benthic_attribute_2.id), interval=10),
    ]
    record["data"]["obs_benthic_pits"] = observations

    result = validator(record)
    assert result.status == WARN
    assert result.code == AllAttributesSameCategoryValidator.ALL_SAME_CATEGORY


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
    assert result.code == BenthicPITObservationCountValidator.NON_POSITIVE.format(
        "interval_size"
    )


def test_benthicpit_observation_count_invalid(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"] = record["data"]["obs_benthic_pits"][0:4]

    result = validator(record)
    assert result.status == ERROR
    assert (
        result.code == BenthicPITObservationCountValidator.INCORRECT_OBSERVATION_COUNT
    )


def test_benthicpit_observation_count_valid_plusone(
    valid_benthic_pit_collect_record, benthic_attribute_4
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    additional_obs = dict(attribute=str(benthic_attribute_4.id), interval=35)
    record["data"]["obs_benthic_pits"].append(additional_obs)

    result = validator(record)
    assert result.status == OK
