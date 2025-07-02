import pytest

from api.models import BenthicPIT, BenthicTransect, Observer
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK
from api.submission.validations.validators import UniqueBenthicTransectValidator


def _get_validator():
    return UniqueBenthicTransectValidator(
        protocol_path="data.protocol",
        label_path="data.benthic_transect.label",
        number_path="data.benthic_transect.number",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
        depth_path="data.benthic_transect.depth",
        observers_path="data.observers",
    )


@pytest.fixture()
def existing_benthic_transect(db, sample_event1, profile1):
    benthic_transect = BenthicTransect.objects.create(
        sample_event=sample_event1, number=1, depth=1, len_surveyed=30
    )
    benthicpit = BenthicPIT.objects.create(
        transect=benthic_transect, interval_size=5, interval_start=5
    )
    observer = Observer.objects.create(transectmethod=benthicpit, profile=profile1)

    return observer


def test_benthicpit_validator_ok(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthicpit_validator_data_invalid(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data
    record["data"]["benthic_transect"]["depth"] = None

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.INVALID_DATA


def test_benthicpit_validator_duplicate_invalid(
    valid_benthic_pit_collect_record, existing_benthic_transect
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.DUPLICATE_BENTHIC_TRANSECT
