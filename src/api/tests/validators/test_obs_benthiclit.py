from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import (
    AllAttributesSameCategoryValidator,
    BenthicLITObservationTotalLengthValidator,
    ListRequiredValidator,
    ERROR,
    OK,
    WARN,
)


def _get_validator():
    return BenthicLITObservationTotalLengthValidator(
        len_surveyed_path="data.benthic_transect.len_surveyed",
        obs_benthiclits_path="data.obs_benthic_lits"
    )


def test_benthicpit_attributes_differentcats(valid_benthic_lit_collect_record):
    validator = AllAttributesSameCategoryValidator(
        obs_benthic_path="data.obs_benthic_lits"
    )
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data

    result = validator(record)
    assert result.status == OK


def test_benthiclit_attributes_allsamecat(
    valid_benthic_lit_collect_record, benthic_attribute_2
):
    validator = AllAttributesSameCategoryValidator(
        obs_benthic_path="data.obs_benthic_lits"
    )
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    observations = [
        dict(attribute=str(benthic_attribute_2.id), length=500),
        dict(attribute=str(benthic_attribute_2.id), length=1000),
        dict(attribute=str(benthic_attribute_2.id), length=1500),
    ]
    record["data"]["obs_benthic_lits"] = observations

    result = validator(record)
    assert result.status == WARN
    assert result.code == AllAttributesSameCategoryValidator.ALL_SAME_CATEGORY

    record["data"]["obs_benthic_lits"][0]["attribute"] = ""
    record["data"]["obs_benthic_lits"][1]["attribute"] = ""
    result = validator(record)
    assert result.status == OK


def test_benthiclit_obs_required_fields(valid_benthic_lit_collect_record):
    validator = ListRequiredValidator(
        list_path="data.obs_benthic_lits",
        path="attribute",
        name_prefix="attribute",
        unique_identifier_label="observation_id",
    )
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    record["data"]["obs_benthic_lits"][0]["attribute"] = ""
    result = validator(record)
    assert result[0].status == ERROR
    assert result[0].code == ListRequiredValidator.REQUIRED


def test_benthiclit_observation_total_length_invalid(valid_benthic_lit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    record["data"]["benthic_transect"]["len_surveyed"] = 50

    result = validator(record)
    assert result.status == WARN
    assert result.code == validator.TOTAL_LENGTH_WARN


def test_benthiclit_observation_total_length_valid_plus50(valid_benthic_lit_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(valid_benthic_lit_collect_record).data
    record["data"]["benthic_transect"]["len_surveyed"] = 150

    result = validator(record)
    assert result.status == OK
