from .base import OK, WARN, BaseValidator, validator_result


class DepthValidator(BaseValidator):
    DEPTH_RANGE = [0, 30]
    INVALID_DEPTH = "invalid_depth"

    def __init__(self, depth_path):
        self.depth_path = depth_path

    @validator_result
    def __call__(self, collect_record, **kwargs):
        depth = self.get_value(collect_record, self.depth_path) or 0
        try:
            depth = float(depth)
        except (TypeError, ValueError):
            return WARN, self.INVALID_DEPTH, {"depth_range": self.DEPTH_RANGE}

        if depth <= self.DEPTH_RANGE[0] or depth > self.DEPTH_RANGE[1]:
            return WARN, self.INVALID_DEPTH, {"depth_range": self.DEPTH_RANGE}

        return OK
