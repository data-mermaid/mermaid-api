from .base import ERROR, OK, BaseValidator, validator_result


class IntervalSizeValidator(BaseValidator):
    INTERVAL_SIZE_RANGE = [0, 10]
    INVALID_INTERVAL_SIZE = "invalid_interval_size"
    EXCEED_MAX_INTERVAL_SIZE = "max_interval_size"

    def __init__(self, interval_size_path, **kwargs):
        self.interval_size_path = interval_size_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        interval_size = self.get_value(collect_record, self.interval_size_path) or 0
        try:
            interval_size = float(interval_size)
        except (TypeError, ValueError):
            return (
                ERROR,
                self.INVALID_INTERVAL_SIZE,
                {"interval_size_range": self.INTERVAL_SIZE_RANGE},
            )

        if interval_size <= self.INTERVAL_SIZE_RANGE[0]:
            return (
                ERROR,
                self.INVALID_INTERVAL_SIZE,
                {"interval_size_range": self.INTERVAL_SIZE_RANGE},
            )
        elif interval_size > self.INTERVAL_SIZE_RANGE[1]:
            return (
                ERROR,
                self.EXCEED_MAX_INTERVAL_SIZE,
                {"interval_size_range": self.INTERVAL_SIZE_RANGE},
            )

        return OK
