from collections import defaultdict

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ...models import (
    BenthicAttribute,
    BenthicAttributeGrowthFormLifeHistory,
    BenthicLifeHistory,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    GrowthForm,
    HabitatComplexity,
    HabitatComplexityScore,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    ObsBenthicPIT,
    ObsColoniesBleached,
    ObsHabitatComplexity,
    Region,
)
from ..base import (
    AttributeAdmin,
    BaseAdmin,
    CachedFKInline,
    ObservationInline,
    ObserverInline,
    SampleUnitAdmin,
    TransectMethodAdmin,
    get_crs_with_attrib,
    get_sus_with_attrib,
)


@admin.register(GrowthForm)
class GrowthFormAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(HabitatComplexityScore)
class HabitatComplexityScoreAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(BenthicTransect)
class BenthicTransectAdmin(SampleUnitAdmin):
    list_display = ("name", "len_surveyed", "depth")


@admin.register(BenthicLifeHistory)
class BenthicLifeHistoryAdmin(BaseAdmin):
    list_display = ("name",)


class BenthicAttributeInline(admin.StackedInline):
    model = BenthicAttribute
    extra = 0
    autocomplete_fields = ("parent",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("parent")
            .prefetch_related("regions", "life_histories")
        )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == "regions" and hasattr(self, "cached_regions"):
            field.choices = self.cached_regions
        elif db_field.name == "life_histories" and hasattr(self, "cached_life_histories"):
            field.choices = self.cached_life_histories
        return field


class BenthicAttributeGrowthFormLifeHistoryInline(CachedFKInline):
    model = BenthicAttributeGrowthFormLifeHistory
    extra = 0
    cache_fields = ["growth_form", "life_history"]
    autocomplete_fields = ("attribute",)

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("attribute", "growth_form", "life_history")
        )


@admin.register(BenthicAttribute)
class BenthicAttributeAdmin(AttributeAdmin):
    model_attrib = BenthicAttribute
    attrib = "attribute"
    protocols = [
        {
            "model_su": BenthicPIT,
            "model_obs": ObsBenthicPIT,
            "cr_obs": "obs_benthic_pits",
            "cr_sampleunit": "benthicpit",
            "su_obs": "obsbenthicpit_set",
            "su_sampleunit": "benthicpit",
        },
        {
            "model_su": BenthicLIT,
            "model_obs": ObsBenthicLIT,
            "cr_obs": "obs_benthic_lits",
            "cr_sampleunit": "benthiclit",
            "su_obs": "obsbenthiclit_set",
            "su_sampleunit": "benthiclit",
        },
        {
            "model_su": BleachingQuadratCollection,
            "model_obs": ObsColoniesBleached,
            "cr_obs": "obs_colonies_bleached",
            "cr_sampleunit": "bleachingqc",
            "su_obs": "obscoloniesbleached",
            "su_sampleunit": "bleachingqc",
        },
        {
            "model_su": BenthicPhotoQuadratTransect,
            "model_obs": ObsBenthicPhotoQuadrat,
            "cr_obs": "obs_benthic_photo_quadrats",
            "cr_sampleunit": "benthicpqt",
            "su_obs": "obsbenthicphotoquadrat",
            "su_sampleunit": "benthicpqt",
        },
    ]

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        protected_descendants = set()
        obj = self.get_object(request, object_id)
        for d in obj.descendants:
            for p in self.protocols:
                cqry = "data__{}__contains".format(p.get("cr_obs"))
                crs = get_crs_with_attrib(cqry, {self.attrib: str(d.pk)})
                sqry = "{}__{}".format(p.get("su_obs"), self.attrib)
                sus = get_sus_with_attrib(p.get("model_su"), sqry, d.pk)
                if crs.count() > 0 or sus.count() > 0:
                    admin_url = reverse(
                        "admin:{}_benthicattribute_change".format(
                            self.model_attrib._meta.app_label
                        ),
                        args=(d.pk,),
                    )
                    sstr = format_html('<a href="{}">{}</a>', admin_url, d)
                    protected_descendants.add(sstr)

        if protected_descendants:
            extra_context.update({"protected_descendants": protected_descendants})

        return super().delete_view(request, object_id, extra_context)

    list_display = ("name", "fk_link", "life_history_list", "region_list")
    exportable_fields = ("name", "parent", "life_history_list", "region_list")
    inlines = [BenthicAttributeGrowthFormLifeHistoryInline, BenthicAttributeInline]
    search_fields = ["name"]
    list_filter = ("status",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("parent")
            .prefetch_related("regions", "life_histories")
        )

    def get_formsets_with_inlines(self, request, obj=None):
        regions = list(Region.objects.values_list("pk", "name"))
        life_histories = list(BenthicLifeHistory.objects.values_list("pk", "name"))
        growth_forms = list(GrowthForm.objects.values_list("pk", "name"))

        for inline in self.get_inline_instances(request, obj):
            if isinstance(inline, BenthicAttributeInline):
                inline.cached_regions = regions
                inline.cached_life_histories = life_histories
            elif isinstance(inline, BenthicAttributeGrowthFormLifeHistoryInline):
                inline.cached_growth_forms = growth_forms
                # CachedFKInline uses f"cached_{field}s" so life_history → cached_life_historys
                inline.cached_life_historys = life_histories
            yield inline.get_formset(request, obj), inline

    def fk_link(self, obj):
        if obj.parent:
            link = reverse("admin:api_benthicattribute_change", args=[obj.parent.pk])
            return format_html('<a href="{}">{}</a>', link, obj.parent.name)
        else:
            return ""

    fk_link.allow_tags = True
    fk_link.admin_order_field = "parent"
    fk_link.short_description = _("Parent")

    def region_list(self, obj):
        return ",".join([r.name for r in obj.regions.all()])

    def life_history_list(self, obj):
        return ",".join([lh.name for lh in obj.life_histories.all()])

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("child_regions", "child_life_histories")
        return ()

    def _child_proportions(self, obj, m2mfield):
        counts = defaultdict(int)
        total = 0
        descendant_ids = [d.pk for d in obj.descendants]
        children = BenthicAttribute.objects.filter(pk__in=descendant_ids).prefetch_related(m2mfield)
        for ba in children:
            for m2m in getattr(ba, m2mfield).all():
                counts[m2m.name] += 1
                total += 1

        proportions = {
            name: round(count / float(total), 3) if total else 0 for name, count in counts.items()
        }

        return proportions

    def child_life_histories(self, obj):
        return self._child_proportions(obj, "life_histories")

    def child_regions(self, obj):
        return self._child_proportions(obj, "regions")


class ObsBenthicLITInline(ObservationInline):
    model = ObsBenthicLIT
    cache_fields = ["attribute", "growth_form"]


@admin.register(BenthicLIT)
class BenthicLITAdmin(TransectMethodAdmin):
    list_display = ("name", "len_surveyed", "depth")
    inlines = (ObserverInline, ObsBenthicLITInline)

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


class ObsBenthicPITInline(ObservationInline):
    model = ObsBenthicPIT
    cache_fields = ["attribute", "growth_form"]


@admin.register(BenthicPIT)
class BenthicPITAdmin(TransectMethodAdmin):
    list_display = ("name", "len_surveyed", "interval_size", "depth")
    inlines = (ObserverInline, ObsBenthicPITInline)

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


class ObsHabitatComplexityInline(ObservationInline):
    model = ObsHabitatComplexity
    cache_fields = ["score"]


@admin.register(HabitatComplexity)
class HabitatComplexityAdmin(TransectMethodAdmin):
    list_display = ("name", "len_surveyed", "interval_size", "interval_start", "depth")
    inlines = (ObserverInline, ObsHabitatComplexityInline)

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
            )
        )

    def get_formsets_with_inlines(self, request, obj=None):
        scores = HabitatComplexityScore.objects.none()
        if obj is not None:
            scores = HabitatComplexityScore.objects.all()

        for inline in self.get_inline_instances(request, obj):
            inline.cached_scores = [(s.pk, str(s)) for s in scores]
            yield inline.get_formset(request, obj), inline


class ObsBenthicPhotoQuadratInline(ObservationInline):
    model = ObsBenthicPhotoQuadrat
    cache_fields = ["attribute", "growth_form"]


@admin.register(BenthicPhotoQuadratTransect)
class BenthicPhotoQuadratTransectAdmin(BaseAdmin):
    list_display = ("name", "quadrat_size", "depth")
    inlines = (
        ObserverInline,
        ObsBenthicPhotoQuadratInline,
    )
    readonly_fields = ["created_by", "updated_by", "cr_id"]
    search_fields = [
        "quadrat_transect__sample_event__site__name",
        "quadrat_transect__sample_event__sample_date",
        "quadrat_transect__sample_event__site__project__name",
    ]
    ordering = ["quadrat_transect__sample_event__site__name"]

    def name(self, obj):
        return str(obj.quadrat_transect)

    name.admin_order_field = "quadrat_transect__sample_event__site__name"

    def quadrat_size(self, obj):
        return obj.quadrat_transect.quadrat_size

    quadrat_size.admin_order_field = "quadrat_transect__quadrat_size"

    def depth(self, obj):
        return obj.quadrat_transect.depth

    depth.admin_order_field = "quadrat_transect__depth"

    def cr_id(self, obj):
        return obj.quadrat_transect.collect_record_id

    cr_id.short_description = "CollectRecord ID"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "created_by",
                "updated_by",
                "quadrat_transect",
                "quadrat_transect__sample_event",
                "quadrat_transect__sample_event__site",
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
