from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import (
    AllAttributesSameCategoryValidator,
    BenthicIntervalObservationCountValidator,
    IntervalAlignmentValidator,
    IntervalSequenceValidator,
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


def _get_interval_sequence_validator():
    return IntervalSequenceValidator(
        len_surveyed_path="data.benthic_transect.len_surveyed",
        interval_size_path="data.interval_size",
        interval_start_path="data.interval_start",
        observations_path="data.obs_benthic_pits",
        observation_interval_path="interval",
    )


def test_benthicpit_interval_sequence_valid(valid_benthic_pit_collect_record):
    validator = _get_interval_sequence_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_interval_sequence_floating_point_precision(valid_benthic_pit_collect_record):
    """
    Regression test for floating-point accumulation bug.
    With 10m transect, 0.1m intervals, and 100 observations starting at 0.1,
    this should NOT report missing intervals like "9.999999999998".
    """
    validator = _get_interval_sequence_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    # Set up: 10m transect, 0.1m intervals, starting at 0.1
    record["data"]["benthic_transect"]["len_surveyed"] = 10
    record["data"]["interval_size"] = 0.1
    record["data"]["interval_start"] = 0.1

    # Create 100 observations at 0.1, 0.2, 0.3, ..., 10.0
    observations = []
    for i in range(1, 101):
        observations.append({"interval": round(i * 0.1, 1), "attribute": "test"})
    record["data"]["obs_benthic_pits"] = observations

    result = validator(record)
    assert (
        result.status == OK
    ), f"Expected OK but got {result.status} with context: {result.context}"


def test_benthicpit_interval_sequence_missing_intervals(valid_benthic_pit_collect_record):
    validator = _get_interval_sequence_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"][0]["interval"] = 100
    record["data"]["obs_benthic_pits"][1]["interval"] = 200

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalSequenceValidator.MISSING_INTERVALS
    assert "missing_intervals" in result.context


def _get_interval_alignment_validator():
    return IntervalAlignmentValidator(
        interval_size_path="data.interval_size",
        interval_start_path="data.interval_start",
        observations_path="data.obs_benthic_pits",
        observation_interval_path="interval",
    )


def test_benthicpit_interval_alignment_valid(valid_benthic_pit_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_interval_alignment_misaligned_interval(valid_benthic_pit_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"][0]["interval"] = 7.3

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalAlignmentValidator.INVALID_INTERVALS
    assert "invalid_intervals" in result.context
    assert 7.3 in result.context["invalid_intervals"]


def test_benthicpit_interval_alignment_before_start(valid_benthic_pit_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"][0]["interval"] = 2

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalAlignmentValidator.INVALID_INTERVALS
    assert "invalid_intervals" in result.context
    assert 2 in result.context["invalid_intervals"]


def test_benthicpit_interval_alignment_multiple_invalid(valid_benthic_pit_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["obs_benthic_pits"][0]["interval"] = 7.3
    record["data"]["obs_benthic_pits"][1]["interval"] = 12.5
    record["data"]["obs_benthic_pits"][2]["interval"] = 2

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalAlignmentValidator.INVALID_INTERVALS
    assert "invalid_intervals" in result.context
    assert len(result.context["invalid_intervals"]) == 3
