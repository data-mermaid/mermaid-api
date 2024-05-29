from django.contrib import admin
from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline

from ..models.gfcr import (  # noqa: F401
    GFCRFinanceSolution,
    GFCRIndicatorSet,
    GFCRInvestmentSource,
    GFCRRevenue,
)


class GFCRInvestmentSourceInline(NestedTabularInline):
    model = GFCRInvestmentSource
    readonly_fields = ["created_by", "updated_by"]


class GFCRRevenueInline(NestedTabularInline):
    model = GFCRRevenue
    readonly_fields = ["created_by", "updated_by"]


class GFCRFinanceSolutionInline(NestedStackedInline):
    model = GFCRFinanceSolution
    extra = 0
    readonly_fields = ["created_by", "updated_by"]

    inlines = [GFCRInvestmentSourceInline, GFCRRevenueInline]


@admin.register(GFCRIndicatorSet)
class GFCRIndicatorSetAdmin(NestedModelAdmin):
    list_display = ("identifier", "report_date")
    readonly_fields = ["created_by", "updated_by"]

    inlines = [GFCRFinanceSolutionInline]
    search_fields = ["project__name", "title", "pk", "project_id"]

    def identifier(self, obj):
        return f"{obj.project.name} - {obj.title}"
