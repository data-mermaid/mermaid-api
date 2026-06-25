from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import (
    ERROR,
    IGNORE,
    OK,
    WARN,
    ValidationRunner,
    belt_fish,
    belt_invert,
    benthic_lit,
    benthic_photo_quadrat_transect,
    benthic_pit,
    bleaching_quadrat_collection,
    habitat_complexity,
)


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
            invalid_collect_record_warn.validations["results"]["data"]["obs_belt_fishes"][2],
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
        invalid_collect_record_warn.validations["results"]["data"]["obs_belt_fishes"][2],
        "fish_size_validator",
        IGNORE,
    )

    _set_result_status(
        invalid_collect_record_warn.validations["results"]["data"]["fishbelt_transect"]["depth"],
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
    assert _get_result_status(transect_results["sample_time"], "sample_time_validator") == WARN

    assert (
        _get_result_status(
            invalid_collect_record_warn.validations["results"]["data"]["obs_belt_fishes"][2],
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
    assert overall_status == ERROR

    results = runner.to_dict()["results"]
    transect_results = results["data"]["fishbelt_transect"]

    assert _get_result_status(transect_results["len_surveyed"], "len_surveyed_validator") == WARN
    assert _get_result_status(transect_results["depth"], "depth_validator") == ERROR
    assert _get_result_status(transect_results["sample_time"], "sample_time_validator") == WARN

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
    assert (
        _get_result_status(
            results["fishbelt_transect"]["depth"],
            "depth_validator",
        )
        == ERROR
    )

    se_results = results["sample_event"]
    assert _get_result_status(se_results["sample_date"], "sample_date_validator") == ERROR
    assert _get_result_status(se_results["management"], "management_rule_validator") == ERROR

    observation_results = results["obs_belt_fishes"]
    assert _get_result_status(observation_results[0], "fish_size_validator") == WARN
    assert _get_result_status(observation_results[1], "fish_size_validator") == ERROR
    assert _get_result_status(observation_results[2], "size_list_required_validator") == ERROR
    assert _get_result_status(observation_results[2], "region_validator") == WARN


def test_bleachingqc_protocol_validation_ok(valid_bleaching_qc_collect_record, profile1_request):
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
        request=profile1_request,
    )
    assert overall_status == OK


def test_benthicpit_protocol_validation_ok(valid_benthic_pit_collect_record, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_benthic_pit_collect_record,
        benthic_pit.benthic_pit_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_benthicpqt_protocol_validation_ok(
    valid_benthic_pq_transect_collect_record, profile1_request
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_benthic_pq_transect_collect_record,
        benthic_photo_quadrat_transect.bpqt_non_classification_validations,
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
        benthic_photo_quadrat_transect.bpqt_non_classification_validations,
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
    assert _get_result_status(results["$record"], "points_per_quadrat_validator") == WARN


def test_habcomp_protocol_validation_ok(valid_habitat_complexity_collect_record, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_habitat_complexity_collect_record,
        habitat_complexity.habcomp_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_belt_invert_protocol_validation_ok(valid_belt_invert_collect_record, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_belt_invert_size_exceeds_max_warn(
    valid_belt_invert_collect_record, profile1_request, invert_species_1
):
    data = valid_belt_invert_collect_record.data
    # invert_species_1 has max_length=8; threshold is 8 * 1.5 = 12; set a size above it
    data["obs_belt_inverts"][0]["size"] = 50
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    results = runner.to_dict()["results"]
    assert overall_status == WARN
    obs_results = results["data"]["obs_belt_inverts"]
    assert _get_result_status(obs_results[0], "invert_size_validator") == WARN


def test_belt_invert_missing_required_fields_error(
    valid_belt_invert_collect_record, profile1_request
):
    data = valid_belt_invert_collect_record.data
    data["beltinvert_transect"]["depth"] = None
    data["beltinvert_transect"]["width"] = None
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    assert overall_status == ERROR


def test_belt_invert_count_zero_error(valid_belt_invert_collect_record, profile1_request):
    data = valid_belt_invert_collect_record.data
    data["obs_belt_inverts"][0]["count"] = 0
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    results = runner.to_dict()["results"]
    assert overall_status == ERROR
    assert (
        _get_result_status(results["data"]["obs_belt_inverts"][0], "invert_count_validator")
        == ERROR
    )


def test_belt_invert_count_high_warn(valid_belt_invert_collect_record, profile1_request):
    data = valid_belt_invert_collect_record.data
    data["obs_belt_inverts"][0]["count"] = 51
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    results = runner.to_dict()["results"]
    assert overall_status == WARN
    assert (
        _get_result_status(
            results["data"]["obs_belt_inverts"][0], "invert_obs_count_high_validator"
        )
        == WARN
    )


def test_belt_invert_size_bin_required_error(valid_belt_invert_collect_record, profile1_request):
    data = valid_belt_invert_collect_record.data
    data["beltinvert_transect"]["size_bin"] = None
    data["obs_belt_inverts"][0]["size"] = 4.5
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    results = runner.to_dict()["results"]
    assert overall_status == ERROR
    assert (
        _get_result_status(
            results["data"]["obs_belt_inverts"][0], "invert_size_bin_required_validator"
        )
        == ERROR
    )


def test_belt_invert_partial_size_ok(valid_belt_invert_collect_record, profile1_request):
    data = valid_belt_invert_collect_record.data
    data["obs_belt_inverts"][0]["size"] = None
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_belt_invert_no_size_no_bin_ok(valid_belt_invert_collect_record_no_size, profile1_request):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record_no_size,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_belt_invert_duplicate_taxon_error(valid_belt_invert_collect_record, profile1_request):
    data = valid_belt_invert_collect_record.data
    attr_id = data["obs_belt_inverts"][0]["invert_attribute"]
    data["obs_belt_inverts"][1]["invert_attribute"] = attr_id
    data["obs_belt_inverts"][1]["size"] = data["obs_belt_inverts"][0]["size"]
    valid_belt_invert_collect_record.data = data
    valid_belt_invert_collect_record.save()

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    results = runner.to_dict()["results"]
    assert overall_status == ERROR
    assert _get_result_status(results["$record"], "duplicate_validator") == ERROR


def test_goi_observation_passes_validation(valid_belt_invert_collect_record_goi, profile1_request):
    """A GoI-level invert observation is valid — no size error, GoI resolves to itself."""
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record_goi,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    assert overall_status == OK


def test_family_observation_passes_validation(
    valid_belt_invert_collect_record_family, profile1_request
):
    """A family-level invert observation is valid."""
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_belt_invert_collect_record_family,
        belt_invert.belt_invert_validations,
        request=profile1_request,
    )
    assert overall_status == OK
