import functools
import itertools
import inspect
import json
import math
import datetime

from . import utils

from api.exceptions import check_uuid
from api.models import (
    BeltTransectWidth,
    BenthicAttribute,
    BenthicTransect,
    FishAttribute,
    FishSpecies,
    FishBeltTransect,
    HabitatComplexityScore,
    Management,
    Observer,
    QuadratCollection,
    Site,
)
from api.utils import calc_biomass_density
from api.utils import get_related_transect_methods
from django.contrib.gis.geos import Polygon
from django.contrib.gis.measure import Distance
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import ugettext as _
from rest_framework.exceptions import ParseError

IGNORE = "ignore"
ERROR = "error"
WARN = "warning"
OK = "ok"
STATUSES = (ERROR, IGNORE, OK, WARN)
# WARNING MESSAGES
LikeMatchWarning = "{}: Similar records detected"
RecordDoesntExist = "{}: Record doesn't exist"
MissingRecordSimilarity = "{} record not available for similarity validation"


def needs_instance(message):
    def _needs_instance(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            # Assume it's a method.
            self = args[0]
            if self.instance is None:
                return self.error(self.identifier, _(message.format(self.name)))

            return func(*args, **kwargs)

        return wrapped

    return _needs_instance


class ObservationsMixin(object):
    @classmethod
    def get_observation_key(cls, data):
        data = data or dict()
        for key in data:
            if "obs_" in key and isinstance(data[key], list):
                return key

        return None

    @classmethod
    def get_observations(cls, data):
        key = cls.get_observation_key(data)
        if key is not None:
            return data[key]

        return []


class BenthicAttributeMixin(ObservationsMixin):
    ALL_HARD_CORAL_MSG = _("All observations are Hard coral")

    def _validate_by_origin(self, origin_name, warn_message):
        obs = self.get_observations(self.data)
        benthic_attr_ids = []
        for ob in obs:
            attr_id = ob.get("attribute")
            if attr_id is not None:
                benthic_attr_ids.append(attr_id)

        benthic_attr_ids = list(set(benthic_attr_ids))
        benthic_attrs = BenthicAttribute.objects.filter(id__in=benthic_attr_ids)

        origin_parents = [ba.origin.name for ba in benthic_attrs]
        if origin_name in origin_parents and len(set(origin_parents)) == 1:
            return WARN, warn_message

        return OK, ""

    def validate_hard_coral(self):
        result, message = self._validate_by_origin(
            "Hard coral", self.ALL_HARD_CORAL_MSG
        )
        return self.log(self.identifier, result, message)


class FishAttributeMixin(ObservationsMixin):
    MAX_SPECIES_SIZE_TMPL = "Fish size greater than {} maximum: {}"

    def validate_fish_lengths(self):
        obs = self.get_observations(self.data)
        obs = [o for o in obs if o.get("fish_attribute") is not None]
        fish_attr_ids = [o.get("fish_attribute") for o in obs]
        fish_attr_ids = list(set(fish_attr_ids))

        # only validate lengths at species level until we know how to aggregate to genus
        fish_attrs = (
            FishSpecies.objects.filter(id__in=fish_attr_ids)
            .select_related("genus__name")
            .values("id", "genus__name", "name", "max_length")
        )
        for ob in obs:
            try:
                fish = [
                    f
                    for f in fish_attrs
                    if str(f.get("id")) == ob.get("fish_attribute")
                ][0]
                max_length = fish.get("max_length")
                obs_size = ob.get("size")
                if (
                    max_length is not None
                    and obs_size is not None
                    and obs_size > max_length
                ):
                    fish_name = "{} {}".format(
                        fish.get("genus__name"), fish.get("name")
                    )
                    warn_message = self.MAX_SPECIES_SIZE_TMPL.format(
                        fish_name, max_length
                    )
                    return self.log(self.identifier, WARN, warn_message)
            except IndexError:
                pass

        return OK, ""


class ValidationLogger(object):
    def __init__(self):
        self.logs = dict()

    def _validate_status(self, status):
        if status not in STATUSES:
            raise ValueError("{}  is not a valid status".format(status))

    def ignore_warning(self, identifier, validation):
        self.logs[identifier][validation]["status"] = IGNORE

    def log(self, identifier, status, message, **kwargs):
        o = dict()
        # Define validation first and then allow
        # overwriting with kwargs
        validation = kwargs.pop("validation", None) or inspect.stack()[1][3]
        o.update(kwargs)
        o["message"] = message
        self._validate_status(status)
        o["status"] = status

        if identifier not in self.logs:
            self.logs[identifier] = dict()

        if validation not in self.logs[identifier]:
            self.logs[identifier][validation] = dict()

        self.logs[identifier][validation].update(o)
        return status

    def error(self, identifier, message="", **kwargs):
        validation = kwargs.pop("validation", None) or inspect.stack()[1][3]
        return self.log(identifier, ERROR, message, validation=validation, **kwargs)

    def ok(self, identifier, message="", **kwargs):
        validation = kwargs.pop("validation", None) or inspect.stack()[1][3]
        return self.log(identifier, OK, message, validation=validation, **kwargs)

    def warning(self, identifier, message="", **kwargs):
        validation = kwargs.pop("validation", None) or inspect.stack()[1][3]
        return self.log(identifier, WARN, message, validation=validation, **kwargs)

    def log_record(self, identifier, validation, record):
        if identifier not in self.logs:
            self.logs[identifier] = dict()

        self.logs[identifier][validation] = record
        status = record.get("status")
        self._validate_status(status)
        return status


class BaseValidation(ValidationLogger):
    _validation_prefix = "validate_"

    def __init__(self, previous_validations=None):
        super(BaseValidation, self).__init__()
        self.previous_validations = previous_validations

    def _get_validation_method_names(self):
        validations = []
        objs = inspect.getmembers(self)
        for obj in objs:
            if inspect.ismethod(obj[1]) and (
                obj[0].startswith(self._validation_prefix)
            ):
                validations.append(obj[0])

        return validations

    def _get_previous_validation(self, validation_name):
        validations = self.previous_validations
        if isinstance(validations, dict) is False:
            return None

        return validations.get(validation_name)

    def _ignore_validation(self, validation_name):
        v = self._get_previous_validation(validation_name) or dict()
        return v.get("status") == IGNORE

    def validate(self):
        has_warns = False
        has_errors = False
        for validation_name in self._get_validation_method_names():
            if self._ignore_validation(validation_name) is True:
                self.log_record(
                    self.identifier,
                    validation_name,
                    self._get_previous_validation(validation_name),
                )
                continue

            status = getattr(self, validation_name)()
            if status == WARN:
                has_warns = True
            elif status == ERROR:
                has_errors = True

        if has_errors:
            return ERROR

        elif has_warns:
            return WARN

        return OK


class DataValidation(BaseValidation):
    def __init__(self, data, previous_validations=None):
        super(DataValidation, self).__init__(previous_validations=previous_validations)
        self.data = data


class ModelValidation(BaseValidation):
    model = None
    instance = None
    identifier = None
    name = None

    def __init__(self, pk, previous_validations=None):
        super(ModelValidation, self).__init__(previous_validations=previous_validations)
        self.setinstance(pk)

    def setinstance(self, pk):
        if pk is None:
            return

        try:
            # Check if id is valid UUID
            check_uuid(pk)
            self.instance = self.model.objects.get(id=pk)
        except (ObjectDoesNotExist, ParseError):
            self.instance = None

    def validate_exists(self):
        if self.instance is None:
            return self.error(self.identifier, _(RecordDoesntExist.format(self.name)))

        return self.ok(self.identifier)


class SiteValidation(ModelValidation):

    model = Site
    name_match_percent = 0.5
    site_buffer = 100  # m

    search_bbox_size = (0.5, 0.5)
    srid = 4326
    identifier = "site"
    name = "Site"

    def _search_bounding_box(self, location):
        x = location.x
        y = location.y
        x1 = x - self.search_bbox_size[0] / 2.0
        x2 = x + self.search_bbox_size[0] / 2.0
        y1 = y - self.search_bbox_size[1] / 2.0
        y2 = y + self.search_bbox_size[1] / 2.0

        return Polygon(
            (((x1, y1), (x1, y2), (x2, y2), (x2, y1), (x1, y1))), srid=self.srid
        )

    @needs_instance(MissingRecordSimilarity)
    def validate_similar(self):
        # 1. Location within buffer
        # 2. Fuzzy match site name

        pk = self.instance.pk
        project_id = self.instance.project_id
        name = self.instance.name
        location = self.instance.location

        # Ignore self and ensure same project
        qry = self.model.objects.filter(~Q(id=pk))
        qry = qry.filter(project_id=project_id)

        if location is not None:
            qry = qry.filter(
                location__distance_lt=(location, Distance(m=self.site_buffer))
            )

        # Fuzzy name match
        qry = qry.annotate(similarity=TrigramSimilarity("name", name))
        qry = qry.filter(similarity__gte=self.name_match_percent)
        qry = qry.order_by("-similarity")

        results = qry[0:3]
        if results.count() > 0:
            matches = [r.id for r in results]
            data = dict(matches=matches)
            return self.warning(
                self.identifier, _(LikeMatchWarning.format(self.name)), data=data
            )

        return self.ok(self.identifier)


class ManagementValidation(ModelValidation):

    model = Management
    name_match_percent = 0.5
    identifier = "management"
    name = "Management Regime"

    @needs_instance(MissingRecordSimilarity)
    def validate_similar(self):
        pk = self.instance.pk
        project_id = self.instance.project_id
        name = self.instance.name

        # Finds MRs that:
        # - are not self and in same project, and fuzzy match name, AND
        # - belong to SEs with the same site (but diff MR) as any SE with associated SUs that uses this MR OR
        # - belong to CRs with the same site (but diff MR) as any CR that uses this MR
        # When we make MR a FK of site, this can be replaced with simple ORM site lookup
        match_sql = """
            WITH se_mrs AS (
                SELECT DISTINCT management_id, site_id FROM
                sample_event ses
                INNER JOIN management ON (ses.management_id = management.id)
                LEFT JOIN transect_benthic tbs ON (ses.id = tbs.sample_event_id)
                LEFT JOIN transect_belt_fish tbfs ON (ses.id = tbfs.sample_event_id)
                LEFT JOIN quadrat_collection qcs ON (ses.id = qcs.sample_event_id)
                WHERE management.project_id = %(project_id)s
                AND (
                    tbs.id IS NOT NULL OR
                    tbfs.id IS NOT NULL OR
                    qcs.id IS NOT NULL
                )
            ),
            cr_mrs AS (
                SELECT DISTINCT (cr.data #>> '{sample_event, management}')::text AS "management_id",
                (cr.data #>> '{sample_event, site}')::text AS "site_id"
                FROM api_collectrecord cr
                WHERE cr.project_id = %(project_id)s
            ),
            se_diff_mrs AS (
                SELECT DISTINCT diffses.management_id FROM
                sample_event ses
                INNER JOIN sample_event diffses ON (ses.site_id = diffses.site_id)
                LEFT JOIN transect_benthic tbs ON (ses.id = tbs.sample_event_id)
                LEFT JOIN transect_belt_fish tbfs ON (ses.id = tbfs.sample_event_id)
                LEFT JOIN quadrat_collection qcs ON (ses.id = qcs.sample_event_id)
                LEFT JOIN transect_benthic tb ON (diffses.id = tb.sample_event_id)
                LEFT JOIN transect_belt_fish tbf ON (diffses.id = tbf.sample_event_id)
                LEFT JOIN quadrat_collection qc ON (diffses.id = qc.sample_event_id)
                WHERE ses.management_id = %(mr_id)s
                AND diffses.management_id != %(mr_id)s
                AND (
                    tb.id IS NOT NULL OR
                    tbf.id IS NOT NULL OR
                    qc.id IS NOT NULL
                )
                AND (
                    tbs.id IS NOT NULL OR
                    tbfs.id IS NOT NULL OR
                    qcs.id IS NOT NULL
                )
            ),
            cr_diff_mrs AS (
                SELECT DISTINCT (diff_cr_mans.data #>> '{sample_event, management}')::text AS "management_id"
                FROM api_collectrecord self_cr_mans
                INNER JOIN api_collectrecord diff_cr_mans ON (
                    (self_cr_mans.data #>> '{sample_event, site}') = (diff_cr_mans.data #>> '{sample_event, site}')
                )
                WHERE (
                    (self_cr_mans.data #>> '{sample_event, management}')::text = %(mr_id)s AND
                    (diff_cr_mans.data #>> '{sample_event, management}')::text != %(mr_id)s
                )
            )
            SELECT management.id, management.project_id, management.name, management.name_secondary,
            SIMILARITY(management.name, %(name)s) AS "similarity"
            FROM management
            WHERE (
                NOT (management.id = %(mr_id)s)
                AND management.project_id = %(project_id)s
                AND SIMILARITY(management.name, %(name)s) >= %(match_percent)s
                AND (
                    management.id IN (SELECT * FROM se_diff_mrs)
                    OR management.id::text IN (SELECT * FROM cr_diff_mrs)
                    OR management.id IN (SELECT * FROM (
                        SELECT CASE
                        WHEN se_mrs.management_id != %(mr_id)s THEN se_mrs.management_id
                        WHEN cr_mrs.management_id::text != %(mr_id)s THEN cr_mrs.management_id::uuid
                        END
                        FROM se_mrs
                        INNER JOIN cr_mrs ON (se_mrs.site_id::text = cr_mrs.site_id)
                        WHERE (se_mrs.management_id = %(mr_id)s AND cr_mrs.management_id != %(mr_id)s) OR
                        (cr_mrs.management_id = %(mr_id)s AND se_mrs.management_id != %(mr_id)s)
                    ) AS se_cr)
                )
            )
            ORDER BY similarity DESC
        """
        params = {
            "mr_id": str(pk),
            "project_id": str(project_id),
            "name": name,
            "match_percent": self.name_match_percent,
        }

        qry = self.model.objects.raw(match_sql, params)
        results = qry[0:3]
        if len(results) > 0:
            matches = [r.id for r in results]
            data = dict(matches=matches)
            return self.warning(
                self.identifier, _(LikeMatchWarning.format(self.name)), data=data
            )

        return True


class ObserverValidation(ModelValidation):

    model = Observer
    identifier = "observers"
    name = "Observer"


class ObservationsValidation(DataValidation, ObservationsMixin):
    OBS_ALL_EQUAL = _("All observations are the same")

    def _to_json(self, d):
        return json.dumps(d, sort_keys=True)

    @property
    def identifier(self):
        data = self.data or dict()
        return self.get_observation_key(data)

    def validate_all_equal(self):
        data = self.data or dict()
        obs_key = self.get_observation_key(data)
        obs = self.get_observations(data)

        if len(obs) < 2:
            return self.ok(obs_key)

        items = [set(o.items()) for o in obs]
        check_item = items.pop()

        for item in items:
            if item != check_item:
                return self.ok(obs_key)

        return self.warning(obs_key, self.OBS_ALL_EQUAL)


class EmptyListValidation(BaseValidation):
    def __init__(self, identifier, value, error_message, previous_validations=None):
        super(EmptyListValidation, self).__init__(
            previous_validations=previous_validations
        )
        self.identifier = identifier
        self.value = value
        self.error_message = error_message

    def validate_list(self):
        if not self.value:
            return self.error(self.identifier, self.error_message)

        return self.ok(self.identifier)


class BenthicObservationCountMixin(ObservationsMixin):
    """
    Length surveyed
    ---------------  == Observation Count
     Interval size
    """

    identifier = None
    OBS_COUNT_TMPL = "Expected number of observations to be {}, {} observation{} found"
    CALC_ERROR_TMPL = _(
        "Expected number of observations cannot be calculated; missing required fields."
    )

    def validate_observation_count(self):
        obs = BenthicObservationCountMixin.get_observations(self.data)
        transect = self.data.get("benthic_transect") or {}
        len_surveyed = transect.get("len_surveyed")
        interval_size = self.data.get("interval_size") or 0

        obs_count = len(obs)
        calc_obs_count = None
        if len_surveyed is not None and interval_size != 0:
            calc_obs_count = int(math.ceil(len_surveyed / interval_size))

        if calc_obs_count is None:
            msg = self.CALC_ERROR_TMPL
            return self.error(self.identifier, msg)
        elif calc_obs_count != obs_count:
            plural = ""
            if obs_count != 1:
                plural = "s"
            msg = self.OBS_COUNT_TMPL.format(calc_obs_count, obs_count, plural)
            msg = _(msg)
            return self.error(self.identifier, msg)

        return self.ok(self.identifier)


class ObsBenthicLITValidation(DataValidation, BenthicAttributeMixin):
    identifier = "obs_benthic_lits"
    TOTAL_LENGTH_WARN = str(
        _("Total length of observations must equal transect length")
    )

    def validate_total_length(self):
        obs = self.data.get("obs_benthic_lits") or []
        benthic_transect = self.data.get("benthic_transect") or {}
        # Convert to cm
        transect_length = (benthic_transect.get("len_surveyed") or 0.0) * 100
        obs_len = sum([ob.get("length") or 0.0 for ob in obs])
        if obs_len != transect_length:
            return self.warning(self.identifier, self.TOTAL_LENGTH_WARN)

        return self.ok(self.identifier)


class ObsBenthicPITValidation(
    DataValidation, BenthicAttributeMixin, BenthicObservationCountMixin
):
    identifier = "obs_benthic_pits"


class ValueInRangeValidation(BaseValidation):
    """
    Check if value is between value_range.  The value range
    validation is inclusive of min/max values.
    """

    DEFAULT_MSG = _("Value out of range")

    def __init__(
        self,
        identifier,
        value,
        value_range,
        status=ERROR,
        message=None,
        previous_validations=None,
        value_range_operators=("<", ">"),
    ):

        super(ValueInRangeValidation, self).__init__(
            previous_validations=previous_validations
        )
        self.identifier = identifier
        self.value = value
        self.value_range = value_range
        self.value_range_operators = value_range_operators
        self._status = status
        self.message = message or self.DEFAULT_MSG

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, val):
        if val not in (WARN, ERROR):
            raise ValueError("{} not valid validation status".format(val))

        self._status = val

    def _op(self, val1, operator, val2):

        if operator == "==":
            return val1 == val2
        elif operator == "<=":
            return val1 <= val2
        elif operator == "<":
            return val1 < val2
        elif operator == ">=":
            return val1 >= val2
        elif operator == ">":
            return val1 > val2

        raise ValueError("Operator not supported")

    def validate_range(self):
        is_valid = True
        if self.value is None:
            is_valid = False
        else:
            if self.value_range[0] is not None and self._op(
                self.value, self.value_range_operators[0], self.value_range[0]
            ):
                is_valid = False
            if len(self.value_range) > 1 and self._op(
                self.value, self.value_range_operators[1], self.value_range[1]
            ):
                is_valid = False

        if is_valid is False:
            return self.log(self.identifier, self.status, self.message)

        return self.ok(self.identifier)


class ObsFishBeltValidation(DataValidation, FishAttributeMixin):
    identifier = "obs_belt_fishes"

    MIN_OBS_COUNT_TMPL = "Fewer than {} observations"
    MAX_OBS_COUNT_TMPL = "Greater than or equal to {} observations"
    DENSITY_GT_TMPL = "Fish biomass greater than {} kg/ha"
    DENSITY_LT_TMPL = "Fish biomass less than {} kg/ha"
    FISH_COUNT_MIN_TMPL = "Total fish count less than {}"

    MIN_OBS_COUNT_WARN = 5
    MAX_OBS_COUNT_WARN = 200
    OBS_GT_DENSITY = 2000  # kg/ha
    OBS_LT_DENSITY = 50  # kg/ha
    FISH_COUNT_MIN = 10

    def __init__(self, data, previous_validations=None):
        super(ObsFishBeltValidation, self).__init__(
            data, previous_validations=previous_validations
        )

        self.MIN_OBS_COUNT_MSG = str(
            _(self.MIN_OBS_COUNT_TMPL.format(self.MIN_OBS_COUNT_WARN))
        )
        self.MAX_OBS_COUNT_MSG = str(
            _(self.MAX_OBS_COUNT_TMPL.format(self.MAX_OBS_COUNT_WARN))
        )
        self.DENSITY_GT_MSG = str(
            _(self.DENSITY_GT_TMPL.format(self.OBS_GT_DENSITY))
        )
        self.DENSITY_LT_MSG = str(
            _(self.DENSITY_LT_TMPL.format(self.OBS_LT_DENSITY))
        )
        self.FISH_COUNT_MIN_MSG = str(
            _(self.FISH_COUNT_MIN_TMPL.format(self.FISH_COUNT_MIN))
        )

    def validate_observation_count(self):
        observations = self.data.get("obs_belt_fishes") or []
        count = len(observations)
        if count < self.MIN_OBS_COUNT_WARN:
            return self.warning(self.identifier, self.MIN_OBS_COUNT_MSG)

        elif count >= self.MAX_OBS_COUNT_WARN:
            return self.warning(self.identifier, self.MAX_OBS_COUNT_MSG)

        return self.ok(self.identifier)

    def validate_observation_density(self):
        observations = self.data.get("obs_belt_fishes") or []
        transect = self.data.get("fishbelt_transect") or {}
        len_surveyed = transect.get("len_surveyed")
        width_id = transect.get("width")
        try:
            _ = check_uuid(width_id)
            width = BeltTransectWidth.objects.get(id=width_id).val
        except (BeltTransectWidth.DoesNotExist, ParseError):
            width = None

        # Create a fish attribute constants lookup
        fishattribute_ids = []
        for o in observations:
            fish_attribute = o.get("fish_attribute")
            if not fish_attribute:
                continue
            fishattribute_ids.append(fish_attribute)

        fish_attr_lookup = {
            str(fa.id): fa.get_biomass_constants()
            for fa in FishAttribute.objects.filter(id__in=fishattribute_ids)
        }

        densities = []
        for obs in observations:
            count = obs.get("count")
            size = obs.get("size")
            fish_attribute = obs.get("fish_attribute")
            constants = fish_attr_lookup.get(fish_attribute) or [None, None, None]
            density = calc_biomass_density(count, size, len_surveyed, width, *constants)
            densities.append(density)

        total_density = sum([d for d in densities if d is not None])
        if total_density > self.OBS_GT_DENSITY:
            return self.warning(self.identifier, self.DENSITY_GT_MSG)

        elif total_density < self.OBS_LT_DENSITY:
            return self.warning(self.identifier, self.DENSITY_LT_MSG)

        return self.ok(self.identifier)

    def validate_fish_count(self):
        obs = self.data.get("obs_belt_fishes") or []
        num_fish = sum([obs.get("count") or 0 for obs in obs])
        if num_fish < self.FISH_COUNT_MIN:
            return self.warning(self.identifier, self.FISH_COUNT_MIN_MSG)

        return self.ok(self.identifier)


class ObsHabitatComplexitiesValidation(DataValidation, BenthicObservationCountMixin):
    identifier = "obs_habitat_complexities"

    def validate_scores(self):
        obs = self.get_observations(self.data)
        hcs_ids = [
            str(pk)
            for pk in HabitatComplexityScore.objects.values_list("id", flat=True)
        ]
        for ob in obs:
            if ob.get("score") not in hcs_ids:
                return self.error(
                    self.identifier,
                    RecordDoesntExist.format("Habitat Complexity Score"),
                )

        return self.ok(self.identifier)


class BenthicTransectValidation(DataValidation):
    DUPLICATE_MSG = _("Transect already exists")
    RELATIVE_DEPTH_MSG = _("Relative depth not valid")
    SITE_MSG = _("Benthic Transect is not valid")
    identifier = "benthic_transect"

    def validate_duplicate(self):
        protocol = self.data.get("protocol")
        sample_event = self.data.get("sample_event") or {}
        benthic_transect = self.data.get("benthic_transect") or {}

        number = benthic_transect.get("number")
        label = benthic_transect.get("label") or ""
        relative_depth = sample_event.get("relative_depth")
        if relative_depth == "":
            relative_depth = None

        site = sample_event.get("site") or None
        if site == "":
            site = None

        if relative_depth is not None:
            try:
                _ = check_uuid(relative_depth)
            except ParseError:
                return self.error(self.identifier, self.RELATIVE_DEPTH_MSG)

        try:
            _ = check_uuid(site)
        except ParseError:
            return self.error(self.identifier, self.SITE_MSG)

        qry = {
            "number": number,
            "label": label,
            "sample_event__relative_depth": relative_depth,
            "sample_event__site": site,
        }

        results = BenthicTransect.objects.select_related().filter(**qry)
        for result in results:
            transect_methods = get_related_transect_methods(result)
            for transect_method in transect_methods:
                if transect_method.protocol == protocol:
                    return self.warning(self.identifier, self.DUPLICATE_MSG)
        return self.ok(self.identifier)


class FishBeltTransectValidation(DataValidation):
    DUPLICATE_MSG = _("Transect already exists")
    RELATIVE_DEPTH_MSG = _("Relative depth not valid")
    SITE_MSG = _("Fish Belt Transect is not valid")
    identifier = "fishbelt_transect"

    def validate_duplicate(self):
        protocol = self.data.get("protocol")
        sample_event = self.data.get("sample_event") or {}
        fishbelt_transect = self.data.get("fishbelt_transect") or {}

        number = fishbelt_transect.get("number")
        label = fishbelt_transect.get("label") or ""
        width = fishbelt_transect.get("width")
        relative_depth = sample_event.get("relative_depth")
        if relative_depth == "":
            relative_depth = None

        site = sample_event.get("site") or None
        if site == "":
            site = None

        if relative_depth is not None:
            try:
                _ = check_uuid(relative_depth)
            except ParseError:
                return self.error(self.identifier, self.RELATIVE_DEPTH_MSG)

        try:
            _ = check_uuid(site)
        except ParseError:
            return self.error(self.identifier, self.SITE_MSG)

        qry = {
            "number": number,
            "label": label,
            "sample_event__relative_depth": relative_depth,
            "sample_event__site": site,
            "width_id": width,
        }

        results = FishBeltTransect.objects.select_related().filter(**qry)
        for result in results:
            transect_methods = get_related_transect_methods(result)
            for transect_method in transect_methods:
                if transect_method.protocol == protocol:
                    return self.warning(self.identifier, self.DUPLICATE_MSG)
        return self.ok(self.identifier)


class SerializerValidation(BaseValidation):
    def __init__(self, collect_record, request, previous_validations=None):
        super(SerializerValidation, self).__init__(previous_validations)
        self.collect_record = collect_record
        self.request = request
        self.status = None
        self.results = None

    def _dry_validation_write(self):
        status, results = utils.write_collect_record(
            self.collect_record, self.request, dry_run=True
        )
        self.status = status
        self.results = results

    def _log_validation_errors(self):
        self.results = self.results or dict()
        for identifier, messages in self.results.items():
            for message in messages:
                self.error(identifier, message, validation="validate_system")

        return ERROR if self.results.keys() else OK

    def validate(self):
        self._dry_validation_write()
        serializer_result = self._log_validation_errors()
        base_result = super(SerializerValidation, self).validate()

        results = (base_result, serializer_result)

        if ERROR in results:
            return ERROR

        elif WARN in results:
            return WARN

        elif len(results) == results.count(OK):
            return OK


class ObsBleachingMixin(object):
    @classmethod
    def get_observations(cls, data):
        return data.get(cls.identifier) or []


class ObsBenthicPercentCoveredValidation(DataValidation, ObsBleachingMixin):
    identifier = "obs_quadrat_benthic_percent"
    LESS_EQUAL_0_MSG = "Percent cover {} is less than or equal to 0"
    GREATER_100_MSG = "Percent cover {} is greater than 100"

    def _check_percent_value(self, value, msg_param):
        if value < 0:
            return ERROR, self.LESS_EQUAL_0_MSG.format(msg_param)
        elif value > 100:
            return ERROR, self.GREATER_100_MSG.format(msg_param)
        return OK, ""

    def _validate_percent_values(self, values, validation, msg_param="value"):
        for val in values:
            result, msg = self._check_percent_value(val, msg_param)
            if result == ERROR:
                return self.error(self.identifier, msg, validation=validation)
        return OK

    def _validate_percent_value_total(self, values, validation):
        total = 0
        for v in values:
            try:
                total += float(v)
            except (TypeError, ValueError):
                pass
        return self._validate_percent_values([total], validation, msg_param="total")

    def validate_percent_values(self):
        obs = self.get_observations(self.data)
        for ob in obs:
            percent_hard = ob.get("percent_hard") or 0
            percent_soft = ob.get("percent_soft") or 0
            percent_algae = ob.get("percent_algae") or 0
            values = [percent_hard, percent_soft, percent_algae]
            if (
                self._validate_percent_values(values, "validate_percent_values")
                == ERROR
            ):
                return ERROR

            if (
                self._validate_percent_value_total(values, "validate_percent_values")
                == ERROR
            ):
                return ERROR

        return self.ok(self.identifier)

    def validate_quadrat_count(self):
        obs = self.get_observations(self.data)
        if len(obs) < 5:
            return self.warning(
                self.identifier,
                _("Observations - Percent Cover: Fewer than 5 observations"),
            )
        return self.ok(self.identifier)


class ObsColoniesBleachedValidation(DataValidation, ObsBleachingMixin):
    identifier = "obs_colonies_bleached"

    def _cast_integer(self, val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    def _get_colony_counts(self, ob):
        return [
            self._cast_integer(ob.get("count_normal")),
            self._cast_integer(ob.get("count_pale")),
            self._cast_integer(ob.get("count_20")),
            self._cast_integer(ob.get("count_50")),
            self._cast_integer(ob.get("count_80")),
            self._cast_integer(ob.get("count_100")),
            self._cast_integer(ob.get("count_dead")),
        ]

    def validate_colony_count(self):
        # WARN
        obs = self.get_observations(self.data)
        total_count = sum([sum(self._get_colony_counts(ob)) for ob in obs])
        if total_count > 600:
            return self.warning(self.identifier, _("Greater than 600 total colonies"))
        return self.ok(self.identifier)

    def validate_duplicate_genus_growth(self):
        # ERROR
        obs = self.get_observations(self.data) or []
        # Obs need to be sorted before grouped
        obs.sort(key=lambda e: "{}_{}".format(e.get("attribute"), e.get("growth_form")))
        grouped_obs = itertools.groupby(
            obs,
            key=lambda ob: "{}_{}".format(ob.get("attribute"), ob.get("growth_form")),
        )

        dup_obs_genus_growth = []
        for ignore, dup_obs in grouped_obs:
            records = list(dup_obs)
            if len(records) < 2:
                continue

            record = records[0]
            dup_obs_genus_growth.append(
                dict(
                    attribute=record.get("attribute"),
                    growth_form=record.get("growth_form"),
                )
            )

        if dup_obs_genus_growth:
            return self.error(
                self.identifier,
                _("Duplicate genus and growth form"),
                data=dup_obs_genus_growth,
            )

        return self.ok(self.identifier)


class QuadratCollectionValidation(DataValidation):
    identifier = "quadrat_collection"
    DUPLICATE_MSG = _("Quadrat collection already exists")
    INVALID_MSG = _("Quadrat Collection is not valid")

    def validate_duplicate(self):
        protocol = self.data.get("protocol")
        sample_event = self.data.get("sample_event") or {}
        quadrat_collection = self.data.get("quadrat_collection") or {}

        label = quadrat_collection.get("label") or ""

        sample_date = sample_event.get("sample_date")
        if sample_date == "":
            sample_date = None

        sample_time = sample_event.get("sample_time")
        if sample_time == "":
            sample_time = None

        site = sample_event.get("site") or None
        if site == "":
            site = None

        profiles = [o.get("profile") for o in self.data.get("observers") or []]

        try:
            for profile in profiles:
                _ = check_uuid(profile)
        except ParseError:
            return self.error(self.identifier, self.INVALID_MSG)

        try:
            _ = check_uuid(site)
        except ParseError:
            return self.error(self.identifier, self.INVALID_MSG)

        qry = {
            "label": label,
            "sample_event__site": site,
            "sample_event__sample_time": sample_time,
            "sample_event__sample_date": sample_date,
        }
        queryset = QuadratCollection.objects.filter(**qry)
        for profile in profiles:
            queryset = queryset.filter(
                bleaching_quadrat_collection__observers__profile_id=profile
            )

        for result in queryset:
            transect_methods = get_related_transect_methods(result)
            for transect_method in transect_methods:
                if transect_method.protocol == protocol:
                    return self.error(self.identifier, self.DUPLICATE_MSG)

        return self.ok(self.identifier)
