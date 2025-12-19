from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK
from api.submission.validations.validators import (
    BenthicIntervalObservationCountValidator,
    IntervalAlignmentValidator,
    IntervalSequenceValidator,
    ListRequiredValidator,
    ListScoreValidator,
)


def _get_validator():
    return BenthicIntervalObservationCountValidator(
        len_surveyed_path="data.benthic_transect.len_surveyed",
        interval_size_path="data.interval_size",
        observations_path="data.obs_habitat_complexities",
    )


def test_habcomp_observation_count_validator_ok(
    valid_habitat_complexity_collect_record,
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_habcomp_observation_count_invalid(valid_habitat_complexity_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"] = record["data"]["obs_habitat_complexities"][0:4]

    result = validator(record)
    assert result.status == ERROR
    assert result.code == BenthicIntervalObservationCountValidator.INCORRECT_OBSERVATION_COUNT


def test_habcomp_missing_score(valid_habitat_complexity_collect_record):
    validator = ListRequiredValidator(
        list_path="data.obs_habitat_complexities",
        path="score",
        name_prefix="score",
        unique_identifier_label="observation_id",
    )
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"][0]["score"] = ""

    result = validator(record)
    assert result[0].status == ERROR
    assert result[0].code == ListRequiredValidator.REQUIRED


def test_habcomp_invalid_score(valid_habitat_complexity_collect_record):
    validator = ListScoreValidator(
        observations_path="data.obs_habitat_complexities",
        score_path="score",
        name_prefix="score",
        unique_identifier_label="observation_id",
    )
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"][1]["score"] = "9a291f1b-c00d-4d5f-9aff-da9f8adeb6bd"

    result = validator(record)
    assert result[1].status == ERROR
    assert result[1].code == ListScoreValidator.INVALID_SCORE


def _get_interval_sequence_validator():
    return IntervalSequenceValidator(
        len_surveyed_path="data.benthic_transect.len_surveyed",
        interval_size_path="data.interval_size",
        interval_start_path="data.interval_start",
        observations_path="data.obs_habitat_complexities",
        observation_interval_path="interval",
    )


def test_habcomp_interval_sequence_valid(valid_habitat_complexity_collect_record):
    validator = _get_interval_sequence_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_habcomp_interval_sequence_missing_intervals(valid_habitat_complexity_collect_record):
    validator = _get_interval_sequence_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"][0]["interval"] = 100
    record["data"]["obs_habitat_complexities"][1]["interval"] = 200

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalSequenceValidator.MISSING_INTERVALS
    assert "missing_intervals" in result.context


def _get_interval_alignment_validator():
    return IntervalAlignmentValidator(
        interval_size_path="data.interval_size",
        interval_start_path="data.interval_start",
        observations_path="data.obs_habitat_complexities",
        observation_interval_path="interval",
    )


def test_habcomp_interval_alignment_valid(valid_habitat_complexity_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_habcomp_interval_alignment_misaligned_interval(valid_habitat_complexity_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"][0]["interval"] = 7.3

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalAlignmentValidator.INVALID_INTERVALS
    assert "invalid_intervals" in result.context
    assert 7.3 in result.context["invalid_intervals"]


def test_habcomp_interval_alignment_before_start(valid_habitat_complexity_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"][0]["interval"] = -2

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalAlignmentValidator.INVALID_INTERVALS
    assert "invalid_intervals" in result.context
    assert -2 in result.context["invalid_intervals"]


def test_habcomp_interval_alignment_multiple_invalid(valid_habitat_complexity_collect_record):
    validator = _get_interval_alignment_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["obs_habitat_complexities"][0]["interval"] = 7.3
    record["data"]["obs_habitat_complexities"][1]["interval"] = 12.5
    record["data"]["obs_habitat_complexities"][2]["interval"] = -2

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IntervalAlignmentValidator.INVALID_INTERVALS
    assert "invalid_intervals" in result.context
    assert len(result.context["invalid_intervals"]) == 3
