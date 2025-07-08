import pytest

from api.models import BenthicTransect, HabitatComplexity, Observer
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
        sample_event=sample_event1, number=2, depth=1, len_surveyed=100
    )
    habitat_complexity = HabitatComplexity.objects.create(transect=benthic_transect)
    observer = Observer.objects.create(transectmethod=habitat_complexity, profile=profile1)

    return observer


def test_habcomp_validator_ok(valid_habitat_complexity_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_habcomp_validator_data_invalid(valid_habitat_complexity_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data
    record["data"]["benthic_transect"]["number"] = None

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.INVALID_DATA


def test_habcomp_validator_duplicate_invalid(
    valid_habitat_complexity_collect_record, existing_benthic_transect
):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_habitat_complexity_collect_record).data

    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueBenthicTransectValidator.DUPLICATE_BENTHIC_TRANSECT
