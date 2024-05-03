from ....utils import safe_sum
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class ColonyCountValidator(BaseValidator):
    MAX_TOTAL_COLONIES = 600
    EXCEED_TOTAL_COLONIES = "exceed_total_colonies"

    def __init__(
        self,
        obs_colonies_bleached_path,
        observation_count_normal_path,
        observation_count_pale_path,
        observation_count_20_path,
        observation_count_50_path,
        observation_count_80_path,
        observation_count_100_path,
        observation_count_dead_path,
        **kwargs,
    ):
        self.obs_colonies_bleached_path = obs_colonies_bleached_path
        self.observation_count_normal_path = observation_count_normal_path
        self.observation_count_pale_path = observation_count_pale_path
        self.observation_count_20_path = observation_count_20_path
        self.observation_count_50_path = observation_count_50_path
        self.observation_count_80_path = observation_count_80_path
        self.observation_count_100_path = observation_count_100_path
        self.observation_count_dead_path = observation_count_dead_path

        super().__init__(**kwargs)

    def _get_colony_counts(self, obs):
        return safe_sum(
            *[
                self.get_value(obs, self.observation_count_normal_path),
                self.get_value(obs, self.observation_count_pale_path),
                self.get_value(obs, self.observation_count_20_path),
                self.get_value(obs, self.observation_count_50_path),
                self.get_value(obs, self.observation_count_80_path),
                self.get_value(obs, self.observation_count_100_path),
                self.get_value(obs, self.observation_count_dead_path),
            ]
        )

    @validator_result
    def __call__(self, collect_record, **kwargs):
        obs_colonies_bleached = (
            self.get_value(collect_record, self.obs_colonies_bleached_path) or []
        )

        total_colony_count = safe_sum(
            *[self._get_colony_counts(obs) for obs in obs_colonies_bleached]
        )
        if total_colony_count > self.MAX_TOTAL_COLONIES:
            return WARN, self.EXCEED_TOTAL_COLONIES

        return OK


class ColonyValuesValidator(BaseValidator):
    INVALID_COUNT = "invalid_count"

    def __init__(self, obs_colonies_bleached_path, observation_count_paths, **kwargs):
        self.obs_colonies_bleached_path = obs_colonies_bleached_path
        self.observation_count_paths = observation_count_paths
        super().__init__(**kwargs)

    @validator_result
    def _check_count(self, obs):
        status = OK
        code = None
        context = {"observation_id": obs.get("id")}

        invalid_paths = []
        for count_path in self.observation_count_paths:
            val = self.get_value(obs, count_path)
            if isinstance(val, int) is False or val < 0:
                invalid_paths.append(count_path)

        if invalid_paths:
            status = ERROR
            code = self.INVALID_COUNT
            context["invalid_paths"] = invalid_paths

        return status, code, context

    def __call__(self, collect_record, **kwargs):
        obs = self.get_value(collect_record, self.obs_colonies_bleached_path) or []

        return [self._check_count(ob) for ob in obs]
