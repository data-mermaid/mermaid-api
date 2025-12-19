from api.models import FishSize
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import ERROR, OK, WARN
from api.submission.validations.validators import FishSizeValidator


def _get_validator():
    return FishSizeValidator(
        observations_path="data.obs_belt_fishes",
        observation_fish_attribute_path="fish_attribute",
        observation_size_path="size",
        fishbelt_transect_path="data.fishbelt_transect",
    )


def _setup_fish_size_bin(size_bin, name, val, min_val, max_val):
    FishSize.objects.get_or_create(
        fish_bin_size=size_bin,
        name=name,
        defaults={"val": val, "min_val": min_val, "max_val": max_val},
    )


def _setup_observation(collect_record, size_bin, obs_size, fish_species):
    collect_record.data["fishbelt_transect"]["size_bin"] = str(size_bin.pk)
    collect_record.data["obs_belt_fishes"][0]["size"] = obs_size
    collect_record.data["obs_belt_fishes"][0]["fish_attribute"] = str(fish_species.pk)
    collect_record.save()


def test_fish_size_validator_ok(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    for result in results:
        assert result.status == OK


def test_fish_count_validator_invalid(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["size"] = 20000

    results = validator(record)
    assert results[0].status == WARN
    assert results[0].code == FishSizeValidator.MAX_FISH_SIZE


def test_fish_count_validator_error(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["size"] = ""

    results = validator(record)
    assert results[0].status == ERROR


def test_fish_size_validator_zero(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["size"] = 0

    results = validator(record)
    assert results[0].status == ERROR
    assert results[0].code == FishSizeValidator.INVALID_FISH_SIZE


def test_fish_size_validator_negative(valid_collect_record):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data

    record["data"]["obs_belt_fishes"][0]["size"] = -5

    results = validator(record)
    assert results[0].status == ERROR
    assert results[0].code == FishSizeValidator.INVALID_FISH_SIZE


def test_fish_size_validator_with_size_bin_no_warning(
    valid_collect_record, fish_species4, fish_size_bin_5
):
    """
    Test that when using size bins, the validator uses bin.min_val for comparison.

    Scenario:
    - Size bin "5" (5cm bins: 0-5, 5-10, 10-15, etc.)
    - Observation size: 12.5 (from "10-15" bin, so min_val=10, max_val=15)
    - Species max: 12 cm
    - Expected: NO WARNING (because bin.min_val (10) <= species_max (12))
    """
    _setup_fish_size_bin(fish_size_bin_5, "10 - 15", 12.5, 10.0, 15.0)
    fish_species4.max_length = 12.0
    fish_species4.save()

    _setup_observation(valid_collect_record, fish_size_bin_5, 12.5, fish_species4)

    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    assert results[0].status == OK


def test_fish_size_validator_with_size_bin_warning(
    valid_collect_record, fish_species4, fish_size_bin_5
):
    """
    Test that warning is triggered when bin.min_val exceeds species max.

    Scenario:
    - Size bin "5" (5cm bins)
    - Observation size: 17.5 (from "15-20" bin, so min_val=15, max_val=20)
    - Species max: 12 cm
    - Expected: WARNING (because bin.min_val (15) > species_max (12))
    """
    _setup_fish_size_bin(fish_size_bin_5, "15 - 20", 17.5, 15.0, 20.0)
    fish_species4.max_length = 12.0
    fish_species4.save()

    _setup_observation(valid_collect_record, fish_size_bin_5, 17.5, fish_species4)

    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    assert results[0].status == WARN
    assert results[0].code == FishSizeValidator.MAX_FISH_SIZE


def test_fish_size_validator_with_size_bin_1_continuous(
    valid_collect_record, fish_species4, fish_size_bin_1
):
    """
    Test that size bin "1" (continuous, no bins) works as before.

    Scenario:
    - Size bin "1" (no FishSize records)
    - Observation size: 20
    - Species max: 15 cm
    - Expected: WARNING (because 20 > 15, using original behavior)
    """
    fish_species4.max_length = 15.0
    fish_species4.save()

    _setup_observation(valid_collect_record, fish_size_bin_1, 20, fish_species4)

    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    assert results[0].status == WARN
    assert results[0].code == FishSizeValidator.MAX_FISH_SIZE


def test_fish_size_validator_size_not_in_any_bin(
    valid_collect_record, fish_species4, fish_size_bin_5
):
    """
    Test edge case where observation size doesn't match any FishSize bin.

    Scenario:
    - Size bin "5" exists
    - Observation size: 2.5 (doesn't match any bin range)
    - Expected: Falls back to original size for comparison
    """
    # Create a bin that doesn't include 2.5
    FishSize.objects.filter(fish_bin_size=fish_size_bin_5).delete()
    _setup_fish_size_bin(fish_size_bin_5, "5 - 10", 7.5, 5.0, 10.0)

    fish_species4.max_length = 2.0
    fish_species4.save()

    _setup_observation(valid_collect_record, fish_size_bin_5, 2.5, fish_species4)

    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    results = validator(record)
    # Should be WARNING because 2.5 > 2.0 (using original size since no bin match)
    assert results[0].status == WARN
    assert results[0].code == FishSizeValidator.MAX_FISH_SIZE
