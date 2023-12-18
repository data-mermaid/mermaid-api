from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    ERROR,
    OK,
    UniqueQuadratCollectionValidator,
)


def _get_validator():
    return UniqueQuadratCollectionValidator(
        protocol_path="data.protocol",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        label_path="data.quadrat_collection.label",
        depth_path="data.quadrat_collection.depth",
        observers_path="data.observers",
    )


def test_quadrat_collection_validator_ok(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_quadrat_collection_validator_data_invalid(valid_bleaching_qc_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data

    record["data"]["quadrat_collection"]["depth"] = None
    result = validator(record)

    assert result.status == ERROR
    assert result.code == UniqueQuadratCollectionValidator.INVALID_DATA


def test_quadrat_collection_validator_duplicate_invalid(
    valid_bleaching_qc_collect_record, observer_bleaching_quadrat_collection1
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_bleaching_qc_collect_record).data
    # valid_bleaching_qc_collect_record and observer_bleaching_quadrat_collection1
    # both have the same quadrat_collection properties, creating duplicate

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueQuadratCollectionValidator.DUPLICATE_QUADRAT_COLLECTION
