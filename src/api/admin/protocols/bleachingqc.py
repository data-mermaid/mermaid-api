from django.contrib import admin

from ...models import (
    BenthicAttribute,
    BleachingQuadratCollection,
    GrowthForm,
    ObsColoniesBleached,
    ObsQuadratBenthicPercent,
    QuadratCollection,
)
from ..base import BaseAdmin, ObservationInline, ObserverInline, SampleUnitAdmin


class ObsColoniesBleachedInline(ObservationInline):
    model = ObsColoniesBleached
    cache_fields = ["attribute", "growth_form"]


class ObsQuadratBenthicPercentInline(ObservationInline):
    model = ObsQuadratBenthicPercent


@admin.register(QuadratCollection)
class QuadratCollectionAdmin(SampleUnitAdmin):
    list_display = ("name", "quadrat_size", "depth")


@admin.register(BleachingQuadratCollection)
class BleachingQuadratCollectionAdmin(BaseAdmin):
    list_display = ("name", "quadrat_size", "depth")
    inlines = (
        ObserverInline,
        ObsColoniesBleachedInline,
        ObsQuadratBenthicPercentInline,
    )
    autocomplete_fields = ("quadrat",)
    readonly_fields = ["created_by", "updated_by", "cr_id"]
    search_fields = [
        "quadrat__sample_event__site__name",
        "quadrat__sample_event__sample_date",
        "quadrat__sample_event__site__project__name",
    ]
    ordering = ["quadrat__sample_event__site__name"]

    def name(self, obj):
        return str(obj.quadrat)

    name.admin_order_field = "quadrat__sample_event__site__name"

    def quadrat_size(self, obj):
        return obj.quadrat.quadrat_size

    quadrat_size.admin_order_field = "quadrat__quadrat_size"

    def depth(self, obj):
        return obj.quadrat.depth

    def cr_id(self, obj):
        return obj.quadrat.collect_record_id

    cr_id.short_description = "CollectRecord ID"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "created_by",
                "updated_by",
                "quadrat",
                "quadrat__sample_event",
                "quadrat__sample_event__site",
            )
        )

    def get_formsets_with_inlines(self, request, obj=None):
        attributes = BenthicAttribute.objects.none()
        growth_forms = GrowthForm.objects.none()
        if obj is not None:
            attributes = BenthicAttribute.objects.only("pk", "name").order_by("name")
            growth_forms = GrowthForm.objects.all()

        for inline in self.get_inline_instances(request, obj):
            inline.cached_attributes = [(a.pk, a.name) for a in attributes]
            inline.cached_growth_forms = [(gf.pk, gf.name) for gf in growth_forms]
            yield inline.get_formset(request, obj), inline
