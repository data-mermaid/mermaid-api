import datetime

import dateutil

from .base import OK, WARN, BaseValidator, validator_result


class SampleTimeValidator(BaseValidator):
    DATE_TIME_RANGE = [datetime.time(6, 0), datetime.time(19, 0)]
    TIME_OUT_OF_RANGE = "sample_time_out_of_range"

    def __init__(self, sample_time_path, **kwargs):
        self.sample_time_path = sample_time_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        sample_time_str = self.get_value(collect_record, self.sample_time_path)
        try:
            sample_time = dateutil.parser.parse(sample_time_str).time()
        except (TypeError, ValueError):
            return OK

        if (
            sample_time < self.DATE_TIME_RANGE[0]
            or sample_time > self.DATE_TIME_RANGE[1]
        ):
            return (
                WARN,
                self.TIME_OUT_OF_RANGE,
                {"time_range": [str(t) for t in self.DATE_TIME_RANGE]},
            )

        return OK
