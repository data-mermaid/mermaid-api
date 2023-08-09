from .base import ERROR, OK, WARN, BaseValidator, validator_result


class DepthValidator(BaseValidator):
    DEPTH_RANGE = [0, 40]
    INVALID_DEPTH = "invalid_depth"
    EXCEED_MAX_DEPTH = "max_depth"

    def __init__(self, depth_path, **kwargs):
        self.depth_path = depth_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        depth = self.get_value(collect_record, self.depth_path) or 0
        try:
            depth = float(depth)
        except (TypeError, ValueError):
            return ERROR, self.INVALID_DEPTH, {"depth_range": self.DEPTH_RANGE}

        if depth <= self.DEPTH_RANGE[0]:
            return ERROR, self.INVALID_DEPTH, {"depth_range": self.DEPTH_RANGE}
        elif depth > self.DEPTH_RANGE[1]:
            return ERROR, self.EXCEED_MAX_DEPTH, {"depth_range": self.DEPTH_RANGE}

        return OK
