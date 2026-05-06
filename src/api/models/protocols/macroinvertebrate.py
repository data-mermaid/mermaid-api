from django.contrib.gis.db import models
from django.db.models import F, Max
from django.utils.translation import gettext as _

from ...utils import create_timestamp, expired_timestamp
from ..base import BaseAttributeModel, BaseChoiceModel, BaseModel, JSONMixin
from ..core import (
    INCLUDE_OBS_TEXT,
    MACROINVERTEBRATE_PROTOCOL,
    Observer,
    Transect,
    TransectMethod,
)


class InvertBeltTransectWidth(BaseChoiceModel):
    val = models.DecimalField(max_digits=4, decimal_places=1)
    name = models.CharField(max_length=100, blank=True, unique=True)

    def __str__(self):
        return _("%s") % self.val

    class Meta:
        db_table = "invert_belt_transect_width"
        ordering = ("val",)
        verbose_name = _("macroinvertebrate belt transect width")
        verbose_name_plural = _("macroinvertebrate belt transect widths")


class InvertSizeBin(BaseChoiceModel):
    val = models.CharField(max_length=100)

    def __str__(self):
        return self.val

    class Meta:
        db_table = "invert_size_bin"
        verbose_name = _("macroinvertebrate size bin")
        verbose_name_plural = _("macroinvertebrate size bins")


class InvertSize(BaseModel):
    invert_bin_size = models.ForeignKey(InvertSizeBin, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    val = models.FloatField()
    min_val = models.FloatField(null=True, blank=True)
    max_val = models.FloatField(null=True, blank=True)

    @property
    def choice(self):
        return {"id": self.val, "name": self.name, "updated_on": self.updated_on}

    class Meta:
        db_table = "invert_size"
        verbose_name = _("macroinvertebrate size")
        verbose_name_plural = _("macroinvertebrate sizes")


class InvertGroupOfInterest(BaseChoiceModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return _("%s") % self.name

    class Meta:
        db_table = "invert_group_of_interest"
        ordering = ("name",)
        verbose_name = _("macroinvertebrate group of interest")
        verbose_name_plural = _("macroinvertebrate groups of interest")


class InvertHarvestType(BaseChoiceModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return _("%s") % self.name

    class Meta:
        db_table = "invert_harvest_type"
        ordering = ("name",)
        verbose_name = _("macroinvertebrate harvest type")
        verbose_name_plural = _("macroinvertebrate harvest types")


class InvertAttribute(BaseAttributeModel):
    CLASS_RANK = "class"
    CLASS_GOI_RANK = "class_goi"
    ORDER_RANK = "order"
    FAMILY_RANK = "family"
    GENUS_RANK = "genus"
    SPECIES_RANK = "species"

    class Meta:
        db_table = "invert_attribute"

    def __str__(self):
        if hasattr(self, "invertclass"):
            return _("%s") % self.invertclass.name
        elif hasattr(self, "invertclassgroupofinterest"):
            return _("%s (%s)") % (
                self.invertclassgroupofinterest.invert_class.name,
                self.invertclassgroupofinterest.group_of_interest.name,
            )
        elif hasattr(self, "invertorder"):
            return _("%s") % self.invertorder.name
        elif hasattr(self, "invertfamily"):
            return _("%s") % self.invertfamily.name
        elif hasattr(self, "invertgenus"):
            return _("%s") % self.invertgenus.name
        elif hasattr(self, "invertspecies"):
            return _("%s %s") % (self.invertspecies.genus.name, self.invertspecies.name)
        return "no-name attribute"

    @property
    def taxonomic_rank(self):
        if hasattr(self, "invertclass"):
            return self.CLASS_RANK
        elif hasattr(self, "invertclassgroupofinterest"):
            return self.CLASS_GOI_RANK
        elif hasattr(self, "invertorder"):
            return self.ORDER_RANK
        elif hasattr(self, "invertfamily"):
            return self.FAMILY_RANK
        elif hasattr(self, "invertgenus"):
            return self.GENUS_RANK
        elif hasattr(self, "invertspecies"):
            return self.SPECIES_RANK
        return None


class InvertMaxLengthMixin:
    """Computes max_length as the maximum across all constituent InvertSpecies.

    Each subclass must set _species_join_path to the F() path from InvertSpecies
    back to its own PK (e.g. "genus__family" for InvertFamily).
    Cache is per-class and refreshes every 30 seconds.
    """

    species_agg = None
    species_agg_timestamp = None
    _species_join_path = None

    def _set_species_agg_vals(self):
        cls = type(self)
        if not cls.species_agg or expired_timestamp(cls.species_agg_timestamp):
            qs = (
                InvertSpecies.objects.order_by()
                .values(taxon=F(cls._species_join_path))
                .annotate(max_length=Max("max_length"))
            )
            cls.species_agg = {str(row["taxon"]): row["max_length"] for row in qs}
            cls.species_agg_timestamp = create_timestamp(ttl=30)
        self._max_length = cls.species_agg.get(str(self.pk))

    @property
    def max_length(self):
        if hasattr(self, "_max_length"):
            return self._max_length
        self._set_species_agg_vals()
        return self._max_length


class InvertClass(InvertMaxLengthMixin, InvertAttribute):
    # Path from InvertSpecies up through InvertClassGroupOfInterest to InvertClass.
    _species_join_path = "genus__family__order__class_goi__invert_class"

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return _("%s") % self.name

    class Meta:
        db_table = "invert_class"
        ordering = ("name",)
        verbose_name = _("macroinvertebrate class")
        verbose_name_plural = _("macroinvertebrate classes")


class InvertClassGroupOfInterest(InvertMaxLengthMixin, InvertAttribute):
    # Path from InvertSpecies up to InvertClassGroupOfInterest via InvertOrder.class_goi.
    _species_join_path = "genus__family__order__class_goi"

    invert_class = models.ForeignKey(
        InvertClass, on_delete=models.PROTECT, related_name="class_gois"
    )
    group_of_interest = models.ForeignKey(
        InvertGroupOfInterest, on_delete=models.PROTECT, related_name="class_gois"
    )

    def __str__(self):
        return _("%s (%s)") % (self.invert_class.name, self.group_of_interest.name)

    class Meta:
        db_table = "invert_class_goi"
        ordering = ("invert_class__name", "group_of_interest__name")
        verbose_name = _("macroinvertebrate class / group of interest")
        verbose_name_plural = _("macroinvertebrate class / groups of interest")
        constraints = [
            models.UniqueConstraint(
                fields=["invert_class", "group_of_interest"],
                name="unique_invert_class_goi",
            )
        ]


class InvertOrder(InvertMaxLengthMixin, InvertAttribute):
    _species_join_path = "genus__family__order"

    name = models.CharField(max_length=100)
    class_goi = models.ForeignKey(
        InvertClassGroupOfInterest, on_delete=models.PROTECT, related_name="orders"
    )

    def __str__(self):
        return _("%s") % self.name

    class Meta:
        db_table = "invert_order"
        ordering = ("name",)
        verbose_name = _("macroinvertebrate order")
        verbose_name_plural = _("macroinvertebrate orders")
        constraints = [
            models.UniqueConstraint(
                fields=["name", "class_goi"], name="unique_invertorder_name_class_goi"
            )
        ]


class InvertFamily(InvertMaxLengthMixin, InvertAttribute):
    _species_join_path = "genus__family"

    name = models.CharField(max_length=100)
    order = models.ForeignKey(InvertOrder, on_delete=models.PROTECT, related_name="families")

    def __str__(self):
        return _("%s") % self.name

    class Meta:
        db_table = "invert_family"
        ordering = ("name",)
        verbose_name = _("macroinvertebrate family")
        verbose_name_plural = _("macroinvertebrate families")
        constraints = [
            models.UniqueConstraint(fields=["name", "order"], name="unique_invertfamily_name_order")
        ]


class InvertGenus(InvertMaxLengthMixin, InvertAttribute):
    _species_join_path = "genus"

    name = models.CharField(max_length=100)
    family = models.ForeignKey(InvertFamily, on_delete=models.PROTECT, related_name="genera")

    def __str__(self):
        return _("%s") % self.name

    class Meta:
        db_table = "invert_genus"
        ordering = ("name",)
        verbose_name = _("macroinvertebrate genus")
        verbose_name_plural = _("macroinvertebrate genera")
        constraints = [
            models.UniqueConstraint(
                fields=["name", "family"], name="unique_invertgenus_name_family"
            )
        ]


class InvertSpecies(InvertAttribute):
    MEASUREMENT_TYPE_CHOICES = (
        ("arm length", "arm length"),
        ("body length", "body length"),
        ("carapace length", "carapace length"),
        ("carapace width", "carapace width"),
        ("mantle length", "mantle length"),
        ("pedal disc diameter", "pedal disc diameter"),
        ("shell length/diameter", "shell length/diameter"),
        ("test diameter", "test diameter"),
    )

    name = models.CharField(max_length=100)
    genus = models.ForeignKey(InvertGenus, on_delete=models.PROTECT, related_name="species")
    max_length = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        verbose_name=_("maximum size (cm)"),
        null=True,
        blank=True,
    )
    max_length_type = models.CharField(
        max_length=50,
        choices=MEASUREMENT_TYPE_CHOICES,
        blank=True,
        verbose_name=_("measurement type"),
    )
    max_length_source = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("size source"),
    )
    max_length_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name=_("size source URL"),
    )
    group_of_interest = models.ForeignKey(
        InvertGroupOfInterest,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return _("%s %s") % (self.genus.name, self.name)

    class Meta:
        db_table = "invert_species"
        ordering = ("genus", "name")
        verbose_name = _("macroinvertebrate species")
        verbose_name_plural = _("macroinvertebrate species")
        constraints = [
            models.UniqueConstraint(
                fields=["name", "genus"], name="unique_invertspecies_name_genus"
            )
        ]


class InvertBeltTransect(Transect):
    number = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=50, blank=True)
    width = models.ForeignKey(
        InvertBeltTransectWidth,
        verbose_name=_("width (m)"),
        on_delete=models.PROTECT,
    )
    size_bin = models.ForeignKey(
        InvertSizeBin,
        on_delete=models.PROTECT,
        verbose_name=_("size bin (cm)"),
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "transect_belt_invert"
        verbose_name = _("macroinvertebrate belt transect")
        verbose_name_plural = _("macroinvertebrate belt transects")


class BeltInvert(TransectMethod):
    protocol = MACROINVERTEBRATE_PROTOCOL
    project_lookup = "transect__sample_event__site__project"

    transect = models.OneToOneField(
        InvertBeltTransect,
        on_delete=models.CASCADE,
        related_name="beltinvert_method",
        verbose_name=_("macroinvertebrate belt transect"),
    )

    def __str__(self):
        return _("macroinvertebrate belt transect %s") % self.transect.__str__()

    class Meta:
        db_table = "transectmethod_transectbeltinvert"
        verbose_name = _("macroinvertebrate belt transect")
        verbose_name_plural = _("macroinvertebrate belt transect observations")


class ObsBeltInvert(BaseModel, JSONMixin):
    project_lookup = "beltinvert__transect__sample_event__site__project"

    beltinvert = models.ForeignKey(
        BeltInvert,
        on_delete=models.CASCADE,
        related_name="beltinvert_observations",
    )
    invert_attribute = models.ForeignKey(InvertAttribute, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(default=1)
    size = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        verbose_name=_("size (cm)"),
        null=True,
        blank=True,
    )
    include = models.BooleanField(default=True, verbose_name=INCLUDE_OBS_TEXT)
    notes = models.TextField(blank=True)

    def __str__(self):
        return _("%s x %s") % (self.invert_attribute.__str__(), self.count)

    @property
    def observers(self):
        if self.beltinvert_id is None:
            return Observer.objects.none()
        return self.beltinvert.observers.all()

    class Meta:
        db_table = "obs_transectbeltinvert"
        verbose_name = _("macroinvertebrate belt transect observation")
        ordering = ["created_on"]
