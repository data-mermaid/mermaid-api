from .base import ERROR, OK, WARN, BaseValidator, validator_result


class FishCountValidator(BaseValidator):
    INVALID_FISH_COUNT = "invalid_fish_count"
    _fish_count = 0

    def __init__(self, observations_path, observation_count_path, **kwargs):
        self.observations_path = observations_path
        self.observation_count_path = observation_count_path
        super().__init__(**kwargs)

    @validator_result
    def check_fish_count(self, obs):
        status = OK
        code = None
        context = {"observation_id": obs.get("id")}
        try:
            fish_count = int(self.get_value(obs, self.observation_count_path))
            if fish_count < 0:
                raise ValueError("Positive integer required")
            self._fish_count += fish_count
        except Exception:
            status = ERROR
            code = self.INVALID_FISH_COUNT

        return status, code, context

    def __call__(self, collect_record, **kwargs):
        obs = self.get_value(collect_record, self.observations_path) or []
        return [self.check_fish_count(ob) for ob in obs]


class TotalFishCountValidator(FishCountValidator):
    MIN_TOTAL_FISH_COUNT = "minimum_total_fish_count"
    FISH_COUNT_MIN = 10

    def __init__(self, observations_path, observation_count_path, **kwargs):
        self.observations_path = observations_path
        self.observation_count_path = observation_count_path
        super().__init__(observations_path, observation_count_path, **kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        super().__call__(collect_record)
        if self._fish_count < self.FISH_COUNT_MIN:
            return WARN, self.MIN_TOTAL_FISH_COUNT, {"minimum_fish_count": self.FISH_COUNT_MIN}

        return OK
