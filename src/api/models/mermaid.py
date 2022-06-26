from __future__ import unicode_literals

import datetime
import itertools
import json
import logging
import uuid
import operator as pyoperator
from decimal import Decimal

from django.contrib.gis.db import models
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import JSONField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Avg, F, Max, Q
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.utils.encoders import JSONEncoder

import pytz
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TagBase
from ..utils import create_timestamp, expired_timestamp, get_sample_unit_number
from ..utils.related import get_related_project
from .base import (
    APPROVAL_STATUSES,
    AreaMixin,
    BaseAttributeModel,
    BaseChoiceModel,
    BaseModel,
    Country,
    JSONMixin,
    Profile,
)

INCLUDE_OBS_TEXT = _(u'include observation in aggregations/analyses?')

logger = logging.getLogger(__name__)

BENTHICLIT_PROTOCOL = "benthiclit"
BENTHICPIT_PROTOCOL = "benthicpit"
FISHBELT_PROTOCOL = "fishbelt"
HABITATCOMPLEXITY_PROTOCOL = "habitatcomplexity"
BLEACHINGQC_PROTOCOL = "bleachingqc"
BENTHICPQT_PROTOCOL = "benthicpqt"

PROTOCOL_MAP = {
    BENTHICLIT_PROTOCOL: "Benthic LIT",
    BENTHICPQT_PROTOCOL: "Benthic Photo Quadrat Transect",
    BENTHICPIT_PROTOCOL: "Benthic PIT",
    FISHBELT_PROTOCOL: "Fish Belt",
    HABITATCOMPLEXITY_PROTOCOL: "Habitat Complexity",
    BLEACHINGQC_PROTOCOL: "Bleaching Quadrat Collection",
}


class Tag(TagBase, BaseModel):
    description = models.TextField(blank=True)
    status = models.PositiveSmallIntegerField(choices=APPROVAL_STATUSES, default=APPROVAL_STATUSES[-1][0])

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ["name", ]

    def __str__(self):
        return _(u'%s') % self.name


class UUIDTaggedItem(GenericUUIDTaggedItemBase):
    tag = models.ForeignKey(
        Tag,
        related_name="tagged_items",
        on_delete=models.CASCADE
    )


class Project(BaseModel, JSONMixin):
    OPEN = 90
    TEST = 80
    LOCKED = 10
    STATUSES = (
        (OPEN, _(u'open')),
        (TEST, _(u'test')),
        (LOCKED, _(u'locked')),
    )

    PRIVATE = 10
    PUBLIC_SUMMARY = 50
    PUBLIC = 100
    DATA_POLICIES = (
        (PRIVATE, _(u'private')),
        (PUBLIC_SUMMARY, _(u'public summary')),
        (PUBLIC, _(u'public')),
    )

    DATA_POLICY_CHOICES_UPDATED_ON = datetime.datetime(2019, 2, 2, 0, 0, 0, 0, pytz.UTC)

    DATA_POLICY_CHOICES = (
        {
            "id": PRIVATE,
            "name": "Private",
            "description": "Collected observations and site-level summary statistics are private, but metadata for "
                           "project, protocol and site, including site location and type and count of sample unit at "
                           "each site, are public."
        },
        {
            "id": PUBLIC_SUMMARY,
            "name": "Public Summary",
            "description": "Collected observations are private, but site-level summary statistics are public, "
                           "along with metadata for project, protocol and site. This option is the default."
        },
        {
            "id": PUBLIC,
            "name": "Public",
            "description": "All collected observations are public."
        },
    )

    name = models.CharField(max_length=255, unique=True)
    notes = models.TextField(blank=True)
    status = models.PositiveSmallIntegerField(choices=STATUSES, default=OPEN)
    data_policy_beltfish = models.PositiveSmallIntegerField(choices=DATA_POLICIES, default=PUBLIC_SUMMARY)
    data_policy_benthiclit = models.PositiveSmallIntegerField(choices=DATA_POLICIES, default=PUBLIC_SUMMARY)
    data_policy_benthicpit = models.PositiveSmallIntegerField(choices=DATA_POLICIES, default=PUBLIC_SUMMARY)
    data_policy_habitatcomplexity = models.PositiveSmallIntegerField(choices=DATA_POLICIES, default=PUBLIC_SUMMARY)
    data_policy_bleachingqc = models.PositiveSmallIntegerField(choices=DATA_POLICIES, default=PUBLIC_SUMMARY)
    data_policy_benthicpqt = models.PositiveSmallIntegerField(choices=DATA_POLICIES, default=PUBLIC_SUMMARY)

    tags = TaggableManager(through=UUIDTaggedItem, blank=True)

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
        notify_fields = [f.name for f in self._meta.get_fields(include_parents=False, include_hidden=False) if
                         f.editable and f.name != 'updated_by']
        if hasattr(self, '_loaded_values'):
            self._old_values = {k: v for k, v in self._loaded_values.items() if k in notify_fields}
        self._new_values = model_to_dict(self, fields=notify_fields)
        super(Project, self).save(*args, **kwargs)

    class Meta:
        db_table = 'project'
        ordering = ['name']

    def __str__(self):
        return _(u'%s') % self.name


class Region(BaseChoiceModel):
    name = models.CharField(max_length=100)
    geom = models.MultiPolygonField(geography=True)

    class Meta:
        db_table = 'region'
        ordering = ('name',)

    def __str__(self):
        return _(u'%s') % self.name
    
    @property
    def choice(self):
        ret = {'id': self.pk, 'name': self.__str__(), 'geom': json.loads(self.geom.json), 'updated_on': self.updated_on}
        if hasattr(self, 'val'):
            ret['val'] = self.val
        return ret


class ManagementParty(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'management_party'
        verbose_name = _(u'management party')
        verbose_name_plural = _(u'management parties')
        ordering = ('name',)

    def __str__(self):
        return _(u'%s') % self.name


class ManagementCompliance(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'management_compliance'
        verbose_name = _(u'management compliance')
        ordering = ('name',)

    def __str__(self):
        return _(u'%s') % self.name


class Management(BaseModel, JSONMixin, AreaMixin):
    project_lookup = 'project'

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    name_secondary = models.CharField(max_length=255, blank=True, verbose_name=_(u'secondary name'))
    parties = models.ManyToManyField(ManagementParty, related_name='management_parties', blank=True)
    compliance = models.ForeignKey(ManagementCompliance, on_delete=models.SET_NULL, null=True, blank=True)
    # help_text=_(u'Optional estimate of level of compliance associated with this management regime'))
    est_year = models.PositiveSmallIntegerField(null=True, blank=True,
                                                validators=[MaxValueValidator(timezone.now().year)],
                                                verbose_name=_(u'year established'))
    predecessor = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    # help_text=_(u'Management regime that preceded this one before a change in name, rules, or boundary'))
    notes = models.TextField(blank=True)
    boundary = models.MultiPolygonField(geography=True, null=True, blank=True)
    size = models.DecimalField(max_digits=12, decimal_places=3,
                               verbose_name=_(u'Size (ha)'),
                               null=True, blank=True,
                               validators=[MinValueValidator(0)])
    # These might be abstracted into separate model detailing all choices
    no_take = models.BooleanField(verbose_name=_(u'no-take zone'), default=False)
    periodic_closure = models.BooleanField(verbose_name=_(u'periodic closure'), default=False)
    open_access = models.BooleanField(verbose_name=_(u'open access'), default=False)
    size_limits = models.BooleanField(verbose_name=_(u'size limits'), default=False)
    gear_restriction = models.BooleanField(verbose_name=_(u'partial gear restriction'), default=False)
    species_restriction = models.BooleanField(verbose_name=_(u'partial species restriction'), default=False)
    access_restriction = models.BooleanField(verbose_name=_(u'access restriction'), default=False)
    validations = JSONField(encoder=JSONEncoder, null=True, blank=True)

    class Meta:
        db_table = 'management'
        verbose_name = _(u'management regime')
        ordering = ('name',)

    def __str__(self):
        fullname = self.name
        if self.name_secondary != '':
            fullname = _(u'%s (%s)') % (fullname, self.name_secondary)
        if self.est_year is not None:
            fullname = _(u'%s [%s]') % (fullname, self.est_year)
        return fullname

    @property
    def rules(self):
        rules = []
        
        if self.no_take:
            rules.append('No Take')
        if self.periodic_closure:
            rules.append('Periodic Closure')
        if self.open_access:
            rules.append('Open Access')
        if self.size_limits:
            rules.append('Size Limits')
        if self.gear_restriction:
            rules.append('Gear Restriction')
        if self.species_restriction:
            rules.append('Species Restriction')
        if self.access_restriction:
            rules.append('Access Restriction')

        return rules


class MPA(BaseModel, AreaMixin):
    name = models.CharField(max_length=255)
    wdpa_id = models.IntegerField(null=True, blank=True)
    est_year = models.PositiveSmallIntegerField(validators=[MaxValueValidator(timezone.now().year)],
                                                verbose_name=_(u'year established'),
                                                null=True, blank=True)
    notes = models.TextField(blank=True)
    boundary = models.MultiPolygonField(geography=True, null=True, blank=True)
    size = models.IntegerField(verbose_name=_(u'Size (km2)'), null=True, blank=True)

    class Meta:
        db_table = 'mpa'
        verbose_name = _(u'MPA')
        verbose_name_plural = _(u'MPAs')
        ordering = ('name', 'est_year')

    def __str__(self):
        return _(u'%s') % self.name


class MPAZone(Management):
    mpa = models.ForeignKey(MPA, related_name='mpa_zones', on_delete=models.CASCADE)

    class Meta:
        db_table = 'mpa_zone'


class ReefType(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _(u'%s') % self.name


class ReefZone(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _(u'%s') % self.name


class ReefExposure(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _(u'%s') % self.name


class ReefSlope(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _(u'%s') % self.name


class Site(BaseModel, JSONMixin):
    project_lookup = 'project'

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    reef_type = models.ForeignKey(ReefType, on_delete=models.PROTECT)
    reef_zone = models.ForeignKey(ReefZone, on_delete=models.PROTECT)
    exposure = models.ForeignKey(ReefExposure, on_delete=models.PROTECT)
    location = models.PointField(srid=4326)
    notes = models.TextField(blank=True)
    predecessor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True)
    validations = JSONField(encoder=JSONEncoder, null=True, blank=True)

    class Meta:
        db_table = 'site'
        ordering = ('name',)

    def __str__(self):
        return _(u'%s') % self.name


class ProjectProfile(BaseModel):
    project_lookup = 'project'
    ADMIN = 90
    COLLECTOR = 50
    READONLY = 10
    ROLES = (
        (ADMIN, _(u'admin')),
        (COLLECTOR, _(u'collector')),  # add/edit
        (READONLY, _(u'read-only')),
    )
    ROLES_UPDATED_ON = datetime.datetime(2019, 2, 2, 0, 0, 0, 0, pytz.UTC)

    project = models.ForeignKey(Project, related_name='profiles', on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, related_name='projects', on_delete=models.CASCADE)
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
        notify_fields = [f.name for f in self._meta.get_fields(include_parents=False, include_hidden=False) if
                         f.editable and f.name != 'updated_by']
        if hasattr(self, '_loaded_values'):
            self._old_values = {k: v for k, v in self._loaded_values.items() if k in notify_fields}
        self._new_values = model_to_dict(self, fields=notify_fields)
        super(ProjectProfile, self).save(*args, **kwargs)

    class Meta:
        db_table = 'project_profile'
        ordering = ('project', 'profile')
        unique_together = ('project', 'profile')


class Visibility(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = u'visibilities'

    def __str__(self):
        return _(u'%s') % self.name


class Current(BaseChoiceModel):
    name = models.CharField(max_length=50)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _(u'%s') % self.name


class RelativeDepth(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _(u'%s') % self.name


class Tide(BaseChoiceModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return _(u'%s') % self.name


def default_date():
    return timezone.now().date()


def default_time():  # no longer used; remove once migrations are squashed
    return timezone.now().time()


class SampleEvent(BaseModel, JSONMixin):

    project_lookup = "site__project"

    # Required
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='sample_events')
    management = models.ForeignKey(Management, on_delete=models.PROTECT)
    sample_date = models.DateField(default=default_date)
    notes = models.TextField(blank=True)
    validations = JSONField(encoder=JSONEncoder, null=True, blank=True)

    class Meta:
        db_table = 'sample_event'
        ordering = ('site', 'sample_date')

    def __str__(self):
        return '%s %s' % (self.site.__str__(), self.sample_date)


class SampleUnit(BaseModel):
    sample_event = models.ForeignKey(SampleEvent, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    collect_record_id = models.UUIDField(null=True, blank=True)
    sample_time = models.TimeField(null=True, blank=True)

    depth = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        verbose_name=_(u'depth (m)'),
        validators=[MinValueValidator(0), MaxValueValidator(40)]
    )
    visibility = models.ForeignKey(Visibility, on_delete=models.SET_NULL, null=True, blank=True)
    current = models.ForeignKey(Current, on_delete=models.SET_NULL, null=True, blank=True)
    relative_depth = models.ForeignKey(RelativeDepth, on_delete=models.SET_NULL, null=True, blank=True)
    tide = models.ForeignKey(Tide, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'sample_unit'
        abstract = True

    def __str__(self):
        if hasattr(self, 'transect') or hasattr(self, 'quadrat'):
            return _(u'%s') % self.__str__()

        return _(u'sample unit')


class Transect(SampleUnit):
    len_surveyed = models.DecimalField(max_digits=4, decimal_places=1,
                                       verbose_name=_(u'transect length surveyed (m)'))
    reef_slope = models.ForeignKey(
        ReefSlope, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'transect'
        abstract = True
        ordering = ('sample_event', )

    def __str__(self):
        su_number = get_sample_unit_number(self)
        if su_number != '':
            su_number = ' {}'.format(su_number)
        return _(u'%s%s') % (
            self.sample_event.__str__(),
            su_number
        )


class BenthicTransect(Transect):
    project_lookup = 'sample_event__site__project'
    number = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'transect_benthic'


class BeltTransectWidth(BaseChoiceModel):
    name = models.CharField(unique=True, max_length=100, null=True, blank=True)

    def __str__(self):
        return _('%s') % self.name

    @property
    def choice(self):
        ret = {
            'id': self.pk,
            'name': self.__str__(),
            'updated_on': self.updated_on,
            'conditions': [cnd.choice for cnd in self.conditions.all().order_by("val")]
        }

        return ret

    def _get_default_condition(self, conditions):
        for i, condition in enumerate(conditions):
            if condition.operator is None or condition.size is None:
                return conditions.pop(i)
                break
        return None

    def _get_conditions_combinations(self, conditions):
        num_conditions = len(conditions)
        combos = []
        for n in range(num_conditions):
            combos.extend(list(itertools.combinations(conditions, n + 1)))
        return combos

    def get_condition(self, size):
        if isinstance(size, (int, float, Decimal)) is False or size < 0:
            return None

        conditions = list(self.conditions.all().order_by("size"))
        default_condition = self._get_default_condition(conditions)
        combos = self._get_conditions_combinations(conditions)

        for combo in combos:
            check = all([cnd.op(size, cnd.size) for cnd in combo])
            if check:
                return combo[0]

        return default_condition


class BeltTransectWidthCondition(BaseChoiceModel):
    OPERATOR_EQ = "=="
    OPERATOR_NE = "!="
    OPERATOR_LT = "<"
    OPERATOR_LTE = "<="
    OPERATOR_GT = ">"
    OPERATOR_GTE = ">="
    OPERATOR_CHOICES = (
        (OPERATOR_EQ, OPERATOR_EQ),
        (OPERATOR_NE, OPERATOR_NE),
        (OPERATOR_LT, OPERATOR_LT),
        (OPERATOR_LTE, OPERATOR_LTE),
        (OPERATOR_GT, OPERATOR_GT),
        (OPERATOR_GTE, OPERATOR_GTE),
    )

    belttransectwidth = models.ForeignKey(
        "BeltTransectWidth",
        on_delete=models.PROTECT,
        related_name="conditions"
    )
    operator = models.CharField(
        max_length=2,
        choices=OPERATOR_CHOICES,
        null=True,
        blank=True
    )
    size = models.DecimalField(
        decimal_places=1,
        max_digits=5,
        null=True,
        blank=True,
        verbose_name=_(u'fish size (cm)')
    )
    val = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("belttransectwidth", "operator", "size")

    def __str__(self):
        if self.operator is None or self.size is None:
            return str(self.belttransectwidth)
        return str(_("{} {}cm @ {}".format(
            str(self.operator or ""),
            str(self.size or ""),
            str(self.belttransectwidth)
        )))

    @property
    def op(self):
        if self.operator == self.OPERATOR_EQ:
            return pyoperator.eq
        elif self.operator == self.OPERATOR_EQ:
            return pyoperator.ne
        elif self.operator == self.OPERATOR_LT:
            return pyoperator.lt
        elif self.operator == self.OPERATOR_LTE:
            return pyoperator.le
        elif self.operator == self.OPERATOR_GT:
            return pyoperator.gt
        elif self.operator == self.OPERATOR_GTE:
            return pyoperator.ge
        return None

    @property
    def choice(self):
        ret = {
            'id': self.pk,
            'name': self.__str__(),
            'updated_on': self.updated_on,
            'size': self.size,
            'operator': self.operator,
            'val': self.val,
        }
        if hasattr(self, 'val'):
            ret['val'] = self.val
        return ret


class FishBeltTransect(Transect):
    project_lookup = 'sample_event__site__project'
    suview = "BeltFishSUView"

    number = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=50, blank=True)
    width = models.ForeignKey(BeltTransectWidth, verbose_name=_(u'width (m)'), on_delete=models.PROTECT)
    size_bin = models.ForeignKey("FishSizeBin", on_delete=models.PROTECT)

    class Meta:
        db_table = 'transect_belt_fish'
        verbose_name = _(u'fish belt transect')


class BaseQuadrat(SampleUnit):
    quadrat_size = models.DecimalField(
        decimal_places=2, max_digits=6,
        verbose_name=_(u'single quadrat area (m2)'),
        default=1,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        abstract = True
        ordering = ('sample_event',)

    def __str__(self):
        su_number = get_sample_unit_number(self)
        if su_number != '':
            su_number = ' {}'.format(su_number)
        return _('%s%s') % (
            self.sample_event.__str__(),
            su_number
        )


class QuadratCollection(BaseQuadrat):
    project_lookup = 'sample_event__site__project'
    label = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'quadrat_collection'


class QuadratTransect(BenthicTransect):
    project_lookup = "sample_event__site__project"

    quadrat_size = models.DecimalField(
        decimal_places=2, max_digits=6,
        verbose_name=_('single quadrat area (m2)'),
        default=1,
        validators=[MinValueValidator(0)]
    )
    num_quadrats = models.PositiveSmallIntegerField()
    num_points_per_quadrat = models.PositiveSmallIntegerField()
    quadrat_number_start = models.PositiveSmallIntegerField(
        default=1, verbose_name=_("number of first quadrat")
    )

    class Meta:
        db_table = 'quadrat_transect'


# TODO: rename this SampleUnitMethod, and abstract all appropriate references elsewhere
class TransectMethod(BaseModel):
    collect_record_id = models.UUIDField(db_index=True, null=True, blank=True)

    class Meta:
        db_table = 'transectmethod'

    @property
    def protocol(self):
        if hasattr(self, 'benthiclit'):
            return self.benthiclit.protocol
        elif hasattr(self, 'benthicpit'):
            return self.benthicpit.protocol
        elif hasattr(self, 'beltfish'):
            return self.beltfish.protocol
        elif hasattr(self, 'habitatcomplexity'):
            return self.habitatcomplexity.protocol
        elif hasattr(self, 'bleachingquadratcollection'):
            return self.bleachingquadratcollection.protocol
        elif hasattr(self, 'benthicphotoquadrattransect'):
            return self.benthicphotoquadrattransect.protocol
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
        return None

    @property
    def sample_unit(self):
        sample_unit_method_subclass = self.subclass
        if sample_unit_method_subclass is None:
            return None

        related_objects = [
            f for f in sample_unit_method_subclass._meta.get_fields()
            if isinstance(f, models.OneToOneField)]

        one2one_fields = [ro for ro in related_objects if ro.name.endswith("_ptr") is False]
        if len(one2one_fields) == 1:
            sample_unit_field = one2one_fields[0]
            return getattr(sample_unit_method_subclass, sample_unit_field.name)

        raise NameError("Sample unit field can't be found")

    def __str__(self):
        return str(_(u'transect method'))

    @property
    def project(self):
        return get_related_project(self.sample_unit)


class Observer(BaseModel):
    transectmethod = models.ForeignKey(TransectMethod, on_delete=models.CASCADE,
                                       verbose_name=_(u'transect method'),
                                       related_name='observers')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    rank = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = 'observer'
        unique_together = ('transectmethod', 'profile')

    def __str__(self):
        return _(u'%s') % (self.profile)

    @property
    def profile_name(self):
        return u'{} {}'.format(self.profile.first_name, self.profile.last_name)


class BenthicLifeHistory(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'benthic_lifehistory'
        verbose_name_plural = _(u'benthic life histories')
        ordering = ['name']

    def __str__(self):
        return _(u'%s') % self.name


class GrowthForm(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'growth_form'
        verbose_name_plural = _(u'growth forms')
        ordering = ['name']

    def __str__(self):
        return _(u'%s') % self.name


class BenthicAttribute(BaseAttributeModel):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    regions = models.ManyToManyField(Region, blank=True)
    life_history = models.ForeignKey(BenthicLifeHistory, on_delete=models.SET_NULL, null=True, blank=True)

    # Get *all* descendants of this instance, not just immediate children.
    # This is good for summarizing aggregate descendant properties, but if we need more
    # we'll want the mptt app.
    @property
    def descendants(self):
        sql = """
            WITH RECURSIVE descendants(id, name, parent_id, life_history_id) AS (
                SELECT id, name, parent_id, life_history_id FROM benthic_attribute WHERE id = '%s'
              UNION ALL
                SELECT a.id, a.name, a.parent_id, a.life_history_id
                FROM descendants d, benthic_attribute a
                WHERE a.parent_id = d.id
            )
            SELECT id, name, parent_id, life_history_id
            FROM descendants
            WHERE id != '%s'
        """ % (self.pk, self.pk)
        return type(self).objects.raw(sql)

    @property
    def origin(self):
        sql = """
            WITH RECURSIVE parents(id, name, parent_id, life_history_id) AS (
                SELECT id, name, parent_id, life_history_id FROM benthic_attribute WHERE id = '{}'
                UNION ALL
                SELECT a.id, a.name, a.parent_id, a.life_history_id
                FROM parents as p, benthic_attribute a
                WHERE a.id = p.parent_id
            )
            SELECT *
            FROM parents
            WHERE parent_id IS NULL
            LIMIT 1
        """.format(self.pk)
        return type(self).objects.raw(sql)[0]

    class Meta:
        db_table = 'benthic_attribute'
        ordering = ['name']

    def __str__(self):
        return _(u'%s') % self.name
        # return u'%s' % str(self.name)


class BenthicLIT(TransectMethod):
    protocol = BENTHICLIT_PROTOCOL
    project_lookup = 'transect__sample_event__site__project'

    transect = models.OneToOneField(BenthicTransect, on_delete=models.CASCADE,
                                    related_name='benthiclit_method',
                                    verbose_name=_(u'benthic transect'))

    class Meta:
        db_table = 'transectmethod_benthiclit'
        verbose_name = _(u'benthic LIT')
        verbose_name_plural = _(u'benthic LIT observations')

    def __str__(self):
        return _(u'benthic LIT %s') % self.transect.__str__()


class ObsBenthicLIT(BaseModel, JSONMixin):
    project_lookup = 'benthiclit__transect__sample_event__site__project'

    benthiclit = models.ForeignKey(BenthicLIT, related_name='obsbenthiclit_set', on_delete=models.CASCADE)
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    length = models.PositiveSmallIntegerField(verbose_name=_(u'length (cm)'))
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'obs_benthiclit'
        verbose_name = _(u'benthic LIT observation')
        ordering = ["created_on"]

    def __str__(self):
        return _(u'%s') % (self.length)


class BenthicPIT(TransectMethod):
    protocol = BENTHICPIT_PROTOCOL
    project_lookup = 'transect__sample_event__site__project'

    transect = models.OneToOneField(BenthicTransect, on_delete=models.CASCADE,
                                    related_name='benthicpit_method',
                                    verbose_name='benthic transect')
    interval_size = models.DecimalField(max_digits=4, decimal_places=2,
                                        default=0.5,
                                        validators=[MinValueValidator(0), MaxValueValidator(10)],
                                        verbose_name=_('interval size (m)'))

    interval_start = models.DecimalField(max_digits=4,
                                         decimal_places=2,
                                         default=0.5,
                                         verbose_name=_('interval start (m)'))

    class Meta:
        db_table = 'transectmethod_benthicpit'
        verbose_name = _(u'benthic PIT')
        verbose_name_plural = _(u'benthic PIT observations')

    def __str__(self):
        return _(u'benthic PIT %s') % self.transect.__str__()


class ObsBenthicPIT(BaseModel, JSONMixin):
    project_lookup = 'benthicpit__transect__sample_event__site__project'

    benthicpit = models.ForeignKey(BenthicPIT, related_name='obsbenthicpit_set', on_delete=models.CASCADE)
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'obs_benthicpit'
        unique_together = ('benthicpit', 'interval')
        verbose_name = _(u'benthic PIT observation')
        ordering = ["interval"]

    def __str__(self):
        return _(u'%s') % self.interval


class HabitatComplexity(TransectMethod):
    protocol = HABITATCOMPLEXITY_PROTOCOL
    project_lookup = 'transect__sample_event__site__project'

    transect = models.OneToOneField(BenthicTransect, on_delete=models.CASCADE,
                                    related_name='habitatcomplexity_method',
                                    verbose_name='benthic transect')
    interval_size = models.DecimalField(max_digits=4, decimal_places=2,
                                        default=0.5,
                                        validators=[MinValueValidator(0), MaxValueValidator(10)],
                                        verbose_name=_(u'interval size (m)'))

    class Meta:
        db_table = 'transectmethod_habitatcomplexity'
        verbose_name = _(u'habitat complexity transect')
        verbose_name_plural = _(u'habitat complexity transect observations')

    def __str__(self):
        return _(u'habitat complexity %s') % self.transect.__str__()


class HabitatComplexityScore(BaseChoiceModel):
    name = models.CharField(max_length=100)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _(u'%s %s') % (self.val, self.name)


class ObsHabitatComplexity(BaseModel, JSONMixin):
    project_lookup = 'habitatcomplexity__transect__sample_event__site__project'

    habitatcomplexity = models.ForeignKey(HabitatComplexity, related_name='habitatcomplexity_set',
                                          on_delete=models.CASCADE)
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    score = models.ForeignKey(HabitatComplexityScore, on_delete=models.PROTECT)
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'obs_habitatcomplexity'
        unique_together = ('habitatcomplexity', 'interval')
        verbose_name = _(u'habitat complexity transect observation')
        ordering = ["interval"]

    def __str__(self):
        return _(u'%s') % self.interval


class BleachingQuadratCollection(TransectMethod):
    protocol = BLEACHINGQC_PROTOCOL
    project_lookup = 'quadrat__sample_event__site__project'

    quadrat = models.OneToOneField(QuadratCollection,
                                   on_delete=models.CASCADE,
                                   related_name='bleachingquadratcollection_method',
                                   verbose_name=_(u'bleaching quadrat collection'))

    class Meta:
        db_table = 'transectmethod_bleaching_quadrat_collection'
        verbose_name = _(u'bleaching quadrat collection')
        verbose_name_plural = _(u'bleaching quadrat collection observations')

    def __str__(self):
        return _(u'bleaching quadrat collection %s') % self.quadrat.__str__()


class ObsColoniesBleached(BaseModel, JSONMixin):
    project_lookup = 'bleachingquadratcollection__quadrat__sample_event__site__project'

    bleachingquadratcollection = models.ForeignKey(BleachingQuadratCollection,
                                                         on_delete=models.CASCADE)
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    count_normal = models.PositiveSmallIntegerField(verbose_name=u'normal', default=0)
    count_pale = models.PositiveSmallIntegerField(verbose_name=u'pale', default=0)
    count_20 = models.PositiveSmallIntegerField(verbose_name=u'0-20% bleached', default=0)
    count_50 = models.PositiveSmallIntegerField(verbose_name=u'20-50% bleached', default=0)
    count_80 = models.PositiveSmallIntegerField(verbose_name=u'50-80% bleached', default=0)
    count_100 = models.PositiveSmallIntegerField(verbose_name=u'80-100% bleached', default=0)
    count_dead = models.PositiveSmallIntegerField(verbose_name=u'recently dead', default=0)

    class Meta:
        db_table = 'obs_colonies_bleached'
        verbose_name = _(u'bleaching quadrat collection colonies bleached observation')
        ordering = ["created_on"]

    def __str__(self):
        gf = ''
        if self.growth_form is not None:
            gf = ' {}'.format(self.growth_form)
        return _(u'%s%s') % (self.attribute.__str__(), gf)


class ObsQuadratBenthicPercent(BaseModel, JSONMixin):
    project_lookup = "bleachingquadratcollection__quadrat__sample_event__site__project"

    bleachingquadratcollection = models.ForeignKey(
        BleachingQuadratCollection, on_delete=models.CASCADE
    )
    quadrat_number = models.PositiveSmallIntegerField(
        verbose_name=u"quadrat number"
    )
    percent_hard = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=u"hard coral, % cover", null=True, blank=True
    )
    percent_soft = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=u"soft coral, % cover", null=True, blank=True
    )
    percent_algae = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name=u"macroalgae, % cover", null=True, blank=True
    )

    class Meta:
        db_table = "obs_quadrat_benthic_percent"
        verbose_name = _(
            u"bleaching quadrat collection percent benthic cover observation"
        )
        unique_together = ("bleachingquadratcollection", "quadrat_number")
        ordering = ["created_on"]

    def __str__(self):
        return _(u"%s") % self.quadrat_number


class BenthicPhotoQuadratTransect(TransectMethod):
    protocol = BENTHICPQT_PROTOCOL
    project_lookup = "quadrat_transect__sample_event__site__project"

    quadrat_transect = models.OneToOneField(
        QuadratTransect, on_delete=models.CASCADE,
        related_name="benthic_photo_quadrat_transect_method",
        verbose_name=_("benthic photo quadrat transect")
    )

    class Meta:
        db_table = "transectmethod_benthicpqt"
        verbose_name = _("benthic photo quadrat transect")
        verbose_name_plural = _("benthic photo quadrat transects")

    def __str__(self):
        return _("benthic photo quadrat transect %s") % self.quadrat_transect.__str__()


class ObsBenthicPhotoQuadrat(BaseModel, JSONMixin):
    project_lookup = "benthic_photo_quadrat_transect__quadrat_transect__sample_event__site__project"

    benthic_photo_quadrat_transect = models.ForeignKey(
        BenthicPhotoQuadratTransect, on_delete=models.CASCADE
    )

    quadrat_number = models.PositiveSmallIntegerField(
        verbose_name="quadrat number"
    )
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    num_points = models.PositiveSmallIntegerField(verbose_name='number of points', default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "obs_benthic_photo_quadrat"
        verbose_name = _(
            "benthic photo quadrat transect observation"
        )
        unique_together = (
            "benthic_photo_quadrat_transect",
            "quadrat_number",
            "attribute",
            "growth_form"
        )
        ordering = ["created_on"]

    def __str__(self):
        return str(self.quadrat_number)


class FishAttribute(BaseAttributeModel):

    GROUPING_RANK = 'grouping'
    FAMILY_RANK = 'family'
    GENUS_RANK = 'genus'
    SPECIES_RANK = 'species'

    class Meta:
        db_table = 'fish_attribute'

    def __str__(self):
        if hasattr(self, 'fishgrouping'):
            return _(u'%s') % self.fishgrouping.name
        elif hasattr(self, 'fishfamily'):
            return _(u'%s') % self.fishfamily.name
        elif hasattr(self, 'fishgenus'):
            return _(u'%s') % self.fishgenus.name
        elif hasattr(self, 'fishspecies'):
            return _(u'%s %s') % (self.fishspecies.genus.name, self.fishspecies.name)
        return "no-name attribute"

    @property
    def taxonomic_rank(self):
        if hasattr(self, 'fishgrouping'):
            return self.GROUPING_RANK
        elif hasattr(self, 'fishfamily'):
            return self.FAMILY_RANK
        elif hasattr(self, 'fishgenus'):
            return self.GENUS_RANK
        elif hasattr(self, 'fishspecies'):
            return self.SPECIES_RANK
        return None

    def _get_taxon(self):
        if hasattr(self, 'fishgrouping'):
            return self.fishgrouping
        elif hasattr(self, 'fishfamily'):
            return self.fishfamily
        elif hasattr(self, 'fishgenus'):
            return self.fishgenus
        elif hasattr(self, 'fishspecies'):
            return self.fishspecies
        return None

    def get_biomass_constants(self):
        taxon = self._get_taxon()
        if taxon is None:
            return None, None, None
        return taxon.biomass_constant_a, taxon.biomass_constant_b, taxon.biomass_constant_c

    @property
    def regions(self):
        return self._get_taxon().regions

    def get_max_length(self):
        return self._get_taxon().max_length


class FishGrouping(FishAttribute):
    name = models.CharField(max_length=100)
    regions = models.ManyToManyField(Region, blank=True)

    def _get_attribute_aggs(self):
        if hasattr(self, "_attribute_aggs"):
            return self._attribute_aggs

        q = Q()
        for a in self.attribute_grouping.all():
            q |= Q(pk=a.attribute.pk)
            q |= Q(genus=a.attribute)
            q |= Q(genus__family=a.attribute)
        # only use species in one of the regions assigned this grouping to calculate constants
        q &= Q(regions__in=self.regions.all())
        species = FishSpecies.objects.filter(q).distinct()

        fishattr_aggs = list(species.aggregate(
            Avg('biomass_constant_a'),
            Avg('biomass_constant_b'),
            Avg('biomass_constant_c'),
            Max('max_length'),
        ).values())
        biomass_constant_a = round(fishattr_aggs[0] or 0, 6)
        biomass_constant_b = round(fishattr_aggs[1] or 0, 6)
        biomass_constant_c = round(fishattr_aggs[2] or 0, 6)
        max_length = fishattr_aggs[3]

        self._attribute_aggs = {
            "biomass_constant_a": biomass_constant_a,
            "biomass_constant_b": biomass_constant_b,
            "biomass_constant_c": biomass_constant_c,
            "max_length": max_length,
        }
        return self._attribute_aggs

    @property
    def biomass_constant_a(self):
        return self._get_attribute_aggs()["biomass_constant_a"]

    @property
    def biomass_constant_b(self):
        return self._get_attribute_aggs()["biomass_constant_b"]

    @property
    def biomass_constant_c(self):
        return self._get_attribute_aggs()["biomass_constant_c"]

    @property
    def max_length(self):
        return self._get_attribute_aggs()["max_length"]

    class Meta:
        db_table = "fish_grouping"
        ordering = ("name",)

    def __str__(self):
        return _(u'%s') % self.name or ""


class FishGroupingRelationship(models.Model):
    grouping = models.ForeignKey(FishGrouping, related_name="attribute_grouping", on_delete=models.CASCADE)
    attribute = models.ForeignKey(FishAttribute, related_name="grouping_attribute", on_delete=models.CASCADE)

    def __str__(self):
        return u"%s > %s" % (self.grouping, self.attribute)


class FishFamily(FishAttribute):
    # Caching at the class level
    species_agg = None
    species_agg_timestamp = None
    regions_agg = None

    name = models.CharField(max_length=100)

    def _set_species_agg_vals(self):
        if (not FishFamily.species_agg or
           expired_timestamp(FishFamily.species_agg_timestamp)):

            species_agg_qs = FishSpecies.objects \
                .select_related("genus__family") \
                .order_by().values(family=F("genus__family")).annotate(
                    biomass_constant_a=Avg('biomass_constant_a'),
                    biomass_constant_b=Avg('biomass_constant_b'),
                    biomass_constant_c=Avg('biomass_constant_c'),
                    max_length=Max('max_length'),
                )

            regions_agg_qs = FishSpecies.objects \
                .select_related("genus__family") \
                .order_by().values(family=F("genus__family")).annotate(
                    regions=ArrayAgg("regions", distinct=True),
                )

            FishFamily.species_agg = {str(bc["family"]): bc for bc in species_agg_qs}
            FishFamily.regions_agg = {str(fr["family"]): fr["regions"] for fr in regions_agg_qs}
            FishFamily.species_agg_timestamp = create_timestamp(ttl=30)

        family = FishFamily.species_agg.get(str(self.pk))
        self._biomass_a = None
        self._biomass_b = None
        self._biomass_c = None
        self._max_length = None
        if family.get("biomass_constant_a") is not None:
            self._biomass_a = round(family.get("biomass_constant_a"), 6)
        if family.get("biomass_constant_b") is not None:
            self._biomass_b = round(family.get("biomass_constant_b"), 6)
        if family.get("biomass_constant_c") is not None:
            self._biomass_c = round(family.get("biomass_constant_c"), 6)
        if family.get("max_length") is not None:
            self._max_length = round(family.get("max_length"), 6)

        self._regions = FishFamily.regions_agg.get(str(self.pk))

        return FishFamily.species_agg

    @property
    def biomass_constant_a(self):
        if hasattr(self, '_biomass_a'):
            return self._biomass_a

        self._set_species_agg_vals()
        return self._biomass_a

    @property
    def biomass_constant_b(self):
        if hasattr(self, '_biomass_b'):
            return self._biomass_b

        self._set_species_agg_vals()
        return self._biomass_b

    @property
    def biomass_constant_c(self):
        if hasattr(self, '_biomass_c'):
            return self._biomass_c

        self._set_species_agg_vals()
        return self._biomass_c

    @property
    def max_length(self):
        if hasattr(self, '_max_length'):
            return self._max_length

        self._set_species_agg_vals()
        return self._max_length

    @property
    def regions(self):
        if hasattr(self, '_regions'):
            return self._regions

        self._set_species_agg_vals()
        return self._regions

    class Meta:
        db_table = 'fish_family'
        ordering = ('name',)
        verbose_name_plural = _(u'fish families')

    def __str__(self):
        return _(u'%s') % self.name


class FishGenus(FishAttribute):

    # Caching at the class level
    species_agg = None
    species_agg_timestamp = None
    regions_agg = None

    name = models.CharField(max_length=100)
    family = models.ForeignKey(FishFamily, on_delete=models.CASCADE)

    def _set_species_agg_vals(self):
        if not FishGenus.species_agg or expired_timestamp(FishGenus.species_agg_timestamp):
            species_agg_qs = FishSpecies.objects.order_by().values("genus").annotate(
                biomass_constant_a=Avg('biomass_constant_a'),
                biomass_constant_b=Avg('biomass_constant_b'),
                biomass_constant_c=Avg('biomass_constant_c'),
                max_length=Max('max_length'),
            )

            regions_agg_qs = FishSpecies.objects.order_by().values("genus").annotate(
                regions=ArrayAgg("regions", distinct=True),
            )

            FishGenus.species_agg = {str(bc["genus"]): bc for bc in species_agg_qs}
            FishGenus.regions_agg = {str(gr["genus"]): gr["regions"] for gr in regions_agg_qs}
            FishGenus.species_agg_timestamp = create_timestamp(ttl=30)

        genus = FishGenus.species_agg.get(str(self.pk))
        self._biomass_a = None
        self._biomass_b = None
        self._biomass_c = None
        self._max_length = None
        if genus.get("biomass_constant_a") is not None:
            self._biomass_a = round(genus.get("biomass_constant_a"), 6)
        if genus.get("biomass_constant_b") is not None:
            self._biomass_b = round(genus.get("biomass_constant_b"), 6)
        if genus.get("biomass_constant_c") is not None:
            self._biomass_c = round(genus.get("biomass_constant_c"), 6)
        if genus.get("max_length") is not None:
            self._max_length = genus.get("max_length")

        self._regions = FishGenus.regions_agg.get(str(self.pk))

        return FishGenus.species_agg

    @property
    def biomass_constant_a(self):
        if hasattr(self, '_biomass_a'):
            return self._biomass_a

        self._set_species_agg_vals()
        return self._biomass_a

    @property
    def biomass_constant_b(self):
        if hasattr(self, '_biomass_b'):
            return self._biomass_b

        self._set_species_agg_vals()
        return self._biomass_b

    @property
    def biomass_constant_c(self):
        if hasattr(self, '_biomass_c'):
            return self._biomass_c

        self._set_species_agg_vals()
        return self._biomass_c

    @property
    def regions(self):
        if hasattr(self, '_regions'):
            return self._regions

        self._set_species_agg_vals()
        return self._regions

    @property
    def max_length(self):
        if hasattr(self, '_max_length'):
            return self._max_length

        self._set_species_agg_vals()
        return self._max_length

    class Meta:
        db_table = 'fish_genus'
        ordering = ('name',)
        verbose_name_plural = _(u'fish genera')

    def __str__(self):
        return _(u'%s') % self.name


class FishGroupSize(BaseChoiceModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'fish_group_size'
        ordering = ('name',)
        verbose_name = _(u'fish group size')

    def __str__(self):
        return _(u'%s') % self.name


class FishGroupTrophic(BaseChoiceModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'fish_group_trophic'
        ordering = ('name',)
        verbose_name = _(u'fish trophic group')

    def __str__(self):
        return _(u'%s') % self.name


class FishGroupFunction(BaseChoiceModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'fish_group_function'
        ordering = ('name',)
        verbose_name = _(u'fish functional group')

    def __str__(self):
        return _(u'%s') % self.name


class FishSpecies(FishAttribute):
    LENGTH_TYPES = (
        ('fork length', 'fork length'),
        ('standard length', 'standard length'),
        ('total length', 'total length'),
        ('wing diameter', 'wing diameter')
    )
    LENGTH_TYPES_CHOICES_UPDATED_ON = datetime.datetime(2020, 1, 21, 0, 0, 0, 0, pytz.UTC)

    name = models.CharField(max_length=100)
    genus = models.ForeignKey(FishGenus, on_delete=models.CASCADE)
    regions = models.ManyToManyField(Region, blank=True)
    biomass_constant_a = models.DecimalField(max_digits=7, decimal_places=6,
                                             null=True, blank=True)
    biomass_constant_b = models.DecimalField(max_digits=7, decimal_places=6,
                                             null=True, blank=True)
    biomass_constant_c = models.DecimalField(max_digits=7, decimal_places=6, default=1,
                                             null=True, blank=True)
    vulnerability = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                                        validators=[MinValueValidator(0),
                                                    MaxValueValidator(100)])
    max_length = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_(u'maximum length (cm)'),
                                     null=True, blank=True,
                                     validators=[MinValueValidator(1),
                                                 MaxValueValidator(2000)])  # Rhincodon typus is world's largest fish
    trophic_level = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True,
                                        validators=[MinValueValidator(1),
                                                    MaxValueValidator(5)])
    max_length_type = models.CharField(max_length=50, choices=LENGTH_TYPES, blank=True)
    group_size = models.ForeignKey(FishGroupSize,  on_delete=models.SET_NULL, null=True, blank=True)
    trophic_group = models.ForeignKey(FishGroupTrophic,
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True)
    functional_group = models.ForeignKey(FishGroupFunction,
                                         on_delete=models.SET_NULL,
                                         null=True, blank=True)
    climate_score = models.DecimalField(max_digits=10, decimal_places=9,
                                        blank=True, null=True,
                                        validators=[MinValueValidator(0),
                                                    MaxValueValidator(1)])
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'fish_species'
        ordering = ('genus', 'name',)
        verbose_name_plural = _(u'fish species')

    def __str__(self):
        return _(u'%s %s') % (self.genus.name, self.name)


class BeltFish(TransectMethod):
    protocol = FISHBELT_PROTOCOL
    project_lookup = 'transect__sample_event__site__project'

    transect = models.OneToOneField(FishBeltTransect, on_delete=models.CASCADE,
                                    related_name='beltfish_method',
                                    verbose_name=_(u'fish belt transect'))

    class Meta:
        db_table = 'transectmethod_transectbeltfish'
        verbose_name = _(u'fish belt transect')
        verbose_name_plural = _(u'fish belt transect observations')

    def __str__(self):
        return _(u'fish belt transect %s') % self.transect.__str__()


class FishSizeBin(BaseChoiceModel):
    val = models.CharField(max_length=100)

    def __str__(self):
        return self.val


class FishSize(BaseModel):
    fish_bin_size = models.ForeignKey(FishSizeBin, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    val = models.FloatField()
    min_val = models.FloatField(null=True, blank=True)
    max_val = models.FloatField(null=True, blank=True)

    @property
    def choice(self):
        return {'id': self.val, 'name': self.name, 'updated_on': self.updated_on}


class ObsBeltFish(BaseModel, JSONMixin):
    project_lookup = "beltfish__transect__sample_event__site__project"

    beltfish = models.ForeignKey(BeltFish, on_delete=models.CASCADE,
                                 related_name='beltfish_observations')
    fish_attribute = models.ForeignKey(FishAttribute, on_delete=models.PROTECT)
    size = models.DecimalField(max_digits=5, decimal_places=1, verbose_name=_(u'size (cm)'),
                               validators=[MinValueValidator(0)])
    count = models.PositiveIntegerField(default=1)
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    _hide_fish_in_repr = False

    class Meta:
        db_table = 'obs_transectbeltfish'
        verbose_name = _(u'fish belt transect observation')
        ordering = ["created_on"]

    def __str__(self):
        if self._hide_fish_in_repr:
            return ""
        return _(u'%s %s x %scm') % (self.fish_attribute.__str__(), self.count, self.size)

    @property
    def observers(self):
        if self.beltfish_id is None:
            return Observer.objects.none()

        return self.beltfish.observers.all()


class CollectRecord(BaseModel):
    project_lookup = "project"

    SAVING_STAGE = 3
    SAVED_STAGE = 5
    VALIDATING_STAGE = 10
    VALIDATED_STAGE = 15
    SUBMITTING_STAGE = 20
    SUBMITTED_STAGE = 25

    STAGE_CHOICES = (
        (SAVING_STAGE, _('Saving'),),
        (SAVED_STAGE, _('Saved'),),
        (VALIDATING_STAGE, _('Validating'),),
        (VALIDATED_STAGE, _('Validated'),),
        (SUBMITTING_STAGE, _('Submitting'),),
        (SUBMITTED_STAGE, _('Submitted'),),
    )
    STAGE_CHOICES_UPDATED_ON = datetime.datetime(2019, 2, 2, 0, 0, 0, 0, pytz.UTC)

    project = models.ForeignKey(Project, related_name='collect_records', on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE,
                                related_name='collect_records')
    data = JSONField(encoder=JSONEncoder, null=True, blank=True)
    validations = JSONField(encoder=JSONEncoder, null=True, blank=True)
    stage = models.PositiveIntegerField(choices=STAGE_CHOICES, null=True, blank=True)

    @property
    def protocol(self):
        data = self.data or {}
        protocol = data.get("protocol")
        if protocol not in PROTOCOL_MAP:
            return None

        return protocol
    
    @property
    def sample_unit(self):
        data = self.data or {}
        protocol = self.protocol
        if protocol in (BENTHICLIT_PROTOCOL, BENTHICPIT_PROTOCOL, HABITATCOMPLEXITY_PROTOCOL):
            return data.get("benthic_transect") or {}
        elif protocol == FISHBELT_PROTOCOL:
            return data.get("fishbelt_transect") or {}
        elif protocol == BENTHICPQT_PROTOCOL:
            return data.get("quadrat_transect") or {}
        elif protocol == BLEACHINGQC_PROTOCOL:
            return data.get("quadrat_collection") or {}
        return None

    def _assign_id(self, record):
        record["id"] = record.get("id") or str(uuid.uuid4())
        return record

    def save(self, ignore_stage=False, **kwargs):
        if ignore_stage is False:
            self.stage = self.SAVED_STAGE

        protocol = self.protocol
        obs_keys = []
        if protocol == FISHBELT_PROTOCOL:
            obs_keys = ["obs_belt_fishes"]
        elif protocol == BLEACHINGQC_PROTOCOL:
            obs_keys = ["obs_colonies_bleached", "obs_quadrat_benthic_percent"]
        elif protocol == BENTHICLIT_PROTOCOL:
            obs_keys = ["obs_benthic_lits"]
        elif protocol == BENTHICPIT_PROTOCOL:
            obs_keys = ["obs_benthic_pits"]
        elif protocol == HABITATCOMPLEXITY_PROTOCOL:
            obs_keys = ["obs_habitat_complexities"]
        elif protocol == BENTHICPQT_PROTOCOL:
            obs_keys = ["obs_benthic_photo_quadrats"]

        for obs_key in obs_keys:
            self.data[obs_key] = [self._assign_id(r) for r in self.data.get(obs_key) or []]



        super(CollectRecord, self).save(**kwargs)


class ArchivedRecord(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    project_pk = models.UUIDField(db_index=True, null=True, blank=True)
    record_pk = models.UUIDField(db_index=True, null=True, blank=True)
    record = JSONField(null=True, blank=True)


class Covariate(BaseModel, JSONMixin):
    SUPPORTED_COVARIATES = (
        ("aca_benthic", "Benthic_Allen Coral Atlas",),
        ("aca_geomorphic", "Geomorphic_Allen Coral Atlas",),
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

    site = models.ForeignKey(
        "Site",
        related_name="covariates",
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100, choices=SUPPORTED_COVARIATES)
    datestamp = models.DateField()
    requested_datestamp = models.DateField()
    value = JSONField(null=True, blank=True)

    class Meta:
        unique_together = ("site", "name",)

    def __str__(self):
        return f"{self.site.name} - {self.name}"


class AuditRecord(JSONMixin):
    SUBMIT_RECORD_EVENT_TYPE = 1
    EDIT_RECORD_EVENT_TYPE = 2

    AUDIT_EVENT_TYPES = (
        (SUBMIT_RECORD_EVENT_TYPE, "Submit Record",),
        (EDIT_RECORD_EVENT_TYPE, "Edit Record",),
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
