from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import (
    SimilarManagementNameValidator,
    UniqueManagementValidator,
)


def _get_validator():
    return UniqueManagementValidator(
        management_path="data.sample_event.management",
        site_path="data.sample_event.site",
    )


def _get_name_validator():
    return SimilarManagementNameValidator(management_path="data.sample_event.management")


def _use_management_copy(management, collect_record, name=None, site=None):
    management.pk = None
    if name is not None:
        management.name = name
    management.save()

    collect_record.data["sample_event"]["management"] = str(management.pk)
    if site is not None:
        collect_record.data["sample_event"]["site"] = str(site.pk)
    collect_record.save()

    return CollectRecordSerializer(instance=collect_record).data


def _new_site(site):
    site.pk = None
    site.save()
    return site


def test_management_validator_ok(valid_collect_record):
    record = CollectRecordSerializer(instance=valid_collect_record).data
    assert _get_validator()(record).status == OK
    assert _get_name_validator()(record).status == OK


def test_management_validator_invalid_not_found(valid_collect_record):
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["sample_event"]["management"] = ""

    result = _get_validator()(record)
    assert result.status == ERROR
    assert result.code == UniqueManagementValidator.MANAGEMENT_NOT_FOUND

    # Missing MR is reported once, by UniqueManagementValidator
    assert _get_name_validator()(record).status == OK


def test_management_validator_not_unique_site_only(
    project1, management1, valid_collect_record, benthic_lit1, benthic_lit_project
):
    other_mr_id = str(management1.pk)
    record = _use_management_copy(management1, valid_collect_record, name="Unrelated MR")

    result = _get_validator()(record)
    assert result.status == WARN
    assert result.code == UniqueManagementValidator.NOT_UNIQUE
    assert result.context["matches"] == [other_mr_id]

    assert _get_name_validator()(record).status == OK


def test_management_validator_similar_name_only(
    project1, management1, site1, valid_collect_record, benthic_lit_project
):
    other_mr_id = str(management1.pk)
    record = _use_management_copy(
        management1,
        valid_collect_record,
        name=management1.name.replace(" ", "-"),
        site=_new_site(site1),
    )

    assert _get_validator()(record).status == OK

    result = _get_name_validator()(record)
    assert result.status == WARN
    assert result.code == SimilarManagementNameValidator.SIMILAR_NAME
    assert result.context["matches"] == [other_mr_id]


def test_management_validator_not_unique_site_and_similar_name(
    project1, management1, valid_collect_record, benthic_lit1, benthic_lit_project
):
    # Same site AND similar name: both warnings must surface, not just the site one
    record = _use_management_copy(
        management1, valid_collect_record, name=management1.name.replace(" ", "-")
    )

    result = _get_validator()(record)
    assert result.status == WARN
    assert result.code == UniqueManagementValidator.NOT_UNIQUE

    result = _get_name_validator()(record)
    assert result.status == WARN
    assert result.code == SimilarManagementNameValidator.SIMILAR_NAME
