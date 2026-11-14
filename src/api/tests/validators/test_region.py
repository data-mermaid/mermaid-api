import pytest

from api.models import FishAttribute, FishFamily, FishGenus, FishSpecies
from api.resources.collect_record import CollectRecordSerializer
from api.submission.validations import OK
from api.submission.validations.validators import RegionValidator


def _get_validator():
    return RegionValidator(
        attribute_model_class=FishAttribute,
        site_path="data.sample_event.site",
        observations_path="data.obs_belt_fishes",
        observation_attribute_path="fish_attribute",
    )


@pytest.fixture
def fish_species_no_regions(db):
    family = FishFamily.objects.create(name="No Region Family")
    genus = FishGenus.objects.create(name="No Region Genus", family=family)
    return FishSpecies.objects.create(
        name="No Region Species",
        genus=genus,
        biomass_constant_a=0.01,
        biomass_constant_b=3.0,
        biomass_constant_c=1.0,
    )


@pytest.fixture(autouse=True)
def clear_fish_agg_caches():
    # Force _set_species_agg_vals to re-query so test DB state is reflected.
    FishFamily.species_agg = None
    FishFamily.regions_agg = None
    FishGenus.species_agg = None
    FishGenus.regions_agg = None
    yield
    FishFamily.species_agg = None
    FishFamily.regions_agg = None
    FishGenus.species_agg = None
    FishGenus.regions_agg = None


def test_region_validator_species_with_no_regions_does_not_crash(
    valid_collect_record, fish_species_no_regions, region1
):
    validator = _get_validator()
    record = CollectRecordSerializer(instance=valid_collect_record).data
    # Point observation at a species with no regions; site1 is inside region1
    # so the validator reaches _get_attribute_region_lookup before the fix it raised
    # AttributeError: 'NoneType' object has no attribute 'all'
    record["data"]["obs_belt_fishes"] = [
        {"fish_attribute": str(fish_species_no_regions.pk), "size": 17.5, "count": 10}
    ]

    results = validator(record)

    for result in results:
        assert result.status == OK
