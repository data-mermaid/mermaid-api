from ....models import InvertAttribute
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class InvertAllObsExcludedValidator(BaseValidator):
    ALL_EXCLUDED = "all_observations_excluded"

    def __init__(self, observations_path, **kwargs):
        self.observations_path = observations_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        if not observations:
            return OK
        if all(not obs.get("include", True) for obs in observations):
            return WARN, self.ALL_EXCLUDED
        return OK


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
    Errors per observation row when a size is recorded but the transect has no size_bin set.
    size_bin is transect-level; the error is reported on the observation that triggered it.
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
        if size is not None and size != "" and not size_bin:
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
        **kwargs,
    ):
        self.observations_path = observations_path
        self.observation_attribute_path = observation_attribute_path
        self.observation_size_path = observation_size_path
        super().__init__(**kwargs)

    @validator_result
    def check_invert_size(self, obs, max_length_lookup):
        context = {"observation_id": obs.get("id")}
        attr_id = self.get_value(obs, self.observation_attribute_path)
        size_raw = self.get_value(obs, self.observation_size_path)

        if size_raw is None:
            return OK

        try:
            size = float(size_raw)
        except (TypeError, ValueError):
            return OK

        max_length = max_length_lookup.get(str(attr_id)) if attr_id else None
        if max_length is not None and size > max_length * 1.5:
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

        return [self.check_invert_size(obs, max_length_lookup) for obs in observations]
