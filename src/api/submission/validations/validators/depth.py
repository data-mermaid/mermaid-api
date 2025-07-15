from decimal import Decimal, InvalidOperation

from ....models import SampleUnit
from .base import ERROR, OK, BaseValidator, validator_result


class DepthValidator(BaseValidator):
    DEPTH_RANGE = [0, 40]
    INVALID_DEPTH = "invalid_depth"
    EXCESSIVE_PRECISION = "excessive_precision"
    EXCEED_MAX_DEPTH = "max_depth"

    def __init__(self, depth_path, **kwargs):
        self.depth_path = depth_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        depth = self.get_numeric_value(collect_record, self.depth_path)
        try:
            depth = Decimal(str(depth))
        except (TypeError, ValueError, InvalidOperation):
            return ERROR, self.INVALID_DEPTH, {"depth_range": self.DEPTH_RANGE}

        if depth <= self.DEPTH_RANGE[0]:
            return ERROR, self.INVALID_DEPTH, {"depth_range": self.DEPTH_RANGE}
        elif depth > self.DEPTH_RANGE[1]:
            return ERROR, self.EXCEED_MAX_DEPTH, {"depth_range": self.DEPTH_RANGE}

        fraction = str(depth).split(".")[1] if "." in str(depth) else ""
        depth_field = SampleUnit._meta.get_field("depth")
        decimal_places = getattr(depth_field, "depth", 1)
        if len(fraction) > decimal_places:
            return ERROR, self.EXCESSIVE_PRECISION, {"decimal_places": decimal_places}

        return OK
