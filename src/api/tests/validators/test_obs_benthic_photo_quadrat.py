from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    OK,
    WARN,
    PointsPerQuadratValidator,
    QuadratCountValidator
)

def test_num_of_pnts_per_quadrat_valid():
    assert False


def test_num_of_pnts_per_quadrat_invalid():
    assert False


def test_number_of_quadrats_valid(valid_benthic_pq_transect_collect_record):
    validator = QuadratCountValidator(
        num_quadrats_path="data.quadrat_transect.num_quadrats",
        obs_benthic_photo_quadrats_path="data.quadrat_transect.obs_benthic_photo_quadrats",
        observation_quadrat_number_path="quadrat_number",
    )
    record = CollectRecordSerializer(instance=valid_benthic_pq_transect_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_number_of_quadrats_invalid():
    assert False
