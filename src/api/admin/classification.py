import unicodedata

from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from nested_admin import NestedTabularInline

from ..admin import BaseAdmin
from ..models.classification import (
    BenthicAttributeGrowthForm,
    ClassificationStatus,
    Classifier,
    Image,
    LabelMapping,
    Point,
)
from ..models.mermaid import BenthicAttribute, GrowthForm


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


@admin.register(BenthicAttributeGrowthForm)
class BenthicAttributeGrowthFormAdmin(BaseAdmin):
    list_display = [
        "benthic_attribute_id",
        "benthic_attribute",
        "growth_form_id",
        "growth_form",
    ]


@admin.register(Classifier)
class ClassifierAdmin(BaseAdmin):
    list_display = ["version", "name", "patch_size", "num_points"]
    readonly_fields = ["created_by", "updated_by"]


class LabelMappingResource(resources.ModelResource):
    benthic_attribute = fields.Field(
        column_name="benthic_attribute_id",
        attribute="benthic_attribute",
        widget=ForeignKeyWidget(BenthicAttribute, field="id"),
    )
    growth_form = fields.Field(
        column_name="growth_form_id",
        attribute="growth_form",
        widget=ForeignKeyWidget(GrowthForm, field="id"),
    )
    benthic_attribute_name = fields.Field(
        column_name="benthic_attribute_name",
        attribute="benthic_attribute__name",
        readonly=True,
    )
    growth_form_name = fields.Field(
        column_name="growth_form_name",
        attribute="growth_form__name",
        readonly=True,
    )

    class Meta:
        model = LabelMapping
        import_id_fields = ["provider", "provider_id"]
        fields = [
            "provider",
            "provider_id",
            "provider_label",
            "benthic_attribute",
            "benthic_attribute_name",
            "growth_form",
            "growth_form_name",
        ]
        skip_unchanged = True
        use_transactions = True

    def before_import_row(self, row, **kwargs):
        label = row.get("provider_label") or ""
        normalized = " ".join(unicodedata.normalize("NFKC", label).split())
        if not normalized:
            raise ValueError(
                f"provider_label is required (provider={row.get('provider')!r}, provider_id={row.get('provider_id')!r})"
            )
        row["provider_label"] = normalized


@admin.register(LabelMapping)
class LabelMappingAdmin(ImportExportModelAdmin, BaseAdmin):
    resource_classes = [LabelMappingResource]
    list_display = ["benthic_attribute", "growth_form", "provider", "provider_label", "provider_id"]
    readonly_fields = ["created_by", "updated_by"]
    list_filter = ["provider"]
    search_fields = [
        "benthic_attribute__name",
        "growth_form__name",
        "provider_label",
        "provider_id",
    ]
    ordering = [
        "benthic_attribute__name",
        "growth_form__name",
        "provider",
        "provider_label",
        "provider_id",
    ]


@admin.register(ClassificationStatus)
class ClassificationStatusAdmin(BaseAdmin):
    readonly_fields = ["created_on", "created_by"]
    ordering = ["created_on", "image__name"]
