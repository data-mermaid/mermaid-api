from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ...models import (
    BeltFish,
    BeltTransectWidth,
    BeltTransectWidthCondition,
    FishAttributeView,
    FishBeltTransect,
    FishFamily,
    FishGenus,
    FishGroupFunction,
    FishGrouping,
    FishGroupingRelationship,
    FishGroupSize,
    FishGroupTrophic,
    FishSize,
    FishSizeBin,
    FishSpecies,
    ObsBeltFish,
    Region,
)
from ..base import (
    AttributeAdmin,
    BaseAdmin,
    ObservationInline,
    ObserverInline,
    SampleUnitAdmin,
    TransectMethodAdmin,
    get_crs_with_attrib,
    get_sus_with_attrib,
)


class FishAttributeAdmin(AttributeAdmin):
    model_attrib = FishAttributeView
    attrib = "fish_attribute"
    protocols = [
        {
            "model_su": BeltFish,
            "model_obs": ObsBeltFish,
            "cr_obs": "obs_belt_fishes",
            "cr_sampleunit": "fishbelt",
            "su_obs": "beltfish_observations",
            "su_sampleunit": "fishbelttransectmethods",
        }
    ]

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        protected_descendants = set()

        if self.model == FishGenus or self.model == FishFamily:
            query = "genus_id"
            if self.model == FishFamily:
                query = "genus__family_id"

            species = FishSpecies.objects.filter(**{query: object_id})
            for s in species:
                for p in self.protocols:
                    cqry = "data__{}__contains".format(p.get("cr_obs"))
                    crs = get_crs_with_attrib(cqry, {self.attrib: str(s.pk)})
                    sqry = "{}__{}".format(p.get("su_obs"), self.attrib)
                    sus = get_sus_with_attrib(p.get("model_su"), sqry, s.pk)
                    if crs.count() > 0 or sus.count() > 0:
                        admin_url = reverse(
                            "admin:{}_fishspecies_change".format(FishSpecies._meta.app_label),
                            args=(s.pk,),
                        )
                        sstr = format_html('<a href="{}">{}</a>', admin_url, s)
                        protected_descendants.add(sstr)

            if protected_descendants:
                extra_context.update({"protected_descendants": protected_descendants})

        return super().delete_view(request, object_id, extra_context)


class BeltTransectWidthConditionInline(admin.StackedInline):
    model = BeltTransectWidthCondition
    extra = 0


@admin.register(BeltTransectWidth)
class BeltTransectWidthAdmin(BaseAdmin):
    list_display = ("name",)
    inlines = [BeltTransectWidthConditionInline]


@admin.register(FishSizeBin)
class FishSizeBinAdmin(BaseAdmin):
    list_display = ("val",)


@admin.register(FishSize)
class FishSizeAdmin(BaseAdmin):
    list_display = ("fish_bin_size", "name", "val")


@admin.register(FishBeltTransect)
class FishTransectAdmin(SampleUnitAdmin):
    list_display = ("name", "len_surveyed", "width", "depth")


@admin.register(FishGroupFunction)
class FishGroupFunctionAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(FishGroupTrophic)
class FishGroupTrophicAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(FishGroupSize)
class FishGroupSizeAdmin(BaseAdmin):
    list_display = ("name",)


class FishAttributeGroupingAdmin(FishAttributeAdmin):
    def region_list(self, obj):
        if not hasattr(obj, "regions"):
            return []
        region_ids = obj.regions.values_list("pk", flat=True)
        return ", ".join(
            [r.name for r in Region.objects.filter(pk__in=region_ids).order_by("name")]
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "biomass_constant_a",
                "biomass_constant_b",
                "biomass_constant_c",
                "region_list",
            )
        return ()


class FishAttributeInline(admin.StackedInline):
    model = FishGroupingRelationship
    fk_name = "grouping"
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "attribute" and hasattr(self, "cached_fish_attributes"):
            field.choices = self.cached_fish_attributes
        return field


@admin.register(FishGrouping)
class FishGroupingAdmin(FishAttributeGroupingAdmin):
    list_display = (
        "name",
        "biomass_constant_a",
        "biomass_constant_b",
        "biomass_constant_c",
        "region_list",
    )
    search_fields = ["name"]
    autocomplete_fields = ["created_by", "updated_by"]
    exportable_fields = (
        "name",
        "biomass_constant_a",
        "biomass_constant_b",
        "biomass_constant_c",
        "region_list",
    )
    inlines = (FishAttributeInline,)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("biomass_constant_a", "biomass_constant_b", "biomass_constant_c")
        return ()

    def get_formsets_with_inlines(self, request, obj=None):
        fish_attributes = FishAttributeView.objects.all().order_by("name")
        for inline in self.get_inline_instances(request, obj):
            inline.cached_fish_attributes = [(fa.pk, fa.name) for fa in fish_attributes]
            yield inline.get_formset(request, obj), inline


class FishGenusInline(admin.StackedInline):
    model = FishGenus
    fk_name = "family"
    extra = 1


@admin.register(FishFamily)
class FishFamilyAdmin(FishAttributeGroupingAdmin):
    list_display = (
        "name",
        "biomass_constant_a",
        "biomass_constant_b",
        "biomass_constant_c",
        "max_length",
    )
    inlines = (FishGenusInline,)
    search_fields = ["name"]


class FishSpeciesInline(admin.StackedInline):
    model = FishSpecies
    fk_name = "genus"
    extra = 1


@admin.register(FishGenus)
class FishGenusAdmin(FishAttributeGroupingAdmin):
    list_display = (
        "name",
        "fk_link",
        "biomass_constant_a",
        "biomass_constant_b",
        "biomass_constant_c",
        "max_length",
    )
    inlines = (FishSpeciesInline,)
    search_fields = ["name", "family__name"]
    exportable_fields = ("name", "family")

    def fk_link(self, obj):
        link = reverse("admin:api_fishfamily_change", args=[obj.family.pk])
        return format_html('<a href="{}">{}</a>', link, obj.family.name)

    fk_link.allow_tags = True
    fk_link.admin_order_field = "family"
    fk_link.short_description = _("Family")


@admin.register(FishSpecies)
class FishSpeciesAdmin(FishAttributeAdmin):
    list_display = (
        "name",
        "fk_link",
        "fish_family",
        "biomass_constant_a",
        "biomass_constant_b",
        "biomass_constant_c",
        "max_length",
        "trophic_level",
        "vulnerability",
        "region_list",
    )
    search_fields = ["name", "genus__name", "genus__family__name"]
    list_filter = (
        "status",
        "group_size",
        "trophic_group",
        "functional_group",
        "genus__family",
    )
    exportable_fields = (
        "name",
        "genus",
        "fish_family",
        "biomass_constant_a",
        "biomass_constant_b",
        "biomass_constant_c",
        "max_length",
        "trophic_level",
        "vulnerability",
        "region_list",
    )

    def fk_link(self, obj):
        link = reverse("admin:api_fishgenus_change", args=[obj.genus.pk])
        return format_html('<a href="{}">{}</a>', link, obj.genus.name)

    fk_link.allow_tags = True
    fk_link.admin_order_field = "genus"
    fk_link.short_description = _("Genus")

    def fish_family(self, obj):
        return obj.genus.family.name

    fish_family.admin_order_field = "genus__family__name"
    fish_family.short_description = "Family"

    def region_list(self, obj):
        return ", ".join([r.name for r in obj.regions.all()])


class ObsTransectBeltFishInline(ObservationInline):
    model = ObsBeltFish
    cache_fields = ["fish_attribute"]


@admin.register(BeltFish)
class BeltFishAdmin(TransectMethodAdmin):
    list_display = ("name", "len_surveyed", "width", "depth")
    inlines = (ObserverInline, ObsTransectBeltFishInline)

    def width(self, obj):
        return obj.transect.width

    width.admin_order_field = "transect__width"

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

    def render_change_form(self, request, context, *args, **kwargs):
        for formset in context["inline_admin_formsets"]:
            qs = formset.formset.queryset
            for model_obj in qs:
                model_obj._hide_fish_in_repr = True

        return super().render_change_form(request, context, *args, **kwargs)

    def get_formsets_with_inlines(self, request, obj=None):
        fish_attributes = FishAttributeView.objects.none()
        size_bins = FishSizeBin.objects.none()
        if obj is not None:
            fish_attributes = FishAttributeView.objects.only("pk", "name").order_by("name")
            size_bins = FishSizeBin.objects.order_by("val")

        for inline in self.get_inline_instances(request, obj):
            inline.cached_fish_attributes = [(fa.pk, fa.name) for fa in fish_attributes]
            inline.cached_size_bins = [(sb.pk, sb.val) for sb in size_bins]
            yield inline.get_formset(request, obj), inline
