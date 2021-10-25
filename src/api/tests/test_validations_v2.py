from api.submission.validations2 import (
    belt_fish,
    ValidationRunner
)
from api.submission.validations import ERROR, OK, WARN, IGNORE
from api.resources.collect_record import CollectRecordSerializer
from api.models import CollectRecord


def test_fishbelt_protocol_validation_ok(
    valid_collect_record, profile1_request, belt_transect_width_condition2
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        valid_collect_record,
        belt_fish.belt_fish_validations,
        request=profile1_request
    )

    assert overall_status == OK


def test_fishbelt_protocol_validation_warn(
    invalid_collect_record_warn, profile1_request, belt_transect_width_condition2
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_warn,
        belt_fish.belt_fish_validations,
        request=profile1_request
    )
    assert overall_status == WARN
    invalid_collect_record_warn.validations = runner.to_dict()
    invalid_collect_record_warn.save()

    invalid_collect_record_warn.validations["results"]["$record"][1]["status"] = "ignore"
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_warn,
        belt_fish.belt_fish_validations,
        request=profile1_request
    )

    results = invalid_collect_record_warn.validations["results"]
    for rec_result in results["$record"]:
        if rec_result["name"] == "observation_count_validator":
            assert rec_result["status"] == IGNORE
        elif rec_result["name"] == "biomass_validator":
            assert rec_result["status"] == WARN

    assert results["data"]["fishbelt_transect"]["depth"][0]["status"] == WARN
    assert results["data"]["fishbelt_transect"]["sample_time"][0]["status"] == WARN


def test_fishbelt_protocol_validation_null_str_warn(
    invalid_collect_record_null_str_warn, profile1_request, belt_transect_width_condition2
):
    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_null_str_warn,
        belt_fish.belt_fish_validations,
        request=profile1_request
    )
    assert overall_status == WARN

    results = runner.to_dict()["results"]
    assert results["data"]["fishbelt_transect"]["len_surveyed"][0]["status"] == WARN
    assert results["data"]["fishbelt_transect"]["depth"][0]["status"] == WARN
    assert results["data"]["fishbelt_transect"]["sample_time"][0]["status"] == WARN

    for rec_result in results["$record"]:
        if rec_result["name"] in ("biomass_validator", "observation_count_validator"):
            assert rec_result["status"] == WARN


def test_fishbelt_protocol_validation_error(
    invalid_collect_record_error, profile1_request, belt_transect_width_condition2
):

    runner = ValidationRunner(serializer=CollectRecordSerializer)
    overall_status = runner.validate(
        invalid_collect_record_error,
        belt_fish.belt_fish_validations,
        request=profile1_request
    )
    assert overall_status == ERROR

    results = runner.to_dict()["results"]
    assert results["data"]["sample_event"]["sample_date"][0]["status"] == ERROR
