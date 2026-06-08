from datetime import timedelta

import pytest

from api.models import BenthicPIT, BenthicTransect, CollectRecord
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import OK, WARN
from api.submission.validations.validators import SimilarDateSampleUnitsValidator


def _get_validator():
    return SimilarDateSampleUnitsValidator(
        protocol_path="data.protocol",
        site_path="data.sample_event.site",
        management_path="data.sample_event.management",
        sample_date_path="data.sample_event.sample_date",
    )


@pytest.fixture
def existing_benthic_pit(sample_event1):
    benthic_transect = BenthicTransect.objects.create(
        sample_event=sample_event1, depth=5, number=1, len_surveyed=30
    )
    return BenthicPIT.objects.create(transect=benthic_transect, interval_size=5, interval_start=5)


def _create_collect_record(
    project,
    profile,
    benthic_attribute,
    management,
    site,
    sample_date,
):
    """Helper to create a benthic PIT collect record with given parameters"""
    observations = [
        dict(attribute=str(benthic_attribute.id), interval=5),
        dict(attribute=str(benthic_attribute.id), interval=10),
    ]
    data = dict(
        protocol="benthicpit",
        obs_benthic_pits=observations,
        benthic_transect=dict(depth=1, number=2, len_surveyed=30),
        interval_size=5,
        interval_start=5,
        sample_event=dict(
            management=str(management.id),
            site=str(site.id),
            sample_date=f"{sample_date:%Y-%m-%d}",
        ),
        observers=[{"profile": str(profile.id)}],
    )
    return CollectRecord.objects.create(
        project=project,
        profile=profile,
        stage=CollectRecord.VALIDATED_STAGE,
        data=data,
    )


def test_similar_date_sample_unit_no_similar(valid_benthic_pit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_benthic_pit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_similar_date_sample_unit_within_threshold(
    existing_benthic_pit,
    benthic_attribute_3,
    project1,
    profile1,
    management1,
    site1,
    sample_date1,
):
    similar_date = sample_date1 + timedelta(days=2)
    collect_record = _create_collect_record(
        project1, profile1, benthic_attribute_3, management1, site1, similar_date
    )

    validator = _get_validator()
    record = CollectRecordSerializer(instance=collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == SimilarDateSampleUnitsValidator.SIMILAR_DATE_SAMPLE_UNIT
    assert "days_difference" in result.context
    assert result.context["days_difference"] == 2


def test_similar_date_sample_unit_same_day(
    existing_benthic_pit,
    benthic_attribute_3,
    project1,
    profile1,
    management1,
    site1,
    sample_date1,
):
    collect_record = _create_collect_record(
        project1, profile1, benthic_attribute_3, management1, site1, sample_date1
    )

    validator = _get_validator()
    record = CollectRecordSerializer(instance=collect_record).data

    result = validator(record)
    # Same day should NOT trigger warning (duplicate validation handles this case)
    assert result.status == OK


def test_similar_date_sample_unit_outside_threshold(
    existing_benthic_pit,
    benthic_attribute_3,
    project1,
    profile1,
    management1,
    site1,
    sample_date1,
):
    different_date = sample_date1 + timedelta(days=31)
    collect_record = _create_collect_record(
        project1, profile1, benthic_attribute_3, management1, site1, different_date
    )

    validator = _get_validator()
    record = CollectRecordSerializer(instance=collect_record).data

    result = validator(record)
    assert result.status == OK


def test_similar_date_sample_unit_exactly_1_day(
    existing_benthic_pit,
    benthic_attribute_3,
    project1,
    profile1,
    management1,
    site1,
    sample_date1,
):
    similar_date = sample_date1 + timedelta(days=1)
    collect_record = _create_collect_record(
        project1, profile1, benthic_attribute_3, management1, site1, similar_date
    )

    validator = _get_validator()
    record = CollectRecordSerializer(instance=collect_record).data

    result = validator(record)
    assert result.status == WARN
    assert result.code == SimilarDateSampleUnitsValidator.SIMILAR_DATE_SAMPLE_UNIT
    assert result.context["days_difference"] == 1


def test_similar_date_sample_unit_different_site(
    existing_benthic_pit,
    benthic_attribute_3,
    project1,
    profile1,
    management1,
    site1,
    site2,
    sample_date1,
):
    similar_date = sample_date1 + timedelta(days=2)
    collect_record = _create_collect_record(
        project1, profile1, benthic_attribute_3, management1, site2, similar_date
    )

    validator = _get_validator()
    record = CollectRecordSerializer(instance=collect_record).data

    result = validator(record)
    assert result.status == OK
