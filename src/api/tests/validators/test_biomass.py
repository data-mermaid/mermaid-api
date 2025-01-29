from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import OK, WARN
from api.submission.validations.validators import BiomassValidator


def _get_validator():
    return BiomassValidator(
        observations_path="data.obs_belt_fishes",
        len_surveyed_path="data.fishbelt_transect.len_surveyed",
        width_path="data.fishbelt_transect.width",
        obs_fish_attribute_path="fish_attribute",
        obs_count_path="count",
        obs_size_path="size",
    )


def test_biomass_validator_ok(valid_collect_record, belt_transect_width_condition2):
    record = CollectRecordSerializer(instance=valid_collect_record).data
    validator = _get_validator()
    result = validator(record)
    assert result.status == OK


def test_biomass_validator_low_density(valid_collect_record, belt_transect_width_condition2):
    record = CollectRecordSerializer(instance=valid_collect_record).data
    validator = _get_validator()

    obs = record["data"]["obs_belt_fishes"]
    for ob in obs:
        ob["count"] = 1
        ob["size"] = 1

    record["data"]["obs_belt_fishes"] = obs

    result = validator(record)
    assert result.status == WARN
    assert result.code == BiomassValidator.LOW_DENSITY


def test_biomass_validator_high_density(valid_collect_record, belt_transect_width_condition2):
    record = CollectRecordSerializer(instance=valid_collect_record).data
    validator = _get_validator()

    obs = record["data"]["obs_belt_fishes"]
    for ob in obs:
        ob["count"] = 999999
        ob["size"] = 999999

    record["data"]["obs_belt_fishes"] = obs

    result = validator(record)
    assert result.status == WARN
    assert result.code == BiomassValidator.HIGH_DENSITY


def test_biomass_validator_invalid_values(valid_collect_record, belt_transect_width_condition2):
    record = CollectRecordSerializer(instance=valid_collect_record).data
    record["data"]["fishbelt_transect"]["len_surveyed"] = ""
    record["data"]["fishbelt_transect"]["width"] = ""
    record["data"]["obs_belt_fishes"][0]["count"] = "0"
    record["data"]["obs_belt_fishes"][0]["size"] = None

    validator = _get_validator()
    result = validator(record)
    assert result.status == WARN
    assert result.code == BiomassValidator.LOW_DENSITY
