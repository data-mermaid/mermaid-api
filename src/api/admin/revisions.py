from django.contrib import admin

from ..models import Revision


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "project_id",
        "table_name",
        "record_id",
        "profile_id",
        "revision_num",
        "updated_on",
        "deleted",
    )
    list_display = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
