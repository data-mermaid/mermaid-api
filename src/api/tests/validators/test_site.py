import uuid

import pytest
from django.contrib.gis.geos import Point

from api.models import Site
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, ERROR, WARN, UniqueSiteValidator


@pytest.fixture
def duplicate_site(project1, country1, reef_type1, reef_exposure1, reef_zone1):
    return Site.objects.create(
        project=project1,
        name="Site 1",
        location=Point(1, 1, srid=4326),
        country=country1,
        reef_type=reef_type1,
        exposure=reef_exposure1,
        reef_zone=reef_zone1,
    )


def _get_validator():
    return UniqueSiteValidator(
        site_path="data.sample_event.site",
    )


def test_site_not_found(valid_collect_record):
    valid_collect_record.data["sample_event"]["site"] = str(uuid.uuid4())
    valid_collect_record.save()

    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)
    assert result.status == ERROR
    assert result.code == UniqueSiteValidator.SITE_NOT_FOUND


def test_site_ok(valid_collect_record, duplicate_site):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)

    assert result.status == OK


def test_not_unique(valid_collect_record, duplicate_site, belt_fish2, sample_event2):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    result = validator(record)

    assert result.status == OK

    sample_event2.site = duplicate_site
    sample_event2.save()

    result = validator(record)
    assert result.status == WARN
    assert result.context["matches"][0] == str(duplicate_site.pk)
