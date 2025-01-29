import pytest

from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import (
    PointsPerQuadratValidator,
    QuadratCountValidator,
    QuadratNumberSequenceValidator,
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
        quadrat_number_start_path="data.quadrat_transect.quadrat_number_start",
    )


@pytest.fixture
def points_per_quadrat_validator():
    return PointsPerQuadratValidator(
        num_points_per_quadrat_path="data.quadrat_transect.num_points_per_quadrat",
        obs_benthic_photo_quadrats_path="data.obs_benthic_photo_quadrats",
        observation_quadrat_number_path="quadrat_number",
        observation_num_points_path="num_points",
    )


def test_num_of_pnts_per_quadrat_valid(
    points_per_quadrat_validator, valid_benthic_pq_transect_collect_record
):
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = points_per_quadrat_validator(record)
    assert result.status == OK


def test_num_of_pnts_per_quadrat_invalid(
    points_per_quadrat_validator, valid_benthic_pq_transect_collect_record
):
    valid_benthic_pq_transect_collect_record.data["obs_benthic_photo_quadrats"][0][
        "num_points"
    ] = 10
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = points_per_quadrat_validator(record)
    assert result.status == WARN


def test_number_of_quadrats_valid(
    quadrat_count_validator, valid_benthic_pq_transect_collect_record
):
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_count_validator(record)
    assert result.status == OK


def test_number_of_quadrats_invalid(
    quadrat_count_validator, valid_benthic_pq_transect_collect_record
):
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 10

    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_count_validator(record)
    assert result.status == WARN


def test_quadrat_number_sequence_valid(
    quadrat_number_sequence_validator, valid_benthic_pq_transect_collect_record
):
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_number_sequence_validator(record)
    assert result.status == OK


def test_quadrat_number_sequence_invalid(
    quadrat_number_sequence_validator, valid_benthic_pq_transect_collect_record
):
    valid_benthic_pq_transect_collect_record.data["obs_benthic_photo_quadrats"][0][
        "quadrat_number"
    ] = 1000
    valid_benthic_pq_transect_collect_record.data["obs_benthic_photo_quadrats"][1][
        "quadrat_number"
    ] = 1000

    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_number_sequence_validator(record)
    assert result.status == WARN


def test_number_of_quadrats_toolarge(
    quadrat_number_sequence_validator, valid_benthic_pq_transect_collect_record
):
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 100000

    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = quadrat_number_sequence_validator(record)
    assert result.status == ERROR
