from django.contrib import admin
from nested_admin import NestedTabularInline

from ..admin import BaseAdmin
from ..models.classification import (
    ClassificationStatus,
    Classifier,
    Image,
    LabelMapping,
    Point,
)


class PointInline(NestedTabularInline):
    model = Point
    extra = 0
    readonly_fields = ["created_by", "updated_by"]


@admin.register(Image)
class ImageAdmin(BaseAdmin):
    inlines = [PointInline]
    readonly_fields = [
        "thumbnail",
        "photo_timestamp",
        "name",
        "data",
        "created_by",
        "updated_by",
    ]


@admin.register(Classifier)
class ClassifierAdmin(BaseAdmin):
    readonly_fields = ["created_by", "updated_by"]


@admin.register(LabelMapping)
class LabelMappingAdmin(BaseAdmin):
    list_display = ["benthic_attribute", "growth_form", "provider", "provider_label", "provider_id"]
    readonly_fields = ["created_by", "updated_by"]
    list_filter = ["provider"]
    search_fields = [
        "benthic_attribute__name",
        "growth_form__name",
        "provider_label",
        "provider_id",
    ]
    ordering = ["provider", "provider_label", "provider_id"]


@admin.register(ClassificationStatus)
class ClassificationStatusAdmin(BaseAdmin):
    readonly_fields = ["created_on", "created_by"]
    ordering = ["created_on", "image__name"]
