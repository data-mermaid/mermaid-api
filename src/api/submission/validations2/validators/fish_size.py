from ....models.mermaid import FishAttribute
from .base import OK, WARN, ERROR, BaseValidator, validator_result


class FishSizeValidator(BaseValidator):
    INVALID_FISH_SIZE = "invalid_fish_size"
    MAX_FISH_SIZE = "max_fish_size"

    def __init__(
        self, observations_path, observation_fish_attribute_path, observation_size_path
    ):
        self.observations_path = observations_path
        self.observation_fish_attribute_path = observation_fish_attribute_path
        self.observation_size_path = observation_size_path

    @validator_result
    def check_fish_size(self, obs, max_fish_length_lookup):
        try:
            fish_attribute_id = self.get_value(obs, self.observation_fish_attribute_path)
            fish_size = float(self.get_value(obs, self.observation_size_path))
            max_length = max_fish_length_lookup.get(fish_attribute_id)
            if max_length is not None and fish_size > max_length:
                return WARN, self.MAX_FISH_SIZE, {"max_length": float(max_length)}

        except (TypeError, ValueError):
            return ERROR, self.INVALID_FISH_SIZE

        return OK

    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        fish_attribute_ids = list(
            {o.get(self.observation_fish_attribute_path) for o in observations}
        )
        max_fish_length_lookup = {
            str(fa.pk): fa.get_max_length()
            for fa in FishAttribute.objects.filter(
                id__in=[fai for fai in fish_attribute_ids if fai]
            )
        }
        return [self.check_fish_size(ob, max_fish_length_lookup) for ob in observations]
