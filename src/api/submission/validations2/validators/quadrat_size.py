from .base import OK, ERROR, BaseValidator, validator_result


class QuadratSizeValidator(BaseValidator):
    REQUIRED = "required"
    INVALID_QUADRAT_SIZE = "invalid_quadrat_size"

    def __init__(self, quadrat_size_path, **kwargs):
        self.quadrat_size_path = quadrat_size_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        quadrat_size = self.get_value(collect_record, self.quadrat_size_path)

        try:
            quadrat_size = float(quadrat_size)
            if quadrat_size == 0:
                raise ValueError("quadrat_size must be greater than 0")
            return OK
        except TypeError:
            return ERROR, self.REQUIRED
        except ValueError:
            return ERROR, self.INVALID_QUADRAT_SIZE
