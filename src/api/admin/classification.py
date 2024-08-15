from django.contrib import admin
from nested_admin import NestedTabularInline

from ..admin import BaseAdmin
from ..models.classification import (
    ClassificationStatus,
    Classifier,
    Image,
    Label,
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


@admin.register(Label)
class LabelAdmin(BaseAdmin):
    list_display = [
        "label_id",
        "label_name",
        "benthic_attribute_id",
        "benthic_attribute",
        "growth_form_id",
        "growth_form",
    ]
    readonly_fields = ["created_by", "updated_by"]

    @admin.display(description="label id", ordering="id")
    def label_id(self, obj):
        return obj.pk

    @admin.display(description="label name", ordering="name")
    def label_name(self, obj):
        return obj.name


@admin.register(LabelMapping)
class LabelMappingAdmin(BaseAdmin):
    list_display = ["label", "ba_id", "gf_id", "provider", "provider_label", "provider_id"]
    readonly_fields = ["created_by", "updated_by"]
    list_filter = ["provider"]
    search_fields = [
        "label__benthic_attribute__name",
        "label__growth_form__name",
        "provider_label",
        "provider_id",
    ]
    ordering = ["label", "provider", "provider_label", "provider_id"]

    @admin.display(description="BA id", ordering="label__benthic_attribute_id")
    def ba_id(self, obj):
        return obj.label.benthic_attribute_id

    @admin.display(description="GF id", ordering="label__growth_form_id")
    def gf_id(self, obj):
        return obj.label.growth_form_id


@admin.register(ClassificationStatus)
class ClassificationStatusAdmin(BaseAdmin):
    readonly_fields = ["created_on", "created_by"]
    ordering = ["created_on", "image__name"]
