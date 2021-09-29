from api.submission.protocol_validations import (
    BenthicLITProtocolValidation,
    BenthicPITProtocolValidation,
    FishBeltProtocolValidation,
    HabitatComplexityProtocolValidation,
)
from api.submission.validations import ERROR, OK, WARN


def test_fishbelt_protocol_validation_ok(
    valid_collect_record, profile1_request, belt_transect_width_condition2
):
    validation = FishBeltProtocolValidation(
        valid_collect_record, request=profile1_request
    )
    results = validation.validate()

    assert results == OK


def test_fishbelt_protocol_validation_warn(
    invalid_collect_record_warn, profile1_request, belt_transect_width_condition2
):
    validation = FishBeltProtocolValidation(
        invalid_collect_record_warn, request=profile1_request
    )
    result = validation.validate()
    assert result == WARN
    assert validation.validations["len_surveyed"]["validate_range"]["status"] == WARN
    assert (
        validation.validations["obs_belt_fishes"]["validate_observation_density"][
            "status"
        ]
        == WARN
    )

    assert (
        validation.validations["obs_belt_fishes"]["validate_observation_count"][
            "status"
        ]
        == WARN
    )
    assert validation.validations["depth"]["validate_range"]["status"] == WARN
    assert validation.validations["sample_time"]["validate_range"]["status"] == WARN


def test_fishbelt_protocol_validation_null_str_warn(
    invalid_collect_record_null_str_warn, profile1_request, belt_transect_width_condition2
):
    validation = FishBeltProtocolValidation(
        invalid_collect_record_null_str_warn, request=profile1_request
    )
    result = validation.validate()
    import json
    print(f"validation.validations: {json.dumps(validation.validations, indent=2)}")
    assert result == WARN
    assert validation.validations["len_surveyed"]["validate_range"]["status"] == WARN
    assert (
        validation.validations["obs_belt_fishes"]["validate_observation_density"][
            "status"
        ]
        == WARN
    )

    assert (
        validation.validations["obs_belt_fishes"]["validate_observation_count"][
            "status"
        ]
        == WARN
    )
    assert validation.validations["depth"]["validate_range"]["status"] == WARN
    assert validation.validations["sample_time"]["validate_range"]["status"] == WARN


def test_fishbelt_protocol_validation_error(
    invalid_collect_record_error, profile1_request, belt_transect_width_condition2
):
    validation = FishBeltProtocolValidation(
        invalid_collect_record_error, request=profile1_request
    )
    assert validation.validate() == ERROR
    assert (validation.validations.get("sample_event") or {}).get("validate_sample_date") == ERROR


def test_benthic_pit_protocol_validation_ok(
    valid_benthic_pit_collect_record, profile1_request
):
    validation = BenthicPITProtocolValidation(
        valid_benthic_pit_collect_record, request=profile1_request
    )
    assert validation.validate() == OK


def test_benthic_pit_protocol_validation_error(
    invalid_benthic_pit_collect_record, profile1_request
):
    validation = BenthicPITProtocolValidation(
        invalid_benthic_pit_collect_record, request=profile1_request
    )

    assert validation.validate() == ERROR
    assert (
        validation.validations["obs_benthic_pits"]["validate_observation_count"][
            "status"
        ]
        == ERROR
    )


def test_benthic_lit_protocol_validation_ok(
    profile1_request,
    valid_benthic_lit_collect_record,
):
    validation = BenthicLITProtocolValidation(
        valid_benthic_lit_collect_record, request=profile1_request
    )
    assert validation.validate() == OK


def test_benthic_lit_protocol_validation_warn(
    profile1_request, invalid_benthic_lit_collect_record
):
    validation = BenthicLITProtocolValidation(
        invalid_benthic_lit_collect_record, request=profile1_request
    )
    assert validation.validate() == WARN
    assert (
        validation.validations["obs_benthic_lits"]["validate_total_length"]["status"]
        == WARN
    )


def test_habitat_complexity_protocol_validation_ok(
    profile1_request,
    valid_habitat_complexity_collect_record,
):
    validation = HabitatComplexityProtocolValidation(
        valid_habitat_complexity_collect_record, request=profile1_request
    )
    assert validation.validate() == OK


def test_habitat_complexity_protocol_validation_error(
    profile1_request,
    invalid_habitat_complexity_collect_record,
):
    validation = HabitatComplexityProtocolValidation(
        invalid_habitat_complexity_collect_record, request=profile1_request
    )
    assert validation.validate() == ERROR
    assert (
        validation.validations["obs_habitat_complexities"]["validate_scores"]["status"]
        == ERROR
    )
