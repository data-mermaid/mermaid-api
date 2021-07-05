from api.submission.protocol_validations import (
    BenthicLITProtocolValidation,
    BenthicPITProtocolValidation,
    FishBeltProtocolValidation,
    HabitatComplexityProtocolValidation,
)
from api.submission.validations import ERROR, OK, WARN


def test_fishbelt_protocol_validation_ok(db_setup, valid_collect_record, profile1_request, belt_transect_width_condition2):
    validation = FishBeltProtocolValidation(
        valid_collect_record, request=profile1_request
    )
    results = validation.validate()

    assert results == OK


def test_fishbelt_protocol_validation_warn(db_setup, invalid_collect_record_warn, profile1_request, belt_transect_width_condition2):
    validation = FishBeltProtocolValidation(
        invalid_collect_record_warn, request=profile1_request
    )
    result = validation.validate()
    assert result == WARN
    assert validation.validations["len_surveyed"]["validate_range"]["status"] == WARN
    assert validation.validations["obs_belt_fishes"]["validate_observation_density"]["status"] == WARN

    assert validation.validations["obs_belt_fishes"]["validate_observation_count"]["status"] == WARN
    assert validation.validations["depth"]["validate_range"]["status"] == WARN
    assert validation.validations["sample_time"]["validate_range"]["status"] == WARN


def test_fishbelt_protocol_validation_error(db_setup, invalid_collect_record_error, profile1_request, belt_transect_width_condition2):
    validation = FishBeltProtocolValidation(
        invalid_collect_record_error, request=profile1_request
    )
    assert validation.validate() == ERROR
