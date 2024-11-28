from django.contrib import admin

from api.admin import BaseAdmin
from .models import UserMetrics


@admin.register(UserMetrics)
class UserMetricsAdmin(BaseAdmin):
    list_per_page = 50
    list_display = (
        "date",
        "project_name",
        "name",
        "num_submitted",
        "num_summary_views",
        "num_project_calls",
        "num_image_uploads",
    )
    ordering = ("-date", "project_name", "first_name", "last_name")
    list_filter = ("date", "project_name")
    search_fields = ("project_name", "first_name", "last_name")
    readonly_fields = [field.name for field in UserMetrics._meta.fields]

    def name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
