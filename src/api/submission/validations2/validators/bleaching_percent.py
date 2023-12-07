from ....utils import cast_int, safe_sum
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class BleachingPercentValidator(BaseValidator):
    INVALID_PERCENT = "invalid_percent_value"
    INVALID_TOTAL_PERCENT = "invalid_total_percent"
    VALUE_NOT_SET = "value_not_set"

    def __init__(self, obs_quadrat_benthic_percent_path, observation_percent_paths, **kwargs):
        self.obs_quadrat_benthic_percent_path = obs_quadrat_benthic_percent_path
        self.observation_percent_paths = observation_percent_paths
        super().__init__(**kwargs)

    @validator_result
    def _check_percent(self, obs):
        status = OK
        code = None
        context = {"observation_id": obs.get("id")}

        pct_vals = [cast_int(self.get_value(obs, k)) for k in self.observation_percent_paths]
        percent_sum = safe_sum(*pct_vals)
        if any(v < 0 for v in pct_vals if v):
            code = self.INVALID_PERCENT
            status = ERROR
        elif percent_sum < 0 or percent_sum > 100:
            code = self.INVALID_TOTAL_PERCENT
            status = ERROR
        elif None in pct_vals:
            code = self.VALUE_NOT_SET
            status = WARN

        return status, code, context

    def __call__(self, collect_record, **kwargs):
        obs = self.get_value(collect_record, self.obs_quadrat_benthic_percent_path) or []

        return [self._check_percent(ob) for ob in obs]
