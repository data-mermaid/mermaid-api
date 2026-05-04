from django.contrib import admin

from ...models import (
    BeltInvert,
    InvertAttribute,
    InvertBeltTransect,
    InvertBeltTransectWidth,
    InvertClass,
    InvertFamily,
    InvertGenus,
    InvertGroupOfInterest,
    InvertHarvestType,
    InvertOrder,
    InvertPhylum,
    InvertSize,
    InvertSizeBin,
    InvertSpecies,
    ObsBeltInvert,
)
from ..base import (
    BaseAdmin,
    ObservationInline,
    ObserverInline,
    SampleUnitAdmin,
    TransectMethodAdmin,
)


@admin.register(InvertBeltTransectWidth)
class InvertBeltTransectWidthAdmin(BaseAdmin):
    list_display = ("val",)


@admin.register(InvertSizeBin)
class InvertSizeBinAdmin(BaseAdmin):
    list_display = ("val",)


@admin.register(InvertSize)
class InvertSizeAdmin(BaseAdmin):
    list_display = ("invert_bin_size", "name", "val")


@admin.register(InvertGroupOfInterest)
class InvertGroupOfInterestAdmin(BaseAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(InvertHarvestType)
class InvertHarvestTypeAdmin(BaseAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class InvertClassInline(admin.TabularInline):
    model = InvertClass
    fk_name = "phylum"
    extra = 0
    fields = ("name",)
    show_change_link = True


@admin.register(InvertPhylum)
class InvertPhylumAdmin(BaseAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [InvertClassInline]


class InvertOrderInline(admin.TabularInline):
    model = InvertOrder
    fk_name = "invert_class"
    extra = 0
    fields = ("name",)
    show_change_link = True


@admin.register(InvertClass)
class InvertClassAdmin(BaseAdmin):
    list_display = ("name", "phylum")
    list_filter = ("phylum",)
    search_fields = ("name", "phylum__name")
    inlines = [InvertOrderInline]


class InvertFamilyInline(admin.TabularInline):
    model = InvertFamily
    fk_name = "order"
    extra = 0
    fields = ("name",)
    show_change_link = True


@admin.register(InvertOrder)
class InvertOrderAdmin(BaseAdmin):
    list_display = ("name", "invert_class")
    search_fields = ("name", "invert_class__name")
    inlines = [InvertFamilyInline]


class InvertGenusInline(admin.TabularInline):
    model = InvertGenus
    fk_name = "family"
    extra = 0
    fields = ("name",)
    show_change_link = True


@admin.register(InvertFamily)
class InvertFamilyAdmin(BaseAdmin):
    list_display = ("name", "order")
    search_fields = ("name", "order__name")
    inlines = [InvertGenusInline]


class InvertSpeciesInline(admin.TabularInline):
    model = InvertSpecies
    fk_name = "genus"
    extra = 0
    fields = ("name", "group_of_interest", "harvest_type", "max_length")
    show_change_link = True


@admin.register(InvertGenus)
class InvertGenusAdmin(BaseAdmin):
    list_display = ("name", "family")
    search_fields = ("name", "family__name")
    inlines = [InvertSpeciesInline]


@admin.register(InvertSpecies)
class InvertSpeciesAdmin(BaseAdmin):
    list_display = (
        "name",
        "genus",
        "group_of_interest",
        "harvest_type",
        "max_length",
        "max_length_type",
    )
    list_filter = ("group_of_interest", "harvest_type")
    search_fields = ("name", "genus__name", "genus__family__name")


class ObsBeltInvertInline(ObservationInline):
    model = ObsBeltInvert
    cache_fields = ["invert_attribute"]


@admin.register(InvertBeltTransect)
class InvertBeltTransectAdmin(SampleUnitAdmin):
    list_display = ("name", "len_surveyed", "width", "size_bin", "depth")


@admin.register(BeltInvert)
class BeltInvertAdmin(TransectMethodAdmin):
    list_display = ("name", "len_surveyed", "width", "depth")
    inlines = (ObserverInline, ObsBeltInvertInline)

    def width(self, obj):
        return obj.transect.width

    width.admin_order_field = "transect__width"

    def get_formsets_with_inlines(self, request, obj=None):
        qs = InvertAttribute.objects.select_related(
            "invertphylum",
            "invertclass",
            "invertorder",
            "invertfamily",
            "invertgenus",
            "invertspecies",
            "invertspecies__genus",
        )
        invert_attributes = sorted(qs, key=str)

        for inline in self.get_inline_instances(request, obj):
            inline.cached_invert_attributes = [(ia.pk, str(ia)) for ia in invert_attributes]
            yield inline.get_formset(request, obj), inline

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "created_by",
                "updated_by",
                "transect",
                "transect__sample_event",
                "transect__sample_event__site",
                "transect__width",
            )
        )
