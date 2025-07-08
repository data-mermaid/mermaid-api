from ..statuses import ERROR, OK, WARN
from .base import BaseValidator, validator_result


class BenthicLITObservationTotalLengthValidator(BaseValidator):
    """
    sum(observation length) = length surveyed
    Total length of observations should be within 50% of transect length
    """

    TOTAL_LENGTH_TOOLARGE = "obs_total_length_toolarge"
    TOTAL_LENGTH_TOOSMALL = "obs_total_length_toosmall"

    def __init__(self, len_surveyed_path, obs_benthiclits_path, **kwargs):
        self.len_surveyed_path = len_surveyed_path
        self.obs_benthiclits_path = obs_benthiclits_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        tolerance = 0.5
        obs_benthiclits = self.get_value(collect_record, self.obs_benthiclits_path) or []

        len_surveyed = self.get_value(collect_record, self.len_surveyed_path) or 0
        len_surveyed_cm = len_surveyed * 100
        obs_len = sum(float(ob.get("length") or 0.0) for ob in obs_benthiclits)
        context = {"total_obs_length": obs_len, "len_surveyed": len_surveyed}

        if len_surveyed_cm <= 0:
            return ERROR, "len_surveyed_not_positive"
        if obs_len > len_surveyed_cm * (1 + tolerance):
            return WARN, self.TOTAL_LENGTH_TOOLARGE, context
        if obs_len < len_surveyed_cm * (1 - tolerance):
            return WARN, self.TOTAL_LENGTH_TOOSMALL, context

        return OK
