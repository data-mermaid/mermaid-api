import csv
import datetime

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.gis.admin import OSMGeoAdmin
from django.db.models import Count
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html

from api.utils.sample_unit_methods import get_project
from tools.models import MERMAIDFeature, UserMERMAIDFeature
from ..models import Application, AuthUser, CollectRecord, Observer, Profile


def lookup_field_from_choices(field_obj, value):
    choices = getattr(field_obj, "choices")
    if choices is not None and len(choices) > 0:
        choices_dict = dict(choices)
        try:
            value = choices_dict[value]
        except KeyError:
            pass

    return value


def export_model_as_csv(modeladmin, request, queryset, field_list):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=%s-%s-export_%s.csv" % (
        __package__.lower(),
        queryset.model.__name__.lower(),
        datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    )

    writer = csv.writer(response)
    writer.writerow(
        [admin.utils.label_for_field(f, queryset.model, modeladmin) for f in field_list]
    )

    for obj in queryset:
        csv_line_values = []
        for field in field_list:
            field_obj, attr, value = admin.utils.lookup_field(field, obj, modeladmin)
            if field_obj is not None and hasattr(field_obj, "choices"):
                value = lookup_field_from_choices(field_obj, value)
            csv_line_values.append(str(value).strip())

        writer.writerow(csv_line_values)

    return response


def export_model_display_as_csv(modeladmin, request, queryset):
    if hasattr(modeladmin, "exportable_fields"):
        field_list = modeladmin.exportable_fields
    else:
        field_list = list(modeladmin.list_display[:])
        if "action_checkbox" in field_list:
            field_list.remove("action_checkbox")

    return export_model_as_csv(modeladmin, request, queryset, field_list)


def export_model_all_as_csv(modeladmin, request, queryset):
    field_list = [
        f.name
        for f in queryset.model._meta.get_fields()
        if f.concrete and (not f.is_relation or f.one_to_one or (f.many_to_one and f.related_model))
    ]
    if hasattr(modeladmin, "exportable_fields"):
        added_fields = [f for f in modeladmin.exportable_fields if f not in field_list]
        field_list = field_list + added_fields

    return export_model_as_csv(modeladmin, request, queryset, field_list)


export_model_display_as_csv.short_description = (
    "Export selected %(verbose_name_plural)s to CSV (display)"
)
export_model_all_as_csv.short_description = (
    "Export selected %(verbose_name_plural)s to CSV (all fields)"
)


class BaseAdmin(OSMGeoAdmin):
    actions = (export_model_display_as_csv, export_model_all_as_csv)


@admin.register(Application)
class ApplicationAdmin(BaseAdmin):
    pass


@admin.register(AuthUser)
class AuthUserAdmin(BaseAdmin):
    search_fields = [
        "user_id",
        "profile__first_name",
        "profile__last_name",
        "profile__email",
    ]


@admin.register(Profile)
class ProfileAdmin(BaseAdmin):
    list_display = ("first_name", "last_name", "linked_email", "project_count")
    search_fields = ["first_name", "last_name", "email"]

    @admin.display(description="Email", ordering="email")
    def linked_email(self, obj):
        return format_html(f'<a href="mailto:{obj.email}">{obj.email}</a>')

    @admin.display(description="Project membership count", ordering="projects__count")
    def project_count(self, obj):
        return obj.projects__count

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("projects"))
        return qs


class UserMERMAIDFeatureInline(admin.TabularInline):
    model = UserMERMAIDFeature
    extra = 0


@admin.register(MERMAIDFeature)
class MermaidFeatureAdmin(BaseAdmin):
    list_display = ("id", "label", "enabled")
    list_display_links = ("id", "label")
    inlines = [UserMERMAIDFeatureInline]


def get_crs_with_attrib(query, attrib_val):
    cr_filter = {query: [attrib_val]}
    return CollectRecord.objects.filter(**cr_filter)


def get_sus_with_attrib(model_su, query, attrib_id):
    su_filter = {query: attrib_id}
    return model_su.objects.filter(**su_filter).distinct()


class AttributeAdmin(BaseAdmin):
    # For any (protected) attribute assigned to mermaid observations, override
    # default "can't delete" admin behavior with form allowing user to
    # reassign existing observations using this attribute to use another attribute.
    # Requires these definitions on the inherited class:
    # model_attrib =
    # attrib = ''
    # protocols = [
    #     {'model_su': ,
    #      'model_obs': ,
    #      'cr_obs': '',
    #      'cr_sampleunit': '',
    #      'su_obs': '',
    #      'su_sampleunit': ''},
    # ]
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update({"objects_that_use_label": "sample units"})

        if not extra_context.get("protected_descendants"):
            # dropdown of other attributes to assign to existing observations before deleting
            other_objs = self.model_attrib.objects.exclude(id=object_id).order_by("name")
            if other_objs.count() > 0:
                extra_context.update({"other_objs": other_objs})

            protocol_crs = CollectRecord.objects.none()
            atleast_one_su = False
            collect_records = []
            sample_units = []
            for p in self.protocols:
                # Collect records that use this attribute, about to be deleted
                crs = get_crs_with_attrib(
                    "data__{}__contains".format(p.get("cr_obs")),
                    {self.attrib: object_id},
                )
                if crs.count() > 0:
                    if not protocol_crs:
                        protocol_crs = crs
                    else:
                        protocol_crs = protocol_crs.union(crs)

                    for cr in crs:
                        project_id = cr.project.id
                        admin_url = reverse(
                            "admin:{}_collectrecord_change".format(
                                p.get("model_su")._meta.app_label
                            ),
                            args=(cr.pk,),
                        )
                        crstr = format_html('<a href="{}">{}</a>', admin_url, cr)
                        if project_id is not None:
                            app_url = "{}/projects/{}/collecting/{}/{}".format(
                                settings.DEFAULT_DOMAIN_COLLECT,
                                project_id,
                                p.get("cr_sampleunit"),
                                cr.pk,
                            )
                            crstr = format_html(
                                '<a href="{}">{}</a> [<a href="{}" target="_blank">{}</a>]',
                                admin_url,
                                cr,
                                app_url,
                                app_url,
                            )
                        collect_records.append(crstr)

                # Sample units that use this attribute, about to be deleted
                sus = get_sus_with_attrib(
                    p.get("model_su"),
                    "{}__{}".format(p.get("su_obs"), self.attrib),
                    object_id,
                )
                if sus.count() > 0:
                    atleast_one_su = True
                    for su in sus:
                        project = get_project(su, su.project_lookup.split("__"))
                        admin_url = reverse(
                            "admin:{}_{}_change".format(
                                p.get("model_su")._meta.app_label,
                                p.get("model_su")._meta.model_name,
                            ),
                            args=(su.pk,),
                        )
                        app_url = "{}/projects/{}/submitted/{}/{}".format(
                            settings.DEFAULT_DOMAIN_COLLECT,
                            project.pk,
                            p.get("su_sampleunit"),
                            su.pk,
                        )
                        sustr = format_html(
                            '<a href="{}">{}</a> [<a href="{}" target="_blank">{}</a>]',
                            admin_url,
                            su,
                            app_url,
                            app_url,
                        )
                        sample_units.append(sustr)

            if collect_records:
                extra_context.update({"collect_records": collect_records})
            if sample_units:
                extra_context.update({"objects_that_use": sample_units})

            # process reassignment, then hand back to django for deletion
            if request.method == "POST":
                replacement_obj = request.POST.get("replacement_obj")
                if (replacement_obj is None or replacement_obj == "") and atleast_one_su:
                    self.message_user(
                        request,
                        "To delete, you must select a replacement object to assign to all items "
                        "using this object.",
                        level=messages.ERROR,
                    )
                    return super().delete_view(request, object_id, extra_context)

                for cr in protocol_crs:
                    for p in self.protocols:
                        observations = cr.data.get(p.get("cr_obs")) or []
                        for obs in observations:
                            if self.attrib in obs and obs[self.attrib] == object_id:
                                obs[self.attrib] = replacement_obj
                    cr.save()

                for p in self.protocols:
                    p.get("model_obs").objects.filter(**{self.attrib: object_id}).update(
                        **{self.attrib: replacement_obj}
                    )

        return super().delete_view(request, object_id, extra_context)


class SampleUnitAdmin(BaseAdmin):
    readonly_fields = ["created_by", "updated_by", "cr_id"]
    exclude = ("collect_record_id",)
    autocomplete_fields = ["sample_event"]
    search_fields = [
        "id",
        "sample_event__site__name",
        "sample_event__sample_date",
        "sample_event__site__project__name",
    ]
    ordering = ["sample_event__site__name"]

    def name(self, obj):
        return str(obj)

    name.admin_order_field = "sample_event"

    def cr_id(self, obj):
        return obj.collect_record_id

    cr_id.short_description = "CollectRecord ID"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("created_by", "updated_by", "sample_event", "sample_event__site")
        )


class CachedFKInline(admin.StackedInline):
    cache_fields = []

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by", "updated_by")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        for cache_field in self.cache_fields:
            cached_choices = f"cached_{cache_field}s"
            if db_field.name == cache_field and hasattr(self, cached_choices):
                field.choices = getattr(self, cached_choices)
                return field
        return field


class ObserverInline(CachedFKInline):
    model = Observer
    extra = 0
    readonly_fields = ["created_by", "updated_by"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by", "updated_by", "profile")


class ObservationInline(CachedFKInline):
    extra = 0
    exclude = ("include",)
    readonly_fields = ["created_by", "updated_by"]


class TransectMethodAdmin(BaseAdmin):
    autocomplete_fields = ("transect",)
    readonly_fields = ["created_by", "updated_by", "cr_id"]
    search_fields = [
        "transect__sample_event__site__name",
        "transect__sample_event__sample_date",
        "transect__sample_event__site__project__name",
    ]
    ordering = ["transect__sample_event__site__name"]

    def name(self, obj):
        return str(obj.transect)

    name.admin_order_field = "transect__sample_event__site__name"

    def cr_id(self, obj):
        return obj.transect.collect_record_id

    cr_id.short_description = "CollectRecord ID"

    def len_surveyed(self, obj):
        return obj.transect.len_surveyed

    def depth(self, obj):
        return obj.transect.depth

    len_surveyed.admin_order_field = "transect__len_surveyed"
