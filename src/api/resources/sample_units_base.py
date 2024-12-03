import django_filters
from rest_framework import serializers

from .base import (
    BaseAPIFilterSet,
    BaseAPISerializer,
    ExtendedSerializer,
    ModelNameReadOnlyField,
)


class SampleUnitExtendedSerializer(ExtendedSerializer):
    visibility = ModelNameReadOnlyField()
    relative_depth = ModelNameReadOnlyField()
    tide = ModelNameReadOnlyField()
    current = ModelNameReadOnlyField()


class SampleUnitSerializer(BaseAPISerializer):
    depth = serializers.DecimalField(
        max_digits=3,
        decimal_places=1,
        coerce_to_string=False,
        min_value=0,
        max_value=40,
        error_messages={"null": "Depth is required"},
    )

    extra_kwargs = {}


class SampleUnitFilterSet(BaseAPIFilterSet):
    depth = django_filters.RangeFilter(field_name="depth")

    fields = ["depth", "sample_time", "visibility", "current", "relative_depth", "tide"]
