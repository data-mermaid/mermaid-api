from django.contrib.gis.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _
from .base import BaseModel, ExtendedManager
from .mermaid import Project


class BeltFishObsView(BaseModel):
    project_lookup = "project_id"

    project_id = models.UUIDField()
    project_name = models.CharField(max_length=255)
    project_status = models.PositiveSmallIntegerField(choices=Project.STATUSES, default=Project.OPEN)
    project_notes = models.TextField(blank=True)
    contact_link = models.CharField(max_length=255)
    site_id = models.UUIDField()
    site_name = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=16, decimal_places=14)
    lon = models.DecimalField(max_digits=17, decimal_places=14)
    site_notes = models.TextField(blank=True)
    country_id = models.UUIDField()
    country_name = models.CharField(max_length=50)
    reef_type = models.CharField(max_length=50)
    reef_zone = models.CharField(max_length=50)
    reef_exposure = models.CharField(max_length=50)
    management_id = models.UUIDField()
    management_name = models.CharField(max_length=255)
    management_name_secondary = models.CharField(max_length=255)
    management_est_year = models.PositiveSmallIntegerField()
    management_size = models.DecimalField(max_digits=12, decimal_places=3,
                                          verbose_name=_(u'Size (ha)'),
                                          null=True, blank=True)
    management_parties = JSONField(null=True, blank=True)
    management_compliance = models.CharField(max_length=100)
    management_rules = JSONField(null=True, blank=True)
    management_notes = models.TextField(blank=True)
    sample_date = models.DateField()
    sample_time = models.TimeField()
    current_name = models.CharField(max_length=50)
    tide_name = models.CharField(max_length=50)
    visibility_name = models.CharField(max_length=50)
    depth = models.DecimalField(max_digits=3, decimal_places=1, verbose_name=_(u'depth (m)'))
    sample_event_notes = models.TextField(blank=True)
    sample_unit_id = models.UUIDField()
    number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True)
    transect_len_surveyed = models.PositiveSmallIntegerField(
        verbose_name=_(u'transect length surveyed (m)'))
    transect_width = models.PositiveSmallIntegerField(null=True, blank=True)
    observers = JSONField(null=True, blank=True)
    fish_taxon = models.CharField(max_length=100)
    trophic_group = models.CharField(max_length=100, blank=True)
    trophic_level = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    functional_group = models.CharField(max_length=100, blank=True)
    vulnerability = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    biomass_constant_a = models.DecimalField(max_digits=7, decimal_places=6,
                                             null=True, blank=True)
    biomass_constant_b = models.DecimalField(max_digits=7, decimal_places=6,
                                             null=True, blank=True)
    biomass_constant_c = models.DecimalField(max_digits=7, decimal_places=6, default=1,
                                             null=True, blank=True)
    size_bin = models.PositiveSmallIntegerField()
    size = models.DecimalField(max_digits=5, decimal_places=1, verbose_name=_(u'size (cm)'))
    count = models.PositiveIntegerField(default=1)
    biomass_kgha = models.DecimalField(max_digits=6, decimal_places=2,
                                       verbose_name=_(u'biomass (kg/ha)'),
                                       null=True, blank=True)
    observation_notes = models.TextField(blank=True)
    data_policy_beltfish = models.CharField(max_length=50)

    objects = ExtendedManager()

    class Meta:
        db_table = "vw_beltfish_obs"
        managed = False
