from django.contrib import admin

from ..models import RecordRevision, TableRevision


@admin.register(RecordRevision)
class RecordRevisionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "project_id",
        "table_name",
        "record_id",
        "profile_id",
        "rev_id",
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


@admin.register(TableRevision)
class TableRevisionAdmin(admin.ModelAdmin):
    actions = None
    list_display = (
        "get_rev_id",
        "get_project_id",
        "get_table_name",
        "get_updated_on",
    )

    def get_rev_id(self, obj):
        return obj.last_revision.rev_id

    def get_project_id(self, obj):
        return obj.last_revision.project_id

    def get_table_name(self, obj):
        return obj.last_revision.table_name

    def get_updated_on(self, obj):
        return obj.last_revision.updated_on

    get_rev_id.short_description = "rev_id"
    get_project_id.short_description = "project_id"
    get_table_name.short_description = "table_name"
    get_updated_on.short_description = "updated_on"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = None
