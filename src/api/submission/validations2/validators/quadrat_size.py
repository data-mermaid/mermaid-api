from .base import OK, ERROR, BaseValidator, validator_result


class QuadratSizeValidator(BaseValidator):
    REQUIRED = "required"
    QUADRAT_SIZE_RANGE = [0, 100]
    INVALID_QUADRAT_SIZE = "invalid_quadrat_size"
    MAX_QUADRAT_SIZE = "max_quadrat_size"

    def __init__(self, quadrat_size_path, **kwargs):
        self.quadrat_size_path = quadrat_size_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        quadrat_size = self.get_value(collect_record, self.quadrat_size_path)

        try:
            quadrat_size = float(quadrat_size)
        except TypeError:
            return ERROR, self.REQUIRED
        except ValueError:
            return ERROR, self.INVALID_QUADRAT_SIZE

        if quadrat_size <= self.QUADRAT_SIZE_RANGE[0]:
            return ERROR, self.INVALID_QUADRAT_SIZE, {"quadrat_size_range": self.QUADRAT_SIZE_RANGE}
        elif quadrat_size >= self.QUADRAT_SIZE_RANGE[1]:
            return ERROR, self.MAX_QUADRAT_SIZE, {"quadrat_size_range": self.QUADRAT_SIZE_RANGE}

        return OK

