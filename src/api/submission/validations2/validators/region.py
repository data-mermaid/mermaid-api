from rest_framework.exceptions import ParseError

from ....exceptions import check_uuid
from ....models import Annotation, Region, Site
from ..utils import valid_id
from .base import OK, WARN, BaseValidator, validator_result


class BaseRegionValidator(BaseValidator):
    NO_REGION_MATCH = "no_region_match"

    def __init__(
        self,
        attribute_model_class,
        site_path,
        **kwargs,
    ):
        self.attribute_model_class = attribute_model_class
        self.site_path = site_path
        super().__init__(**kwargs)

    def get_records(self, collect_record, **kwargs):
        return NotImplementedError()

    def _get_ok(self, records):
        return [self.skip({"observation_id": r.get("id")}) for r in records]

    def get_observation_ids_and_attribute_ids(self, records):
        return NotImplementedError()

    def _get_attribute_region_lookup(self, attribute_ids):
        return {
            str(attr.pk): [str(r) for r in attr.regions]
            if isinstance(attr.regions, list)
            else [str(r.id) for r in attr.regions.all()]
            for attr in self.attribute_model_class.objects.filter(id__in=attribute_ids)
        }

    @validator_result
    def check_region(self, observation_id, site_region, attribute_id, attribute_regions):
        status = OK
        code = None
        context = {"observation_id": observation_id}
        if attribute_id is None:
            # Skip
            ...
        elif attribute_id not in attribute_regions or not attribute_regions[attribute_id]:
            # Skip
            ...
        elif site_region not in attribute_regions[attribute_id]:
            status = WARN
            code = self.NO_REGION_MATCH

        return status, code, context

    def __call__(self, collect_record, **kwargs):
        site_id = self.get_value(collect_record, self.site_path)
        records = self.get_records(collect_record) or []
        try:
            check_uuid(site_id)
            site = Site.objects.get_or_none(id=site_id)
            if site is None or site.location is None:
                raise ParseError()
        except ParseError:
            return self._get_ok(records)

        regions = Region.objects.filter(geom__intersects=site.location)
        if regions.count() == 0:
            return self._get_ok(records)

        site_region_id = str(regions[0].pk)

        observation_ids, attribute_ids = self.get_observation_ids_and_attribute_ids(records)
        attr_lookup = self._get_attribute_region_lookup(set(attribute_ids))

        return [
            self.check_region(observation_id, site_region_id, attribute_id, attr_lookup)
            for observation_id, attribute_id in zip(observation_ids, attribute_ids)
        ]


class RegionValidator(BaseRegionValidator):
    def __init__(
        self,
        attribute_model_class,
        site_path,
        observations_path,
        observation_attribute_path,
        **kwargs,
    ):
        self.observations_path = observations_path
        self.observation_attribute_path = observation_attribute_path
        super().__init__(attribute_model_class, site_path, **kwargs)

    def get_observation_ids_and_attribute_ids(self, observations):
        observation_ids = []
        attribute_ids = []
        for ob in observations:
            attr_id = valid_id(self.get_value(ob, self.observation_attribute_path))
            _id = ob.get("id")
            if attr_id is not None:
                attribute_ids.append(attr_id)
                observation_ids.append(_id)
        return observation_ids, attribute_ids

    def get_records(self, collect_record, **kwargs):
        return self.get_value(collect_record, self.observations_path) or []


class AnnotationRegionValidator(BaseRegionValidator):
    def __init__(
        self,
        attribute_model_class,
        site_path,
        **kwargs,
    ):
        super().__init__(attribute_model_class, site_path, **kwargs)

    def get_observation_ids_and_attribute_ids(self, observations):
        observation_ids = []
        attribute_ids = []
        for obs in observations:
            if not obs.get("id") or not obs.get("attribute"):
                continue
            observation_ids.append(obs.get("id"))
            attribute_ids.append(obs.get("attribute"))

        return observation_ids, attribute_ids

    def get_records(self, collect_record, **kwargs):
        collect_record_id = collect_record.get("id")
        if not collect_record_id:
            return []

        annos = Annotation.objects.select_related("point", "point__image").filter(
            is_confirmed=True, point__image__collect_record_id=collect_record_id
        )

        records = []
        for anno in annos:
            growth_form = ""
            if anno.growth_form:
                growth_form = anno.growth_form.pk

            uid = f"{anno.point.image.pk}::{anno.benthic_attribute.id}::{growth_form}"
            records.append({"id": uid, "attribute": str(anno.benthic_attribute.id)})

        return records
