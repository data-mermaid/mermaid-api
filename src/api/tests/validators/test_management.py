from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, WARN, ERROR, UniqueManagementValidator


def _get_validator():
    return UniqueManagementValidator(
        management_path="data.sample_event.management",
    )


def test_management_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_management_validator_invalid_not_found(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["sample_event"]["management"] = ""
    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueManagementValidator.MANAGEMENT_NOT_FOUND


def test_management_validator_invalid_not_unique_site(project1, management1, valid_collect_record, valid_benthic_lit_collect_record):
    validator = _get_validator()

    management1.id = None
    management1.save()
    valid_collect_record.data["sample_event"]["management"] = str(management1.pk)
    valid_collect_record.save()

    record = CollectRecordSerializer(instance=valid_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == UniqueManagementValidator.NOT_UNIQUE


def test_management_validator_invalid_not_unique_name(project1, management1, site1, valid_collect_record, valid_benthic_lit_collect_record):
    validator = _get_validator()

    management1.id = None
    management1.name = management1.name.replace(" ", "-")
    management1.save()

    site1.id = None
    site1.save()

    valid_collect_record.data["sample_event"]["management"] = str(management1.pk)
    valid_collect_record.data["sample_event"]["site"] = str(site1.pk)
    valid_collect_record.save()

    record = CollectRecordSerializer(instance=valid_collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == UniqueManagementValidator.SIMILAR_NAME