from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    ERROR,
    OK,
    BenthicIntervalObservationCountValidator,
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
