import pytest

from api.models import (
    BLEACHING_STATUS_NORMAL,
    BLEACHING_STATUS_PALE,
    SUPERUSER_APPROVED,
    BenthicAttribute,
)
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import (
    BleachingStatusMissingValidator,
    BleachingStatusValidator,
    IncludeBleachingValidator,
)

OBS_PATHS = [
    ("valid_benthic_lit_collect_record", "obs_benthic_lits"),
    ("valid_benthic_pit_collect_record", "obs_benthic_pits"),
]


@pytest.fixture
def soft_coral(db):
    return BenthicAttribute.objects.create(status=SUPERUSER_APPROVED, name="Soft coral")


def _record(request, fixture_name):
    return CollectRecordSerializer(request.getfixturevalue(fixture_name)).data


def _status_validator(obs_key):
    return BleachingStatusValidator(
        include_bleaching_path="data.include_bleaching",
        observations_path=f"data.{obs_key}",
    )


def _missing_validator(obs_key):
    return BleachingStatusMissingValidator(
        include_bleaching_path="data.include_bleaching",
        observations_path=f"data.{obs_key}",
    )


def _set_coral(record, obs_key, *attributes):
    for ob, attribute in zip(record["data"][obs_key], attributes):
        ob["attribute"] = str(attribute.id)


def test_include_bleaching_not_provided(valid_benthic_lit_collect_record):
    validator = IncludeBleachingValidator(include_bleaching_path="data.include_bleaching")
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    record["data"].pop("include_bleaching", None)

    assert validator(record).status == OK


@pytest.mark.parametrize("value", [None, ""])
def test_include_bleaching_not_answered(valid_benthic_lit_collect_record, value):
    validator = IncludeBleachingValidator(include_bleaching_path="data.include_bleaching")
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    record["data"]["include_bleaching"] = value

    result = validator(record)
    assert result.status == ERROR
    assert result.code == IncludeBleachingValidator.REQUIRED


@pytest.mark.parametrize("value", [True, False])
def test_include_bleaching_answered(valid_benthic_lit_collect_record, value):
    validator = IncludeBleachingValidator(include_bleaching_path="data.include_bleaching")
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    record["data"]["include_bleaching"] = value

    assert validator(record).status == OK


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
@pytest.mark.parametrize("include_bleaching", [False, None])
def test_status_not_assessed(request, fixture_name, obs_key, include_bleaching):
    record = _record(request, fixture_name)
    if include_bleaching is None:
        record["data"].pop("include_bleaching", None)
    else:
        record["data"]["include_bleaching"] = include_bleaching
    record["data"][obs_key][0]["bleaching_status"] = BLEACHING_STATUS_PALE

    results = _status_validator(obs_key)(record)
    assert results[0].status == ERROR
    assert results[0].code == BleachingStatusValidator.NOT_ASSESSED
    assert all(r.status == OK for r in results[1:])
    assert _missing_validator(obs_key)(record).status == OK


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
def test_not_assessed_no_statuses(request, fixture_name, obs_key, benthic_attribute_2):
    record = _record(request, fixture_name)
    record["data"]["include_bleaching"] = False
    _set_coral(record, obs_key, benthic_attribute_2)

    assert all(r.status == OK for r in _status_validator(obs_key)(record))
    assert _missing_validator(obs_key)(record).status == OK


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
def test_missing_coral_status_warns_once(
    request, fixture_name, obs_key, benthic_attribute_2a, soft_coral
):
    record = _record(request, fixture_name)
    record["data"]["include_bleaching"] = True
    # Child of Hard coral, to check the category resolves through parents
    _set_coral(record, obs_key, benthic_attribute_2a, soft_coral, benthic_attribute_2a)
    record["data"][obs_key][2]["bleaching_status"] = BLEACHING_STATUS_PALE

    assert all(r.status == OK for r in _status_validator(obs_key)(record))
    result = _missing_validator(obs_key)(record)
    assert result.status == WARN
    assert result.code == BleachingStatusMissingValidator.MISSING_BLEACHING_STATUS
    assert result.context == {"count": 2}


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
@pytest.mark.parametrize("status", [BLEACHING_STATUS_NORMAL, 1, 2, 3, 4, "0", "4"])
def test_coral_status_set(request, fixture_name, obs_key, benthic_attribute_2, status):
    record = _record(request, fixture_name)
    record["data"]["include_bleaching"] = True
    _set_coral(record, obs_key, benthic_attribute_2)
    record["data"][obs_key][0]["bleaching_status"] = status

    assert all(r.status == OK for r in _status_validator(obs_key)(record))
    assert _missing_validator(obs_key)(record).status == OK


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
def test_non_coral_status(request, fixture_name, obs_key):
    record = _record(request, fixture_name)
    record["data"]["include_bleaching"] = True
    observation_id = record["data"][obs_key][0].get("id")
    record["data"][obs_key][0]["bleaching_status"] = BLEACHING_STATUS_PALE

    results = _status_validator(obs_key)(record)
    assert results[0].status == ERROR
    assert results[0].code == BleachingStatusValidator.NOT_CORAL
    assert results[0].context["observation_id"] == observation_id
    assert all(r.status == OK for r in results[1:])


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
def test_no_coral_rows(request, fixture_name, obs_key):
    record = _record(request, fixture_name)
    record["data"]["include_bleaching"] = True

    assert all(r.status == OK for r in _status_validator(obs_key)(record))
    assert _missing_validator(obs_key)(record).status == OK


@pytest.mark.parametrize("fixture_name,obs_key", OBS_PATHS)
@pytest.mark.parametrize("status", [5, -1, 1.5, "pale", True])
def test_invalid_status(request, fixture_name, obs_key, benthic_attribute_2, status):
    record = _record(request, fixture_name)
    record["data"]["include_bleaching"] = True
    _set_coral(record, obs_key, benthic_attribute_2)
    record["data"][obs_key][0]["bleaching_status"] = status

    results = _status_validator(obs_key)(record)
    assert results[0].status == ERROR
    assert results[0].code == BleachingStatusValidator.INVALID_STATUS
    assert results[0].context["bleaching_status"] == status
