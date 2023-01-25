from api.submission.validations2 import (
    belt_fish,
    benthic_photo_quadrat_transect,
    benthic_lit,
    benthic_pit,
    bleaching_quadrat_collection,
    habitat_complexity,
    ValidationRunner,
)
from api.submission.validations import ERROR, OK, WARN, IGNORE
from api.resources.collect_record import CollectRecordSerializer


def _get_result_status(validator_results, validator_name):
    for result in validator_results:
        if result["name"] == validator_name:
            return result["status"]
    return None


def _set_result_status(validator_results, validator_name, status):
    for result in validator_results:
        if result["name"] == validator_name:
            result["status"] = status


def test_fishbelt_protocol_validation_ok(
    valid_collect_record, profile1_request, belt_transect_width_condition2
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_collect_record, belt_fish.belt_fish_validations, request=profile1_request
    )

    assert overall_status == OK


def test_fishbelt_protocol_validation_warn(
    invalid_collect_record_warn, profile1_request, belt_transect_width_condition2
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_warn,
        belt_fish.belt_fish_validations,
        request=profile1_request,
    )

    assert overall_status == WARN
    invalid_collect_record_warn.validations = runner.to_dict()
    invalid_collect_record_warn.save()
    assert (
        _get_result_status(
            invalid_collect_record_warn.validations["results"]["data"][
                "fishbelt_transect"
            ]["depth"],
            "depth_validator",
        )
        == WARN
    )
    assert (
        _get_result_status(
            invalid_collect_record_warn.validations["results"]["data"][
                "obs_belt_fishes"
            ][2],
            "fish_size_validator",
        )
        == WARN
    )

    _set_result_status(
        invalid_collect_record_warn.validations["results"]["$record"],
        "observation_count_validator",
        IGNORE,
    )

    _set_result_status(
        invalid_collect_record_warn.validations["results"]["data"]["obs_belt_fishes"][
            2
        ],
        "fish_size_validator",
        IGNORE,
    )

    _set_result_status(
        invalid_collect_record_warn.validations["results"]["data"]["fishbelt_transect"][
            "depth"
        ],
        "depth_validator",
        IGNORE,
    )

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_warn,
        belt_fish.belt_fish_validations,
        request=profile1_request,
    )

    results = invalid_collect_record_warn.validations["results"]

    record_results = results["$record"]
    assert _get_result_status(record_results, "observation_count_validator") == IGNORE
    assert _get_result_status(record_results, "biomass_validator") == WARN

    transect_results = results["data"]["fishbelt_transect"]
    assert _get_result_status(transect_results["depth"], "depth_validator") == IGNORE
    assert (
        _get_result_status(transect_results["sample_time"], "sample_time_validator")
        == WARN
    )

    assert (
        _get_result_status(
            invalid_collect_record_warn.validations["results"]["data"][
                "obs_belt_fishes"
            ][2],
            "fish_size_validator",
        )
        == IGNORE
    )


def test_fishbelt_protocol_validation_null_str_warn(
    invalid_collect_record_null_str_warn,
    profile1_request,
    belt_transect_width_condition2,
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_null_str_warn,
        belt_fish.belt_fish_validations,
        request=profile1_request,
    )
    assert overall_status == WARN

    results = runner.to_dict()["results"]
    transect_results = results["data"]["fishbelt_transect"]

    assert (
        _get_result_status(transect_results["len_surveyed"], "len_surveyed_validator")
        == WARN
    )
    assert _get_result_status(transect_results["depth"], "depth_validator") == WARN
    assert (
        _get_result_status(transect_results["sample_time"], "sample_time_validator")
        == WARN
    )

    assert _get_result_status(results["$record"], "biomass_validator") == WARN
    assert _get_result_status(results["$record"], "observation_count_validator") == WARN


def test_fishbelt_protocol_validation_error(
    invalid_collect_record_error, profile1_request, belt_transect_width_condition2
):

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_error,
        belt_fish.belt_fish_validations,
        request=profile1_request,
    )
    assert overall_status == ERROR

    results = runner.to_dict()["results"]["data"]
    se_results = results["sample_event"]
    assert (
        _get_result_status(se_results["sample_date"], "sample_date_validator") == ERROR
    )
    assert (
        _get_result_status(se_results["management"], "management_rule_validator")
        == ERROR
    )

    observation_results = results["obs_belt_fishes"]
    assert _get_result_status(observation_results[0], "fish_size_validator") == WARN
    assert _get_result_status(observation_results[1], "fish_size_validator") == ERROR
    assert (
        _get_result_status(observation_results[2], "size_list_required_validator")
        == ERROR
    )
    assert _get_result_status(observation_results[2], "region_validator") == WARN


def test_bleachingqc_protocol_validation_ok(
    valid_bleaching_qc_collect_record, profile1_request
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_bleaching_qc_collect_record,
        bleaching_quadrat_collection.bleaching_quadrat_collection_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_benthiclit_protocol_validation_ok(valid_benthic_lit_collect_record, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_benthic_lit_collect_record,
        benthic_lit.benthic_lit_validations,
        request=profile1_request
    )
    assert overall_status == OK


def test_benthicpit_protocol_validation_ok(valid_benthic_pit_collect_record, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_benthic_pit_collect_record,
        benthic_pit.benthic_pit_validations,
        request=profile1_request
    )
    assert overall_status == OK


def test_benthicpqt_protocol_validation_ok(
    valid_benthic_pq_transect_collect_record, profile1_request
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_benthic_pq_transect_collect_record,
        benthic_photo_quadrat_transect.benthic_photo_quadrat_transect_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_benthicpqt_protocol_validation_warn(
    valid_benthic_pq_transect_collect_record, profile1_request
):

    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_quadrats"] = 2
    valid_benthic_pq_transect_collect_record.data["quadrat_transect"]["num_points_per_quadrat"] = 1
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_benthic_pq_transect_collect_record,
        benthic_photo_quadrat_transect.benthic_photo_quadrat_transect_validations,
        request=profile1_request,
    )

    assert overall_status == WARN

    results = runner.to_dict()["results"]
    assert (
        _get_result_status(
            results["$record"],
            "quadrat_count_validator",
        )
        == WARN
    )
    assert (
        _get_result_status(
            results["$record"],
            "points_per_quadrat_validator"
        )
        == WARN
    )


def test_habcomp_protocol_validation_ok(valid_habitat_complexity_collect_record, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_habitat_complexity_collect_record,
        habitat_complexity.habcomp_validations,
        request=profile1_request
    )
    assert overall_status == OK
