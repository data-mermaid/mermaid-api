from .base import OK, WARN, BaseValidator, validator_result


class ObservationCountValidator(BaseValidator):
    MIN_OBS_COUNT_WARN = 5
    MAX_OBS_COUNT_WARN = 200

    TO_FEW_OBS = "to_few_observations"
    TO_MANY_OBS = "to_many_observations"

    def __init__(self, observations_path, **kwargs):
        self.observations_path = observations_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        num_obs = len(observations)
        if num_obs < self.MIN_OBS_COUNT_WARN:
            return (
                WARN,
                self.MIN_OBS_COUNT_WARN,
                {
                    "observation_count_range": [
                        self.MIN_OBS_COUNT_WARN,
                        self.MAX_OBS_COUNT_WARN,
                    ]
                },
            )
        elif num_obs > self.MAX_OBS_COUNT_WARN:
            return (
                WARN,
                self.MAX_OBS_COUNT_WARN,
                {
                    "observation_count_range": [
                        self.MIN_OBS_COUNT_WARN,
                        self.MAX_OBS_COUNT_WARN,
                    ]
                },
            )

        return OK
