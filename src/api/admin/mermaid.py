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
    CollectRecord,
    Country,
    Covariate,
    Current,
    Management,
    ManagementCompliance,
    ManagementParty,
    Notification,
    Observer,
    Profile,
    Project,
    ProjectProfile,
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
from .base import BaseAdmin, CachedFKInline


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
        "data_policy_macroinvertebrate",
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
        return ", ".join("{}".format(t.name) for t in obj.tags.all())

    tag_list.short_description = _("organizations")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by", "updated_by")

    def delete_view(self, request, object_id, extra_context=None):
        if request.method == "POST":
            ses = SampleEvent.objects.filter(site__project=object_id)
            for se in ses:
                for suclass in get_subclasses(SampleUnit):
                    suclass.objects.filter(sample_event=se).delete()
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


@admin.register(Country)
class CountryAdmin(BaseAdmin):
    list_display = ("iso", "name")


@admin.register(Current)
class CurrentAdmin(BaseAdmin):
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

        crs = CollectRecord.objects.filter(data__sample_event__management=obj.pk)
        if crs.count() > 0:
            for cr in crs:
                admin_url = reverse(
                    "admin:{}_collectrecord_change".format(SampleEvent._meta.app_label),
                    args=(cr.pk,),
                )
                crstr = format_html('<a href="{}">{}</a>', admin_url, cr)
                collect_records.append(crstr)

        ses = SampleEvent.objects.filter(management=obj).distinct()
        if ses.count() > 0:
            atleast_one_se = True
            for se in ses:
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


@admin.register(SampleEvent)
class SampleEventAdmin(BaseAdmin):
    list_display = ("site", "management", "sample_date")
    list_display_links = ("site", "sample_date")
    search_fields = ["site__name", "sample_date"]


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

        other_objs = Tag.objects.exclude(id=object_id).order_by("name")
        if other_objs.count() > 0:
            extra_context.update({"other_objs": other_objs})

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
