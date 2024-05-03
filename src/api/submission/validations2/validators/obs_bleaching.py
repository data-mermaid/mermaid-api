from ....utils import cast_int, safe_sum
from .base import ERROR, OK, BaseValidator, validator_result


class BleachingObsValidator(BaseValidator):
    INVALID_COUNT = "invalid_count"
    INVALID_PERCENT = "invalid_percent_value"
    INVALID_TOTAL = "invalid_total"
    COLONY_COUNT = "colony_count"
    BENTHIC_PERCENT = "benthic_percent"
    COUNT_RANGE = [0, 1000]
    PERCENT_RANGE = [0, 100]

    def __init__(self, obs_path, observation_field_paths, **kwargs):
        self.obs_path = obs_path
        self.observation_field_paths = observation_field_paths
        self.obs_type = self.COLONY_COUNT
        if obs_path == "data.obs_quadrat_benthic_percent":
            self.obs_type = self.BENTHIC_PERCENT
        super().__init__(**kwargs)

    @validator_result
    def _check_field_values(self, obs):
        status = OK
        code = None
        context = {"observation_id": obs.get("id")}

        vals = []
        invalid_paths = []
        for field_path in self.observation_field_paths:
            val = cast_int(self.get_value(obs, field_path))
            if isinstance(val, int) is False or val < 0:
                invalid_paths.append(field_path)
            vals.append(val)

        obs_sum = safe_sum(*vals)
        minval, maxval = self.COUNT_RANGE
        if self.obs_type == self.BENTHIC_PERCENT:
            minval, maxval = self.PERCENT_RANGE
        if obs_sum < minval or obs_sum > maxval:
            status = ERROR
            code = self.INVALID_TOTAL
            context["value_range"] = [minval, maxval]

        if invalid_paths:
            status = ERROR
            code = self.INVALID_COUNT
            if self.obs_type == self.BENTHIC_PERCENT:
                code = self.INVALID_PERCENT
            context["invalid_paths"] = invalid_paths

        return status, code, context

    def __call__(self, collect_record, **kwargs):
        obs = self.get_value(collect_record, self.obs_path) or []

        return [self._check_field_values(ob) for ob in obs]
