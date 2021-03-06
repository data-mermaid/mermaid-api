import django_filters
from rest_framework import serializers
from .base import BaseAPIFilterSet, BaseProjectApiViewSet, BaseAPISerializer
from ..models import BenthicPIT


class BenthicPITSerializer(BaseAPISerializer):
    interval_size = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval size is required"},
    )

    interval_start = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        coerce_to_string=False,
        error_messages={"null": "Interval start is required"},
    )

    class Meta:
        model = BenthicPIT
        exclude = []


class BenthicPITFilterSet(BaseAPIFilterSet):
    interval_size = django_filters.RangeFilter(field_name="interval_size")
    interval_start = django_filters.RangeFilter(field_name="interval_start")

    class Meta:
        model = BenthicPIT
        fields = [
            "transect",
            "transect__sample_event",
            "interval_size",
            "interval_start",
        ]


class BenthicPITViewSet(BaseProjectApiViewSet):
    serializer_class = BenthicPITSerializer
    queryset = BenthicPIT.objects.all()
    filter_class = BenthicPITFilterSet
