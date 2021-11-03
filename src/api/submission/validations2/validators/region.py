from ....models import Region, Site
from .base import OK, WARN, BaseValidator, validator_result


class RegionValidator(BaseValidator):
    NO_REGION_MATCH = "no_region_match"

    def __init__(
        self,
        attribute_model_class,
        site_path,
        observations_path,
        observation_attribute_path,
        **kwargs
    ):
        self.attribute_model_class = attribute_model_class
        self.site_path = site_path
        self.observations_path = observations_path
        self.observation_attribute_path = observation_attribute_path
        super().__init__(**kwargs)

    def _get_ok(self, observations):
        return [self.skip() for _ in observations]

    def _get_attribute_ids(self, observations):
        attribute_ids = []
        for ob in observations:
            attr_id = self.get_value(ob, self.observation_attribute_path)
            if attr_id is None:
                continue
            attribute_ids.append(attr_id)
        return attribute_ids

    def _get_attribute_region_lookup(self, attribute_ids):
        return {
            str(attr.pk): [str(r) for r in attr.regions]
            if isinstance(attr.regions, list)
            else [str(r.id) for r in attr.regions.all()]
            for attr in self.attribute_model_class.objects.filter(id__in=attribute_ids)
        }

    @validator_result
    def check_region(self, site_region, attribute_id, attribute_regions):
        if attribute_id is None:
            return OK

        if attribute_id not in attribute_regions or not attribute_regions[attribute_id]:
            return OK

        if site_region not in attribute_regions[attribute_id]:
            return WARN, self.NO_REGION_MATCH

        return OK

    def __call__(self, collect_record, **kwargs):
        site_id = self.get_value(collect_record, self.site_path)
        obs = self.get_value(collect_record, self.observations_path) or []

        site = Site.objects.get_or_none(id=site_id)
        if site is None or site.location is None:
            return self._get_ok(obs)

        regions = Region.objects.filter(geom__intersects=site.location)
        if regions.count() == 0:
            return self._get_ok(obs)

        site_region_id = str(regions[0].pk)

        attribute_ids = self._get_attribute_ids(obs)
        attr_lookup = self._get_attribute_region_lookup(set(attribute_ids))

        return [
            self.check_region(site_region_id, attribute_id, attr_lookup)
            for attribute_id in attribute_ids
        ]
