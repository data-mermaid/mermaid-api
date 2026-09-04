import csv
import datetime
import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.gis.admin import GISModelAdmin
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html

from api.utils.apikeys import (
    DEFAULT_LIFETIME_DAYS,
    default_expires_at,
    generate_api_key,
    log_key_created,
)
from api.utils.sample_unit_methods import get_project
from tools.models import MERMAIDFeature, UserMERMAIDFeature
from ..models import APIKey, Application, AuthUser, CollectRecord, Observer, Profile
from ..models.classification import Annotation

logger = logging.getLogger(__name__)


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
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    response["Content-Disposition"] = (
        f"attachment; filename={__package__.lower()}-{queryset.model.__name__.lower()}"
        f"-export_{timestamp}.csv"
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


class BaseAdmin(GISModelAdmin):
    actions = (export_model_display_as_csv, export_model_all_as_csv)


@admin.register(Application)
class ApplicationAdmin(BaseAdmin):
    pass


class APIKeyExpiryFilter(admin.SimpleListFilter):
    """Answers the question this list exists to answer: which keys never expire.

    A no-expiry key is a legitimate choice, but it is also the one that gets
    forgotten, so it is one click away rather than a column to scan.
    """

    title = "expiry"
    parameter_name = "expiry"

    def lookups(self, request, model_admin):
        return (("never", "Never expires"), ("set", "Has an expiry date"))

    def queryset(self, request, queryset):
        value = self.value()
        if value == "never":
            return queryset.filter(expires_at__isnull=True)
        if value == "set":
            return queryset.filter(expires_at__isnull=False)
        return queryset


class APIKeyAdminForm(forms.ModelForm):
    never_expires = forms.BooleanField(
        required=False,
        label="Never expires",
        help_text=(
            "Leave this unchecked and the expiry blank to get the default of "
            f"{DEFAULT_LIFETIME_DAYS} days from now. Ticking it issues a credential "
            "that stays valid until somebody revokes it."
        ),
    )

    class Meta:
        model = APIKey
        # secret_hash is absent on purpose: nothing a human does here needs it,
        # and a field that is never rendered cannot be copied out of a screenshot.
        fields = ("profile", "name", "expires_at", "never_expires", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None and self.instance.expires_at is None:
            self.fields["never_expires"].initial = True

    def clean(self):
        cleaned_data = super().clean()
        expires_at = cleaned_data.get("expires_at")
        never_expires = cleaned_data.get("never_expires")

        if never_expires and expires_at is not None:
            raise forms.ValidationError("Set an expiry date or tick 'never expires', not both.")
        if not never_expires and expires_at is None:
            # No expiry is never the silent default. cleaned_data is what
            # construct_instance() writes onto the instance, so setting it
            # here is what lands on the row.
            cleaned_data["expires_at"] = default_expires_at()

        return cleaned_data


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Phase 1 issues API keys here, so this page is the whole management UI.

    A plain ModelAdmin, not BaseAdmin: BaseAdmin attaches
    export_model_all_as_csv, which walks every concrete field and would write
    secret_hash to a CSV. Only the display export is offered, and nothing in
    list_display is a secret.
    """

    form = APIKeyAdminForm
    list_display = ("name", "key_id", "profile", "is_active", "expires_at", "last_used_at")
    list_display_links = ("name", "key_id")
    list_filter = (APIKeyExpiryFilter, "is_active", ("revoked_at", admin.EmptyFieldListFilter))
    search_fields = (
        "name",
        "key_id",
        "profile__email",
        "profile__first_name",
        "profile__last_name",
    )
    autocomplete_fields = ("profile",)
    exclude = ("secret_hash",)
    readonly_fields = (
        "key_id",
        "last_used_at",
        "last_used_ip",
        "revoked_at",
        "revoked_reason",
        "created_by",
        "created_on",
        "updated_by",
        "updated_on",
    )
    exportable_fields = list_display
    actions = ("revoke_keys", "generate_replacement_keys", export_model_display_as_csv)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            # The key is its profile's access, so repointing an existing key at
            # another profile silently changes what a deployed credential can
            # do. Issue a new key instead.
            readonly_fields.append("profile")
        return readonly_fields

    def has_add_permission(self, request):
        # Minting a credential for any profile is a superuser action (C5).
        return request.user.is_superuser and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Revoking retires a key and keeps the row, which is what answers
        # "what did this credential do, and when did it stop working". Delete
        # throws that away, so it stays with the superuser.
        return request.user.is_superuser and super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("generate_replacement_keys", None)
        return actions

    @admin.action(description="Revoke selected API keys")
    def revoke_keys(self, request, queryset):
        actor = request.user.get_username()
        reason = f"admin_revoked:{actor}"[:255]
        revoked = sum(1 for key in queryset if key.revoke(reason, actor=actor))
        already = queryset.count() - revoked
        message = f"Revoked {revoked} API key(s)."
        if already:
            message = f"{message} {already} was already revoked and is unchanged."
        self.message_user(request, message, messages.SUCCESS)

    @admin.action(description="Generate replacement key for selected API keys")
    def generate_replacement_keys(self, request, queryset):
        """Issue a fresh key for the same profile as each selection.

        The original is left alone: this hands over a new secret without
        breaking a running client, and whoever redeploys revokes the old key
        afterwards. Timed rotation with an automatic tail is C5.
        """

        if not request.user.is_superuser:
            self.message_user(request, "Only a superuser can issue API keys.", messages.ERROR)
            return

        for key in queryset.select_related("profile"):
            replacement, raw = self._issue_key(
                request,
                profile=key.profile,
                name=key.name,
                # A no-expiry key is replaced by a no-expiry key; anything else
                # starts a fresh default lifetime.
                expires_at=None if key.expires_at is None else default_expires_at(),
                replaces=key,
            )
            self._show_raw_key(request, replacement, raw)

    def _issue_key(self, request, profile, name, expires_at, replaces=None):
        return APIKey.issue(
            profile=profile,
            name=name,
            expires_at=expires_at,
            actor=request.user.get_username(),
            replaces=replaces,
        )

    def _show_raw_key(self, request, key, raw):
        # The only time the secret is ever readable. It reaches the browser
        # through the messages framework (cookie, falling back to the session)
        # for exactly one response, which is the same exposure as rendering it
        # in the page, and nothing stores it.
        self.message_user(
            request,
            format_html(
                "API key <strong>{}</strong> issued for {}. Copy it now: it is not "
                "stored and cannot be shown again.<br><code>{}</code>",
                key.name,
                key.profile,
                raw,
            ),
            messages.SUCCESS,
        )

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        # The raw key exists only for this request, and this is the one place
        # it is ever readable.
        obj.key_id, obj.secret_hash, raw = generate_api_key()
        super().save_model(request, obj, form, change)
        log_key_created(obj, request.user.get_username())
        self._show_raw_key(request, obj, raw)


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
    list_display = (
        "first_name",
        "last_name",
        "linked_email",
        "project_count",
        "has_collect_state",
        "has_explore_state",
    )
    search_fields = ["first_name", "last_name", "email"]

    @admin.display(description="Email", ordering="email")
    def linked_email(self, obj):
        return format_html(f'<a href="mailto:{obj.email}">{obj.email}</a>')

    @admin.display(description="Project membership count", ordering="projects__count")
    def project_count(self, obj):
        return obj.projects__count

    @admin.display(description="Has Collect State", boolean=True)
    def has_collect_state(self, obj):
        return bool(obj.collect_state)

    @admin.display(description="Has Explore State", boolean=True)
    def has_explore_state(self, obj):
        return bool(obj.explore_state)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(Count("projects"))
        return qs


class UserMERMAIDFeatureInline(admin.TabularInline):
    model = UserMERMAIDFeature
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "profile":
            kwargs["queryset"] = Profile.objects.order_by("last_name", "first_name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(MERMAIDFeature)
class MermaidFeatureAdmin(BaseAdmin):
    list_display = ("id", "label", "enabled")
    list_display_links = ("id", "label")
    inlines = [UserMERMAIDFeatureInline]


def get_crs_with_attrib(query, attrib_val):
    cr_filter = {query: [attrib_val]}
    return CollectRecord.objects.filter(**cr_filter).select_related("project")


def get_sus_with_attrib(model_su, query, attrib_id):
    su_filter = {query: attrib_id}
    return model_su.objects.filter(**su_filter).select_related(model_su.project_lookup).distinct()


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

            # Annotations that reference this attribute directly
            annotation_qs = Annotation.objects.filter(benthic_attribute_id=object_id)
            annotation_count = annotation_qs.count()
            if annotation_count > 0:
                atleast_one_su = True
                extra_context.update({"annotation_count": annotation_count})

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

                with transaction.atomic():
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

                    if replacement_obj:
                        annotation_qs.update(benthic_attribute_id=replacement_obj)

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
