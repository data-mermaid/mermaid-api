from django.contrib.gis.db import models
from django.utils.translation import gettext as _

from ..base import BaseModel, JSONMixin
from ..core import BLEACHINGQC_PROTOCOL, BaseQuadrat, TransectMethod
from .benthic import BenthicAttribute, GrowthForm


class QuadratCollection(BaseQuadrat):
    project_lookup = "sample_event__site__project"
    label = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "quadrat_collection"


class BleachingQuadratCollection(TransectMethod):
    protocol = BLEACHINGQC_PROTOCOL
    project_lookup = "quadrat__sample_event__site__project"

    quadrat = models.OneToOneField(
        QuadratCollection,
        on_delete=models.CASCADE,
        related_name="bleachingquadratcollection_method",
        verbose_name=_("bleaching quadrat collection"),
    )

    class Meta:
        db_table = "transectmethod_bleaching_quadrat_collection"
        verbose_name = _("bleaching quadrat collection")
        verbose_name_plural = _("bleaching quadrat collection observations")

    def __str__(self):
        return _("bleaching quadrat collection %s") % self.quadrat.__str__()


class ObsColoniesBleached(BaseModel, JSONMixin):
    project_lookup = "bleachingquadratcollection__quadrat__sample_event__site__project"

    bleachingquadratcollection = models.ForeignKey(
        BleachingQuadratCollection, on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    count_normal = models.PositiveSmallIntegerField(verbose_name="normal", default=0)
    count_pale = models.PositiveSmallIntegerField(verbose_name="pale", default=0)
    count_20 = models.PositiveSmallIntegerField(verbose_name="0-20% bleached", default=0)
    count_50 = models.PositiveSmallIntegerField(verbose_name="20-50% bleached", default=0)
    count_80 = models.PositiveSmallIntegerField(verbose_name="50-80% bleached", default=0)
    count_100 = models.PositiveSmallIntegerField(verbose_name="80-100% bleached", default=0)
    count_dead = models.PositiveSmallIntegerField(verbose_name="recently dead", default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "obs_colonies_bleached"
        verbose_name = _("bleaching quadrat collection colonies bleached observation")
        ordering = ["created_on"]

    def __str__(self):
        gf = ""
        if self.growth_form is not None:
            gf = " {}".format(self.growth_form)
        return _("%s%s") % (self.attribute.__str__(), gf)


class ObsQuadratBenthicPercent(BaseModel, JSONMixin):
    project_lookup = "bleachingquadratcollection__quadrat__sample_event__site__project"

    bleachingquadratcollection = models.ForeignKey(
        BleachingQuadratCollection, on_delete=models.CASCADE
    )
    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    percent_hard = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="hard coral, % cover",
        null=True,
        blank=True,
    )
    percent_soft = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="soft coral, % cover",
        null=True,
        blank=True,
    )
    percent_algae = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="macroalgae, % cover",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "obs_quadrat_benthic_percent"
        verbose_name = _("bleaching quadrat collection percent benthic cover observation")
        ordering = ["created_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["bleachingquadratcollection", "quadrat_number"],
                name="unique_obsquadratbenthicpercent_collection_quadrat",
            )
        ]

    def __str__(self):
        return _("%s") % self.quadrat_number
