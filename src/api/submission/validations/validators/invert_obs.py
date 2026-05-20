from ....models import InvertAttribute, InvertBeltTransectWidth, InvertGroupOfInterest
from ....utils.invert_goi import invert_attribute_goi_distribution
from .base import ERROR, OK, WARN, BaseValidator, validator_result


class AllObsExcludedValidator(BaseValidator):
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


class TotalMacroinvertCountValidator(BaseValidator):
    """Warns when density for any group of interest exceeds its upper bound (ind/ha)."""

    EXCEED_DENSITY_PER_GOI = "exceed_density_per_goi"

    def __init__(self, observations_path, transect_path, **kwargs):
        self.observations_path = observations_path
        self.transect_path = transect_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        transect = self.get_value(collect_record, self.transect_path) or {}

        try:
            width_id = transect.get("width")
            len_surveyed = float(transect.get("len_surveyed") or 0)
            width_val = float(InvertBeltTransectWidth.objects.get(pk=width_id).val)
            area_m2 = width_val * len_surveyed
        except (InvertBeltTransectWidth.DoesNotExist, TypeError, ValueError):
            return OK

        if area_m2 <= 0:
            return OK

        attr_ids = {
            obs.get("invert_attribute") for obs in observations if obs.get("invert_attribute")
        }
        distributions = {
            attr_id: invert_attribute_goi_distribution(attr_id) for attr_id in attr_ids
        }

        goi_counts = {}
        for obs in observations:
            if not obs.get("include", True):
                continue
            attr_id = obs.get("invert_attribute")
            if not attr_id:
                continue
            try:
                count = float(obs.get("count") or 0)
            except (TypeError, ValueError):
                continue
            for goi_id, weight in (distributions.get(str(attr_id)) or {}).items():
                goi_counts[str(goi_id)] = goi_counts.get(str(goi_id), 0.0) + count * weight

        if not goi_counts:
            return OK

        goi_qs = InvertGroupOfInterest.objects.filter(pk__in=goi_counts.keys())
        exceeded = []
        for goi in goi_qs:
            total_count = goi_counts.get(str(goi.pk), 0.0)
            density_per_ha = (total_count / area_m2) * 10_000
            if density_per_ha > goi.density_upper_bound:
                exceeded.append(
                    {
                        "goi_id": str(goi.pk),
                        "density": round(density_per_ha, 1),
                        "threshold": goi.density_upper_bound,
                    }
                )

        if exceeded:
            return WARN, self.EXCEED_DENSITY_PER_GOI, {"exceeded": exceeded}

        return OK


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
        if max_length is not None and size > max_length:
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
