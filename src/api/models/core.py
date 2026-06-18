import datetime
import json
import logging
import uuid

from django.contrib.gis.db import models
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.utils.encoders import JSONEncoder
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TagBase

from ..utils import get_sample_unit_number
from ..utils.related import get_related_project
from .base import (
    APPROVAL_STATUSES,
    AreaMixin,
    BaseChoiceModel,
    BaseModel,
    Country,
    JSONMixin,
    Profile,
)

INCLUDE_OBS_TEXT = _("include observation in aggregations/analyses?")

logger = logging.getLogger(__name__)

BENTHICLIT_PROTOCOL = "benthiclit"
BENTHICPIT_PROTOCOL = "benthicpit"
FISHBELT_PROTOCOL = "fishbelt"
HABITATCOMPLEXITY_PROTOCOL = "habitatcomplexity"
BLEACHINGQC_PROTOCOL = "bleachingqc"
BENTHICPQT_PROTOCOL = "benthicpqt"
MACROINVERTEBRATE_PROTOCOL = "macroinvertebrate"

PROTOCOL_MAP = {
    BENTHICLIT_PROTOCOL: "Benthic LIT",
    BENTHICPQT_PROTOCOL: "Benthic Photo Quadrat Transect",
    BENTHICPIT_PROTOCOL: "Benthic PIT",
    FISHBELT_PROTOCOL: "Fish Belt",
    HABITATCOMPLEXITY_PROTOCOL: "Habitat Complexity",
    BLEACHINGQC_PROTOCOL: "Bleaching Quadrat Collection",
    MACROINVERTEBRATE_PROTOCOL: "Macroinvertebrate Belt",
}


class Tag(TagBase, BaseModel):
    description = models.TextField(blank=True)
    status = models.PositiveSmallIntegerField(
        choices=APPROVAL_STATUSES, default=APPROVAL_STATUSES[-1][0]
    )

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = [
            "name",
        ]

    def __str__(self):
        return _("%s") % self.name


class UUIDTaggedItem(GenericUUIDTaggedItemBase):
    tag = models.ForeignKey(Tag, related_name="tagged_items", on_delete=models.CASCADE)


class Project(BaseModel, JSONMixin):
    OPEN = 90
    TEST = 80
    LOCKED = 10
    STATUSES = (
        (OPEN, _("open")),
        (TEST, _("test")),
        (LOCKED, _("locked")),
    )

    PRIVATE = 10
    PUBLIC_SUMMARY = 50
    PUBLIC = 100
    DATA_POLICIES = (
        (PRIVATE, _("private")),
        (PUBLIC_SUMMARY, _("public summary")),
        (PUBLIC, _("public")),
    )

    DATA_POLICY_CHOICES_UPDATED_ON = datetime.datetime(
        2019, 2, 2, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

    DATA_POLICY_CHOICES = (
        {
            "id": PRIVATE,
            "name": "Private",
            "description": "Collected observations and site-level summary statistics are private, but metadata for "
            "project, protocol and site, including site location and type and count of sample unit at "
            "each site, are public.",
        },
        {
            "id": PUBLIC_SUMMARY,
            "name": "Public Summary",
            "description": "Collected observations are private, but site-level summary statistics are public, "
            "along with metadata for project, protocol and site. This option is the default.",
        },
        {
            "id": PUBLIC,
            "name": "Public",
            "description": "All collected observations are public.",
        },
    )

    name = models.CharField(max_length=255, unique=True)
    notes = models.TextField(blank=True)
    status = models.PositiveSmallIntegerField(choices=STATUSES, default=OPEN)
    is_demo = models.BooleanField(default=False)
    data_policy_beltfish = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )
    data_policy_benthiclit = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )
    data_policy_benthicpit = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )
    data_policy_habitatcomplexity = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )
    data_policy_bleachingqc = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )
    data_policy_benthicpqt = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )
    data_policy_macroinvertebrate = models.PositiveSmallIntegerField(
        choices=DATA_POLICIES, default=PUBLIC_SUMMARY
    )

    tags = TaggableManager(through=UUIDTaggedItem, blank=True)
    includes_gfcr = models.BooleanField(default=False)
    user_citation = models.TextField(blank=True)

    @property
    def is_open(self):
        return self.status > self.LOCKED

    @property
    def is_locked(self):
        return self.status < self.OPEN

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super(Project, cls).from_db(db, field_names, values)
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    def save(self, *args, **kwargs):
        if self.is_demo:
            self.status = self.TEST

        old_status = None
        if self.pk and hasattr(self, "_loaded_values"):
            old_status = self._loaded_values.get("status")

        notify_fields = [
            f.name
            for f in self._meta.get_fields(include_parents=False, include_hidden=False)
            if f.editable and f.name != "updated_by"
        ]
        if hasattr(self, "_loaded_values"):
            self._old_values = {k: v for k, v in self._loaded_values.items() if k in notify_fields}

        if self.name is not None:
            self.name = self.name.strip()
        self._new_values = model_to_dict(self, fields=notify_fields)
        super(Project, self).save(*args, **kwargs)

        if hasattr(self, "_loaded_values"):
            self._loaded_values["status"] = self.status

        if old_status is not None and old_status != self.status:
            from .classification import get_image_bucket_for_status

            old_bucket = get_image_bucket_for_status(old_status)
            new_bucket = get_image_bucket_for_status(self.status)
            if old_bucket != new_bucket:
                from ..utils.image_migration import queue_image_migration

                pk = self.pk
                transaction.on_commit(lambda: queue_image_migration(pk, old_bucket, new_bucket))

    @classmethod
    def get_sample_unit_method_policy(cls, protocol):
        su_method = None
        if protocol == FISHBELT_PROTOCOL or protocol == "beltfish":
            su_method = "beltfish"
        elif protocol in PROTOCOL_MAP:
            su_method = protocol.lower()

        if su_method is None:
            raise ValueError(f"Unknown protocol '{protocol}'.")

        field_name = f"data_policy_{su_method}"
        if not hasattr(cls, field_name):
            raise ValueError(f"No data policy for '{protocol}' protocol.")

        return field_name

    class Meta:
        db_table = "project"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by"],
                condition=models.Q(is_demo=True),
                name="unique_demo_project_per_user",
            )
        ]

    def __str__(self):
        return _("%s") % self.name


class Region(BaseChoiceModel):
    name = models.CharField(max_length=100)
    geom = models.MultiPolygonField(geography=True)

    class Meta:
        db_table = "region"
        ordering = ("name",)

    def __str__(self):
        return _("%s") % self.name

    @property
    def choice(self):
        ret = {
            "id": self.pk,
            "name": self.__str__(),
            "geom": json.loads(self.geom.json),
            "updated_on": self.updated_on,
        }
        if hasattr(self, "val"):
            ret["val"] = self.val
        return ret


class ManagementParty(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "management_party"
        verbose_name = _("management party")
        verbose_name_plural = _("management parties")
        ordering = ("name",)

    def __str__(self):
        return _("%s") % self.name


class ManagementCompliance(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "management_compliance"
        verbose_name = _("management compliance")
        ordering = ("name",)

    def __str__(self):
        return _("%s") % self.name


class Management(BaseModel, JSONMixin, AreaMixin):
    project_lookup = "project"

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    name_secondary = models.CharField(max_length=255, blank=True, verbose_name=_("secondary name"))
    parties = models.ManyToManyField(ManagementParty, related_name="management_parties", blank=True)
    compliance = models.ForeignKey(
        ManagementCompliance, on_delete=models.SET_NULL, null=True, blank=True
    )
    est_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("year established"),
    )
    predecessor = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    boundary = models.MultiPolygonField(geography=True, null=True, blank=True)
    size = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_("Size (ha)"),
        null=True,
        blank=True,
    )
    no_take = models.BooleanField(verbose_name=_("no-take zone"), default=False)
    periodic_closure = models.BooleanField(verbose_name=_("periodic closure"), default=False)
    open_access = models.BooleanField(verbose_name=_("open access"), default=False)
    size_limits = models.BooleanField(verbose_name=_("size limits"), default=False)
    gear_restriction = models.BooleanField(
        verbose_name=_("partial gear restriction"), default=False
    )
    species_restriction = models.BooleanField(
        verbose_name=_("partial species restriction"), default=False
    )
    access_restriction = models.BooleanField(verbose_name=_("access restriction"), default=False)
    validations = models.JSONField(encoder=JSONEncoder, null=True, blank=True)

    class Meta:
        db_table = "management"
        verbose_name = _("management regime")
        ordering = ("name",)

    def __str__(self):
        fullname = self.name
        if self.name_secondary != "":
            fullname = _("%s (%s)") % (fullname, self.name_secondary)
        if self.est_year is not None:
            fullname = _("%s [%s]") % (fullname, self.est_year)
        return fullname

    @property
    def rules(self):
        rules = []

        if self.no_take:
            rules.append("No Take")
        if self.periodic_closure:
            rules.append("Periodic Closure")
        if self.open_access:
            rules.append("Open Access")
        if self.size_limits:
            rules.append("Size Limits")
        if self.gear_restriction:
            rules.append("Gear Restriction")
        if self.species_restriction:
            rules.append("Species Restriction")
        if self.access_restriction:
            rules.append("Access Restriction")

        return rules


class ReefType(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _("%s") % self.name


class ReefZone(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _("%s") % self.name


class ReefExposure(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _("%s") % self.name


class ReefSlope(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _("%s") % self.name


class Site(BaseModel, JSONMixin):
    project_lookup = "project"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    reef_type = models.ForeignKey(ReefType, on_delete=models.PROTECT)
    reef_zone = models.ForeignKey(ReefZone, on_delete=models.PROTECT)
    exposure = models.ForeignKey(ReefExposure, on_delete=models.PROTECT)
    location = models.PointField(srid=4326)
    notes = models.TextField(blank=True)
    predecessor = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    validations = models.JSONField(encoder=JSONEncoder, null=True, blank=True)

    class Meta:
        db_table = "site"
        ordering = ("name",)

    def __str__(self):
        return _("%s") % self.name


class ProjectProfile(BaseModel):
    project_lookup = "project"
    ADMIN = 90
    COLLECTOR = 50
    READONLY = 10
    ROLES = (
        (ADMIN, _("admin")),
        (COLLECTOR, _("collector")),
        (READONLY, _("read-only")),
    )
    ROLES_UPDATED_ON = datetime.datetime(2019, 2, 2, 0, 0, 0, 0, tzinfo=datetime.timezone.utc)

    project = models.ForeignKey(Project, related_name="profiles", on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, related_name="projects", on_delete=models.CASCADE)
    role = models.PositiveSmallIntegerField(choices=ROLES)

    @property
    def is_collector(self):
        return self.role >= self.COLLECTOR

    @property
    def is_admin(self):
        return self.role >= self.ADMIN

    @property
    def profile_name(self):
        return self.profile.full_name

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super(ProjectProfile, cls).from_db(db, field_names, values)
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    def save(self, *args, **kwargs):
        notify_fields = [
            f.name
            for f in self._meta.get_fields(include_parents=False, include_hidden=False)
            if f.editable and f.name != "updated_by"
        ]
        if hasattr(self, "_loaded_values"):
            self._old_values = {k: v for k, v in self._loaded_values.items() if k in notify_fields}
        self._new_values = model_to_dict(self, fields=notify_fields)
        super(ProjectProfile, self).save(*args, **kwargs)

    class Meta:
        db_table = "project_profile"
        ordering = ("project", "profile")
        constraints = [
            models.UniqueConstraint(fields=["project", "profile"], name="unique_project_profile")
        ]


class Visibility(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = "visibilities"

    def __str__(self):
        return _("%s") % self.name


class Current(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("val", "name")

    def __str__(self):
        return _("%s") % self.name


class RelativeDepth(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _("%s") % self.name


class Tide(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("val", "name")

    def __str__(self):
        return _("%s") % self.name


def default_date():
    return timezone.now().date()


class SampleEvent(BaseModel, JSONMixin):
    project_lookup = "site__project"

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="sample_events")
    management = models.ForeignKey(Management, on_delete=models.PROTECT)
    sample_date = models.DateField(default=default_date)
    notes = models.TextField(blank=True)
    validations = models.JSONField(encoder=JSONEncoder, null=True, blank=True)

    class Meta:
        db_table = "sample_event"
        ordering = ("site", "sample_date")

    def __str__(self):
        return "%s %s" % (self.site.__str__(), self.sample_date)


class SampleUnit(BaseModel):
    sample_event = models.ForeignKey(SampleEvent, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    collect_record_id = models.UUIDField(null=True, blank=True)
    sample_time = models.TimeField(null=True, blank=True)

    depth = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        verbose_name=_("depth (m)"),
    )
    visibility = models.ForeignKey(Visibility, on_delete=models.SET_NULL, null=True, blank=True)
    current = models.ForeignKey(Current, on_delete=models.SET_NULL, null=True, blank=True)
    relative_depth = models.ForeignKey(
        RelativeDepth, on_delete=models.SET_NULL, null=True, blank=True
    )
    tide = models.ForeignKey(Tide, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "sample_unit"
        abstract = True

    @property
    def su_method(self):
        for tmclass in TransectMethod.__subclasses__():
            for field in tmclass._meta.fields:
                if field.one_to_one is True and isinstance(self, field.related_model):
                    return getattr(self, field.related_query_name())

        raise NameError("Sample unit method field can't be found")

    def __str__(self):
        return _("sample unit")


class Transect(SampleUnit):
    project_lookup = "sample_event__site__project"

    len_surveyed = models.DecimalField(
        max_digits=4, decimal_places=1, verbose_name=_("transect length surveyed (m)")
    )
    reef_slope = models.ForeignKey(ReefSlope, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "transect"
        abstract = True
        ordering = ("sample_event",)

    def __str__(self):
        su_number = get_sample_unit_number(self)
        if su_number != "":
            su_number = " {}".format(su_number)
        return _("%s%s") % (self.sample_event.__str__(), su_number)


class BaseQuadrat(SampleUnit):
    quadrat_size = models.DecimalField(
        decimal_places=2,
        max_digits=6,
        verbose_name=_("single quadrat area (m2)"),
        default=1,
    )

    class Meta:
        abstract = True
        ordering = ("sample_event",)

    def __str__(self):
        su_number = get_sample_unit_number(self)
        if su_number != "":
            su_number = " {}".format(su_number)
        return _("%s%s") % (self.sample_event.__str__(), su_number)


# TODO: rename this SampleUnitMethod, and abstract all appropriate references elsewhere
class TransectMethod(BaseModel):
    collect_record_id = models.UUIDField(db_index=True, null=True, blank=True)

    class Meta:
        db_table = "transectmethod"

    @property
    def protocol(self):
        if hasattr(self, "benthiclit"):
            return self.benthiclit.protocol
        elif hasattr(self, "benthicpit"):
            return self.benthicpit.protocol
        elif hasattr(self, "beltfish"):
            return self.beltfish.protocol
        elif hasattr(self, "habitatcomplexity"):
            return self.habitatcomplexity.protocol
        elif hasattr(self, "bleachingquadratcollection"):
            return self.bleachingquadratcollection.protocol
        elif hasattr(self, "benthicphotoquadrattransect"):
            return self.benthicphotoquadrattransect.protocol
        elif hasattr(self, "beltinvert"):
            return self.beltinvert.protocol
        return None

    @property
    def subclass(self):
        if hasattr(self, "benthiclit"):
            return getattr(self, "benthiclit")
        elif hasattr(self, "benthicpit"):
            return getattr(self, "benthicpit")
        elif hasattr(self, "beltfish"):
            return getattr(self, "beltfish")
        elif hasattr(self, "habitatcomplexity"):
            return getattr(self, "habitatcomplexity")
        elif hasattr(self, "bleachingquadratcollection"):
            return getattr(self, "bleachingquadratcollection")
        elif hasattr(self, "benthicphotoquadrattransect"):
            return getattr(self, "benthicphotoquadrattransect")
        elif hasattr(self, "beltinvert"):
            return getattr(self, "beltinvert")
        return None

    @property
    def sample_unit(self):
        sample_unit_method_subclass = self.subclass
        if sample_unit_method_subclass is None:
            return None

        related_objects = [
            f
            for f in sample_unit_method_subclass._meta.get_fields()
            if isinstance(f, models.OneToOneField)
        ]

        one2one_fields = [ro for ro in related_objects if ro.name.endswith("_ptr") is False]
        if len(one2one_fields) == 1:
            sample_unit_field = one2one_fields[0]
            return getattr(sample_unit_method_subclass, sample_unit_field.name)

        raise NameError("Sample unit field can't be found")

    def __str__(self):
        return str(_("transect method"))

    @property
    def project(self):
        return get_related_project(self.sample_unit)


class Observer(BaseModel):
    transectmethod = models.ForeignKey(
        TransectMethod,
        on_delete=models.CASCADE,
        verbose_name=_("transect method"),
        related_name="observers",
    )
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    rank = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "observer"
        unique_together = ("transectmethod", "profile")

    def __str__(self):
        return _("%s") % (self.profile)

    @property
    def profile_name(self):
        return self.profile.full_name


class CollectRecord(BaseModel):
    project_lookup = "project"

    SAVING_STAGE = 3
    SAVED_STAGE = 5
    VALIDATING_STAGE = 10
    VALIDATED_STAGE = 15
    SUBMITTING_STAGE = 20
    SUBMITTED_STAGE = 25

    STAGE_CHOICES = (
        (SAVING_STAGE, _("Saving")),
        (SAVED_STAGE, _("Saved")),
        (VALIDATING_STAGE, _("Validating")),
        (VALIDATED_STAGE, _("Validated")),
        (SUBMITTING_STAGE, _("Submitting")),
        (SUBMITTED_STAGE, _("Submitted")),
    )
    STAGE_CHOICES_UPDATED_ON = datetime.datetime(
        2019, 2, 2, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
    )

    project = models.ForeignKey(Project, related_name="collect_records", on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="collect_records")
    data = models.JSONField(encoder=JSONEncoder, null=True, blank=True)
    validations = models.JSONField(encoder=JSONEncoder, null=True, blank=True)
    stage = models.PositiveIntegerField(choices=STAGE_CHOICES, null=True, blank=True)

    @property
    def protocol(self):
        data = self.data or {}
        protocol = data.get("protocol")
        if protocol not in PROTOCOL_MAP:
            return None

        return protocol

    @property
    def obs_keys(self):
        protocol_obs_keys = {
            FISHBELT_PROTOCOL: ["obs_belt_fishes"],
            BLEACHINGQC_PROTOCOL: [
                "obs_colonies_bleached",
                "obs_quadrat_benthic_percent",
            ],
            BENTHICLIT_PROTOCOL: ["obs_benthic_lits"],
            BENTHICPIT_PROTOCOL: ["obs_benthic_pits"],
            HABITATCOMPLEXITY_PROTOCOL: ["obs_habitat_complexities"],
            BENTHICPQT_PROTOCOL: ["obs_benthic_photo_quadrats"],
            MACROINVERTEBRATE_PROTOCOL: ["obs_belt_inverts"],
        }
        return protocol_obs_keys.get(self.protocol)

    @property
    def sample_unit(self):
        data = self.data or {}
        protocol = self.protocol
        if protocol in (
            BENTHICLIT_PROTOCOL,
            BENTHICPIT_PROTOCOL,
            HABITATCOMPLEXITY_PROTOCOL,
        ):
            return data.get("benthic_transect") or {}
        elif protocol == FISHBELT_PROTOCOL:
            return data.get("fishbelt_transect") or {}
        elif protocol == BENTHICPQT_PROTOCOL:
            return data.get("quadrat_transect") or {}
        elif protocol == BLEACHINGQC_PROTOCOL:
            return data.get("quadrat_collection") or {}
        elif protocol == MACROINVERTEBRATE_PROTOCOL:
            return data.get("beltinvert_transect") or {}
        return None

    def _assign_id(self, record):
        record["id"] = record.get("id") or str(uuid.uuid4())
        return record

    def ensure_obs_ids(self):
        if self.obs_keys:
            for obs_key in self.obs_keys:
                self.data[obs_key] = [self._assign_id(r) for r in self.data.get(obs_key) or []]

    def save(self, *args, ignore_stage=False, **kwargs):
        if ignore_stage is False:
            self.stage = self.SAVED_STAGE
            self.validations = self.validations or {}

            from ..submission.validations.statuses import STALE

            self.validations["status"] = STALE

        self.ensure_obs_ids()

        super(CollectRecord, self).save(*args, **kwargs)


class ArchivedRecord(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    project_pk = models.UUIDField(db_index=True, null=True, blank=True)
    record_pk = models.UUIDField(db_index=True, null=True, blank=True)
    record = models.JSONField(null=True, blank=True)


class Covariate(BaseModel, JSONMixin):
    SUPPORTED_COVARIATES = (
        (
            "aca_benthic",
            "Benthic_Allen Coral Atlas",
        ),
        (
            "aca_geomorphic",
            "Geomorphic_Allen Coral Atlas",
        ),
        ("beyer_score", "50 Reefs score_Beyer"),
        ("beyer_scorecn", "50 Reefs connectivity_Beyer"),
        ("beyer_scorecy", "50 Reefs cyclones_Beyer"),
        ("beyer_scorepfc", "50 Reefs thermal future_Beyer"),
        ("beyer_scoreth", "50 Reefs thermal history_Beyer"),
        ("beyer_scoretr", "50 Reefs thermal recent_Beyer"),
        ("andrello_grav_nc", "Market gravity_Andrello"),
        ("andrello_sediment", "Sediment_Andrello"),
        ("andrello_nutrient", "Nutrient_Andrello"),
        ("andrello_pop_count", "Human population_Andrello"),
        ("andrello_num_ports", "Number of ports_Andrello"),
        ("andrello_reef_value", "Tourism value_Andrello"),
        ("andrello_cumul_score", "Cumulative local pressure_Andrello"),
    )

    site = models.ForeignKey("Site", related_name="covariates", on_delete=models.CASCADE)
    name = models.CharField(max_length=100, choices=SUPPORTED_COVARIATES)
    datestamp = models.DateField()
    requested_datestamp = models.DateField()
    value = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = (
            "site",
            "name",
        )

    def __str__(self):
        return f"{self.site.name} - {self.name}"


class AuditRecord(JSONMixin):
    SUBMIT_RECORD_EVENT_TYPE = 1
    EDIT_RECORD_EVENT_TYPE = 2

    AUDIT_EVENT_TYPES = (
        (
            SUBMIT_RECORD_EVENT_TYPE,
            "Submit Record",
        ),
        (
            EDIT_RECORD_EVENT_TYPE,
            "Edit Record",
        ),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.IntegerField(choices=AUDIT_EVENT_TYPES)
    event_on = models.DateTimeField(auto_now_add=True)
    event_by = models.ForeignKey("Profile", on_delete=models.SET_NULL, null=True, blank=True)
    model = models.CharField(max_length=100)
    record_id = models.UUIDField(db_index=True)


class Notification(BaseModel):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    STATUSES = (
        (INFO, INFO),
        (WARNING, WARNING),
        (ERROR, ERROR),
    )

    title = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUSES)
    description = models.TextField(null=True, blank=True)
    owner = models.ForeignKey("Profile", on_delete=models.CASCADE)

    class Meta:
        db_table = "notification"
        ordering = ["created_on"]
