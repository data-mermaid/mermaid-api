from django.contrib.gis.db import models
from django.utils.translation import gettext as _

from ..base import BaseAttributeModel, BaseChoiceModel, BaseModel, JSONMixin
from ..core import (
    BENTHICLIT_PROTOCOL,
    BENTHICPIT_PROTOCOL,
    BENTHICPQT_PROTOCOL,
    HABITATCOMPLEXITY_PROTOCOL,
    INCLUDE_OBS_TEXT,
    Region,
    Transect,
    TransectMethod,
)


class BenthicTransect(Transect):
    number = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "transect_benthic"


class QuadratTransect(Transect):
    number = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=50, blank=True)
    quadrat_size = models.DecimalField(
        decimal_places=2,
        max_digits=6,
        verbose_name=_("single quadrat area (m2)"),
        default=1,
    )
    num_quadrats = models.PositiveSmallIntegerField()
    num_points_per_quadrat = models.PositiveSmallIntegerField()
    quadrat_number_start = models.PositiveSmallIntegerField(
        default=1, verbose_name=_("number of first quadrat")
    )

    class Meta:
        db_table = "quadrat_transect"


class BenthicLifeHistory(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "benthic_lifehistory"
        verbose_name_plural = _("benthic life histories")
        ordering = ["name"]

    def __str__(self):
        return _("%s") % self.name


class GrowthForm(BaseChoiceModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "growth_form"
        verbose_name_plural = _("growth forms")
        ordering = ["name"]

    def __str__(self):
        return _("%s") % self.name


class BenthicAttribute(BaseAttributeModel):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    regions = models.ManyToManyField(Region, blank=True)
    life_histories = models.ManyToManyField(BenthicLifeHistory, blank=True)

    @property
    def descendants(self):
        sql = """
            WITH RECURSIVE descendants(id, name, parent_id) AS (
                SELECT id, name, parent_id FROM benthic_attribute WHERE id = '%s'
              UNION ALL
                SELECT a.id, a.name, a.parent_id
                FROM descendants d, benthic_attribute a
                WHERE a.parent_id = d.id
            )
            SELECT id, name, parent_id
            FROM descendants
            WHERE id != '%s'
        """ % (
            self.pk,
            self.pk,
        )
        return type(self).objects.raw(sql)

    @property
    def origin(self):
        sql = """
            WITH RECURSIVE parents(id, name, parent_id) AS (
                SELECT id, name, parent_id FROM benthic_attribute WHERE id = '{}'
                UNION ALL
                SELECT a.id, a.name, a.parent_id
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
        db_table = "benthic_attribute"
        ordering = ["name"]

    def __str__(self):
        return _("%s") % self.name


class BenthicAttributeGrowthForm(models.Model):
    benthic_attribute = models.ForeignKey(
        BenthicAttribute, related_name="benthic_attribute_growth_forms", on_delete=models.CASCADE
    )
    growth_form = models.ForeignKey(
        GrowthForm,
        related_name="benthic_attribute_growth_forms",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("benthic_attribute", "growth_form")
        db_table = "benthic_attribute_growth_form"
        verbose_name_plural = _("BA/GF unique combinations")
        ordering = ["benthic_attribute__name", "growth_form__name"]

    def __str__(self):
        name = self.benthic_attribute.name
        if self.growth_form:
            name = f"{name} {self.growth_form.name}"
        return name


class BenthicAttributeGrowthFormLifeHistory(BaseModel):
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.PROTECT)
    life_history = models.ForeignKey(BenthicLifeHistory, on_delete=models.PROTECT)

    class Meta:
        db_table = "ba_gf_life_histories"
        verbose_name_plural = _("benthic attribute growth form life histories")

    def __str__(self):
        return _(f"{self.attribute.name} - {self.growth_form.name} {self.life_history.name}")


class BenthicLIT(TransectMethod):
    protocol = BENTHICLIT_PROTOCOL
    project_lookup = "transect__sample_event__site__project"

    transect = models.OneToOneField(
        BenthicTransect,
        on_delete=models.CASCADE,
        related_name="benthiclit_method",
        verbose_name=_("benthic transect"),
    )

    class Meta:
        db_table = "transectmethod_benthiclit"
        verbose_name = _("benthic LIT")
        verbose_name_plural = _("benthic LIT observations")

    def __str__(self):
        return _("benthic LIT %s") % self.transect.__str__()


class ObsBenthicLIT(BaseModel, JSONMixin):
    project_lookup = "benthiclit__transect__sample_event__site__project"

    benthiclit = models.ForeignKey(
        BenthicLIT, related_name="obsbenthiclit_set", on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    length = models.PositiveSmallIntegerField(verbose_name=_("length (cm)"))
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "obs_benthiclit"
        verbose_name = _("benthic LIT observation")
        ordering = ["created_on"]

    def __str__(self):
        return _("%s") % (self.length)


class BenthicPIT(TransectMethod):
    protocol = BENTHICPIT_PROTOCOL
    project_lookup = "transect__sample_event__site__project"

    transect = models.OneToOneField(
        BenthicTransect,
        on_delete=models.CASCADE,
        related_name="benthicpit_method",
        verbose_name="benthic transect",
    )
    interval_size = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval size (m)"),
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )

    class Meta:
        db_table = "transectmethod_benthicpit"
        verbose_name = _("benthic PIT")
        verbose_name_plural = _("benthic PIT observations")

    def __str__(self):
        return _("benthic PIT %s") % self.transect.__str__()


class ObsBenthicPIT(BaseModel, JSONMixin):
    project_lookup = "benthicpit__transect__sample_event__site__project"

    benthicpit = models.ForeignKey(
        BenthicPIT, related_name="obsbenthicpit_set", on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "obs_benthicpit"
        unique_together = ("benthicpit", "interval")
        verbose_name = _("benthic PIT observation")
        ordering = ["interval"]

    def __str__(self):
        return _("%s") % self.interval


class HabitatComplexity(TransectMethod):
    protocol = HABITATCOMPLEXITY_PROTOCOL
    project_lookup = "transect__sample_event__site__project"

    transect = models.OneToOneField(
        BenthicTransect,
        on_delete=models.CASCADE,
        related_name="habitatcomplexity_method",
        verbose_name="benthic transect",
    )
    interval_size = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval size (m)"),
    )
    interval_start = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        verbose_name=_("interval start (m)"),
    )

    class Meta:
        db_table = "transectmethod_habitatcomplexity"
        verbose_name = _("habitat complexity transect")
        verbose_name_plural = _("habitat complexity transect observations")

    def __str__(self):
        return _("habitat complexity %s") % self.transect.__str__()


class HabitatComplexityScore(BaseChoiceModel):
    name = models.CharField(max_length=100)
    val = models.PositiveSmallIntegerField()

    def __str__(self):
        return _("%s %s") % (self.val, self.name)


class ObsHabitatComplexity(BaseModel, JSONMixin):
    project_lookup = "habitatcomplexity__transect__sample_event__site__project"

    habitatcomplexity = models.ForeignKey(
        HabitatComplexity,
        related_name="habitatcomplexity_set",
        on_delete=models.CASCADE,
    )
    interval = models.DecimalField(max_digits=7, decimal_places=2)
    score = models.ForeignKey(HabitatComplexityScore, on_delete=models.PROTECT)
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "obs_habitatcomplexity"
        unique_together = ("habitatcomplexity", "interval")
        verbose_name = _("habitat complexity transect observation")
        ordering = ["interval"]

    def __str__(self):
        return _("%s") % self.interval


class BenthicPhotoQuadratTransect(TransectMethod):
    protocol = BENTHICPQT_PROTOCOL
    project_lookup = "quadrat_transect__sample_event__site__project"

    quadrat_transect = models.OneToOneField(
        QuadratTransect,
        on_delete=models.CASCADE,
        related_name="benthic_photo_quadrat_transect_method",
        verbose_name=_("benthic photo quadrat transect"),
    )
    image_classification = models.BooleanField(default=False)

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

    quadrat_number = models.PositiveSmallIntegerField(verbose_name="quadrat number")
    attribute = models.ForeignKey(BenthicAttribute, on_delete=models.PROTECT)
    growth_form = models.ForeignKey(GrowthForm, on_delete=models.SET_NULL, null=True, blank=True)
    num_points = models.PositiveSmallIntegerField(verbose_name="number of points", default=0)
    notes = models.TextField(blank=True)

    image = models.ForeignKey(
        "api.Image",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="obs_benthic_photo_quadrats",
    )

    class Meta:
        db_table = "obs_benthic_photo_quadrat"
        verbose_name = _("benthic photo quadrat transect observation")
        unique_together = (
            "benthic_photo_quadrat_transect",
            "quadrat_number",
            "attribute",
            "growth_form",
        )
        ordering = ["created_on"]

    def __str__(self):
        return str(self.quadrat_number)
