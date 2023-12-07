import pytest

from api.submission.validations2.validators import ERROR, OK, QuadratSizeValidator


@pytest.fixture
def base_collect_record():
    return {"protocol": "bleachingqc", "data": {"quadrat_collection": {"quadrat_size": 1}}}


def _get_validator():
    return QuadratSizeValidator(
        quadrat_size_path="data.quadrat_collection.quadrat_size",
    )


def test_quadrat_size_validator_ok(base_collect_record):
    validator = _get_validator()
    result = validator(base_collect_record)
    assert result.status == OK


def test_quadrat_size_validator_invalid(base_collect_record):
    base_collect_record["data"]["quadrat_collection"]["quadrat_size"] = 0

    validator = _get_validator()
    result = validator(base_collect_record)
    assert result.status == ERROR

    base_collect_record["data"]["quadrat_collection"]["quadrat_size"] = None

    validator = _get_validator()
    result = validator(base_collect_record)
    assert result.status == ERROR

    base_collect_record["data"]["quadrat_collection"]["quadrat_size"] = ""

    validator = _get_validator()
    result = validator(base_collect_record)
    assert result.status == ERROR

    base_collect_record["data"]["quadrat_collection"].pop("quadrat_size")

    validator = _get_validator()
    result = validator(base_collect_record)
    assert result.status == ERROR
