import datetime as _datetime
import itertools
import operator as pyoperator
from decimal import Decimal

from django.contrib.gis.db import models
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Avg, F, Max, Q
from django.utils.translation import gettext as _

from ...utils import create_timestamp, expired_timestamp
from ..base import BaseAttributeModel, BaseChoiceModel, BaseModel, JSONMixin
from ..core import FISHBELT_PROTOCOL, Observer, Region, Transect, TransectMethod


class BeltTransectWidth(BaseChoiceModel):
    name = models.CharField(unique=True, max_length=100, null=True, blank=True)

    def __str__(self):
        return _("%s") % (self.name or "")

    @property
    def choice(self):
        ret = {
            "id": self.pk,
            "name": self.__str__(),
            "updated_on": self.updated_on,
            "conditions": [cnd.choice for cnd in self.conditions.all().order_by("val")],
        }

        return ret

    def _get_default_condition(self, conditions):
        for i, condition in enumerate(conditions):
            if condition.operator is None or condition.size is None:
                return conditions.pop(i)
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
        "BeltTransectWidth", on_delete=models.PROTECT, related_name="conditions"
    )
    operator = models.CharField(max_length=2, choices=OPERATOR_CHOICES, null=True, blank=True)
    size = models.DecimalField(
        decimal_places=1,
        max_digits=5,
        null=True,
        blank=True,
        verbose_name=_("fish size (cm)"),
    )
    val = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["belttransectwidth", "operator", "size"],
                name="unique_belt_width_operator_size",
            )
        ]

    def __str__(self):
        if self.operator is None or self.size is None:
            return str(self.belttransectwidth)
        return str(
            _(
                "{} {}cm @ {}".format(
                    str(self.operator or ""),
                    str(self.size or ""),
                    str(self.belttransectwidth),
                )
            )
        )

    @property
    def op(self):
        if self.operator == self.OPERATOR_EQ:
            return pyoperator.eq
        elif self.operator == self.OPERATOR_NE:
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
            "id": self.pk,
            "name": self.__str__(),
            "updated_on": self.updated_on,
            "size": self.size,
            "operator": self.operator,
            "val": self.val,
        }
        return ret


class FishSizeBin(BaseChoiceModel):
    val = models.CharField(max_length=100)

    def __str__(self):
        return self.val


class FishBeltTransect(Transect):
    number = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=50, blank=True)
    width = models.ForeignKey(
        BeltTransectWidth, verbose_name=_("width (m)"), on_delete=models.PROTECT
    )
    size_bin = models.ForeignKey("FishSizeBin", on_delete=models.PROTECT)

    class Meta:
        db_table = "transect_belt_fish"
        verbose_name = _("fish belt transect")


class FishAttribute(BaseAttributeModel):
    GROUPING_RANK = "grouping"
    FAMILY_RANK = "family"
    GENUS_RANK = "genus"
    SPECIES_RANK = "species"

    class Meta:
        db_table = "fish_attribute"

    def __str__(self):
        if hasattr(self, "fishgrouping"):
            return _("%s") % self.fishgrouping.name
        elif hasattr(self, "fishfamily"):
            return _("%s") % self.fishfamily.name
        elif hasattr(self, "fishgenus"):
            return _("%s") % self.fishgenus.name
        elif hasattr(self, "fishspecies"):
            return _("%s %s") % (self.fishspecies.genus.name, self.fishspecies.name)
        return "no-name attribute"

    @property
    def taxonomic_rank(self):
        if hasattr(self, "fishgrouping"):
            return self.GROUPING_RANK
        elif hasattr(self, "fishfamily"):
            return self.FAMILY_RANK
        elif hasattr(self, "fishgenus"):
            return self.GENUS_RANK
        elif hasattr(self, "fishspecies"):
            return self.SPECIES_RANK
        return None

    def _get_taxon(self):
        if hasattr(self, "fishgrouping"):
            return self.fishgrouping
        elif hasattr(self, "fishfamily"):
            return self.fishfamily
        elif hasattr(self, "fishgenus"):
            return self.fishgenus
        elif hasattr(self, "fishspecies"):
            return self.fishspecies
        return None

    def get_biomass_constants(self):
        taxon = self._get_taxon()
        if taxon is None:
            return None, None, None
        return (
            taxon.biomass_constant_a,
            taxon.biomass_constant_b,
            taxon.biomass_constant_c,
        )

    @property
    def regions(self):
        taxon = self._get_taxon()
        if taxon is None:
            return Region.objects.none()
        return taxon.regions

    def get_max_length(self):
        taxon = self._get_taxon()
        if taxon is None:
            return None
        return taxon.max_length


class FishGrouping(FishAttribute):
    name = models.CharField(max_length=100)
    regions = models.ManyToManyField(Region, blank=True)

    def _get_attribute_aggs(self):
        if hasattr(self, "_attribute_aggs"):
            return self._attribute_aggs

        attributes = list(self.attribute_grouping.all())
        if not attributes:
            species = FishSpecies.objects.none()
        else:
            q = Q()
            for a in attributes:
                q |= Q(pk=a.attribute.pk)
                q |= Q(genus=a.attribute)
                q |= Q(genus__family=a.attribute)
            q &= Q(regions__in=self.regions.all())
            species = FishSpecies.objects.filter(q).distinct()

        fishattr_aggs = list(
            species.aggregate(
                Avg("biomass_constant_a"),
                Avg("biomass_constant_b"),
                Avg("biomass_constant_c"),
                Max("max_length"),
            ).values()
        )
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
        return _("%s") % (self.name or "")


class FishGroupingRelationship(models.Model):
    grouping = models.ForeignKey(
        FishGrouping, related_name="attribute_grouping", on_delete=models.CASCADE
    )
    attribute = models.ForeignKey(
        FishAttribute, related_name="grouping_attribute", on_delete=models.CASCADE
    )

    def __str__(self):
        return "%s > %s" % (self.grouping, self.attribute)


class FishFamily(FishAttribute):
    # Caching at the class level
    species_agg = None
    species_agg_timestamp = None
    regions_agg = None

    name = models.CharField(max_length=100)

    def _set_species_agg_vals(self):
        if not FishFamily.species_agg or expired_timestamp(FishFamily.species_agg_timestamp):
            species_agg_qs = (
                FishSpecies.objects.select_related("genus__family")
                .order_by()
                .values(family=F("genus__family"))
                .annotate(
                    biomass_constant_a=Avg("biomass_constant_a"),
                    biomass_constant_b=Avg("biomass_constant_b"),
                    biomass_constant_c=Avg("biomass_constant_c"),
                    max_length=Max("max_length"),
                )
            )

            regions_agg_qs = (
                FishSpecies.objects.select_related("genus__family")
                .order_by()
                .values(family=F("genus__family"))
                .annotate(
                    regions=ArrayAgg("regions", distinct=True),
                )
            )

            FishFamily.species_agg = {str(bc["family"]): bc for bc in species_agg_qs}
            FishFamily.regions_agg = {str(fr["family"]): fr["regions"] for fr in regions_agg_qs}
            FishFamily.species_agg_timestamp = create_timestamp(ttl=30)

        family = FishFamily.species_agg.get(str(self.pk))
        self._biomass_a = None
        self._biomass_b = None
        self._biomass_c = None
        self._max_length = None
        self._regions = []

        if family is not None:
            if family.get("biomass_constant_a") is not None:
                self._biomass_a = round(family.get("biomass_constant_a"), 6)
            if family.get("biomass_constant_b") is not None:
                self._biomass_b = round(family.get("biomass_constant_b"), 6)
            if family.get("biomass_constant_c") is not None:
                self._biomass_c = round(family.get("biomass_constant_c"), 6)
            if family.get("max_length") is not None:
                self._max_length = round(family.get("max_length"), 6)

        if FishFamily.regions_agg is not None:
            self._regions = [
                r for r in (FishFamily.regions_agg.get(str(self.pk)) or []) if r is not None
            ]

        return FishFamily.species_agg

    @property
    def biomass_constant_a(self):
        if hasattr(self, "_biomass_a"):
            return self._biomass_a

        self._set_species_agg_vals()
        return self._biomass_a

    @property
    def biomass_constant_b(self):
        if hasattr(self, "_biomass_b"):
            return self._biomass_b

        self._set_species_agg_vals()
        return self._biomass_b

    @property
    def biomass_constant_c(self):
        if hasattr(self, "_biomass_c"):
            return self._biomass_c

        self._set_species_agg_vals()
        return self._biomass_c

    @property
    def max_length(self):
        if hasattr(self, "_max_length"):
            return self._max_length

        self._set_species_agg_vals()
        return self._max_length

    @property
    def regions(self):
        if hasattr(self, "_regions"):
            return self._regions

        self._set_species_agg_vals()
        return self._regions

    class Meta:
        db_table = "fish_family"
        ordering = ("name",)
        verbose_name_plural = _("fish families")

    def __str__(self):
        return _("%s") % self.name


class FishGenus(FishAttribute):
    # Caching at the class level
    species_agg = None
    species_agg_timestamp = None
    regions_agg = None

    name = models.CharField(max_length=100)
    family = models.ForeignKey(FishFamily, on_delete=models.CASCADE)

    def _set_species_agg_vals(self):
        if not FishGenus.species_agg or expired_timestamp(FishGenus.species_agg_timestamp):
            species_agg_qs = (
                FishSpecies.objects.order_by()
                .values("genus")
                .annotate(
                    biomass_constant_a=Avg("biomass_constant_a"),
                    biomass_constant_b=Avg("biomass_constant_b"),
                    biomass_constant_c=Avg("biomass_constant_c"),
                    max_length=Max("max_length"),
                )
            )

            regions_agg_qs = (
                FishSpecies.objects.order_by()
                .values("genus")
                .annotate(
                    regions=ArrayAgg("regions", distinct=True),
                )
            )

            FishGenus.species_agg = {str(bc["genus"]): bc for bc in species_agg_qs}
            FishGenus.regions_agg = {str(gr["genus"]): gr["regions"] for gr in regions_agg_qs}
            FishGenus.species_agg_timestamp = create_timestamp(ttl=30)

        genus = FishGenus.species_agg.get(str(self.pk))
        self._biomass_a = None
        self._biomass_b = None
        self._biomass_c = None
        self._max_length = None
        self._regions = []
        if genus is not None:
            if genus.get("biomass_constant_a") is not None:
                self._biomass_a = round(genus.get("biomass_constant_a"), 6)
            if genus.get("biomass_constant_b") is not None:
                self._biomass_b = round(genus.get("biomass_constant_b"), 6)
            if genus.get("biomass_constant_c") is not None:
                self._biomass_c = round(genus.get("biomass_constant_c"), 6)
            if genus.get("max_length") is not None:
                self._max_length = genus.get("max_length")

        if FishGenus.regions_agg is not None:
            self._regions = [
                r for r in (FishGenus.regions_agg.get(str(self.pk)) or []) if r is not None
            ]

        return FishGenus.species_agg

    @property
    def biomass_constant_a(self):
        if hasattr(self, "_biomass_a"):
            return self._biomass_a

        self._set_species_agg_vals()
        return self._biomass_a

    @property
    def biomass_constant_b(self):
        if hasattr(self, "_biomass_b"):
            return self._biomass_b

        self._set_species_agg_vals()
        return self._biomass_b

    @property
    def biomass_constant_c(self):
        if hasattr(self, "_biomass_c"):
            return self._biomass_c

        self._set_species_agg_vals()
        return self._biomass_c

    @property
    def regions(self):
        if hasattr(self, "_regions"):
            return self._regions

        self._set_species_agg_vals()
        return self._regions

    @property
    def max_length(self):
        if hasattr(self, "_max_length"):
            return self._max_length

        self._set_species_agg_vals()
        return self._max_length

    class Meta:
        db_table = "fish_genus"
        ordering = ("name",)
        verbose_name_plural = _("fish genera")

    def __str__(self):
        return _("%s") % self.name


class FishGroupSize(BaseChoiceModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "fish_group_size"
        ordering = ("name",)
        verbose_name = _("fish group size")

    def __str__(self):
        return _("%s") % self.name


class FishGroupTrophic(BaseChoiceModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "fish_group_trophic"
        ordering = ("name",)
        verbose_name = _("fish trophic group")

    def __str__(self):
        return _("%s") % self.name


class FishGroupFunction(BaseChoiceModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "fish_group_function"
        ordering = ("name",)
        verbose_name = _("fish functional group")

    def __str__(self):
        return _("%s") % self.name


class FishSpecies(FishAttribute):
    LENGTH_TYPES = (
        ("fork length", "fork length"),
        ("standard length", "standard length"),
        ("total length", "total length"),
        ("wing diameter", "wing diameter"),
    )
    LENGTH_TYPES_CHOICES_UPDATED_ON = _datetime.datetime(
        2020, 1, 21, 0, 0, 0, 0, tzinfo=_datetime.timezone.utc
    )

    name = models.CharField(max_length=100)
    genus = models.ForeignKey(FishGenus, on_delete=models.CASCADE)
    regions = models.ManyToManyField(Region, blank=True)
    biomass_constant_a = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True)
    biomass_constant_b = models.DecimalField(max_digits=7, decimal_places=6, null=True, blank=True)
    biomass_constant_c = models.DecimalField(
        max_digits=7, decimal_places=6, default=1, null=True, blank=True
    )
    vulnerability = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_length = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("maximum length (cm)"),
        null=True,
        blank=True,
    )
    trophic_level = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )
    max_length_type = models.CharField(max_length=50, choices=LENGTH_TYPES, blank=True)
    group_size = models.ForeignKey(FishGroupSize, on_delete=models.SET_NULL, null=True, blank=True)
    trophic_group = models.ForeignKey(
        FishGroupTrophic, on_delete=models.SET_NULL, null=True, blank=True
    )
    functional_group = models.ForeignKey(
        FishGroupFunction, on_delete=models.SET_NULL, null=True, blank=True
    )
    climate_score = models.DecimalField(
        max_digits=10,
        decimal_places=9,
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "fish_species"
        ordering = (
            "genus",
            "name",
        )
        verbose_name_plural = _("fish species")

    def __str__(self):
        return _("%s %s") % (self.genus.name, self.name)


class FishSize(BaseModel):
    fish_bin_size = models.ForeignKey(FishSizeBin, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    val = models.FloatField()
    min_val = models.FloatField(null=True, blank=True)
    max_val = models.FloatField(null=True, blank=True)

    @property
    def choice(self):
        return {"id": self.val, "name": self.name, "updated_on": self.updated_on}


class BeltFish(TransectMethod):
    protocol = FISHBELT_PROTOCOL
    project_lookup = "transect__sample_event__site__project"

    transect = models.OneToOneField(
        FishBeltTransect,
        on_delete=models.CASCADE,
        related_name="beltfish_method",
        verbose_name=_("fish belt transect"),
    )

    class Meta:
        db_table = "transectmethod_transectbeltfish"
        verbose_name = _("fish belt transect")
        verbose_name_plural = _("fish belt transect observations")

    def __str__(self):
        return _("fish belt transect %s") % self.transect.__str__()


class ObsBeltFish(BaseModel, JSONMixin):
    project_lookup = "beltfish__transect__sample_event__site__project"

    beltfish = models.ForeignKey(
        BeltFish, on_delete=models.CASCADE, related_name="beltfish_observations"
    )
    fish_attribute = models.ForeignKey(FishAttribute, on_delete=models.PROTECT)
    size = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name=_("size (cm)"),
    )
    count = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

    _hide_fish_in_repr = False

    class Meta:
        db_table = "obs_transectbeltfish"
        verbose_name = _("fish belt transect observation")
        ordering = ["created_on"]

    def __str__(self):
        if self._hide_fish_in_repr:
            return ""
        return _("%s %s x %scm") % (
            self.fish_attribute.__str__(),
            self.count,
            self.size,
        )

    @property
    def observers(self):
        if self.beltfish_id is None:
            return Observer.objects.none()

        return self.beltfish.observers.all()
