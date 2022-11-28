from .base import OK, ERROR, WARN, BaseValidator, validator_result


class BenthicLITObservationTotalLengthValidator(BaseValidator):
    """
    sum(observation length) = length surveyed
    Total length of observations should be within 50% of transect length
    """

    TOTAL_LENGTH_WARN = "observations_total_length_incorrect"

    def __init__(
        self, len_surveyed_path, obs_benthiclits_path, **kwargs
    ):
        self.len_surveyed_path = len_surveyed_path
        self.obs_benthiclits_path = obs_benthiclits_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        tolerance = 0.5
        obs_benthiclits = (
            self.get_value(collect_record, self.obs_benthiclits_path) or []
        )

        # convert to cm
        len_surveyed = (self.get_value(collect_record, self.len_surveyed_path) or 0) * 100
        obs_len = sum(ob.get("length") or 0.0 for ob in obs_benthiclits)

        if len_surveyed <= 0:
            return ERROR, "len_surveyed_not_positive"

        if obs_len > len_surveyed * (1 + tolerance) or obs_len < len_surveyed * tolerance:
            return WARN, self.TOTAL_LENGTH_WARN, {"total_obs_length": obs_len}

        return OK
