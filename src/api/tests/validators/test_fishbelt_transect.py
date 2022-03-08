from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, ERROR, UniqueFishbeltTransectValidator


def _get_validator():
    return UniqueFishbeltTransectValidator(
        protocol="fishbelt",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        label_path="data.fishbelt_transect.label",
        depth_path="data.fishbelt_transect.depth",
        number_path="data.fishbelt_transect.number",
        width_path="data.fishbelt_transect.width",
        observers_path="data.observers",
    )


def test_fishbelt_transect_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_collect_record).data
    result = validator(record)
    assert result.status == OK


def test_fishbelt_transect_validator_data_invalid(
    valid_collect_record
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_collect_record).data

    record["data"]["fishbelt_transect"]["depth"] = None
    result = validator(record)

    assert result.status == ERROR
    assert result.code == UniqueFishbeltTransectValidator.INVALID_DATA


def test_fishbelt_transect_validator_duplicate_invalid(
    valid_collect_record,
    observer_belt_fish1
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_collect_record).data

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueFishbeltTransectValidator.DUPLICATE_FISHBELT_TRANSECT
