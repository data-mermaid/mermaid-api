import csv
import datetime
from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.http import HttpResponse

from ..models.base import *


def lookup_field_from_choices(field_obj, value):
    choices = getattr(field_obj, 'choices')
    if choices is not None and len(choices) > 0:
        choices_dict = dict(choices)
        try:
            value = choices_dict[value]
        except KeyError:
            pass

    return value


def export_model_as_csv(modeladmin, request, queryset, field_list):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s-%s-export_%s.csv' % (
        __package__.lower(),
        queryset.model.__name__.lower(),
        datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
    )

    writer = csv.writer(response)
    writer.writerow(
        [admin.utils.label_for_field(f, queryset.model, modeladmin) for f in field_list],
    )

    for obj in queryset:
        csv_line_values = []
        for field in field_list:
            field_obj, attr, value = admin.utils.lookup_field(field, obj, modeladmin)
            if field_obj is not None and hasattr(field_obj, 'choices'):
                value = lookup_field_from_choices(field_obj, value)
            csv_line_values.append(str(value).strip())

        writer.writerow(csv_line_values)

    return response


def export_model_display_as_csv(modeladmin, request, queryset):
    if hasattr(modeladmin, 'exportable_fields'):
        field_list = modeladmin.exportable_fields
    else:
        field_list = list(modeladmin.list_display[:])
        if 'action_checkbox' in field_list:
            field_list.remove('action_checkbox')

    return export_model_as_csv(modeladmin, request, queryset, field_list)


def export_model_all_as_csv(modeladmin, request, queryset):
    field_list = [
        f.name for f in queryset.model._meta.get_fields()
        if f.concrete and (
                not f.is_relation
                or f.one_to_one
                or (f.many_to_one and f.related_model)
        )
    ]
    if hasattr(modeladmin, 'exportable_fields'):
        added_fields = [f for f in modeladmin.exportable_fields if f not in field_list]
        field_list = field_list + added_fields

    return export_model_as_csv(modeladmin, request, queryset, field_list)


export_model_display_as_csv.short_description = 'Export selected %(verbose_name_plural)s to CSV (display)'
export_model_all_as_csv.short_description = 'Export selected %(verbose_name_plural)s to CSV (all fields)'


class BaseAdmin(OSMGeoAdmin):
    actions = (export_model_display_as_csv, export_model_all_as_csv, )


@admin.register(Application)
class ApplicationAdmin(BaseAdmin):
    pass


@admin.register(AuthUser)
class AuthUserAdmin(BaseAdmin):
    search_fields = ['user_id', 'profile__first_name', 'profile__last_name', 'profile__email', ]


@admin.register(Profile)
class ProfileAdmin(BaseAdmin):
    list_display = ('first_name', 'last_name', 'email')
    search_fields = ['first_name', 'last_name', 'email', ]


@admin.register(AppVersion)
class AppVersionAdmin(BaseAdmin):
    list_display = ('application', 'version',)
