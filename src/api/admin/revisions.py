from django.contrib import admin

from ..models import RecordRevision, TableRevision


@admin.register(RecordRevision)
class RecordRevisionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "project_id",
        "profile_id",
        "updated_on",
        "table_name",
        "record_id",
        "deleted",
    )
    list_display = (
        "project_id",
        "table_name",
        "record_id",
        "rev_id",
        "updated_on",
        "deleted",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TableRevision)
class TableRevisionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "last_rev_id",
        "project_id",
        "table_name",
        "updated_on",
    )
    list_display = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
