import math

from .base import OK, WARN, ERROR, BaseValidator, validator_result
from ..utils import valid_id
from ....models import BenthicAttribute


class BenthicPITObservationCountValidator(BaseValidator):
    """
    Length surveyed
    ---------------  == Observation count
     Interval size
    """

    INCORRECT_OBSERVATION_COUNT = "incorrect_observation_count"
    NON_POSITIVE = "{}_not_positive"

    def __init__(
        self, len_surveyed_path, interval_size_path, obs_benthicpits_path, **kwargs
    ):
        self.len_surveyed_path = len_surveyed_path
        self.interval_size_path = interval_size_path
        self.obs_benthicpits_path = obs_benthicpits_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        tolerance = 1
        obs_benthicpits = (
            self.get_value(collect_record, self.obs_benthicpits_path) or []
        )
        obs_benthicpit_count = len(obs_benthicpits)
        len_surveyed = self.get_value(collect_record, self.len_surveyed_path) or 0
        interval_size = self.get_value(collect_record, self.interval_size_path) or 0

        if len_surveyed <= 0:
            return ERROR, self.NON_POSITIVE.format("len_surveyed")
        if interval_size <= 0:
            return ERROR, self.NON_POSITIVE.format("interval_size")

        calc_obs_count = int(math.ceil(len_surveyed / interval_size))
        if (
            obs_benthicpit_count > calc_obs_count + tolerance
            or obs_benthicpit_count < calc_obs_count - tolerance
        ):
            return (
                ERROR,
                self.INCORRECT_OBSERVATION_COUNT,
                {"expected_count": calc_obs_count},
            )

        return OK


class AllAttributesSameCategoryValidator(BaseValidator):
    ALL_SAME_CATEGORY = "all_attributes_same_category"
    CATEGORIES_TO_CHECK = ["Hard coral"]

    def __init__(self, obs_benthicpits_path, **kwargs):
        self.obs_benthicpits_path = obs_benthicpits_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        obs_benthicpits = (
            self.get_value(collect_record, self.obs_benthicpits_path) or []
        )

        benthic_attr_ids = []
        for ob in obs_benthicpits:
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
