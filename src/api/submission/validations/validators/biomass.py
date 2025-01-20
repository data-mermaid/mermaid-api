from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import BeltTransectWidth, FishAttribute
from ....utils import calc_biomass_density, cast_float, cast_int
from .base import OK, WARN, BaseValidator, validator_result


class BiomassValidator(BaseValidator):
    OBS_GT_DENSITY = 5000  # kg/ha
    OBS_LT_DENSITY = 50  # kg/ha
    LOW_DENSITY = "low_density"
    HIGH_DENSITY = "high_density"

    def __init__(
        self,
        observations_path,
        len_surveyed_path,
        width_path,
        obs_fish_attribute_path,
        obs_count_path,
        obs_size_path,
        **kwargs,
    ):
        self.observations_path = observations_path
        self.len_surveyed_path = len_surveyed_path
        self.width_path = width_path
        self.obs_fish_attribute_path = obs_fish_attribute_path
        self.obs_count_path = obs_count_path
        self.obs_size_path = obs_size_path

        super().__init__(**kwargs)

    def _check_total_density(self, total_density):
        if total_density > self.OBS_GT_DENSITY:
            return (
                WARN,
                self.HIGH_DENSITY,
                {"biomass_range": [self.OBS_LT_DENSITY, self.OBS_GT_DENSITY]},
            )
        elif total_density < self.OBS_LT_DENSITY:
            return (
                WARN,
                self.LOW_DENSITY,
                {"biomass_range": [self.OBS_LT_DENSITY, self.OBS_GT_DENSITY]},
            )

        return OK

    def _get_fish_attribute_lookup(self, observations):
        fishattribute_ids = [
            o.get("fish_attribute") for o in observations if o.get("fish_attribute") is not None
        ]
        return {
            str(fa.id): fa.get_biomass_constants()
            for fa in FishAttribute.objects.filter(id__in=fishattribute_ids)
        }

    def _calc_biomass(self, observation, width, len_surveyed, fish_attr_lookup):
        count = cast_int(observation.get("count"))
        size = cast_float(observation.get("size"))
        try:
            width_val = width.get_condition(size).val
        except AttributeError:
            width_val = None

        fish_attribute = observation.get("fish_attribute")
        constants = fish_attr_lookup.get(fish_attribute) or [None, None, None]
        return calc_biomass_density(count, size, len_surveyed, width_val, *constants)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        len_surveyed = cast_float(self.get_value(collect_record, self.len_surveyed_path))
        width_id = self.get_value(collect_record, self.width_path)
        try:
            _ = check_uuid(width_id)
            width = BeltTransectWidth.objects.get(id=width_id)
        except (BeltTransectWidth.DoesNotExist, ParseError):
            width = None

        fish_attr_lookup = self._get_fish_attribute_lookup(observations)

        densities = []
        for obs in observations:
            density = self._calc_biomass(obs, width, len_surveyed, fish_attr_lookup)
            densities.append(density)

        total_density = sum(d for d in densities if d is not None)
        return self._check_total_density(total_density)
