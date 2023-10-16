from .base import ERROR, OK, WARN, BaseValidator, validator_result


class LenSurveyedValidator(BaseValidator):
    LENGTH_RANGE = [10, 100]
    LENGTH_RANGE_ABS = [1, 999]
    LEN_SURVEYED_OUT_OF_RANGE = "len_surveyed_out_of_range"
    REQUIRED = "required"

    def __init__(self, len_surveyed_path, **kwargs):
        self.len_surveyed_path = len_surveyed_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        try:
            len_surveyed = float(self.get_value(collect_record, self.len_surveyed_path))
        except (TypeError, ValueError):
            len_surveyed = None

        if not len_surveyed:
            return (ERROR, self.REQUIRED)

        if len_surveyed < self.LENGTH_RANGE_ABS[0] or len_surveyed > self.LENGTH_RANGE_ABS[1]:
            return (
                ERROR,
                self.LEN_SURVEYED_OUT_OF_RANGE,
                {"len_surveyed_range": self.LENGTH_RANGE_ABS},
            )
        if len_surveyed < self.LENGTH_RANGE[0] or len_surveyed > self.LENGTH_RANGE[1]:
            return (
                WARN,
                self.LEN_SURVEYED_OUT_OF_RANGE,
                {"len_surveyed_range": self.LENGTH_RANGE},
            )

        return OK
