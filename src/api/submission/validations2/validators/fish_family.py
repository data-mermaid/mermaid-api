from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import FishAttributeView, Site
from .base import OK, WARN, BaseValidator, validator_result


class FishFamilySubsetValidator(BaseValidator):
    INVALID_FISH_FAMILY = "not_part_of_fish_family_subset"

    def __init__(self, observations_path, site_path, **kwargs):
        self.observations_path = observations_path
        self.site_path = site_path
        super().__init__(**kwargs)

    @validator_result
    def check_fish_family_subset(
        self, observation, fish_family_subset, fish_family_lookup
    ):
        fish_attribute_id = fish_family_lookup[observation["fish_attribute"]]
        status = OK
        code = None
        context = {"observation_id": observation.get("id")}
        if fish_attribute_id not in fish_family_subset:
            status = WARN
            code = self.INVALID_FISH_FAMILY
            
        return status, code, context

    def _get_ok(self, observations):
        return [self.skip() for _ in observations]

    def __call__(self, collect_record, **kwargs):
        observations = self.get_value(collect_record, self.observations_path) or []
        site_id = self.get_value(collect_record, self.site_path)

        try:
            check_uuid(site_id)
            site = Site.objects.get_or_none(id=site_id)
        except ParseError:
            site = None

        if site is None:
            return self._get_ok(observations)

        project = site.project
        project_data = project.data or {}
        fish_family_subset = (project_data.get("settings") or {}).get(
            "fishFamilySubset"
        )

        if (
            isinstance(fish_family_subset, list) is False
            or len(fish_family_subset) == 0
        ):
            return self._get_ok(observations)

        fish_attribute_ids = {ob.get("fish_attribute") for ob in observations}
        fish_family_lookup = {
            str(fa.id): str(fa.id_family)
            for fa in FishAttributeView.objects.filter(id__in=fish_attribute_ids)
        }

        return [
            self.check_fish_family_subset(ob, fish_family_subset, fish_family_lookup)
            for ob in observations
        ]
