from django.contrib import admin

from ..models import SummaryCacheQueue


@admin.register(SummaryCacheQueue)
class SummaryCacheQueueAdmin(admin.ModelAdmin):
    readonly_fields = (
        "project_id",
        "created_on",
    )
    list_display = (
        "project_id",
        "processing",
        "attempts",
        "created_on",
    )
