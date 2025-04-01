from collections import defaultdict

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.db.models import Q
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ..models import (
    PROTOCOL_MAP,
    ArchivedRecord,
    AuditRecord,
    BeltFish,
    BeltTransectWidth,
    BeltTransectWidthCondition,
    BenthicAttribute,
    BenthicAttributeGrowthFormLifeHistory,
    BenthicLifeHistory,
    BenthicLIT,
    BenthicPhotoQuadratTransect,
    BenthicPIT,
    BenthicTransect,
    BleachingQuadratCollection,
    CollectRecord,
    Country,
    Covariate,
    Current,
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
    GrowthForm,
    HabitatComplexity,
    HabitatComplexityScore,
    Management,
    ManagementCompliance,
    ManagementParty,
    Notification,
    ObsBeltFish,
    ObsBenthicLIT,
    ObsBenthicPhotoQuadrat,
    ObsBenthicPIT,
    ObsColoniesBleached,
    Observer,
    ObsHabitatComplexity,
    ObsQuadratBenthicPercent,
    Profile,
    Project,
    ProjectProfile,
    QuadratCollection,
    ReefExposure,
    ReefSlope,
    ReefType,
    ReefZone,
    Region,
    RelativeDepth,
    SampleEvent,
    SampleUnit,
    Site,
    Tag,
    Tide,
    Visibility,
)
from ..utils import get_subclasses
from ..utils.notification import add_notification
from .base import (
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

    # before using AttributeAdmin reassignment logic, check to see if any descendants are used by observations
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        protected_descendants = set()

        if self.model == FishGenus or self.model == FishFamily:
            query = "genus_id"
            if self.model == FishFamily:
                query = "genus__family_id"

            species = FishSpecies.objects.filter(**{query: object_id})
            for s in species:
                cqry = "data__{}__contains".format(self.protocols[0].get("cr_obs"))
                crs = get_crs_with_attrib(cqry, {self.attrib: str(s.pk)})
                sqry = "{}__{}".format(self.protocols[0].get("su_obs"), self.attrib)
                sus = get_sus_with_attrib(self.protocols[0].get("model_su"), sqry, s.pk)
                if crs.count() > 0 or sus.count() > 0:
                    admin_url = reverse(
                        "admin:{}_fishspecies_change".format(FishSpecies._meta.app_label),
                        args=(s.pk,),
                    )
                    sstr = format_html('<a href="{}">{}</a>', admin_url, s)
                    protected_descendants.add(sstr)

            extra_context.update({"protected_descendants": protected_descendants})

        return super().delete_view(request, object_id, extra_context)


class SiteInline(CachedFKInline):
    model = Site
    extra = 0
    readonly_fields = ["created_by", "updated_by"]
    cache_fields = ["country", "reef_type", "reef_zone", "exposure", "predecessor"]


@admin.register(Project)
class ProjectAdmin(BaseAdmin):
    list_display = ("name", "status", "admin_list", "country_list", "tag_list")
    readonly_fields = ["created_by", "updated_by"]
    exportable_fields = (
        "name",
        "status",
        "admin_list",
        "country_list",
        "tag_list",
        "data_policy_beltfish",
        "data_policy_benthiclit",
        "data_policy_benthicpit",
        "data_policy_habitatcomplexity",
        "data_policy_bleachingqc",
        "data_policy_benthicpqt",
        "notes",
    )
    inlines = [SiteInline]
    search_fields = [
        "name",
        "pk",
        "profiles__profile__email",
        "profiles__profile__id",
        "profiles__profile__first_name",
        "profiles__profile__last_name",
    ]
    list_filter = ("status", "tags")
    _admins = None
    _sites = None

    def _get_admins(self):
        if self._admins:
            return self._admins
        self._admins = ProjectProfile.objects.filter(role=ProjectProfile.ADMIN).select_related()
        return self._admins

    def admin_list(self, obj):
        pps = self._get_admins()
        return ", ".join(
            [
                "{} <{}>".format(p.profile.full_name, p.profile.email)
                for p in pps
                if p.project == obj
            ]
        )

    def _get_sites(self):
        if self._sites:
            return self._sites
        self._sites = Site.objects.select_related()
        return self._sites

    def country_list(self, obj):
        all_sites = self._get_sites()
        sites = [s for s in all_sites if s.project == obj]
        countries = []
        for s in sites:
            if s.country not in countries:
                countries.append(s.country)
        return ", ".join([c.name for c in countries])

    def tag_list(self, obj):
        # TODO: cache this
        return ", ".join("{}".format(t.name) for t in obj.tags.all())

    tag_list.short_description = _("organizations")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by", "updated_by")

    def delete_view(self, request, object_id, extra_context=None):
        # Delete any (protected) related SampleEvents before deleting project.
        # If any other protected FKs get added to project, this will need to be updated.
        if request.method == "POST":
            ses = SampleEvent.objects.filter(site__project=object_id)
            for se in ses:
                for suclass in get_subclasses(SampleUnit):
                    suclass.objects.filter(sample_event=se).delete()
                # Actual SE gets deleted via SU signal
        return super(ProjectAdmin, self).delete_view(request, object_id, extra_context)

    def get_formsets_with_inlines(self, request, obj=None):
        countries = Country.objects.none()
        reef_types = ReefType.objects.none()
        reef_zones = ReefZone.objects.none()
        exposures = ReefExposure.objects.none()
        sites = Site.objects.none()
        if obj is not None:
            countries = Country.objects.all()
            reef_types = ReefType.objects.all()
            reef_zones = ReefZone.objects.all()
            exposures = ReefExposure.objects.all()
            sites = Site.objects.all()

        for inline in self.get_inline_instances(request, obj):
            inline.cached_countrys = [(c.pk, c.name) for c in countries]
            inline.cached_reef_types = [(rt.pk, rt.name) for rt in reef_types]
            inline.cached_reef_zones = [(rz.pk, rz.name) for rz in reef_zones]
            inline.cached_exposures = [(e.pk, e.name) for e in exposures]
            inline.cached_predecessors = [(s.pk, s.name) for s in sites]
            yield inline.get_formset(request, obj), inline


@admin.register(ProjectProfile)
class ProjectProfileAdmin(BaseAdmin):
    list_display = ("project", "profile", "role")
    search_fields = [
        "id",
        "project__name",
        "profile__first_name",
        "profile__last_name",
        "profile__email",
        "project__id",
        "profile__id",
    ]
    list_filter = ("role",)


@admin.register(Region)
class RegionAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(Site)
class SiteAdmin(BaseAdmin):
    list_display = ("country", "name", "reef_type", "reef_zone", "exposure")
    list_display_links = ("name",)
    search_fields = ["country__name", "name"]
    list_filter = ("reef_type", "reef_zone", "exposure")


class BeltTransectWidthConditionInline(admin.StackedInline):
    model = BeltTransectWidthCondition
    extra = 0


@admin.register(BeltTransectWidth)
class BeltTransectWidthAdmin(BaseAdmin):
    list_display = ("name",)
    inlines = [BeltTransectWidthConditionInline]


@admin.register(Country)
class CountryAdmin(BaseAdmin):
    list_display = ("iso", "name")


@admin.register(Current)
class CurrentAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(FishSizeBin)
class FishSizeBinAdmin(BaseAdmin):
    list_display = ("val",)


@admin.register(FishSize)
class FishSizeAdmin(BaseAdmin):
    list_display = ("fish_bin_size", "name", "val")


@admin.register(GrowthForm)
class GrowthFormAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(HabitatComplexityScore)
class HabitatComplexityScoreAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(ReefExposure)
class ReefExposureAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(ReefSlope)
class ReefSlopeAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(ReefType)
class ReefTypeAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(ReefZone)
class ReefZoneAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(RelativeDepth)
class RelativeDepthAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(Tide)
class TideAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(Visibility)
class VisibilityAdmin(BaseAdmin):
    list_display = ("val", "name")


@admin.register(Management)
class ManagementAdmin(BaseAdmin):
    list_display = (
        "name",
        "name_secondary",
        "project",
        "est_year",
        "open_access",
        "periodic_closure",
        "size_limits",
        "gear_restriction",
        "species_restriction",
        "access_restriction",
        "no_take",
    )
    readonly_fields = ("area",)
    search_fields = ["name", "name_secondary", "project__name", "est_year"]

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({"objects_that_use_label": "sample events"})

        obj = self.get_object(request, unquote(object_id))
        other_objs = Management.objects.filter(~Q(pk=obj.pk), project=obj.project)
        if other_objs.count() > 0:
            extra_context.update({"other_objs": other_objs})

        atleast_one_se = False
        collect_records = []
        sample_events = []

        # Collect records that use this attribute, about to be deleted
        crs = CollectRecord.objects.filter(data__sample_event__management=obj.pk)
        if crs.count() > 0:
            for cr in crs:
                project_id = cr.project.id
                admin_url = reverse(
                    "admin:{}_collectrecord_change".format(SampleEvent._meta.app_label),
                    args=(cr.pk,),
                )
                crstr = format_html('<a href="{}">{}</a>', admin_url, cr)
                if project_id is not None:
                    crstr = format_html('<a href="{}">{}</a>', admin_url, cr)
                collect_records.append(crstr)

        # Sample events that use this MR, about to be deleted
        ses = SampleEvent.objects.filter(management=obj).distinct()
        if ses.count() > 0:
            atleast_one_se = True
            for se in ses:
                project_id = se.site.project.pk
                admin_url = reverse(
                    "admin:{}_{}_change".format(
                        SampleEvent._meta.app_label, SampleEvent._meta.model_name
                    ),
                    args=(se.pk,),
                )
                sestr = format_html('<a href="{}">{}</a>', admin_url, se)
                sample_events.append(sestr)

        if collect_records:
            extra_context.update({"collect_records": collect_records})
        if sample_events:
            extra_context.update({"objects_that_use": sample_events})

        # process reassignment, then hand back to django for deletion
        if request.method == "POST":
            replacement_obj = request.POST.get("replacement_obj")
            if (replacement_obj is None or replacement_obj == "") and atleast_one_se:
                self.message_user(
                    request,
                    "To delete, you must select a replacement object to assign to all items "
                    "using this object.",
                    level=messages.ERROR,
                )
                return super().delete_view(request, object_id, extra_context)

            for cr in crs:
                if "sample_event" in cr.data and "management" in cr.data["sample_event"]:
                    cr.data["sample_event"]["management"] = replacement_obj
                cr.save()

            ses.update(management=replacement_obj)

        return super().delete_view(request, object_id, extra_context)


@admin.register(ManagementCompliance)
class ManagementComplianceAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(ManagementParty)
class ManagementPartyAdmin(BaseAdmin):
    list_display = ("name",)


@admin.register(BenthicTransect)
class BenthicTransectAdmin(SampleUnitAdmin):
    list_display = ("name", "len_surveyed", "depth")


@admin.register(FishBeltTransect)
class FishTransectAdmin(SampleUnitAdmin):
    list_display = ("name", "len_surveyed", "width", "depth")


@admin.register(QuadratCollection)
class QuadratCollectionAdmin(SampleUnitAdmin):
    list_display = ("name", "quadrat_size", "depth")


@admin.register(SampleEvent)
class SampleEventAdmin(BaseAdmin):
    list_display = ("site", "management", "sample_date")
    list_display_links = ("site", "sample_date")
    search_fields = ["site__name", "sample_date"]


@admin.register(BenthicLifeHistory)
class BenthicLifeHistoryAdmin(BaseAdmin):
    list_display = ("name",)


class BenthicAttributeInline(admin.StackedInline):
    model = BenthicAttribute
    extra = 0


class BenthicAttributeGrowthFormLifeHistoryInline(admin.StackedInline):
    model = BenthicAttributeGrowthFormLifeHistory
    extra = 0


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

    # before using AttributeAdmin reassignment logic, check to see if any descendants are used by observations
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        protected_descendants = set()
        obj = self.get_object(request, object_id)
        if obj.descendants:
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

            extra_context.update({"protected_descendants": protected_descendants})

        return super().delete_view(request, object_id, extra_context)

    list_display = ("name", "fk_link", "life_history_list", "region_list")
    exportable_fields = ("name", "parent", "life_history_list", "region_list")
    inlines = [BenthicAttributeGrowthFormLifeHistoryInline, BenthicAttributeInline]
    search_fields = ["name"]
    list_filter = ("status",)

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
        if obj:  # editing an existing object
            return ("child_regions", "child_life_histories")
        return ()

    def _child_proportions(self, obj, m2mfield):
        counts = defaultdict(int)
        total = 0
        m2m_sets = [getattr(ba, m2mfield).all() for ba in obj.descendants]

        for m2ms in m2m_sets:
            for m2m in m2ms:
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
    list_display = ("name", "len_surveyed", "interval_size", "depth")
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


class ObsColoniesBleachedInline(ObservationInline):
    model = ObsColoniesBleached
    cache_fields = ["attribute", "growth_form"]


class ObsQuadratBenthicPercentInline(ObservationInline):
    model = ObsQuadratBenthicPercent


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

    def depth(self, obj):
        return obj.quadrat.depth

    quadrat_size.admin_order_field = "quadrat__quadrat_size"

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
        if obj:  # editing an existing object
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
        if obj:  # editing an existing object
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

    fish_family.admin_order_field = "genus.family.name"
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


@admin.register(Observer)
class ObserverAdmin(BaseAdmin):
    list_display = ("profile", "transectmethod")
    search_fields = [
        "id",
        "profile__first_name",
        "profile__last_name",
        "profile__email",
    ]


class ProtocolFilter(admin.SimpleListFilter):
    title = _("protocol")
    parameter_name = "protocol"

    def lookups(self, request, model_admin):
        return [(key, val) for key, val in PROTOCOL_MAP.items()]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(data__protocol=self.value())


@admin.register(CollectRecord)
class CollectRecordAdmin(BaseAdmin):
    list_display = ("id", "protocol", "profile", "created_by")
    search_fields = [
        "id",
        "project__id",
        "project__name",
        "profile__first_name",
        "profile__last_name",
        "profile__email",
    ]
    list_filter = [ProtocolFilter]

    def protocol(self, obj):
        data = obj.data or dict()
        return data.get("protocol")


@admin.register(ArchivedRecord)
class ArchivedRecordAdmin(BaseAdmin):
    list_display = ("app_label", "model", "record_pk", "project_pk")
    list_filter = ("model", "project_pk")


@admin.register(Tag)
class TagAdmin(BaseAdmin):
    list_display = ("name", "status", "updated_by")
    list_filter = ("status",)
    readonly_fields = ["created_on", "updated_on"]
    search_fields = ["name"]

    def delete_view(self, request, object_id, extra_context=None):
        obj = Tag.objects.get(pk=object_id)
        extra_context = extra_context or {}

        # dropdown of other tags to assign to existing projects before deleting
        other_objs = Tag.objects.exclude(id=object_id).order_by("name")
        if other_objs.count() > 0:
            extra_context.update({"other_objs": other_objs})

        # Projects that use this tag
        projects = []
        ps = Project.objects.filter(tags=obj)
        for p in ps:
            admin_url = reverse(
                "admin:{}_{}_change".format(Project._meta.app_label, Project._meta.model_name),
                args=(p.pk,),
            )
            app_url = "{}/projects/{}/project-info".format(settings.DEFAULT_DOMAIN_COLLECT, p.pk)
            pstr = format_html(
                '<a href="{}">{}</a> [<a href="{}" target="_blank">{}</a>]',
                admin_url,
                p,
                app_url,
                app_url,
            )
            projects.append(pstr)

        if projects:
            extra_context.update({"projects": projects})

        # process reassignment, then hand back to django for deletion
        if request.method == "POST":
            replacement_obj = request.POST.get("replacement_obj")
            if replacement_obj is not None:
                for p in ps:
                    p.tags.remove(obj)
                    p.tags.add(replacement_obj)

        return super(TagAdmin, self).delete_view(request, object_id, extra_context)


@admin.register(Covariate)
class CovariateAdmin(BaseAdmin):
    pass


@admin.register(AuditRecord)
class AuditRecordAdmin(BaseAdmin):
    list_display = ("event_on", "event_type", "model", "record_id")


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

    depth.admin_order_field = "quadrat_transect__sample_event__depth"

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


@admin.register(Notification)
class NotificationAdmin(BaseAdmin):
    list_display = ("owner", "status", "title", "created_on")
    search_fields = ["owner__first_name", "owner__last_name", "owner__pk", "title", "status"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "bulk_notification/",
                self.admin_site.admin_view(self.bulk_notification_view),
                name="bulk_notification",
            )
        ]
        return custom_urls + urls

    def bulk_notification_view(self, request):
        template = "admin/api/notification/bulk_create_notification.html"
        opts = self.model._meta
        statuses = [s[0] for s in Notification.STATUSES]
        all_projects = Project.objects.order_by("name")
        projects = [{"id": p.id, "name": p.name} for p in all_projects]
        context = dict(
            self.admin_site.each_context(request),
            opts=opts,
            statuses=statuses,
            projects=projects,
        )

        if request.method == "POST":
            data = request.POST
            title = data.get("title") or ""
            status = data.get("status") or ""
            description = data.get("description") or ""
            project_id = data.get("project") or ""
            if title == "" or status == "" or description == "":
                messages.error(request, "Missing required input(s)")
                return TemplateResponse(request, template, context)

            notify_template = "notifications/adhoc.txt"
            form_context = {"adhoctext": description}

            profiles = Profile.objects.all()
            if project_id != "":
                project_profiles = ProjectProfile.objects.filter(
                    project_id=project_id
                ).select_related("profile")
                profiles = [p.profile for p in project_profiles]

            add_notification(title, status, notify_template, form_context, profiles)
            messages.success(request, "Notifications created")

        return TemplateResponse(request, template, context)
