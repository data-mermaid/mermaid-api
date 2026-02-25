from ....models.mermaid import FishAttribute, FishSize
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class FishSizeValidator(BaseValidator):
    INVALID_FISH_SIZE = "invalid_fish_size"
    MAX_FISH_SIZE = "max_fish_size"

    def __init__(
        self,
        observations_path,
        observation_fish_attribute_path,
        observation_size_path,
        fishbelt_transect_path=None,
        **kwargs,
    ):
        self.observations_path = observations_path
        self.observation_fish_attribute_path = observation_fish_attribute_path
        self.observation_size_path = observation_size_path
        self.fishbelt_transect_path = fishbelt_transect_path
        super().__init__(**kwargs)

    @validator_result
    def check_fish_size(self, obs, max_fish_length_lookup, fish_size_bins=None):
        status = OK
        code = None
        context = {"observation_id": obs.get("id")}
        try:
            fish_attribute_id = self.get_value(obs, self.observation_fish_attribute_path)
            fish_size = float(self.get_value(obs, self.observation_size_path))

            if fish_size <= 0:
                status = ERROR
                code = self.INVALID_FISH_SIZE
            else:
                # Use actual obs size if no bins are available ('1cm')
                comparison_size = fish_size

                # If fish_size_bins are available, find which bin this observation falls into
                if fish_size_bins:
                    for fish_size_bin in fish_size_bins:
                        if fish_size_bin.min_val <= fish_size <= fish_size_bin.max_val:
                            # Use the minimum value of the bin for comparison
                            comparison_size = fish_size_bin.min_val
                            break

                max_length = max_fish_length_lookup.get(fish_attribute_id)
                if max_length is not None and comparison_size > max_length:
                    status = WARN
                    code = self.MAX_FISH_SIZE
                    context["max_length"] = float(max_length)

        except (TypeError, ValueError):
            status = ERROR
            code = self.INVALID_FISH_SIZE

        return status, code, context

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

        # Pre-fetch FishSize records for the size bin if available
        fish_size_bins = None
        if self.fishbelt_transect_path:
            size_bin_id = self.get_value(collect_record, f"{self.fishbelt_transect_path}.size_bin")
            if size_bin_id:
                fish_size_bins = list(FishSize.objects.filter(fish_bin_size_id=size_bin_id))

        return [
            self.check_fish_size(ob, max_fish_length_lookup, fish_size_bins) for ob in observations
        ]
