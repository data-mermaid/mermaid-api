from django.contrib import admin
from nested_admin import NestedTabularInline

from ..admin import BaseAdmin
from ..models.classification import ClassificationStatus, Classifier, Image, Label, Point


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
    readonly_fields = ["created_by", "updated_by"]


@admin.register(ClassificationStatus)
class ClassificationStatusAdmin(BaseAdmin):
    readonly_fields = ["created_on", "created_by"]
