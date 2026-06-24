from ....models import InvertAttribute, InvertSize
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class InvertCountValidator(BaseValidator):
    """Errors when a single observation's count is not a positive integer (< 1)."""

    INVALID_INVERT_COUNT = "invalid_invert_count"

    def __init__(self, observations_path, observation_count_path, **kwargs):
        self.observations_path = observations_path
        self.observation_count_path = observation_count_path
        super().__init__(**kwargs)

    @validator_result
    def check_invert_count(self, obs):
        context = {"observation_id": obs.get("id")}
        try:
            count = int(self.get_value(obs, self.observation_count_path))
            if count < 1:
                return ERROR, self.INVALID_INVERT_COUNT, context
        except (TypeError, ValueError):
            return ERROR, self.INVALID_INVERT_COUNT, context
        return OK

    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        return [self.check_invert_count(obs) for obs in observations]


class InvertObsCountHighValidator(BaseValidator):
    """Warns when a single observation's count exceeds MAX_COUNT."""

    INVERT_COUNT_HIGH = "invert_count_high"
    MAX_COUNT = 50

    def __init__(self, observations_path, observation_count_path, **kwargs):
        self.observations_path = observations_path
        self.observation_count_path = observation_count_path
        super().__init__(**kwargs)

    @validator_result
    def check_count_high(self, obs):
        context = {"observation_id": obs.get("id")}
        try:
            count = int(self.get_value(obs, self.observation_count_path))
            if count > self.MAX_COUNT:
                return WARN, self.INVERT_COUNT_HIGH, {**context, "max_count": self.MAX_COUNT}
        except (TypeError, ValueError):
            return OK
        return OK

    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        return [self.check_count_high(obs) for obs in observations]


class InvertSizeBinRequiredValidator(BaseValidator):
    """
    Errors on any observation that has a size when size_bin is not set on the transect.
    Observations without a size are always valid regardless of size_bin.
    """

    SIZE_BIN_REQUIRED = "size_bin_required"

    def __init__(self, observations_path, size_path, size_bin_path, **kwargs):
        self.observations_path = observations_path
        self.size_path = size_path
        self.size_bin_path = size_bin_path
        super().__init__(**kwargs)

    @validator_result
    def check_size_bin(self, obs, size_bin):
        context = {"observation_id": obs.get("id")}
        size = self.get_value(obs, self.size_path)
        size_present = size is not None and size != ""
        if size_present and not size_bin:
            return ERROR, self.SIZE_BIN_REQUIRED, context
        return OK

    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        size_bin = self.get_value(collect_record, self.size_bin_path)
        return [self.check_size_bin(obs, size_bin) for obs in observations]


class InvertSizeValidator(BaseValidator):
    SIZE_EXCEEDS_MAXIMUM = "invert_size_exceeds_maximum"

    def __init__(
        self,
        observations_path,
        observation_attribute_path,
        observation_size_path,
        beltinvert_transect_path=None,
        **kwargs,
    ):
        self.observations_path = observations_path
        self.observation_attribute_path = observation_attribute_path
        self.observation_size_path = observation_size_path
        self.beltinvert_transect_path = beltinvert_transect_path
        super().__init__(**kwargs)

    @validator_result
    def check_invert_size(self, obs, max_length_lookup, invert_size_bins=None):
        context = {"observation_id": obs.get("id")}
        attr_id = self.get_value(obs, self.observation_attribute_path)
        size_raw = self.get_value(obs, self.observation_size_path)

        if size_raw is None:
            return OK

        try:
            size = float(size_raw)
        except (TypeError, ValueError):
            return OK

        comparison_size = size
        if invert_size_bins:
            for invert_size_bin in invert_size_bins:
                max_ok = invert_size_bin.max_val is None or size <= invert_size_bin.max_val
                if invert_size_bin.min_val <= size and max_ok:
                    comparison_size = invert_size_bin.min_val
                    break

        max_length = max_length_lookup.get(str(attr_id)) if attr_id else None
        if max_length is not None and comparison_size > max_length * 1.5:
            return WARN, self.SIZE_EXCEEDS_MAXIMUM, {**context, "max_length": max_length}

        return OK

    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        attr_ids = list(
            {self.get_value(obs, self.observation_attribute_path) for obs in observations}
        )

        attr_instances = InvertAttribute.objects.select_related(
            "invertspecies",
            "invertgenus",
            "invertfamily",
            "invertorder",
            "invertclass",
        ).filter(pk__in=[a for a in attr_ids if a])

        max_length_lookup = {}
        for attr in attr_instances:
            for subattr_name in (
                "invertspecies",
                "invertgenus",
                "invertfamily",
                "invertorder",
                "invertclass",
            ):
                subattr = getattr(attr, subattr_name, None)
                if subattr is not None:
                    ml = subattr.max_length
                    if ml is not None:
                        max_length_lookup[str(attr.pk)] = float(ml)
                    break

        invert_size_bins = None
        if self.beltinvert_transect_path:
            size_bin_id = self.get_value(
                collect_record, f"{self.beltinvert_transect_path}.size_bin"
            )
            if size_bin_id:
                invert_size_bins = list(InvertSize.objects.filter(invert_bin_size_id=size_bin_id))

        return [
            self.check_invert_size(obs, max_length_lookup, invert_size_bins) for obs in observations
        ]
