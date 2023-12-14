from api.submission.validations2.validators import ERROR, OK, DrySubmitValidator


def test_dry_submit_validator_ok(valid_collect_record, profile1_request):
    validator = DrySubmitValidator()
    result = validator(valid_collect_record, request=profile1_request)
    assert result.status == OK


def test_dry_submit_validator_invalid_sample_event(valid_collect_record, profile1_request):
    validator = DrySubmitValidator()

    collect_record = valid_collect_record
    collect_record.data["sample_event"]["site"] = None
    collect_record.data["sample_event"]["management"] = None

    result = validator(collect_record, request=profile1_request)
    assert result.status == ERROR
    assert "site" in result.context["dry_submit_results"]
    assert "management" in result.context["dry_submit_results"]


def test_dry_submit_validator_invalid_fishbelt_transect(valid_collect_record, profile1_request):
    validator = DrySubmitValidator()

    collect_record = valid_collect_record
    collect_record.data["fishbelt_transect"]["depth"] = None

    result = validator(collect_record, request=profile1_request)
    assert result.status == ERROR
    assert "depth" in result.context["dry_submit_results"]
