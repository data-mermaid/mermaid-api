from api.models import BenthicAttribute
from ..utils import valid_id
from .base import OK, WARN, BaseValidator, validator_result


class ObservationCountValidator(BaseValidator):
    MIN_OBS_COUNT_WARN = 5
    MAX_OBS_COUNT_WARN = 200

    TOO_FEW_OBS = "too_few_observations"
    TOO_MANY_OBS = "too_many_observations"

    def __init__(self, observations_path, **kwargs):
        self.observations_path = observations_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        num_obs = len(observations)
        if num_obs < self.MIN_OBS_COUNT_WARN:
            return (
                WARN,
                self.TOO_FEW_OBS,
                {
                    "observation_count_range": [
                        self.MIN_OBS_COUNT_WARN,
                        self.MAX_OBS_COUNT_WARN,
                    ]
                },
            )
        elif num_obs > self.MAX_OBS_COUNT_WARN:
            return (
                WARN,
                self.TOO_MANY_OBS,
                {
                    "observation_count_range": [
                        self.MIN_OBS_COUNT_WARN,
                        self.MAX_OBS_COUNT_WARN,
                    ]
                },
            )

        return OK


class AllAttributesSameCategoryValidator(BaseValidator):
    ALL_SAME_CATEGORY = "all_attributes_same_category"
    CATEGORIES_TO_CHECK = ["Hard coral"]

    def __init__(self, obs_benthic_path, **kwargs):
        self.obs_benthic_path = obs_benthic_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        obs_benthics = self.get_value(collect_record, self.obs_benthic_path) or []

        benthic_attr_ids = []
        for ob in obs_benthics:
            attr_id = valid_id(ob.get("attribute"))
            if attr_id is not None:
                benthic_attr_ids.append(attr_id)
        if len(benthic_attr_ids) < 2:
            return OK

        benthic_attr_ids = list(set(benthic_attr_ids))
        benthic_attrs = BenthicAttribute.objects.filter(id__in=benthic_attr_ids)

        attribute_categories = [ba.origin.name for ba in benthic_attrs]
        for category in self.CATEGORIES_TO_CHECK:
            if category in attribute_categories and len(set(attribute_categories)) == 1:
                return WARN, self.ALL_SAME_CATEGORY, {"category": category}

        return OK
