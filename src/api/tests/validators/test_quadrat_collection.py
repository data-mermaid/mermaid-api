from api.models import QuadratCollection
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, ERROR, QuadratCollectionValidator


def _get_validator():
    return QuadratCollectionValidator(
        protocol_path="data.protocol",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        label_path="data.quadrat_collection.label",
        depth_path="data.quadrat_collection.depth",
    )


def test_quadrat_collection_validator_ok(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_quadrat_collection_validator_data_invalid(
    valid_bleaching_qc_collect_record
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    
    record["data"]["quadrat_collection"]["depth"] = None
    result = validator(record)

    assert result.status == ERROR
    assert result.code == QuadratCollectionValidator.INVALID_DATA


def test_quadrat_collection_validator_duplicate_invalid(
    valid_bleaching_qc_collect_record,
    bleaching_quadrat_collection1
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data

    result = validator(record)
    assert result.status == ERROR
    assert result.code == QuadratCollectionValidator.DUPLICATE_QUADRAT_COLLECTION
