from django.db import connection

from ....models import BLEACHING_CATEGORIES, BLEACHING_STATUS_CHOICES
from ..utils import valid_id
from .base import ERROR, OK, WARN, BaseValidator, validator_result

# Collect sends ints, ingest sends the choice key as a string
BLEACHING_STATUS_VALUES = {str(val) for val, _ in BLEACHING_STATUS_CHOICES}


def _is_blank(value):
    return value is None or value == ""


class BaseBleachingStatusValidator(BaseValidator):
    def __init__(self, include_bleaching_path, observations_path, **kwargs):
        self.include_bleaching_path = include_bleaching_path
        self.observations_path = observations_path
        super().__init__(**kwargs)

    def _include_bleaching(self, collect_record):
        return self.get_value(collect_record, self.include_bleaching_path) is True

    def _get_observations(self, collect_record):
        return self.get_value(collect_record, self.observations_path) or []

    def _get_attribute_categories(self, collect_record, observations):
        """Top-level benthic category name for each observation attribute id.

        Resolves every attribute in one recursive query and caches the lookup
        for the validation run, so validators sharing it query once.
        """
        attribute_ids = {valid_id(ob.get("attribute")) for ob in observations} - {None}
        cache = self.get_run_cache(collect_record, "benthic_attribute_categories")
        missing_ids = [str(attr_id) for attr_id in attribute_ids if str(attr_id) not in cache]
        if missing_ids:
            sql = """
                WITH RECURSIVE parents(attribute_id, id, name, parent_id) AS (
                    SELECT id, id, name, parent_id
                    FROM benthic_attribute
                    WHERE id = ANY(%s::uuid[])
                    UNION ALL
                    SELECT p.attribute_id, a.id, a.name, a.parent_id
                    FROM parents p
                    INNER JOIN benthic_attribute a ON a.id = p.parent_id
                )
                SELECT attribute_id, name
                FROM parents
                WHERE parent_id IS NULL
            """
            with connection.cursor() as cursor:
                cursor.execute(sql, [missing_ids])
                for attribute_id, name in cursor.fetchall():
                    cache[str(attribute_id)] = name

        return cache

    def _is_coral(self, observation, categories):
        attr_id = valid_id(observation.get("attribute"))
        if attr_id is None:
            return None
        return categories.get(str(attr_id)) in BLEACHING_CATEGORIES


class IncludeBleachingValidator(BaseValidator):
    """
    A missing include_bleaching key defaults to false (API, integrations). CSV import always
    sets the key, so a blank Include bleaching value is an error.
    """

    REQUIRED = "include_bleaching_required"

    def __init__(self, include_bleaching_path, **kwargs):
        self.include_bleaching_path = include_bleaching_path
        super().__init__(**kwargs)

    @validator_result
    def __call__(self, collect_record, **kwargs):
        parent_path, _, key = self.include_bleaching_path.rpartition(".")
        parent = self.get_value(collect_record, parent_path) if parent_path else collect_record
        if not isinstance(parent, dict) or key not in parent:
            return OK

        if _is_blank(parent[key]):
            return ERROR, self.REQUIRED

        return OK


class BleachingStatusValidator(BaseBleachingStatusValidator):
    """
    Per observation, a bleaching status may be set only when the sample unit
    includes bleaching, the value is a known status and the attribute is
    hard or soft coral.
    """

    NOT_ASSESSED = "bleaching_status_not_assessed"
    INVALID_STATUS = "invalid_bleaching_status"
    NOT_CORAL = "bleaching_status_not_coral"

    @validator_result
    def _check_observation(self, observation, include_bleaching, categories):
        context = {"observation_id": observation.get("id")}
        status = observation.get("bleaching_status")
        if _is_blank(status):
            return OK, None, context

        if include_bleaching is False:
            return ERROR, self.NOT_ASSESSED, context

        if str(status) not in BLEACHING_STATUS_VALUES:
            context["bleaching_status"] = status
            return ERROR, self.INVALID_STATUS, context

        if self._is_coral(observation, categories) is False:
            return ERROR, self.NOT_CORAL, context

        return OK, None, context

    def __call__(self, collect_record, **kwargs):
        observations = self._get_observations(collect_record)
        include_bleaching = self._include_bleaching(collect_record)
        categories = {}
        if include_bleaching:
            categories = self._get_attribute_categories(collect_record, observations)

        return [self._check_observation(ob, include_bleaching, categories) for ob in observations]


class BleachingStatusMissingValidator(BaseBleachingStatusValidator):
    """
    When the sample unit includes bleaching, hard and soft coral observations
    without a status are stored as NULL (not assessed) and are left out of
    percent bleached. Warn once per sample unit so the diver confirms it.
    """

    MISSING_BLEACHING_STATUS = "missing_bleaching_status"

    @validator_result
    def __call__(self, collect_record, **kwargs):
        if not self._include_bleaching(collect_record):
            return OK

        observations = self._get_observations(collect_record)
        categories = self._get_attribute_categories(collect_record, observations)
        missing_count = sum(
            1
            for ob in observations
            if _is_blank(ob.get("bleaching_status")) and self._is_coral(ob, categories)
        )
        if missing_count > 0:
            return WARN, self.MISSING_BLEACHING_STATUS, {"count": missing_count}

        return OK
