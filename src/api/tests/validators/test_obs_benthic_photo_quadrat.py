import pytest

from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    OK,
    WARN,
    PointsPerQuadratValidator,
    QuadratCountValidator,
    QuadratNumberSequenceValidator
)


@pytest.fixture
def quadrat_count_validator():
    return QuadratCountValidator(
        num_quadrats_path="data.quadrat_transect.num_quadrats",
        obs_benthic_photo_quadrats_path="data.obs_benthic_photo_quadrats",
        observation_quadrat_number_path="quadrat_number",
    )


@pytest.fixture
def quadrat_number_sequence_validator():
    return QuadratNumberSequenceValidator(
        num_quadrats_path="data.quadrat_transect.num_quadrats",
        obs_benthic_photo_quadrats_path="data.obs_benthic_photo_quadrats",
        observation_quadrat_number_path="quadrat_number",
    )


def test_num_of_pnts_per_quadrat_valid():
    assert False


def test_num_of_pnts_per_quadrat_invalid():
    assert False


def test_number_of_quadrats_valid(quadrat_count_validator, valid_benthic_pq_transect_collect_record):
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_count_validator(record)
    assert result.status == OK


def test_number_of_quadrats_invalid(quadrat_count_validator, valid_benthic_pq_transect_collect_record):
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 10

    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_count_validator(record)
    assert result.status == WARN


def test_quadrat_number_sequence_valid(quadrat_number_sequence_validator, valid_benthic_pq_transect_collect_record):
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_number_sequence_validator(record)
    assert result.status == OK


def test_quadrat_number_sequence_invalid(quadrat_number_sequence_validator, valid_benthic_pq_transect_collect_record):
    valid_benthic_pq_transect_collect_record.data["obs_benthic_photo_quadrats"][0]["quadrat_number"] = 1000

    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_number_sequence_validator(record)
    assert result.status == WARN
