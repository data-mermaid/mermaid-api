import math

from .base import OK, ERROR, BaseValidator, validator_result


class BenthicPITObservationCountValidator(BaseValidator):
    """
    Length surveyed
    ---------------  == Observation count
     Interval size
    """

    INCORRECT_OBSERVATION_COUNT = "incorrect_observation_count"
    NON_POSITIVE = "{}_not_positive"

    def __init__(
        self, len_surveyed_path, interval_size_path, obs_benthicpits_path, **kwargs
    ):
        self.len_surveyed_path = len_surveyed_path
        self.interval_size_path = interval_size_path
        self.obs_benthicpits_path = obs_benthicpits_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        tolerance = 1
        obs_benthicpits = (
            self.get_value(collect_record, self.obs_benthicpits_path) or []
        )
        obs_benthicpit_count = len(obs_benthicpits)
        len_surveyed = self.get_value(collect_record, self.len_surveyed_path) or 0
        interval_size = self.get_value(collect_record, self.interval_size_path) or 0

        if len_surveyed <= 0:
            return ERROR, self.NON_POSITIVE.format("len_surveyed")
        if interval_size <= 0:
            return ERROR, self.NON_POSITIVE.format("interval_size")

        calc_obs_count = int(math.ceil(len_surveyed / interval_size))
        if (
            obs_benthicpit_count > calc_obs_count + tolerance
            or obs_benthicpit_count < calc_obs_count - tolerance
        ):
            return (
                ERROR,
                self.INCORRECT_OBSERVATION_COUNT,
                {"expected_count": calc_obs_count},
            )

        return OK
