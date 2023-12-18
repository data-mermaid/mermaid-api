from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations2.validators import OK, WARN, FishFamilySubsetValidator


def _get_validator():
    return FishFamilySubsetValidator(
        observations_path="data.obs_belt_fishes",
        project_path="project",
    )


def test_fish_family_subset_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_fish_family_subset_validator_invalid(valid_collect_record, project4):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["project"] = str(project4.pk)
    results = validator(record)
    for result in results[:3]:
        assert result.status == WARN
        assert result.code == FishFamilySubsetValidator.INVALID_FISH_FAMILY
