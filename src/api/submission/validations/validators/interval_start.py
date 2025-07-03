from .base import ERROR, OK, BaseValidator, validator_result


class IntervalStartValidator(BaseValidator):
    INTERVAL_START_RANGE = [0, 10]
    INVALID_INTERVAL_START = "invalid_interval_start"
    EXCEED_MAX_INTERVAL_START = "max_interval_start"

    def __init__(self, interval_start_path, **kwargs):
        self.interval_start_path = interval_start_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        interval_start = self.get_value(collect_record, self.interval_start_path) or 0
        try:
            interval_start = float(interval_start)
        except (TypeError, ValueError):
            return (
                ERROR,
                self.INVALID_INTERVAL_START,
                {"interval_start_range": self.INTERVAL_START_RANGE},
            )

        if interval_start < self.INTERVAL_START_RANGE[0]:
            return (
                ERROR,
                self.INVALID_INTERVAL_START,
                {"interval_start_range": self.INTERVAL_START_RANGE},
            )
        elif interval_start > self.INTERVAL_START_RANGE[1]:
            return (
                ERROR,
                self.EXCEED_MAX_INTERVAL_START,
                {"interval_start_range": self.INTERVAL_START_RANGE},
            )

        return OK
